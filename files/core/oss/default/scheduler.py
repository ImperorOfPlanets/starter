# files/core/oss/default/scheduler.py
"""
Планировщик периодических задач
Задачи выполняются как отдельные процессы: python starter.py --task <name>
Это гарантирует что падение задачи не уронит стартер.
"""
import json
import os
import subprocess
import sys
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional

from files.core.base_module import BaseModule
from files.core.utils.globalVars_utils import get_global, set_global
from files.core.utils.log_utils import LogManager


def _si():
    """STARTUPINFO для скрытия окон на Windows"""
    if sys.platform != 'win32':
        return None
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = subprocess.SW_HIDE
    return si

logger = LogManager.get_logger('scheduler')

# Built-in task registry — here you register all available tasks
BUILTIN_TASKS = {
    'check_updates': {
        'name': 'check_updates',
        'description': {'ru': 'Проверка обновлений стартера', 'en': 'Check starter updates', 'cn': '检查启动器更新'},
        'module': 'updates',
        'func': 'check_updates',
        'default_enabled': True,
        'default_schedule': 'daily',
        'params': {},
        'category': 'system',
        'events': ['on_startup', 'on_schedule']
    },
    'check_service_status': {
        'name': 'check_service_status',
        'description': {'ru': 'Проверка статуса сервиса', 'en': 'Check service status', 'cn': '检查服务状态'},
        'module': 'service',
        'func': 'get_service_status',
        'default_enabled': True,
        'default_schedule': 'hourly',
        'params': {},
        'category': 'monitoring',
        'events': ['on_schedule']
    },
    'cleanup_logs': {
        'name': 'cleanup_logs',
        'description': {'ru': 'Очистка старых логов', 'en': 'Cleanup old logs', 'cn': '清理旧日志'},
        'module': None,
        'func': '_cleanup_logs_builtin',
        'default_enabled': True,
        'default_schedule': 'weekly',
        'params': {'max_days': 30},
        'category': 'maintenance',
        'events': ['on_schedule']
    },
    'check_ports': {
        'name': 'check_ports',
        'description': {'ru': 'Проверка занятых портов', 'en': 'Check occupied ports', 'cn': '检查占用端口'},
        'module': 'portmanager',
        'func': 'check_ports',
        'default_enabled': False,
        'default_schedule': 'daily',
        'params': {},
        'category': 'monitoring',
        'events': ['on_schedule']
    },
    'check_docker': {
        'name': 'check_docker',
        'description': {'ru': 'Проверка статуса Docker', 'en': 'Check Docker status', 'cn': '检查Docker状态'},
        'module': 'docker',
        'func': 'check_docker_installed',
        'default_enabled': False,
        'default_schedule': 'hourly',
        'params': {},
        'category': 'monitoring',
        'events': ['on_schedule']
    },
    'server_status_refresh': {
        'name': 'server_status_refresh',
        'description': {'ru': 'Обновление статусов серверов',
                        'en': 'Refresh server statuses',
                        'cn': '刷新服务器状态'},
        'module': None,
        'func': '_run_server_status_refresh',
        'default_enabled': True,
        'default_schedule': 'every_30sec',
        'params': {},
        'category': 'monitoring',
        # лёгкая задача в потоке: без спавна процесса, кеш в SQLite
        # обновляется напрямую (см. _launch_task)
        'in_process': True,
        'events': ['on_schedule']
    }
}


