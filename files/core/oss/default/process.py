# files/core/oss/default/process.py
"""
Модуль управления процессами (Unix/Linux/Mac и fallback для Windows)
"""
import os
import sys
import signal
import time
import threading
import json
import subprocess
import platform
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from files.core.base_module import BaseModule
from files.core.utils.globalVars_utils import get_global, set_global
from files.core.utils.log_utils import LogManager

logger = LogManager.get_logger('process')


class ProcessModule(BaseModule):
    """Модуль управления процессами"""
    
    _running = True
    _watchdog_thread = None
    _parent_pid = None
    _child_pid = None
    _processes_killed = False
    
    @staticmethod
    def check() -> bool:
        return True
    
    @staticmethod
    def set_globals():
        starter_path = get_global('starter_path')
        if starter_path:
            set_global('process_file', starter_path / "processes.json")
            set_global('process_pid_file', starter_path / "starter.pid")
            logger.debug(f"Process files in: {starter_path}")
    
    @staticmethod
    def _get_processes_file() -> Path:
        return get_global('process_file')
    
    @staticmethod
    def _get_pid_file() -> Path:
        return get_global('process_pid_file')
    
    @staticmethod
    def is_werkzeug_child() -> bool:
        return get_global('WERKZEUG', False)
    
    @staticmethod
    def get_current_pid() -> int:
        return os.getpid()
    
    @staticmethod
    def get_parent_pid() -> int:
        return os.getppid()
    
    @staticmethod
    def is_process_alive(pid: int) -> bool:
        try:
            if platform.system() == 'Windows':
                import ctypes
                kernel32 = ctypes.windll.kernel32
                handle = kernel32.OpenProcess(0x1000, False, pid)
                if handle:
                    kernel32.CloseHandle(handle)
                    return True
                return False
            else:
                os.kill(pid, 0)
                return True
        except:
            return False
    
    @staticmethod
    def kill_process(pid: int, force: bool = False) -> Tuple[bool, str]:
        try:
            if platform.system() == 'Windows':
                if force:
                    subprocess.run(['taskkill', '/F', '/PID', str(pid)], capture_output=True)
                else:
                    subprocess.run(['taskkill', '/PID', str(pid)], capture_output=True)
                msg = f"Process {pid} killed"
            else:
                if force:
                    os.kill(pid, signal.SIGKILL)
                else:
                    os.kill(pid, signal.SIGTERM)
                msg = f"Process {pid} terminated"
            logger.info(msg)
            return True, msg
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def kill_orphaned_processes() -> List[int]:
        """Убивает все потерянные процессы starter.py"""
        print("\n🧹 ПОИСК И УБИЙСТВО ПОТЕРЯННЫХ ПРОЦЕССОВ")
        print("-" * 50)
        killed = []
        current_pid = os.getpid()
        if platform.system() == 'Windows':
            try:
                output = subprocess.check_output(
                    ['tasklist', '/FI', 'IMAGENAME eq python.exe', '/FO', 'CSV', '/NH'],
                    text=True
                )
                import re
                for line in output.split('\n'):
                    if 'starter.py' in line.lower():
                        match = re.search(r'"(\d+)"', line)
                        if match:
                            pid = int(match.group(1))
                            if pid != current_pid:
                                subprocess.run(['taskkill', '/F', '/PID', str(pid)], capture_output=True)
                                killed.append(pid)
                                print(f"   ✅ Убит потерянный процесс PID: {pid}")
            except Exception as e:
                print(f"   ⚠️ Ошибка: {e}")
        else:
            try:
                import psutil
                for proc in psutil.process_iter(['pid', 'cmdline']):
                    try:
                        cmdline = ' '.join(proc.info['cmdline'] or [])
                        if 'starter.py' in cmdline:
                            pid = proc.info['pid']
                            if pid != current_pid:
                                proc.kill()
                                killed.append(pid)
                                print(f"   ✅ Убит потерянный процесс PID: {pid}")
                    except:
                        pass
            except ImportError:
                os.system('pkill -f starter.py')
        return killed
    
    @staticmethod
    def kill_process_with_children(pid: int, force: bool = False) -> Dict[str, Any]:
        result = {'killed': [], 'failed': [], 'pid': pid}
        try:
            import psutil
            parent = psutil.Process(pid)
            for child in parent.children(recursive=True):
                success, _ = ProcessModule.kill_process(child.pid, force)
                if success:
                    result['killed'].append(child.pid)
                else:
                    result['failed'].append(child.pid)
            success, _ = ProcessModule.kill_process(pid, force)
            if success:
                result['killed'].append(pid)
            else:
                result['failed'].append(pid)
        except ImportError:
            success, _ = ProcessModule.kill_process(pid, force)
            if success:
                result['killed'].append(pid)
            else:
                result['failed'].append(pid)
        except Exception as e:
            result['failed'].append(pid)
        return result
    
    @staticmethod
    def register_process() -> Dict[str, Any]:
        current_pid = os.getpid()
        is_child = ProcessModule.is_werkzeug_child()
        processes_file = ProcessModule._get_processes_file()
        pid_file = ProcessModule._get_pid_file()
        result = {'status': 'success', 'pid': current_pid, 'is_child': is_child}
        try:
            processes = {}
            if processes_file and processes_file.exists():
                with open(processes_file, 'r', encoding='utf-8') as f:
                    processes = json.load(f)
            processes[str(current_pid)] = {
                'pid': current_pid,
                'is_child': is_child,
                'start_time': time.time(),
                'start_time_str': time.strftime('%Y-%m-%d %H:%M:%S'),
                'parent_pid': os.getppid() if is_child else None,
                'child_pid': None,
                'port': get_global('port', 2000),
                'python': sys.executable,
                'script': str(get_global('script_path')),
                'starter_path': str(get_global('starter_path')),
                'project_path': str(get_global('project_path')),
                'os_family': get_global('os_family', 'unknown'),
                'os_name': get_global('os', 'unknown')
            }
            if is_child:
                parent_pid = os.getppid()
                if str(parent_pid) in processes:
                    processes[str(parent_pid)]['child_pid'] = current_pid
                    result['linked_to'] = parent_pid
                else:
                    processes[str(parent_pid)] = {
                        'pid': parent_pid,
                        'is_child': False,
                        'start_time': time.time(),
                        'start_time_str': time.strftime('%Y-%m-%d %H:%M:%S'),
                        'parent_pid': None,
                        'child_pid': current_pid,
                        'port': get_global('port', 2000),
                        'python': sys.executable,
                        'script': str(get_global('script_path')),
                        'starter_path': str(get_global('starter_path')),
                        'project_path': str(get_global('project_path')),
                        'os_family': get_global('os_family', 'unknown'),
                        'os_name': get_global('os', 'unknown'),
                        'is_placeholder': True
                    }
                    result['linked_to'] = parent_pid
            else:
                for pid_str, proc in processes.items():
                    if proc.get('parent_pid') == current_pid:
                        processes[str(current_pid)]['child_pid'] = int(pid_str)
                        result['linked_to'] = int(pid_str)
                        break
            if processes_file:
                with open(processes_file, 'w', encoding='utf-8') as f:
                    json.dump(processes, f, indent=2, ensure_ascii=False)
            if not is_child:
                pid_file.write_text(str(current_pid))
            logger.info(f"Process registered: PID={current_pid}")
        except Exception as e:
            logger.error(f"Failed to register process: {e}")
            result['status'] = 'error'
            result['error'] = str(e)
        return result
    
    @staticmethod
    def unregister_process() -> Dict[str, Any]:
        current_pid = os.getpid()
        processes_file = ProcessModule._get_processes_file()
        pid_file = ProcessModule._get_pid_file()
        result = {'status': 'success', 'pid': current_pid}
        try:
            if processes_file and processes_file.exists():
                with open(processes_file, 'r', encoding='utf-8') as f:
                    processes = json.load(f)
                if str(current_pid) in processes:
                    child_pid = processes[str(current_pid)].get('child_pid')
                    if child_pid and str(child_pid) in processes:
                        processes[str(child_pid)]['parent_pid'] = None
                        processes[str(child_pid)]['is_orphan'] = True
                    del processes[str(current_pid)]
                with open(processes_file, 'w', encoding='utf-8') as f:
                    json.dump(processes, f, indent=2, ensure_ascii=False)
                logger.info(f"Process unregistered: PID={current_pid}")
            if pid_file.exists() and int(pid_file.read_text().strip()) == current_pid:
                pid_file.unlink()
        except Exception as e:
            logger.error(f"Failed to unregister process: {e}")
            result['status'] = 'error'
            result['error'] = str(e)
        return result
    
    @staticmethod
    def get_all_processes() -> List[Dict[str, Any]]:
        processes = []
        processes_file = ProcessModule._get_processes_file()
        try:
            if processes_file and processes_file.exists():
                with open(processes_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for pid_str, info in data.items():
                    info['pid'] = int(pid_str)
                    info['alive'] = ProcessModule.is_process_alive(int(pid_str))
                    processes.append(info)
        except Exception as e:
            logger.error(f"Failed to get processes: {e}")
        return processes
    
    @staticmethod
    def kill_all_processes(exclude_current: bool = True) -> Dict[str, Any]:
        result = {'killed': [], 'failed': [], 'total': 0}
        processes = ProcessModule.get_all_processes()
        current_pid = os.getpid()
        for proc in processes:
            pid = proc['pid']
            if exclude_current and pid == current_pid:
                continue
            if ProcessModule.is_process_alive(pid):
                success, _ = ProcessModule.kill_process(pid, force=True)
                if success:
                    result['killed'].append(pid)
                else:
                    result['failed'].append(pid)
        result['total'] = len(result['killed']) + len(result['failed'])
        return result
    
    @staticmethod
    def cleanup_orphaned() -> Dict[str, Any]:
        result = {'status': 'success', 'killed': [], 'total': 0}
        print("\n🧹 ОЧИСТКА ПОТЕРЯННЫХ ПРОЦЕССОВ")
        print("-" * 40)
        killed = ProcessModule.kill_orphaned_processes()
        result['killed'] = killed
        result['total'] = len(killed)
        # Очистка файла реестра от мёртвых записей
        processes_file = ProcessModule._get_processes_file()
        if processes_file and processes_file.exists():
            try:
                with open(processes_file, 'r', encoding='utf-8') as f:
                    processes = json.load(f)
                alive_processes = {}
                for pid_str, proc in processes.items():
                    pid = int(pid_str)
                    if ProcessModule.is_process_alive(pid):
                        alive_processes[pid_str] = proc
                    else:
                        print(f"   🗑️ Удалена запись о мёртвом процессе PID: {pid}")
                with open(processes_file, 'w', encoding='utf-8') as f:
                    json.dump(alive_processes, f, indent=2, ensure_ascii=False)
            except Exception as e:
                logger.error(f"Error cleaning processes file: {e}")
        # Очистка сессий
        starter_path = get_global('starter_path')
        if starter_path:
            session_dir = starter_path / "files" / "web" / "sessions"
            if session_dir.exists():
                for f in session_dir.glob("*"):
                    try:
                        f.unlink()
                    except:
                        pass
                print("   ✅ Файлы сессий очищены")
        return result
    
    @staticmethod
    def start_parent_watchdog():
        if not ProcessModule.is_werkzeug_child():
            return
        ProcessModule._parent_pid = os.getppid()
        def watchdog():
            logger.info(f"Parent watchdog started. Monitoring parent PID: {ProcessModule._parent_pid}")
            while ProcessModule._running:
                if not ProcessModule.is_process_alive(ProcessModule._parent_pid):
                    logger.info("Parent process died! Shutting down child...")
                    ProcessModule._emergency_shutdown()
                    break
                time.sleep(1)
        ProcessModule._watchdog_thread = threading.Thread(target=watchdog, daemon=True)
        ProcessModule._watchdog_thread.start()
    
    @staticmethod
    def start_child_watchdog():
        processes = ProcessModule.get_all_processes()
        current_pid = os.getpid()
        for proc in processes:
            if proc.get('parent_pid') == current_pid:
                ProcessModule._child_pid = proc['pid']
                break
        if not ProcessModule._child_pid:
            return
        def watchdog():
            logger.info(f"Child watchdog started. Monitoring child PID: {ProcessModule._child_pid}")
            while ProcessModule._running:
                if not ProcessModule.is_process_alive(ProcessModule._child_pid):
                    logger.info("Child process died! Shutting down parent...")
                    ProcessModule._emergency_shutdown()
                    break
                time.sleep(1)
        ProcessModule._watchdog_thread = threading.Thread(target=watchdog, daemon=True)
        ProcessModule._watchdog_thread.start()
    
    @staticmethod
    def _emergency_shutdown():
        ProcessModule._running = False
        ProcessModule.unregister_process()
        if not ProcessModule._processes_killed:
            ProcessModule._processes_killed = True
            ProcessModule.kill_orphaned_processes()
        if platform.system() == 'Windows':
            os._exit(0)
        else:
            os.kill(os.getpid(), signal.SIGTERM)
        sys.exit(0)
    
    @staticmethod
    def setup_signal_handlers():
        def signal_handler(signum, frame):
            print(f"\n\n{'='*60}")
            print(f"🛑 Получен сигнал {signum}, завершаем работу...")
            print(f"{'='*60}")
            ProcessModule._running = False
            if ProcessModule.is_werkzeug_child() and ProcessModule._parent_pid:
                print(f"   Убиваем родительский процесс: {ProcessModule._parent_pid}")
                ProcessModule.kill_process(ProcessModule._parent_pid, force=True)
            if not ProcessModule.is_werkzeug_child() and ProcessModule._child_pid:
                print(f"   Убиваем дочерний процесс: {ProcessModule._child_pid}")
                ProcessModule.kill_process(ProcessModule._child_pid, force=True)
            print(f"\n   🧹 Очистка потерянных процессов...")
            ProcessModule.kill_orphaned_processes()
            ProcessModule.unregister_process()
            print("\n👋 Работа завершена")
            sys.exit(0)
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        if platform.system() != 'Windows':
            signal.signal(signal.SIGHUP, signal_handler)
            signal.signal(signal.SIGQUIT, signal_handler)
    
    @staticmethod
    def get_status() -> Dict[str, Any]:
        processes = ProcessModule.get_all_processes()
        current_pid = os.getpid()
        return {
            'status': 'success',
            'current_pid': current_pid,
            'is_child': ProcessModule.is_werkzeug_child(),
            'parent_pid': os.getppid(),
            'processes': processes,
            'count': len(processes)
        }
    
    @staticmethod
    def print_status():
        status = ProcessModule.get_status()
        print("\n" + "=" * 60)
        print("📊 СТАТУС ПРОЦЕССОВ STARTER")
        print("=" * 60)
        if status['count'] == 0:
            print("   Нет зарегистрированных процессов")
            return
        current_port = get_global('port', 2000)
        for proc in status['processes']:
            pid = proc['pid']
            is_current = pid == status['current_pid']
            is_child = proc.get('is_child', False)
            is_alive = proc.get('alive', False)
            marker = "🔵 ТЕКУЩИЙ" if is_current else ("✅ ЖИВ" if is_alive else "💀 МЕРТВ")
            role = "Дочерний (Werkzeug)" if is_child else "Родительский"
            port_to_show = current_port if is_current else proc.get('port', 'unknown')
            print(f"\n   {marker}")
            print(f"      PID: {pid}")
            print(f"      Роль: {role}")
            print(f"      Запущен: {proc.get('start_time_str', 'unknown')}")
            print(f"      Порт: {port_to_show}")
            if proc.get('child_pid'):
                child_alive = ProcessModule.is_process_alive(proc['child_pid'])
                print(f"      Дочерний PID: {proc['child_pid']} ({'✅ жив' if child_alive else '💀 мертв'})")
            if proc.get('parent_pid'):
                parent_alive = ProcessModule.is_process_alive(proc['parent_pid'])
                print(f"      Родительский PID: {proc['parent_pid']} ({'✅ жив' if parent_alive else '💀 мертв'})")
        print("=" * 60 + "\n")
    
    @staticmethod
    def bind_processes():
        if ProcessModule.is_werkzeug_child():
            ProcessModule.start_parent_watchdog()
        else:
            ProcessModule.start_child_watchdog()