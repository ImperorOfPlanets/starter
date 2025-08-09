import os
import sys
import platform
import socket
from datetime import datetime, timedelta
from pathlib import Path
from starter_files.utils.docker_utils import DockerUtils
from starter_files.utils.fs_utils import FSUtils
from starter_files.utils.i18n import t

from starter_files.utils.logger import get_logger
logger = get_logger()

def collect_system_info(registry_url="gitflic.myidon.site:80"):
    """Собирает полную системную информацию"""
    sys_info = {
        'os': platform.system(),
        'os_version': platform.version(),
        'python_version': platform.python_version(),
        'docker_installed': DockerUtils.check_installed(),
        'docker_compose_installed': DockerUtils.check_docker_compose_installed(),
        'docker_registry_auth': DockerUtils.check_docker_registry_auth(registry_url),
        'registry_url': registry_url,
        'is_service': '--service-run' in sys.argv,
        'hostname': socket.gethostname(),
        'username': os.getenv('USER') or os.getenv('USERNAME') or 'N/A',
        'current_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'uptime': get_system_uptime(),
        'cpu': get_cpu_info(),
        'memory': get_memory_info(),
        'disk': get_disk_usage(),
        'python_info': {
            'version': platform.python_version(),
            'implementation': platform.python_implementation(),
            'compiler': platform.python_compiler()
        }
    }
    return sys_info

def log_system_info(sys_info):
    """Логирует системную информацию"""
    logger.log("=== SYSTEM INFORMATION ===", "SYSTEM")
    logger.log(f"OS: {sys_info['os']} {sys_info['os_version']}", "SYSTEM")
    logger.log(f"Python: {sys_info['python_version']}", "SYSTEM")
    
    # Docker информация
    docker_status = "Installed" if sys_info['docker_installed'] else "Not installed"
    compose_status = "Installed" if sys_info['docker_compose_installed'] else "Not installed"
    auth_status = "Authenticated" if sys_info['docker_registry_auth'] else "Not authenticated"
    
    logger.log(f"Docker: {docker_status}", "SYSTEM")
    logger.log(f"Docker Compose: {compose_status}", "SYSTEM")
    logger.log(f"Registry Auth ({sys_info['registry_url']}): {auth_status}", "SYSTEM")
    
    # IP-адреса
    ips = ', '.join(sys_info['valid_ips']) if sys_info['valid_ips'] else "not detected"
    logger.log(f"IP addresses: {ips}", "SYSTEM")

def get_system_uptime():
    """Возвращает время работы системы"""
    try:
        if platform.system() == 'Windows':
            import psutil
            return str(datetime.now() - datetime.fromtimestamp(psutil.boot_time()))
        else:
            with open('/proc/uptime', 'r') as f:
                uptime_seconds = float(f.readline().split()[0])
                return str(timedelta(seconds=uptime_seconds))
    except Exception:
        return t('unknown')

def get_cpu_info():
    """Возвращает информацию о процессоре"""
    try:
        import psutil
        return {
            'name': platform.processor(),
            'cores': psutil.cpu_count(logical=False),
            'logical_cores': psutil.cpu_count(logical=True),
            'usage': f"{psutil.cpu_percent(interval=1)}%"
        }
    except Exception:
        return {
            'name': t('unknown'),
            'cores': t('unknown'),
            'logical_cores': t('unknown'),
            'usage': t('unknown')
        }

def get_memory_info():
    """Возвращает информацию об оперативной памяти"""
    try:
        import psutil
        mem = psutil.virtual_memory()
        return {
            'total': f"{mem.total / (1024**3):.2f} GB",
            'available': f"{mem.available / (1024**3):.2f} GB",
            'used': f"{mem.used / (1024**3):.2f} GB",
            'percent': f"{mem.percent}%"
        }
    except Exception:
        return {
            'total': t('unknown'),
            'available': t('unknown'),
            'used': t('unknown'),
            'percent': t('unknown')
        }

def get_disk_usage():
    """Возвращает информацию о использовании диска"""
    try:
        import psutil
        disk = psutil.disk_usage('/')
        return {
            'total': f"{disk.total / (1024**3):.2f} GB",
            'used': f"{disk.used / (1024**3):.2f} GB",
            'free': f"{disk.free / (1024**3):.2f} GB",
            'percent': f"{disk.percent}%"
        }
    except Exception:
        return {
            'total': t('unknown'),
            'used': t('unknown'),
            'free': t('unknown'),
            'percent': t('unknown')
        }

def display_system_info(sys_info):
    """Выводит системную информацию на экран (для интерактивного режима)"""
    print(f"\n=== {t('system_info')} ===")
    print(f"{t('os_version')}: {sys_info['os']} {sys_info['os_version']}")
    print(f"{t('python_version')}: {sys_info['python_version']}")
    
    # Docker информация
    docker_status = t('docker_installed') if sys_info['docker_installed'] else t('docker_not_installed')
    compose_status = t('docker_compose_installed') if sys_info['docker_compose_installed'] else t('docker_compose_not_installed')
    auth_status = t('docker_auth_success') if sys_info['docker_registry_auth'] else t('docker_auth_required', registry=sys_info['registry_url'])

    
    print(f"\nDocker: {docker_status}")
    print(f"Docker Compose: {compose_status}")
    print(f"Registry Auth ({sys_info['registry_url']}): {auth_status}")
    
    # IP-адреса
    print(f"\n{t('ip_addresses')}: {', '.join(sys_info['valid_ips']) if sys_info['valid_ips'] else t('no_ips_found')}")

def handle_system_info(registry_url="gitflic.myidon.site:80"):
    """
    Основная функция обработки системной информации
    Автоматически определяет режим работы и соответствующим образом логирует/выводит информацию
    """
    sys_info = collect_system_info(registry_url)
    log_system_info(sys_info)
    
    if not sys_info['is_service']:
        display_system_info(sys_info)
    
    return sys_info