class SchedulerModule(BaseModule):
    """Планировщик периодических задач"""

    @staticmethod
    def check() -> bool:
        return True

    @staticmethod
    def set_globals():
        starter_path = get_global('starter_path')
        if starter_path:
            tasks_dir = os.path.join(str(starter_path), 'files', 'tasks')
            os.makedirs(tasks_dir, exist_ok=True)
            set_global('tasks_dir', tasks_dir)
            # Ensure tasks config exists
            config_path = os.path.join(tasks_dir, 'tasks.json')
            if not os.path.exists(config_path):
                SchedulerModule._create_default_config(config_path)
            else:
                # Задачи, добавленные в BUILTIN_TASKS после создания файла
                # (например server_status_refresh), без мержа не появлялись:
                # tasks.json создаётся один раз, и кеш статусов серверов
                # не обновлялся никогда.
                SchedulerModule._merge_missing_defaults(config_path)

    @staticmethod
    def get_active_sessions() -> list:
        """Получить список активных сессий (файлы, обновлённые за последние 5 минут)"""
        import time
        sessions_dir = get_global('starter_path')
        if not sessions_dir:
            return []
        sessions_path = os.path.join(str(sessions_dir), 'files', 'web', 'sessions')
        if not os.path.exists(sessions_path):
            return []

        now = time.time()
        active = []
        for fname in os.listdir(sessions_path):
            fpath = os.path.join(sessions_path, fname)
            try:
                mtime = os.path.getmtime(fpath)
                age_seconds = now - mtime
                if age_seconds < 300:  # 5 минут
                    active.append({
                        'id': fname,
                        'last_active': datetime.fromtimestamp(mtime).isoformat(),
                        'age_seconds': int(age_seconds)
                    })
            except Exception:
                continue
        return active

    @staticmethod
    def is_user_active() -> bool:
        """Проверить есть ли активные пользователи (сессии обновлённые < 5 мин)"""
        return len(SchedulerModule.get_active_sessions()) > 0

    @staticmethod
    def _create_default_config(config_path: str):
        """Create default tasks configuration"""
        tasks = []
        for name, task_def in BUILTIN_TASKS.items():
            tasks.append({
                'name': name,
                'enabled': task_def['default_enabled'],
                'schedule': task_def['default_schedule'],
                'module': task_def['module'],
                'func': task_def['func'],
                'params': task_def['params'],
                'category': task_def['category'],
                'description': task_def['description'],
                'last_run': None,
                'last_status': None,
                'last_duration': None,
                'run_count': 0,
                'events': task_def.get('events', [])
            })
        config = {
            'version': 1,
            'tasks': tasks,
            'global_enabled': True,
            'max_log_size_mb': 10,
            'max_log_days': 30
        }
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        logger.info(f"Created default tasks config: {config_path}")

    @staticmethod
    def _task_defaults(name: str, task_def: dict) -> dict:
        """Запись задачи в tasks.json из описания BUILTIN_TASKS."""
        return {
            'name': name,
            'enabled': task_def['default_enabled'],
            'schedule': task_def['default_schedule'],
            'module': task_def['module'],
            'func': task_def['func'],
            'params': task_def['params'],
            'category': task_def['category'],
            'description': task_def['description'],
            'last_run': None,
            'last_status': None,
            'last_duration': None,
            'run_count': 0,
            'events': task_def.get('events', [])
        }

    @staticmethod
    def _merge_missing_defaults(config_path: str):
        """Доставляет новые встроенные задачи в существующий tasks.json.

        tasks.json создаётся один раз, и задачи, добавленные в BUILTIN_TASKS
        позже, без мержа никогда не появлялись (создание шло только при
        первом создании файла). Существующие записи и их настройки не
        трогаются — доставляются только отсутствующие.
        """
        try:
            with open(config_path, 'r', encoding='utf-8-sig') as f:
                config = json.load(f)
        except Exception as e:
            logger.warning(f"scheduler: tasks.json не прочитан для мержа: {e}")
            return

        tasks = config.setdefault('tasks', [])
        have = {t.get('name') for t in tasks if isinstance(t, dict)}
        added = []
        for name, task_def in BUILTIN_TASKS.items():
            if name in have:
                continue
            tasks.append(SchedulerModule._task_defaults(name, task_def))
            added.append(name)

        if added:
            try:
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
                logger.info(f"scheduler: в tasks.json доставлены задачи: {', '.join(added)}")
            except Exception as e:
                logger.warning(f"scheduler: не удалось сохранить tasks.json: {e}")

    @staticmethod
    def _get_config_path() -> str:
        tasks_dir = get_global('tasks_dir')
        if not tasks_dir:
            starter_path = get_global('starter_path')
            if starter_path:
                tasks_dir = os.path.join(str(starter_path), 'files', 'tasks')
                os.makedirs(tasks_dir, exist_ok=True)
                set_global('tasks_dir', tasks_dir)
        if tasks_dir:
            return os.path.join(tasks_dir, 'tasks.json')
        return None

    @staticmethod
    def _load_config() -> dict:
        config_path = SchedulerModule._get_config_path()
        if config_path and os.path.exists(config_path):
            # utf-8-sig: переживаем BOM, если файл правили внешним редактором
            with open(config_path, 'r', encoding='utf-8-sig') as f:
                return json.load(f)
        return {'version': 1, 'tasks': [], 'global_enabled': True}

    @staticmethod
    def _save_config(config: dict):
        config_path = SchedulerModule._get_config_path()
        if config_path:
            # без BOM — json.load() на utf-8 падает на BOM-марке
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

    # ===== API Methods =====

    @staticmethod
    def get_tasks() -> Dict[str, Any]:
        """Получить все задачи (встроенные + кастомные из files/tasks/custom/)"""
        config = SchedulerModule._load_config()
        config_tasks = {t['name']: t for t in config.get('tasks', [])}

        # Собираем все доступные задачи
        from files.core.oss.default.task_base import discover_custom_tasks
        all_builtin = dict(BUILTIN_TASKS)
        custom_tasks = discover_custom_tasks()

        # Объединяем: встроенные + кастомные, с настройками из конфига
        result = []

        # Встроенные
        for name, task_def in all_builtin.items():
            saved = config_tasks.get(name, {})
            result.append({
                'name': name,
                'builtin': True,
                'description': task_def.get('description', {}),
                'category': task_def.get('category', 'custom'),
                'enabled': saved.get('enabled', task_def.get('default_enabled', False)),
                'schedule': saved.get('schedule', task_def.get('default_schedule', 'daily')),
                'custom_schedule': saved.get('custom_schedule'),
                'params': saved.get('params', task_def.get('params', {})),
                'events': saved.get('events', task_def.get('events', ['on_schedule'])),
                'in_process': task_def.get('in_process', False),
                'last_run': saved.get('last_run'),
                'last_status': saved.get('last_status'),
                'last_duration': saved.get('last_duration'),
                'run_count': saved.get('run_count', 0),
            })

        # Кастомные из файлов
        for meta in custom_tasks:
            name = meta['name']
            saved = config_tasks.get(name, {})
            result.append({
                'name': name,
                'builtin': False,
                'description': meta.get('description', {}),
                'category': meta.get('category', 'custom'),
                'enabled': saved.get('enabled', meta.get('default_enabled', False)),
                'schedule': saved.get('schedule', meta.get('default_schedule', 'daily')),
                'custom_schedule': saved.get('custom_schedule'),
                'params': {p['name']: p.get('default') for p in meta.get('params', [])} if not saved.get('params') else saved.get('params'),
                'param_schema': meta.get('params', []),
                'events': saved.get('events', meta.get('events', ['on_schedule'])),
                'in_process': meta.get('in_process', False),
                'last_run': saved.get('last_run'),
                'last_status': saved.get('last_status'),
                'last_duration': saved.get('last_duration'),
                'run_count': saved.get('run_count', 0),
                'source': meta.get('_source', ''),
            })

        return {'status': 'success', 'tasks': result}

    @staticmethod
    def get_task(name: str) -> Dict[str, Any]:
        """Get single task by name"""
        config = SchedulerModule._load_config()
        for task in config.get('tasks', []):
            if task['name'] == name:
                return {'status': 'success', 'task': task}
        return {'status': 'error', 'message': f'Task not found: {name}'}

    @staticmethod
    def add_task(data: dict) -> Dict[str, Any]:
        """Add a new task"""
        config = SchedulerModule._load_config()
        name = data.get('name')
        if not name:
            return {'status': 'error', 'message': 'Task name required'}

        # Check duplicate
        for task in config.get('tasks', []):
            if task['name'] == name:
                return {'status': 'error', 'message': f'Task already exists: {name}'}

        new_task = {
            'name': name,
            'enabled': data.get('enabled', True),
            'schedule': data.get('schedule', 'daily'),
            'custom_schedule': data.get('custom_schedule'),
            'module': data.get('module'),
            'func': data.get('func'),
            'description': data.get('description', {}),
            'params': data.get('params', {}),
            'category': data.get('category', 'custom'),
            'last_run': None,
            'last_status': None,
            'last_duration': None,
            'run_count': 0,
            'events': data.get('events', ['on_schedule'])
        }
        config['tasks'].append(new_task)
        SchedulerModule._save_config(config)
        return {'status': 'success', 'message': f'Task added: {name}'}

    @staticmethod
    def update_task(data: dict) -> Dict[str, Any]:
        """Update an existing task"""
        config = SchedulerModule._load_config()
        name = data.get('name')
        if not name:
            return {'status': 'error', 'message': 'Task name required'}

        for i, task in enumerate(config['tasks']):
            if task['name'] == name:
                for key in ['enabled', 'schedule', 'custom_schedule', 'module', 'func',
                           'description', 'params', 'category', 'events']:
                    if key in data:
                        config['tasks'][i][key] = data[key]
                SchedulerModule._save_config(config)
                return {'status': 'success', 'message': f'Task updated: {name}'}
        return {'status': 'error', 'message': f'Task not found: {name}'}

    @staticmethod
    def delete_task(data: dict) -> Dict[str, Any]:
        """Delete a task"""
        config = SchedulerModule._load_config()
        name = data.get('name')
        if not name:
            return {'status': 'error', 'message': 'Task name required'}

        original_count = len(config['tasks'])
        config['tasks'] = [t for t in config['tasks'] if t['name'] != name]
        if len(config['tasks']) < original_count:
            SchedulerModule._save_config(config)
            return {'status': 'success', 'message': f'Task deleted: {name}'}
        return {'status': 'error', 'message': f'Task not found: {name}'}

    @staticmethod
    def toggle_task(data: dict) -> Dict[str, Any]:
        """Enable/disable a task"""
        config = SchedulerModule._load_config()
        name = data.get('name')
        if not name:
            return {'status': 'error', 'message': 'Task name required'}

        for task in config['tasks']:
            if task['name'] == name:
                task['enabled'] = not task.get('enabled', True)
                SchedulerModule._save_config(config)
                status = 'enabled' if task['enabled'] else 'disabled'
                return {'status': 'success', 'message': f'Task {status}: {name}'}
        return {'status': 'error', 'message': f'Task not found: {name}'}

    @staticmethod
    def run_task_now(data: dict) -> Dict[str, Any]:
        """Execute a task immediately (as separate process)"""
        name = data.get('name')
        if not name:
            return {'status': 'error', 'message': 'Task name required'}

        starter_path = get_global('starter_path')
        if not starter_path:
            return {'status': 'error', 'message': 'starter_path not set'}

        python_exe = sys.executable
        script_path = os.path.join(str(starter_path), 'starter.py')

        cmd = [python_exe, '-u', script_path, '--task', name]
        task = SchedulerModule._find_task(name)
        if task and task.get('params'):
            cmd.extend(['--task-params', json.dumps(task['params'])])

        # Run as separate process — crash won't affect starter
        try:
            kwargs = {'cwd': str(starter_path)}
            if sys.platform == 'win32':
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                si.wShowWindow = subprocess.SW_HIDE
                kwargs['startupinfo'] = si

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                **kwargs
            )
            return {'status': 'success', 'message': f'Task started: {name}', 'pid': process.pid}
        except Exception as e:
            logger.error(f"Failed to run task {name}: {e}")
            return {'status': 'error', 'message': str(e)}

    @staticmethod
    def get_task_log(data: dict) -> Dict[str, Any]:
        """Get task execution log"""
        name = data.get('name')
        if not name:
            return {'status': 'error', 'message': 'Task name required'}

        tasks_dir = get_global('tasks_dir')
        if not tasks_dir:
            return {'status': 'error', 'message': 'tasks_dir not set'}

        log_path = os.path.join(tasks_dir, f'{name}.log')
        if os.path.exists(log_path):
            with open(log_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return {'status': 'success', 'log': content, 'log_file': log_path}
        return {'status': 'success', 'log': '', 'log_file': log_path}

    @staticmethod
    def clear_task_log(data: dict) -> Dict[str, Any]:
        """Clear task log"""
        name = data.get('name')
        if not name:
            return {'status': 'error', 'message': 'Task name required'}

        tasks_dir = get_global('tasks_dir')
        if not tasks_dir:
            return {'status': 'error', 'message': 'tasks_dir not set'}

        log_path = os.path.join(tasks_dir, f'{name}.log')
        if os.path.exists(log_path):
            with open(log_path, 'w', encoding='utf-8') as f:
                f.write('')
        return {'status': 'success', 'message': f'Log cleared: {name}'}

    @staticmethod
    def get_task_history() -> Dict[str, Any]:
        """Get execution history for all tasks"""
        config = SchedulerModule._load_config()
        history = []
        for task in config.get('tasks', []):
            history.append({
                'name': task['name'],
                'last_run': task.get('last_run'),
                'last_status': task.get('last_status'),
                'last_duration': task.get('last_duration'),
                'run_count': task.get('run_count', 0),
                'enabled': task.get('enabled', False)
            })
        return {'status': 'success', 'history': history}

    # ===== Helper =====

    @staticmethod
    def _find_task(name: str) -> Optional[dict]:
        config = SchedulerModule._load_config()
        for task in config.get('tasks', []):
            if task['name'] == name:
                return task
        return None

    # ===== Built-in task runners (called via --task) =====

    @staticmethod
    def execute_task(task_name: str, params: dict = None):
        """
        Execute a built-in task. Called from starter.py --task <name>
        This runs in a SEPARATE process, so if it crashes, starter survives.
        """
        tasks_dir = get_global('tasks_dir')
        log_file = os.path.join(tasks_dir, f'{task_name}.log') if tasks_dir else None

        start_time = time.time()
        status = 'success'
        error_msg = None

        try:
            if task_name == 'check_updates':
                result = SchedulerModule._run_check_updates(params or {})
            elif task_name == 'check_service_status':
                result = SchedulerModule._run_check_service_status(params or {})
            elif task_name == 'cleanup_logs':
                result = SchedulerModule._run_cleanup_logs(params or {})
            elif task_name == 'check_ports':
                result = SchedulerModule._run_check_ports(params or {})
            elif task_name == 'check_docker':
                result = SchedulerModule._run_check_docker(params or {})
            elif task_name == 'server_status_refresh':
                result = SchedulerModule._run_server_status_refresh(params or {})
            else:
                # Custom task — try to load via module loader
                result = SchedulerModule._run_custom_task(task_name, params or {})
        except Exception as e:
            status = 'error'
            error_msg = str(e)
            result = {'status': 'error', 'message': error_msg}
            logger.error(f"Task {task_name} failed: {e}")

        duration = round(time.time() - start_time, 2)
        now = datetime.now().isoformat()

        # Write log
        if log_file:
            log_entry = f"[{now}] {task_name} — {status} ({duration}s)\n"
            if error_msg:
                log_entry += f"  Error: {error_msg}\n"
            if result and isinstance(result, dict):
                log_entry += f"  Result: {json.dumps(result, ensure_ascii=False)}\n"
            log_entry += "---\n"
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)

        # Update task stats (upsert: кастомная задача могла ещё не быть
        # сохранена в конфиг — тогда добавляем запись со статистикой)
        with SchedulerModule._config_lock:
            config = SchedulerModule._load_config()
            task_entry = None
            for task in config.get('tasks', []):
                if task['name'] == task_name:
                    task_entry = task
                    break
            if task_entry is None:
                # берём дефолты из метаданных (встроенные/кастомные)
                meta = {}
                try:
                    for m in SchedulerModule.get_tasks().get('tasks', []):
                        if m['name'] == task_name:
                            meta = m
                            break
                except Exception:
                    pass
                task_entry = {
                    'name': task_name,
                    'enabled': meta.get('enabled', True),
                    'schedule': meta.get('schedule', 'daily'),
                    'custom_schedule': meta.get('custom_schedule'),
                    'module': None,
                    'func': None,
                    'params': params or {},
                    'category': meta.get('category', 'custom'),
                    'description': meta.get('description', {}),
                    'events': meta.get('events', ['on_schedule']),
                    'run_count': 0,
                }
                config.setdefault('tasks', []).append(task_entry)
            task_entry['last_run'] = now
            task_entry['last_status'] = status
            task_entry['last_duration'] = f"{duration}s"
            task_entry['run_count'] = task_entry.get('run_count', 0) + 1
            SchedulerModule._save_config(config)

        print(f"[{now}] Task '{task_name}' completed: {status} ({duration}s)")
        return result

    # ===== Built-in task implementations =====

    @staticmethod
    def _run_check_updates(params: dict) -> dict:
        """Check for starter updates"""
        starter_path = get_global('starter_path')
        if not starter_path:
            return {'status': 'error', 'message': 'starter_path not set'}

        try:
            from files.core.utils.loader_utils import get
            updates = get('updates', 'check_starter_updates')
            return {'status': 'success', 'updates': updates}
        except Exception as e:
            # Fallback — just check git
            try:
                result = subprocess.run(
                    ['git', 'fetch', '--dry-run'],
                    cwd=str(starter_path),
                    capture_output=True, text=True, timeout=30,
                    startupinfo=_si() if sys.platform == 'win32' else None
                )
                has_updates = bool(result.stdout.strip())
                return {'status': 'success', 'has_updates': has_updates}
            except Exception as e2:
                return {'status': 'error', 'message': str(e2)}

    @staticmethod
    def _run_check_service_status(params: dict) -> dict:
        """Check service status and log if changed"""
        try:
            from files.core.utils.loader_utils import get
            status = get('service', 'get_service_status')
            logger.info(f"Service status check: {status}")

            # Write status to global for web UI
            if status.get('installed'):
                set_global('service_installed', True)
                set_global('service_status', 'running' if status.get('running') else 'installed')

            return {'status': 'success', 'service': status}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    @staticmethod
    def _run_cleanup_logs(params: dict) -> dict:
        """Clean old log files"""
        max_days = params.get('max_days', 30)
        starter_path = get_global('starter_path')
        if not starter_path:
            return {'status': 'error', 'message': 'starter_path not set'}

        logs_dir = os.path.join(str(starter_path), 'logs')
        if not os.path.exists(logs_dir):
            return {'status': 'success', 'message': 'No logs directory'}

        cutoff = datetime.now() - timedelta(days=max_days)
        removed = 0
        freed = 0

        for root, dirs, files in os.walk(logs_dir):
            for fname in files:
                fpath = os.path.join(root, fname)
                try:
                    mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
                    if mtime < cutoff:
                        size = os.path.getsize(fpath)
                        os.remove(fpath)
                        removed += 1
                        freed += size
                except Exception:
                    continue

        return {
            'status': 'success',
            'removed_files': removed,
            'freed_bytes': freed,
            'freed_mb': round(freed / 1024 / 1024, 2)
        }

    @staticmethod
    def _run_check_ports(params: dict) -> dict:
        """Check occupied ports"""
        try:
            from files.core.utils.loader_utils import get
            ports = get('portmanager', 'get_used_ports')
            return {'status': 'success', 'ports': ports}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    @staticmethod
    def _run_check_docker(params: dict) -> dict:
        """Check Docker status"""
        try:
            from files.core.utils.loader_utils import get
            installed = get('docker', 'check_docker_installed')
            compose = get('docker', 'check_docker_compose_installed')
            return {'status': 'success', 'docker': installed, 'compose': compose}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    @staticmethod
    def _run_server_status_refresh(params: dict) -> dict:
        """Обновить кеш статусов серверов (server_monitor, SQLite).

        Без этой задачи files/server_status.db не обновлялся никогда:
        streams показывал not_deployed при живых контейнерах, а статусы
        висели неделями. Расписание — server_status_refresh в tasks.json
        (интервал status_interval из настроек монитора).
        """
        try:
            from files.core.oss.default.server_monitor import ServerMonitorModule
            ServerMonitorModule.refresh_all(background=False)
            info = ServerMonitorModule.get_status()
            return {'status': 'success',
                    'servers': info.get('servers_count', 0),
                    'updated_at': info.get('updated_at')}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    @staticmethod
    def _run_custom_task(task_name: str, params: dict) -> dict:
        """Run a custom task — сначала из files/tasks/custom/, потом из конфига"""
        # Пробуем найти в файлах tasks/custom/
        try:
            from files.core.oss.default.task_base import run_custom_task
            result = run_custom_task(task_name, params)
            if result.get('status') != 'error':
                return result
        except Exception:
            pass

        # Fallback — из конфига (старый способ)
        config = SchedulerModule._load_config()
        for task in config.get('tasks', []):
            if task['name'] == task_name:
                module_name = task.get('module')
                func_name = task.get('func')
                if module_name and func_name:
                    try:
                        from files.core.utils.loader_utils import get
                        func = get(module_name, func_name)
                        if callable(func):
                            result = func(**params) if params else func()
                            return {'status': 'success', 'result': result}
                        return {'status': 'error', 'message': f'Function not callable: {func_name}'}
                    except Exception as e:
                        return {'status': 'error', 'message': str(e)}
                return {'status': 'error', 'message': 'Module/func not configured'}
        return {'status': 'error', 'message': f'Task not found: {task_name}'}

    # ===== Цикл выполнения по расписанию =====

    SCHEDULE_INTERVALS = {
        'every_10sec': 10,
        'every_30sec': 30,
        'every_1min': 60,
        'every_5min': 300,
        'every_30min': 1800,
        'hourly': 3600,
        'every_6h': 21600,
        'daily': 86400,
        'weekly': 604800,
        'monthly': 2592000,
    }
    TICK_SECONDS = 10

    _loop_thread: Optional[threading.Thread] = None
    _loop_stop = threading.Event()
    _running_tasks: set = set()
    _running_lock = threading.Lock()
    _config_lock = threading.Lock()

    @staticmethod
    def interval_seconds(task: dict) -> int:
        """Интервал задачи в секундах: custom_schedule (сек) или schedule."""
        custom = task.get('custom_schedule')
        if custom:
            try:
                return max(5, int(custom))
            except (TypeError, ValueError):
                pass
        return SchedulerModule.SCHEDULE_INTERVALS.get(task.get('schedule'), 3600)

    @staticmethod
    def is_running() -> bool:
        """Крутится ли цикл планировщика в этом процессе"""
        t = SchedulerModule._loop_thread
        return bool(t and t.is_alive())

    @staticmethod
    def is_global_enabled() -> bool:
        return bool(SchedulerModule._load_config().get('global_enabled', True))

    @staticmethod
    def _task_due(task: dict) -> bool:
        last = task.get('last_run')
        if not last:
            return True
        try:
            last_ts = datetime.fromisoformat(last).timestamp()
        except Exception:
            return True
        return (time.time() - last_ts) >= SchedulerModule.interval_seconds(task)

    @staticmethod
    def _launch_task(task: dict):
        """Запуск просроченной задачи.

        in_process=True — в отдельном потоке (лёгкие задачи, например
        мониторинг серверов: без спавна процесса, кеш в SQLite общается
        напрямую). Остальные — отдельным процессом, как задумано: падение
        задачи не роняет стартер.
        """
        name = task['name']
        params = task.get('params') or {}

        with SchedulerModule._running_lock:
            if name in SchedulerModule._running_tasks:
                return
            SchedulerModule._running_tasks.add(name)

        if task.get('in_process'):
            def _run():
                try:
                    SchedulerModule.execute_task(name, params)
                except Exception as e:
                    logger.error(f"scheduler: задача {name} упала: {e}")
                finally:
                    with SchedulerModule._running_lock:
                        SchedulerModule._running_tasks.discard(name)
            threading.Thread(target=_run, daemon=True, name=f'task-{name}').start()
        else:
            res = SchedulerModule.run_task_now({'name': name})
            if res.get('status') != 'success':
                with SchedulerModule._running_lock:
                    SchedulerModule._running_tasks.discard(name)
                logger.error(f"scheduler: не удалось запустить {name}: {res.get('message')}")
                return

            def _clear_after_interval():
                # маркер снимаем через интервал — задача-процесс не должна
                # перезапускаться раньше, чем отработает её расписание
                time.sleep(SchedulerModule.interval_seconds(task))
                with SchedulerModule._running_lock:
                    SchedulerModule._running_tasks.discard(name)
            threading.Thread(target=_clear_after_interval, daemon=True).start()

    @staticmethod
    def _run_due_tasks():
        tasks = SchedulerModule.get_tasks().get('tasks', [])
        for task in tasks:
            if not task.get('enabled'):
                continue
            if 'on_schedule' not in (task.get('events') or ['on_schedule']):
                continue
            if not SchedulerModule._task_due(task):
                continue
            SchedulerModule._launch_task(task)

    @staticmethod
    def _scheduler_loop():
        logger.info(f"Планировщик запущен (тик {SchedulerModule.TICK_SECONDS}с)")
        while not SchedulerModule._loop_stop.is_set():
            try:
                if SchedulerModule.is_global_enabled():
                    SchedulerModule._run_due_tasks()
            except Exception as e:
                logger.error(f"scheduler loop error: {e}")
            SchedulerModule._loop_stop.wait(SchedulerModule.TICK_SECONDS)

    @staticmethod
    def start_scheduler():
        """Запускает цикл выполнения задач по расписанию"""
        if SchedulerModule._loop_thread and SchedulerModule._loop_thread.is_alive():
            logger.info("scheduler: цикл уже запущен")
            return
        SchedulerModule._loop_stop.clear()
        SchedulerModule._loop_thread = threading.Thread(
            target=SchedulerModule._scheduler_loop, daemon=True, name='scheduler')
        SchedulerModule._loop_thread.start()
        logger.info("scheduler: цикл расписания инициирован")

    @staticmethod
    def stop_scheduler():
        SchedulerModule._loop_stop.set()
        if SchedulerModule._loop_thread:
            SchedulerModule._loop_thread.join(timeout=5)
        logger.info("scheduler: цикл остановлен")

    # ===== Event system =====

    @staticmethod
    def trigger_event(event_name: str, data: dict = None):
        """
        Trigger an event — runs all tasks registered for this event.
        Used for future extensibility: on_startup, on_shutdown, on_update, etc.
        """
        config = SchedulerModule._load_config()
        triggered = []
        for task in config.get('tasks', []):
            if task.get('enabled') and event_name in task.get('events', []):
                result = SchedulerModule.run_task_now({'name': task['name']})
                triggered.append({'task': task['name'], 'result': result})
        return {'status': 'success', 'event': event_name, 'triggered': triggered}
