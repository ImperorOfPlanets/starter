from starter_files.core.base_module import BaseModule
import os
import platform
import re
import socket
import subprocess
import sys
import ctypes

from datetime import datetime, timedelta
from typing import Dict, Any
from pathlib import Path

from starter_files.core.utils.globalVars_utils import set_global, get_global

class SystemModule(BaseModule):

    @staticmethod
    def check() -> bool:
        return True

    @staticmethod
    def collect_basic_system_info() -> Dict[str, Any]:
        """Собирает базовую информацию о системе (без зависимостей от внешних утилит)"""

        # Проверякем где запущен скрипт в докере или нет
        set_global('running_in_docker', SystemModule.running_in_docker())

        privilege_info = SystemModule.get_privilege_info()
        set_global('is_root', privilege_info['is_root'])
        set_global('has_sudo', privilege_info['has_sudo'])
        set_global('use_sudo', privilege_info['use_sudo'])

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

        venv_path = SystemModule.detect_venv_path()
        python_path = str(Path(venv_path) / 'bin' / 'python') if venv_path else sys.executable

        os_name, os_version = SystemModule.detect_os_name_version()

        sys_info = {
            # Ядро
            'core': platform.system(),
            'core_version': platform.version(),
            'core_release': platform.release(),

            # ОС
            'os': os_name,
            'os_version': os_version,
            'os_family': SystemModule.get_os_family(),
            'os_type': SystemModule.get_os_type(),

            'architecture': platform.machine(),
            'hostname': socket.gethostname(),
            'username': os.getenv('USER') or os.getenv('USERNAME') or 'N/A',
            'current_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'python_info': {
                'version': platform.python_version(),
                'implementation': platform.python_implementation(),
                'compiler': platform.python_compiler(),
                'executable': sys.executable
            },
            'venv_path': venv_path,
            'python_path': python_path,
            'is_service': '--service' in sys.argv,
            'environment_vars': {
                'PATH': os.getenv('PATH'),
                'LANG': os.getenv('LANG'),
                'HOME': os.getenv('HOME')
            },
            'script_path': Path(sys.argv[0]).absolute().parent,
            'starter_path': Path(sys.argv[0]).absolute().parent,
            'privilege_info': privilege_info,
            'uptime': SystemModule.get_system_uptime(),
            'timezone': SystemModule.get_timezone_info(),
        }

        for key, value in sys_info.items():
            set_global(key, value)
        return sys_info

    @staticmethod
    def get_privilege_info() -> Dict[str, bool]:
        """Возвращает информацию о привилегиях пользователя"""
        is_root = False
        try:
            # Linux/MacOS
            if hasattr(os, 'getuid'):
                is_root = os.getuid() == 0
            # Windows
            else:
                is_root = ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception as e:
            is_root = False
        
        has_sudo = False
        if not is_root:
            try:
                # Проверяем доступность sudo
                result = subprocess.run(
                    ['sudo', '-n', 'true'],
                    check=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=2
                )
                has_sudo = result.returncode == 0
            except (FileNotFoundError, subprocess.TimeoutExpired, subprocess.CalledProcessError):
                has_sudo = False
            except Exception as e:
                has_sudo = False
        
        return {
            'is_root': is_root,
            'has_sudo': has_sudo,
            'use_sudo': not is_root and has_sudo
        }

    @staticmethod
    def check_sudo() -> bool:
        """Проверяет, нужно ли использовать sudo для выполнения команд"""
        priv_info = SystemModule.get_privilege_info()
        return priv_info['use_sudo']

    @staticmethod
    def check_python_version() -> bool:
        """Проверяет соответствие версии Python требованиям"""
        version_info = sys.version_info
        if version_info < (3, 8):
            return False
        return True

    @staticmethod
    def detect_os_name():
        try:
            with open("/etc/os-release") as f:
                data = dict(line.strip().split("=", 1) for line in f if "=" in line)
            return data.get("PRETTY_NAME") or data.get("NAME")
        except Exception:
            return "Unknown"

    @staticmethod
    def detect_os_name_version():
        """
        Определяет ОС и версию ОС.
        Возвращает кортеж (os, os_version):
            os: windows, linux, darwin, или unknown
            os_version: версия ОС
        """
        system = platform.system().lower()
        
        # Для Windows
        if system == "windows":
            version = platform.version()
            release = platform.release()
            return "windows", f"{release}_{version}"
        
        # Для Linux
        elif system == "linux":
            try:
                with open("/etc/os-release") as f:
                    data = dict(line.strip().split("=", 1) for line in f if "=" in line)
                pretty_name = data.get("PRETTY_NAME") or data.get("NAME") or "unknown"
                pretty_name = pretty_name.strip().strip('"')
                
                parts = pretty_name.split(" ", 1)
                name = parts[0].lower()
                version = parts[1].split(" ")[0] if len(parts) > 1 else "unknown"
                return name, version
            except Exception:
                return "linux", "unknown"
        
        # Для macOS
        elif system == "darwin":
            version = platform.mac_ver()[0]
            return "macos", version
        
        # Для неизвестных систем
        else:
            return "unknown", "unknown"

    @staticmethod
    def get_os_family() -> str:
        """
        Определяет семейство операционной системы.
        Возвращает: 'debian', 'rhel', 'arch', 'suse', 'macos', 'windows' или 'unknown'
        """
        system = platform.system().lower()
        
        # Для Windows и macOS сразу возвращаем результат
        if system == 'windows':
            return 'windows'
        elif system == 'darwin':
            return 'macos'
        
        # Для Linux определяем дистрибутив
        try:
            # Пробуем прочитать /etc/os-release
            with open('/etc/os-release', 'r') as f:
                content = f.read()
            
            # Ищем ID_LIKE или ID
            id_like_match = re.search(r'ID_LIKE="?([^"\n]+)"?', content)
            id_match = re.search(r'ID="?([^"\n]+)"?', content)
            
            if id_like_match:
                ids = id_like_match.group(1).lower()
            elif id_match:
                ids = id_match.group(1).lower()
            else:
                return 'unknown'
            
            # Определяем семейство по известным меткам
            if 'debian' in ids or 'ubuntu' in ids:
                return 'debian'
            elif 'rhel' in ids or 'fedora' in ids or 'centos' in ids:
                return 'rhel'
            elif 'arch' in ids:
                return 'arch'
            elif 'suse' in ids or 'opensuse' in ids:
                return 'suse'
            else:
                return 'unknown'
                
        except FileNotFoundError:
            # Если файла нет, пробуем определить через менеджер пакетов
            try:
                # Проверяем apt (Debian/Ubuntu)
                subprocess.run(['apt', '--version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                return 'debian'
            except:
                try:
                    # Проверяем yum/dnf (RHEL/CentOS/Fedora)
                    subprocess.run(['yum', '--version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                    return 'rhel'
                except:
                    try:
                        # Проверяем pacman (Arch)
                        subprocess.run(['pacman', '--version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                        return 'arch'
                    except:
                        try:
                            # Проверяем zypper (SUSE)
                            subprocess.run(['zypper', '--version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                            return 'suse'
                        except:
                            return 'unknown'

    def get_os_type() -> str:
        """
        Определяет тип операционной системы.
        Возвращает: 'linux', 'windows', 'macos' или 'unknown'
        """
        system = platform.system().lower()
        
        if system == 'linux':
            return 'linux'
        elif system == 'windows':
            return 'windows'
        elif system == 'darwin':
            return 'macos'
        else:
            return 'unknown'

    @staticmethod
    def check_docker_compose_installed() -> bool:
        """Проверяет, установлен ли Docker Compose (POSIX-совместимый метод)"""
        try:
            result = subprocess.run(
                ['docker-compose', '--version'],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return result.returncode == 0
        except (FileNotFoundError, PermissionError):
            return False
        except Exception as e:
            return False

    @staticmethod
    def get_cpu_info() -> Dict[str, Any]:
        """Возвращает информацию о процессоре (POSIX-совместимый метод)"""
        try:
            cpu_info = {
                'name': 'N/A',
                'cores': 'N/A',
                'logical_cores': 'N/A',
                'usage': 'N/A'
            }
            
            # Получаем количество ядер
            if platform.system() == "Darwin":
                # macOS
                cpu_info['logical_cores'] = int(subprocess.check_output(
                    ['sysctl', '-n', 'hw.logicalcpu']).decode().strip())
                cpu_info['cores'] = int(subprocess.check_output(
                    ['sysctl', '-n', 'hw.physicalcpu']).decode().strip())
            elif platform.system() == "Linux":
                # Linux
                cpu_info['logical_cores'] = os.cpu_count()
                with open('/proc/cpuinfo', 'r') as f:
                    cores = set()
                    for line in f:
                        if line.startswith('physical id'):
                            cores.add(line.split(':')[1].strip())
                    cpu_info['cores'] = len(cores) if cores else os.cpu_count()
            
            # Получаем модель процессора
            if platform.system() == "Darwin":
                cpu_info['name'] = subprocess.check_output(
                    ['sysctl', '-n', 'machdep.cpu.brand_string']).decode().strip()
            elif platform.system() == "Linux":
                with open('/proc/cpuinfo', 'r') as f:
                    for line in f:
                        if line.startswith('model name'):
                            cpu_info['name'] = line.split(':')[1].strip()
                            break
            
            # Получаем загрузку CPU
            if platform.system() in ["Linux", "Darwin"]:
                try:
                    # Читаем первую строку /proc/stat
                    with open('/proc/stat', 'r') as f:
                        stat_line = f.readline().split()[1:]
                    # Конвертируем в числа
                    times = [int(x) for x in stat_line]
                    # Суммируем все время CPU
                    total_time = sum(times)
                    # Вычисляем время простоя
                    idle_time = times[3]
                    # Рассчитываем загрузку
                    cpu_info['usage'] = f"{100 * (1 - idle_time / total_time):.1f}%"
                except Exception:
                    cpu_info['usage'] = 'N/A'
            
            return cpu_info
        except Exception as e:
            return {
                'name': 'N/A',
                'cores': 'N/A',
                'logical_cores': 'N/A',
                'usage': 'N/A'
            }

    @staticmethod
    def get_memory_info() -> Dict[str, Any]:
        """Возвращает информацию о памяти (POSIX-совместимый метод)"""
        try:
            mem_info = {
                'total': 'N/A',
                'used': 'N/A',
                'percent': 'N/A',
                'available': 'N/A'
            }
            
            if platform.system() == "Linux":
                with open('/proc/meminfo', 'r') as f:
                    mem_data = {}
                    for line in f:
                        parts = line.split(':')
                        if len(parts) == 2:
                            key = parts[0].strip()
                            value = parts[1].strip().split()[0]
                            mem_data[key] = int(value) * 1024  # kB to bytes
                
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
                # Используем sysctl для macOS
                total = int(subprocess.check_output(
                    ['sysctl', '-n', 'hw.memsize']).decode().strip())
                
                # Используем vm_stat для получения информации об использованной памяти
                vm_stat = subprocess.check_output(['vm_stat']).decode().split('\n')
                stats = {}
                for line in vm_stat:
                    if ':' in line:
                        key, value = line.split(':', 1)
                        stats[key.strip()] = int(value.strip().rstrip('.'))
                
                # Рассчитываем свободную память
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
            return {
                'total': 'N/A',
                'used': 'N/A',
                'percent': 'N/A',
                'available': 'N/A'
            }

    @staticmethod
    def get_disk_info() -> Dict[str, Any]:
        """Возвращает информацию о дисках (POSIX-совместимый метод)"""
        try:
            disk_info = {
                'total': 'N/A',
                'used': 'N/A',
                'percent': 'N/A',
                'free': 'N/A'
            }
            
            if platform.system() == "Linux":
                # Используем df для получения информации о корневой файловой системе
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
                # Используем df для macOS
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
            return {
                'total': 'N/A',
                'used': 'N/A',
                'percent': 'N/A',
                'free': 'N/A'
            }

    @staticmethod
    def get_load_average() -> Dict[str, str]:
        """Возвращает среднюю загрузку системы (POSIX-совместимый метод)"""
        try:
            if platform.system() == "Linux":
                with open('/proc/loadavg', 'r') as f:
                    load_avg = f.read().split()[:3]
                return {
                    '1min': load_avg[0],
                    '5min': load_avg[1],
                    '15min': load_avg[2]
                }
            elif platform.system() == "Darwin":
                # Используем sysctl для macOS
                load_avg = subprocess.check_output(
                    ['sysctl', '-n', 'vm.loadavg']).decode().split()[1:4]
                return {
                    '1min': load_avg[0].rstrip(','),
                    '5min': load_avg[1].rstrip(','),
                    '15min': load_avg[2]
                }
            else:
                return {
                    '1min': 'N/A',
                    '5min': 'N/A',
                    '15min': 'N/A'
                }
        except Exception as e:
            return {
                '1min': 'N/A',
                '5min': 'N/A',
                '15min': 'N/A'
            }

    @staticmethod
    def get_timezone_info() -> Dict[str, str]:
        """Возвращает информацию о временной зоне (POSIX-совместимый метод)"""
        try:
            if platform.system() == "Linux":
                # Читаем симлинк /etc/localtime
                tz_path = os.path.realpath('/etc/localtime')
                if 'zoneinfo' in tz_path:
                    # Извлекаем название зоны
                    tz_name = tz_path.split('zoneinfo/')[-1]
                    return {'timezone': tz_name}
                
                # Альтернативный метод: через /etc/timezone
                if os.path.exists('/etc/timezone'):
                    with open('/etc/timezone', 'r') as f:
                        tz_name = f.read().strip()
                    return {'timezone': tz_name}
            
            elif platform.system() == "Darwin":
                # Используем systemsetup для macOS
                tz_name = subprocess.check_output(
                    ['systemsetup', '-gettimezone']).decode().split(': ')[1].strip()
                return {'timezone': tz_name}
            
            # Возвращаем значение переменной окружения как запасной вариант
            tz_name = os.environ.get('TZ', 'UTC')
            return {'timezone': tz_name}
        except Exception as e:
            return {'timezone': 'UTC'}

    @staticmethod
    def get_system_uptime() -> str:
        """Возвращает время работы системы"""
        try:
            if platform.system() == "Windows":
                # Windows implementation
                tick_count = ctypes.windll.kernel32.GetTickCount64()
                uptime_seconds = tick_count / 1000
            else:
                # Linux/MacOS implementation
                with open('/proc/uptime', 'r') as f:
                    uptime_seconds = float(f.readline().split()[0])
            
            uptime = str(timedelta(seconds=uptime_seconds))
            return uptime.split('.')[0]  # Remove microseconds
        except Exception as e:
            return "N/A"

    @staticmethod
    def running_in_docker() -> bool:
        """Проверяет запущен в докере или нет"""
        if os.name == 'nt':
            return False
        try:
            if Path('/.dockerenv').exists():
                return True
            with open('/proc/1/cgroup', 'r') as f:
                return any('docker' in line for line in f)
        except (FileNotFoundError, PermissionError):
            return False

    @staticmethod
    def detect_venv_path() -> str:
        """Определяет путь к виртуальному окружению (строго POSIX-совместимый)"""
        # 1. Проверяем переменные окружения
        env_venv_path = os.environ.get('STARTER_VENV_PATH')
        if env_venv_path and os.path.exists(env_venv_path):
            return env_venv_path
        
        # 2. Проверяем виртуальное окружение Python
        if hasattr(sys, 'real_prefix'):
            # virtualenv
            return sys.real_prefix
        elif hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix:
            # venv module
            return sys.prefix
        
        # 3. Проверяем стандартные пути
        script_path = get_global('script_path')
        
        # ДОБАВЬТЕ ЭТУ ПРОВЕРКУ:
        if script_path is None:
            # Если script_path не установлен, используем текущую директорию
            script_path = os.path.dirname(os.path.abspath(__file__))
        
        possible_paths = [
            os.path.join(script_path, 'venv'),
            os.path.join(script_path, '.venv'),
            '/app/starter/venv',
            os.path.join(os.path.expanduser('~'), 'venv'),
            '/venv',
            '/opt/venv'
        ]
        
        for path in possible_paths:
            # POSIX-совместимая проверка существования Python
            python_bin = os.path.join(path, 'bin', 'python')
            if os.path.exists(path) and os.path.exists(python_bin):
                # Дополнительная проверка, что это действительно Python
                try:
                    # Проверяем, что файл исполняемый и является Python
                    if os.access(python_bin, os.X_OK):
                        # Проверяем версию Python
                        result = subprocess.run(
                            [python_bin, '--version'],
                            capture_output=True,
                            text=True,
                            timeout=5,
                            check=False
                        )
                        if result.returncode == 0 and 'Python' in result.stdout:
                            return path
                except (OSError, subprocess.TimeoutExpired, subprocess.SubprocessError):
                    continue
        
        # 4. Возвращаем путь по умолчанию
        return os.path.join(script_path, 'venv')

    @staticmethod
    def set_globals():
        """Возвращает время работы системы"""
        set_global("path_log_install",get_global('script_path') / 'starter_files' / 'logs' / 'install')
        set_global("path_log_web",get_global('script_path') / 'starter_files' / 'logs' / 'web')
