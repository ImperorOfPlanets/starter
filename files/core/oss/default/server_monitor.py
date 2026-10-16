# files/core/oss/default/server_monitor.py
"""
ФОНДОВЫЙ МОНИТОРИНГ СТАТУСОВ СЕРВЕРОВ (SQLite-кеш)

Раньше каждый запрос списка серверов синхронно для каждого проекта
запускал docker compose ps и даже git fetch (сеть) — страница
«Серверы» грузилась десятки секунд.

Модуль опрашивает реестр в фоне:
- docker-статус — каждые status_interval секунд (настройка);
- git fetch (проверка обновлений) — каждые git_interval секунд
  (сеть, дорого; тоже настройка);
и пишет результат в SQLite (files/server_status.db). Панель читает
кеш мгновенно и показывает в шапке время последнего обновления;
force-обновление лишь будит фоновый опрос.

Интервалы хранятся в files/server_monitor.json и меняются без
рестарта — фоновый цикл перечитывает настройки каждый проход.
"""
import json
import sqlite3
import subprocess
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional

from files.core.base_module import BaseModule
from files.core.utils.globalVars_utils import get_global
from files.core.utils.log_utils import LogManager

logger = LogManager.get_logger('server_monitor')

DB_FILE = 'server_status.db'
CONFIG_FILE = 'server_monitor.json'

# Дефолты и границы настроек (секунды)
# status_interval — фолбэк; эффективный интервал задаёт расписание задачи
# server_status_refresh в планировщике (настройка в интерфейсе панели)
DEFAULTS = {'status_interval': 30, 'git_interval': 600}
LIMITS = {
    'status_interval': (5, 86400),    # docker-статус
    'git_interval': (30, 604800),     # git fetch (сеть)
}

_SCHEMA = """
CREATE TABLE IF NOT EXISTS servers (
    path TEXT PRIMARY KEY,
    name TEXT DEFAULT '',
    type TEXT DEFAULT 'unknown',
    status TEXT DEFAULT 'unknown',
    port INTEGER DEFAULT 0,
    subnet_octet INTEGER DEFAULT 0,
    has_web_interface INTEGER DEFAULT 0,
    has_git INTEGER DEFAULT 0,
    has_update INTEGER DEFAULT 0,
    updated_at REAL DEFAULT 0,
    git_checked_at REAL DEFAULT 0
)
"""


def _bg_refresh():
    """Фоновое обновление кеша (для refresh_all(background=True))."""
    if not ServerMonitorModule._refresh_lock.acquire(blocking=False):
        return
    try:
        ServerMonitorModule._refresh_all_now()
    except Exception as e:
        logger.error(f"server_monitor: ошибка фонового обновления: {e}")
    finally:
        ServerMonitorModule._refresh_lock.release()


