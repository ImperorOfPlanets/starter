import os
import platform
import socket
import sys
from datetime import datetime
from typing import Dict, Any

from starter_files.utils.global_vars import set_global
from starter_files.utils.logger import get_logger

logger = get_logger()

def collect_basic_system_info() -> Dict[str, Any]:
    """Собирает базовую информацию о системе (без зависимостей от внешних утилит)"""
    sys_info = {
        'os': platform.system(),
        'os_version': platform.version(),
        'os_release': platform.release(),
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
        'is_service': '--service' in sys.argv,
        'environment_vars': {
            'PATH': os.getenv('PATH'),
            'LANG': os.getenv('LANG'),
            'HOME': os.getenv('HOME')
        }
    }
    
    # Сохраняем в глобальные переменные
    set_global('system_info', sys_info)
    set_global('os_name', sys_info['os'])
    set_global('python_version', sys_info['python_info']['version'])
    
    return sys_info

def log_basic_system_info() -> None:
    """Логирует базовую системную информацию"""
    sys_info = get_global('system_info', {})
    
    if not sys_info:
        sys_info = collect_basic_system_info()
    
    logger.info("=== BASIC SYSTEM INFORMATION ===")
    logger.info(f"OS: {sys_info['os']} {sys_info['os_version']} ({sys_info['architecture']})")
    logger.info(f"Hostname: {sys_info['hostname']}")
    logger.info(f"Username: {sys_info['username']}")
    logger.info(f"Python: {sys_info['python_info']['version']} ({sys_info['python_info']['implementation']})")
    logger.info(f"Service mode: {'Yes' if sys_info['is_service'] else 'No'}")