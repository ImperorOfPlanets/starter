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
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {'version': 1, 'tasks': [], 'global_enabled': True}

    @staticmethod
    def _save_config(config: dict):
        config_path = SchedulerModule._get_config_path()
        if config_path:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

    # ===== API Methods =====

    @staticmethod
    def get_tasks() -> Dict[str, Any]:
        """Get all tasks"""
        config = SchedulerModule._load_config()
        return {'status': 'success', 'tasks': config.get('tasks', [])}

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

        # Update task stats
        config = SchedulerModule._load_config()
        for task in config.get('tasks', []):
            if task['name'] == task_name:
                task['last_run'] = now
                task['last_status'] = status
                task['last_duration'] = f"{duration}s"
                task['run_count'] = task.get('run_count', 0) + 1
                break
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
                    capture_output=True, text=True, timeout=30
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
    def _run_custom_task(task_name: str, params: dict) -> dict:
        """Run a custom task by loading module and calling function"""
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
