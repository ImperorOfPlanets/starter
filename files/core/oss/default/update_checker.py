"""
МОДУЛЬ ЕЖЕДНЕВНОЙ ПРОВЕРКИ ОБНОВЛЕНИЙ
Фоновая проверка GitFlic репозиториев раз в сутки
"""
import subprocess
import threading
import time
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from files.core.base_module import BaseModule
from files.core.utils.globalVars_utils import get_global, set_global
from files.core.utils.log_utils import LogManager

logger = LogManager.get_logger('update_checker')

CHECK_STATE_FILE = 'update_check_state.json'
CHECK_INTERVAL_SECONDS = 86400  # 24 часа


class UpdateCheckerModule(BaseModule):
    """Фоновая ежедневная проверка обновлений из GitFlic"""

    _check_thread: Optional[threading.Thread] = None
    _stop_event = threading.Event()
    _state: Dict = {}
    _lock = threading.Lock()

    @staticmethod
    def check() -> bool:
        return True

    @staticmethod
    def set_globals():
        pass

    @staticmethod
    def _get_state_path() -> Path:
        starter_path = get_global('starter_path')
        return Path(starter_path) / 'files' / CHECK_STATE_FILE

    @staticmethod
    def _load_state() -> Dict:
        path = UpdateCheckerModule._get_state_path()
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {'last_check': None, 'projects': {}}

    @staticmethod
    def _save_state(state: Dict):
        path = UpdateCheckerModule._get_state_path()
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Ошибка сохранения состояния проверки: {e}")

    @staticmethod
    def get_remote_last_commit(repo_url: str, branch: str = 'main', credentials: str = '', auth_type: str = '') -> Optional[str]:
        """Получает последний commit hash из удалённого репозитория"""
        from files.core.software.default.git_service import GitService
        return GitService.get_remote_commit(repo_url, branch, credentials, auth_type)

    @staticmethod
    def get_local_last_commit(project_path: str) -> Optional[str]:
        """Получает последний commit hash из локального репозитория"""
        from files.core.software.default.git_service import GitService
        return GitService.get_local_commit(project_path)

    @staticmethod
    def check_project_updates(project_type: str, repo_url: str, branch: str,
                               project_path: str = None, credentials: str = '', auth_type: str = '') -> Dict:
        """Проверяет обновления для одного проекта"""
        state = UpdateCheckerModule._load_state()
        project_state = state.get('projects', {}).get(project_type, {})

        remote_commit = UpdateCheckerModule.get_remote_last_commit(repo_url, branch, credentials, auth_type)

        if not remote_commit:
            return {
                'project_type': project_type,
                'status': 'error',
                'has_update': False,
                'message': 'Не удалось получить данные из репозитория'
            }

        local_commit = None
        if project_path:
            local_commit = UpdateCheckerModule.get_local_last_commit(project_path)

        last_known_remote = project_state.get('remote_commit')

        has_update = False
        if local_commit and remote_commit:
            has_update = local_commit != remote_commit
        elif last_known_remote and remote_commit:
            has_update = last_known_remote != remote_commit
        elif not local_commit and not last_known_remote:
            has_update = False

        with UpdateCheckerModule._lock:
            if 'projects' not in state:
                state['projects'] = {}
            state['projects'][project_type] = {
                'remote_commit': remote_commit,
                'local_commit': local_commit,
                'last_check': datetime.now().isoformat(),
                'has_update': has_update
            }
            state['last_check'] = datetime.now().isoformat()
            UpdateCheckerModule._save_state(state)

        return {
            'project_type': project_type,
            'status': 'ok',
            'has_update': has_update,
            'remote_commit': remote_commit[:12] if remote_commit else None,
            'local_commit': local_commit[:12] if local_commit else None,
            'checked_at': datetime.now().isoformat()
        }

    @staticmethod
    def check_all_installed_projects() -> List[Dict]:
        """Проверяет обновления для ВСЕХ установленных проектов"""
        from files.configs.server_types import SERVER_TYPES
        from files.core.oss.default.registry import RegistryModule

        results = []
        registry = RegistryModule.load_registry()
        installed_paths = {Path(p['path']).name: p['path'] for p in registry.get('projects', [])}

        for server_type, server_info in SERVER_TYPES.items():
            repo = server_info.get('repository', {})
            if not repo:
                continue

            repo_url = repo.get('url', '')
            branch = repo.get('branch', 'main')

            project_path = installed_paths.get(server_type)
            if not project_path:
                for name, path in installed_paths.items():
                    if server_type in name or name in server_type:
                        project_path = path
                        break

            result = UpdateCheckerModule.check_project_updates(
                project_type=server_type,
                repo_url=repo_url,
                branch=branch,
                project_path=project_path
            )
            result['name'] = server_info.get('name', server_type)
            result['description'] = server_info.get('description', '')
            results.append(result)

        return results

    @staticmethod
    def get_all_updates_status() -> Dict:
        """Возвращает статус всех проверок"""
        state = UpdateCheckerModule._load_state()
        last_check = state.get('last_check')
        projects = state.get('projects', {})

        has_any_update = any(p.get('has_update', False) for p in projects.values())

        return {
            'last_check': last_check,
            'has_any_update': has_any_update,
            'projects': projects,
            'next_check': (
                datetime.fromisoformat(last_check) + timedelta(seconds=CHECK_INTERVAL_SECONDS)
            ).isoformat() if last_check else None
        }

    @staticmethod
    def _check_loop():
        """Фоновый цикл проверки"""
        logger.info("Фоновая проверка обновлений запущена")
        while not UpdateCheckerModule._stop_event.is_set():
            try:
                state = UpdateCheckerModule._load_state()
                last_check = state.get('last_check')

                should_check = True
                if last_check:
                    try:
                        last_dt = datetime.fromisoformat(last_check)
                        if (datetime.now() - last_dt).total_seconds() < CHECK_INTERVAL_SECONDS:
                            should_check = False
                    except Exception:
                        pass

                if should_check:
                    logger.info("Запуск ежедневной проверки обновлений...")
                    results = UpdateCheckerModule.check_all_installed_projects()
                    updates_found = [r for r in results if r.get('has_update')]
                    if updates_found:
                        logger.info(f"Найдены обновления: {[r['project_type'] for r in updates_found]}")
                        set_global('updates_available', True)
                        set_global('updates_list', updates_found)
                    else:
                        logger.info("Обновлений не найдено")
                        set_global('updates_available', False)
                        set_global('updates_list', [])

            except Exception as e:
                logger.error(f"Ошибка в фоновой проверке: {e}")

            UpdateCheckerModule._stop_event.wait(CHECK_INTERVAL_SECONDS)

    @staticmethod
    def start_background_checker():
        """Запускает фоновую проверку"""
        if UpdateCheckerModule._check_thread and UpdateCheckerModule._check_thread.is_alive():
            logger.info("Фоновая проверка уже запущена")
            return

        UpdateCheckerModule._stop_event.clear()
        UpdateCheckerModule._check_thread = threading.Thread(
            target=UpdateCheckerModule._check_loop,
            daemon=True,
            name='update-checker'
        )
        UpdateCheckerModule._check_thread.start()
        logger.info("Фоновая проверка обновлений инициирована")

    @staticmethod
    def stop_background_checker():
        """Останавливает фоновую проверку"""
        UpdateCheckerModule._stop_event.set()
        if UpdateCheckerModule._check_thread:
            UpdateCheckerModule._check_thread.join(timeout=5)
        logger.info("Фоновая проверка обновлений остановлена")

    @staticmethod
    def force_check_now() -> List[Dict]:
        """Принудительная немедленная проверка"""
        state = UpdateCheckerModule._load_state()
        state['last_check'] = None
        UpdateCheckerModule._save_state(state)

        results = UpdateCheckerModule.check_all_installed_projects()
        updates_found = [r for r in results if r.get('has_update')]
        set_global('updates_available', len(updates_found) > 0)
        set_global('updates_list', updates_found)
        return results