class ServerMonitorModule(BaseModule):
    """Кеш статусов серверов в SQLite; периодический опрос — планировщик."""

    _refresh_lock = threading.Lock()

    @staticmethod
    def check() -> bool:
        return True

    @staticmethod
    def set_globals():
        pass

    # ===== Настройки =====

    @staticmethod
    def _config_path() -> Path:
        starter_path = get_global('starter_path')
        return Path(starter_path) / 'files' / CONFIG_FILE

    @staticmethod
    def get_settings() -> Dict:
        """Настройки монитора: интервалы опроса (сек) с дефолтами и границами"""
        cfg = {}
        try:
            p = ServerMonitorModule._config_path()
            if p.exists():
                cfg = json.loads(p.read_text(encoding='utf-8'))
        except Exception as e:
            logger.warning(f"server_monitor: конфиг не прочитан: {e}")

        result = {}
        for key, default in DEFAULTS.items():
            try:
                value = int(cfg.get(key, default))
            except (TypeError, ValueError):
                value = default
            lo, hi = LIMITS[key]
            result[key] = max(lo, min(hi, value))
        return result

    @staticmethod
    def save_settings(data: Dict) -> Dict:
        """Сохраняет настройки монитора (интервалы валидируются по границам)"""
        current = ServerMonitorModule.get_settings()
        updated = {}
        for key, default in DEFAULTS.items():
            if key in data and data.get(key) is not None:
                try:
                    value = int(data.get(key))
                except (TypeError, ValueError):
                    value = current[key]
                lo, hi = LIMITS[key]
                value = max(lo, min(hi, value))
            else:
                value = current[key]
            updated[key] = value

        p = ServerMonitorModule._config_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(updated, indent=2), encoding='utf-8')
        logger.info(f"server_monitor: настройки сохранены: {updated}")
        return updated

    @staticmethod
    def get_status() -> Dict:
        """Состояние кеша: время последнего обновления, интервалы, размер"""
        settings = ServerMonitorModule.get_settings()
        try:
            from files.core.oss.default.scheduler import SchedulerModule
            monitor_running = SchedulerModule.is_running()
        except Exception:
            monitor_running = False
        info = {
            'status_interval': settings['status_interval'],
            'git_interval': settings['git_interval'],
            'updated_at': None,       # последний проход docker-статусов
            'git_checked_at': None,   # последний git fetch
            'servers_count': 0,
            'monitor_running': monitor_running,
        }
        try:
            conn = ServerMonitorModule._connect()
            try:
                r = conn.execute(
                    'SELECT MAX(updated_at) AS u, MAX(git_checked_at) AS g,'
                    ' COUNT(*) AS c FROM servers').fetchone()
                info['updated_at'] = r['u']
                info['git_checked_at'] = r['g']
                info['servers_count'] = r['c'] or 0
            finally:
                conn.close()
        except Exception as e:
            logger.warning(f"server_monitor: статус недоступен: {e}")
        return info

    # ===== SQLite =====

    @staticmethod
    def _db_path() -> Path:
        starter_path = get_global('starter_path')
        return Path(starter_path) / 'files' / DB_FILE

    @staticmethod
    def _connect() -> sqlite3.Connection:
        db = ServerMonitorModule._db_path()
        db.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db), timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA busy_timeout=5000')
        conn.execute(_SCHEMA)
        conn.commit()
        return conn

    @staticmethod
    def _row_to_dict(r: sqlite3.Row) -> Dict:
        """Строка БД → dict в форме, которую ждёт панель (см. _get_user_servers)."""
        return {
            'id': r['path'],
            'name': r['name'],
            'path': r['path'],
            'type': r['type'],
            'status': r['status'],
            'port': r['port'],
            'subnet_octet': r['subnet_octet'],
            'has_web_interface': bool(r['has_web_interface']),
            'has_git': bool(r['has_git']),
            'has_update': bool(r['has_update']),
        }

    @staticmethod
    def get_cached_servers() -> Optional[List[Dict]]:
        """Мгновенное чтение кеша. None — кещ ещё не наполнен."""
        try:
            conn = ServerMonitorModule._connect()
            try:
                rows = conn.execute('SELECT * FROM servers ORDER BY name').fetchall()
            finally:
                conn.close()
        except Exception as e:
            logger.warning(f"server_monitor: кеш недоступен: {e}")
            return None
        if not rows:
            return None
        return [ServerMonitorModule._row_to_dict(r) for r in rows]

    @staticmethod
    def _load_cached_rows() -> Dict[str, sqlite3.Row]:
        conn = ServerMonitorModule._connect()
        try:
            return {r['path']: r for r in conn.execute('SELECT * FROM servers').fetchall()}
        finally:
            conn.close()

    @staticmethod
    def _upsert(row: Dict):
        conn = ServerMonitorModule._connect()
        try:
            conn.execute(
                'INSERT OR REPLACE INTO servers '
                '(path, name, type, status, port, subnet_octet, has_web_interface,'
                ' has_git, has_update, updated_at, git_checked_at)'
                ' VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                (row['path'], row['name'], row['type'], row['status'], row['port'],
                 row['subnet_octet'], row['has_web_interface'], row['has_git'],
                 row['has_update'], row['updated_at'], row['git_checked_at'])
            )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def forget_path(path: str):
        """Удаляет запись сервера из кеша (после удаления сервера)."""
        try:
            conn = ServerMonitorModule._connect()
            try:
                conn.execute('DELETE FROM servers WHERE path = ?', (path,))
                conn.commit()
            finally:
                conn.close()
        except Exception as e:
            logger.warning(f"server_monitor: forget {path} failed: {e}")

    # ===== Опрос =====

    @staticmethod
    def _git_has_update(git_path: Path, kw) -> Optional[bool]:
        """fetch + сравнение локального и удалённого HEAD.

        None — не удалось проверить (не менять сохранённое значение).
        """
        try:
            subprocess.run(['git', 'fetch', '--quiet'], cwd=str(git_path), **kw)
            local = subprocess.run(
                ['git', 'rev-parse', 'HEAD'], cwd=str(git_path), **kw).stdout.strip()
            remote = subprocess.run(
                ['git', 'rev-parse', '@{u}'], cwd=str(git_path), **kw).stdout.strip()
            if not remote:
                return False
            return local != remote
        except Exception:
            return None

    @staticmethod
    def _probe_and_store(project: Dict, prev_row=None, force_git: bool = False) -> Dict:
        """Опрашивает один проект реестра и сохраняет строку в кеш."""
        from files.web.sections.servers import (
            _check_server_status, _project_files_exist, _server_port, _subprocess_kwargs)
        from files.configs.server_types import SERVER_TYPES

        path = project.get('path', '')
        ptype = project.get('project_type', 'unknown')
        type_info = SERVER_TYPES.get(ptype, {})

        if not _project_files_exist(path):
            status = 'missing_files'
        else:
            status = _check_server_status(path, ptype)

        port = _server_port(path, project.get('port', 0))

        # git: .git может лежать в code/ (Laravel) или в корне (repo_root)
        git_path = Path(path) / 'src'
        if not (git_path / '.git').exists() and (Path(path) / '.git').exists():
            git_path = Path(path)
        has_git = (git_path / '.git').exists()

        now = time.time()
        has_update = bool(prev_row['has_update']) if prev_row else False
        git_checked_at = float(prev_row['git_checked_at']) if prev_row else 0.0

        # fetch — сетевой и медленный: только по git_interval или по запросу
        if has_git and (force_git or (now - git_checked_at) > ServerMonitorModule.get_settings()['git_interval']):
            kw = _subprocess_kwargs(10)
            result = ServerMonitorModule._git_has_update(git_path, kw)
            if result is not None:
                has_update = result
                git_checked_at = now

        row = {
            'path': path,
            'name': path.replace('\\', '/').rstrip('/').split('/')[-1] or path,
            'type': ptype,
            'status': status,
            'port': int(port or 0),
            'subnet_octet': int(project.get('subnet_octet', 0) or 0),
            'has_web_interface': 1 if type_info.get('has_web_interface') else 0,
            'has_git': 1 if has_git else 0,
            'has_update': 1 if has_update else 0,
            'updated_at': now,
            'git_checked_at': git_checked_at,
        }
        ServerMonitorModule._upsert(row)

        # Реестр синхронизируем только при реальной смене статуса
        if not prev_row or prev_row['status'] != status:
            try:
                from files.core.oss.default.registry import RegistryModule
                RegistryModule.update_project_status(path, status)
            except Exception as e:
                logger.warning(f"server_monitor: реестр не обновлён для {path}: {e}")

        return row

    @staticmethod
    def _refresh_all_now():
        """Полный проход по реестру: docker-статусы, git — по TTL."""
        from files.core.oss.default.registry import RegistryModule

        data = RegistryModule.load_registry()
        projects = [p for p in data.get('projects', []) if p.get('installed_by_starter')]
        prev_rows = ServerMonitorModule._load_cached_rows()
        seen = set()

        for project in projects:
            path = project.get('path', '')
            if not path:
                continue
            seen.add(path)
            try:
                ServerMonitorModule._probe_and_store(project, prev_rows.get(path))
            except Exception as e:
                logger.error(f"server_monitor: ошибка опроса {path}: {e}")

        # Убираем записи проектов, которых больше нет в реестре
        try:
            conn = ServerMonitorModule._connect()
            try:
                stale = [r['path'] for r in conn.execute('SELECT path FROM servers').fetchall()
                         if r['path'] not in seen]
                if stale:
                    conn.executemany('DELETE FROM servers WHERE path = ?', [(p,) for p in stale])
                    conn.commit()
            finally:
                conn.close()
        except Exception as e:
            logger.warning(f"server_monitor: cleanup failed: {e}")

    # ===== Публичное API =====

    @staticmethod
    def refresh_all(background: bool = True) -> bool:
        """Обновить весь кеш. background=True — не блокировать вызывающего."""
        if background:
            if ServerMonitorModule._refresh_lock.locked():
                return False
            threading.Thread(target=_bg_refresh, daemon=True,
                             name='server-monitor-refresh').start()
            return True
        with ServerMonitorModule._refresh_lock:
            ServerMonitorModule._refresh_all_now()
        return True

    @staticmethod
    def refresh_path(path: str):
        """Быстрый перепровер одного сервера (после start/stop/install)."""
        try:
            from files.core.oss.default.registry import RegistryModule
            from files.web.sections.servers import _paths_equal

            data = RegistryModule.load_registry()
            project = None
            for p in data.get('projects', []):
                if p.get('path') and _paths_equal(p.get('path'), path):
                    project = p
                    break

            if project is None:
                ServerMonitorModule.forget_path(path)
                return

            prev = ServerMonitorModule._load_cached_rows().get(project.get('path', ''))
            ServerMonitorModule._probe_and_store(project, prev)
        except Exception as e:
            logger.error(f"server_monitor: refresh_path({path}) failed: {e}")

    # ===== Фоновый цикл =====
    # Периодический опрос выполняет планировщик (задача
    # server_status_refresh в files/tasks/custom/). Здесь только
    # разовые вызовы: refresh_all / refresh_path.

    @staticmethod
    def start_background_monitor():
        logger.info("server_monitor: периодический опрос выполняет планировщик "
                    "(задача server_status_refresh)")

    @staticmethod
    def stop_background_monitor():
        pass
