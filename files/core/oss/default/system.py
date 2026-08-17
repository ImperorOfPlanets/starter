from files.core.base_module import BaseModule
import os
import platform
import re
import socket
import subprocess
import sys
import ctypes
import time

try:
    import psutil
except ImportError:
    psutil = None

from datetime import datetime, timedelta
from typing import Dict, Any
from pathlib import Path

from files.core.utils.globalVars_utils import set_global, get_global


class SystemModule(BaseModule):

    @staticmethod
    def check() -> bool:
        return True

    @staticmethod
    def collect_basic_system_info() -> Dict[str, Any]:
        """Собирает базовую информацию о системе"""
        import secrets

        script_path = Path(sys.argv[0]).resolve()
        print(f"📄 Путь к скрипту (script_path): {script_path}")
        set_global('script_path', script_path)

        starter_path = script_path.parent
        print(f"📁 Путь к папке (starter_path): {starter_path}")
        set_global('starter_path', starter_path)

        set_global('starter_env_path', starter_path / '.env')
        set_global('starter_env_example_path', starter_path / '.env.example')

        debug_value = 'FALSE'
        env_path = get_global('starter_env_path')
        if env_path and env_path.exists():
            try:
                with open(env_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        stripped = line.strip()
                        if not stripped or stripped.startswith('#'):
                            continue
                        if stripped.startswith('DEBUG='):
                            debug_value = stripped.split('=', 1)[1].strip().upper()
                            break
            except Exception:
                pass
        set_global('DEBUG', debug_value in ('TRUE', '1', 'YES', 'ON'))
        print(f"🔧 Режим отладки: {'ВКЛЮЧЕН' if get_global('DEBUG') else 'ВЫКЛЮЧЕН'}")

        running_in_docker = os.path.exists('/.dockerenv')
        set_global('running_in_docker', running_in_docker)
        print(f"🐳 В Docker: {'Да' if running_in_docker else 'Нет'}")

        set_global('os_type', platform.system().lower())
        set_global('os', platform.system())
        set_global('os_version', platform.version())
        set_global('os_release', platform.release())
        set_global('architecture', platform.machine())
        set_global('hostname', socket.gethostname())
        set_global('python_version', platform.python_version())
        set_global('python_implementation', platform.python_implementation())
        set_global('python_compiler', platform.python_compiler())
        set_global('python_executable', sys.executable)

        try:
            set_global('username', os.getenv('USER') or os.getenv('USERNAME') or 'N/A')
        except Exception:
            set_global('username', 'N/A')

        set_global('current_time', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

        try:
            if psutil:
                uptime_seconds = time.time() - psutil.boot_time()
            else:
                uptime_seconds = 0
            hours = int(uptime_seconds // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            seconds = int(uptime_seconds % 60)
            set_global('uptime', f"{hours:02d}:{minutes:02d}:{seconds:02d}")
        except Exception:
            set_global('uptime', 'N/A')

        is_root = False
        is_admin = False
        if platform.system() == "Windows":
            try:
                is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
            except Exception:
                is_admin = False
            is_root = is_admin
        else:
            is_root = os.geteuid() == 0
        set_global('is_root', is_root)
        set_global('use_sudo', not is_root)

        port = 2000
        env_path = get_global('starter_env_path')
        if env_path and env_path.exists():
            try:
                with open(env_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        stripped = line.strip()
                        if stripped.startswith('PORT='):
                            port_val = stripped.split('=', 1)[1].strip()
                            if port_val.isdigit():
                                port = int(port_val)
                            break
            except Exception:
                pass
        set_global('port', port)
        os.environ["PORT"] = str(port)

        cpu_info = SystemModule.get_cpu_info()
        set_global('cpu_model', cpu_info.get('name', 'N/A'))
        set_global('cpu_cores', cpu_info.get('cores', 'N/A'))
        set_global('cpu_logical_cores', cpu_info.get('logical_cores', 'N/A'))
        set_global('cpu_usage', cpu_info.get('usage', 'N/A'))

        memory_info = SystemModule.get_memory_info()
        set_global('memory_total', memory_info.get('total', 'N/A'))
        set_global('memory_used', memory_info.get('used', 'N/A'))
        set_global('memory_percent', memory_info.get('percent', 'N/A'))
        set_global('memory_available', memory_info.get('available', 'N/A'))

        disk_info = SystemModule.get_disk_info()
        set_global('disk_total', disk_info.get('total', 'N/A'))
        set_global('disk_used', disk_info.get('used', 'N/A'))
        set_global('disk_percent', disk_info.get('percent', 'N/A'))
        set_global('disk_free', disk_info.get('free', 'N/A'))

        set_global('WERKZEUG', os.environ.get('WERKZEUG_RUN_MAIN') == 'true')

        print(f"   ✅ starter_path: {starter_path}")

        # project_path, docker_path, code_path устанавливаются при выборе сервера
        set_global('project_path', None)
        set_global('docker_path', None)
        set_global('code_path', None)

        return {}

    @staticmethod
    def get_cpu_info() -> Dict[str, Any]:
        try:
            cpu_info = {
                'name': 'N/A',
                'cores': 'N/A',
                'logical_cores': 'N/A',
                'usage': 'N/A'
            }

            if platform.system() == "Darwin":
                cpu_info['logical_cores'] = int(subprocess.check_output(
                    ['sysctl', '-n', 'hw.logicalcpu']).decode().strip())
                cpu_info['cores'] = int(subprocess.check_output(
                    ['sysctl', '-n', 'hw.physicalcpu']).decode().strip())
                cpu_info['name'] = subprocess.check_output(
                    ['sysctl', '-n', 'machdep.cpu.brand_string']).decode().strip()

            elif platform.system() == "Linux":
                cpu_info['logical_cores'] = os.cpu_count()
                with open('/proc/cpuinfo', 'r') as f:
                    cores = set()
                    for line in f:
                        if line.startswith('physical id'):
                            cores.add(line.split(':')[1].strip())
                    cpu_info['cores'] = len(cores) if cores else os.cpu_count()
                with open('/proc/cpuinfo', 'r') as f:
                    for line in f:
                        if line.startswith('model name'):
                            cpu_info['name'] = line.split(':')[1].strip()
                            break
                try:
                    with open('/proc/stat', 'r') as f:
                        stat_line = f.readline().split()[1:]
                    times = [int(x) for x in stat_line]
                    total_time = sum(times)
                    idle_time = times[3]
                    cpu_info['usage'] = f"{100 * (1 - idle_time / total_time):.1f}%"
                except Exception:
                    cpu_info['usage'] = 'N/A'

            return cpu_info
        except Exception as e:
            return {'name': 'N/A', 'cores': 'N/A', 'logical_cores': 'N/A', 'usage': 'N/A'}

    @staticmethod
    def get_memory_info() -> Dict[str, Any]:
        try:
            mem_info = {'total': 'N/A', 'used': 'N/A', 'percent': 'N/A', 'available': 'N/A'}

            if platform.system() == "Linux":
                with open('/proc/meminfo', 'r') as f:
                    mem_data = {}
                    for line in f:
                        parts = line.split(':')
                        if len(parts) == 2:
                            key = parts[0].strip()
                            value = parts[1].strip().split()[0]
                            mem_data[key] = int(value) * 1024
                total = mem_data.get('MemTotal')
                free = mem_data.get('MemFree')
                buffers = mem_data.get('Buffers', 0)
                cached = mem_data.get('Cached', 0)
                sreclaimable = mem_data.get('SReclaimable', 0)
                if total is not None and free is not None:
                    available = free + buffers + cached + sreclaimable
                    used = total - free - buffers - cached - sreclaimable
                    percent = (used / total) * 100
                    mem_info = {
                        'total': f"{total / (1024**3):.2f} GB",
                        'used': f"{used / (1024**3):.2f} GB",
                        'percent': f"{percent:.1f}%",
                        'available': f"{available / (1024**3):.2f} GB"
                    }

            elif platform.system() == "Darwin":
                total = int(subprocess.check_output(
                    ['sysctl', '-n', 'hw.memsize']).decode().strip())
                vm_stat = subprocess.check_output(['vm_stat']).decode().split('\n')
                stats = {}
                for line in vm_stat:
                    if ':' in line:
                        key, value = line.split(':', 1)
                        stats[key.strip()] = int(value.strip().rstrip('.'))
                free = (stats['Pages free'] + stats['Pages inactive']) * 4096
                used = total - free
                percent = (used / total) * 100
                mem_info = {
                    'total': f"{total / (1024**3):.2f} GB",
                    'used': f"{used / (1024**3):.2f} GB",
                    'percent': f"{percent:.1f}%",
                    'available': f"{free / (1024**3):.2f} GB"
                }

            return mem_info
        except Exception as e:
            return {'total': 'N/A', 'used': 'N/A', 'percent': 'N/A', 'available': 'N/A'}

    @staticmethod
    def get_disk_info() -> Dict[str, Any]:
        try:
            disk_info = {'total': 'N/A', 'used': 'N/A', 'percent': 'N/A', 'free': 'N/A'}

            if platform.system() == "Linux":
                df_output = subprocess.check_output(
                    ['df', '-B1', '/']).decode().split('\n')[1]
                parts = df_output.split()
                if len(parts) >= 5:
                    total = int(parts[1])
                    used = int(parts[2])
                    free = int(parts[3])
                    percent = parts[4].rstrip('%')
                    disk_info = {
                        'total': f"{total / (1024**3):.2f} GB",
                        'used': f"{used / (1024**3):.2f} GB",
                        'percent': f"{percent}%",
                        'free': f"{free / (1024**3):.2f} GB"
                    }

            elif platform.system() == "Darwin":
                df_output = subprocess.check_output(
                    ['df', '/']).decode().split('\n')[1]
                parts = [p for p in df_output.split(' ') if p]
                if len(parts) >= 9:
                    total = int(parts[8])
                    used = int(parts[9])
                    free = int(parts[10])
                    percent = parts[4].rstrip('%')
                    disk_info = {
                        'total': f"{total / (1024**3):.2f} GB",
                        'used': f"{used / (1024**3):.2f} GB",
                        'percent': f"{percent}%",
                        'free': f"{free / (1024**3):.2f} GB"
                    }

            return disk_info
        except Exception as e:
            return {'total': 'N/A', 'used': 'N/A', 'percent': 'N/A', 'free': 'N/A'}

    @staticmethod
    def get_load_average() -> Dict[str, str]:
        try:
            if platform.system() == "Linux":
                with open('/proc/loadavg', 'r') as f:
                    parts = f.read().split()
                return {'1min': parts[0], '5min': parts[1], '15min': parts[2]}
            elif platform.system() == "Darwin":
                output = subprocess.check_output(['uptime']).decode().strip()
                match = re.search(r'load averages?: ([\d.]+) ([\d.]+) ([\d.]+)', output)
                if match:
                    return {'1min': match.group(1), '5min': match.group(2), '15min': match.group(3)}
            return {'1min': 'N/A', '5min': 'N/A', '15min': 'N/A'}
        except Exception:
            return {'1min': 'N/A', '5min': 'N/A', '15min': 'N/A'}

    @staticmethod
    def get_network_info() -> Dict[str, Any]:
        try:
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
            return {'hostname': hostname, 'ip': ip}
        except Exception:
            return {'hostname': 'N/A', 'ip': 'N/A'}
