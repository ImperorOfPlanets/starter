import os
import platform
import socket
import sys

from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from starter_files.utils.globalVars_utils import GlobalVars, set_global, get_global
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
        },
        'script_path': Path(sys.argv[0]).absolute().parent
    }

    # Записываем все ключи из sys_info в глобальные переменные
    for key, value in sys_info.items():
        set_global(key, value)

    return sys_info

def log_basic_system_info() -> None:
    """Логирует полную базовую системную информацию"""
    sys_info = get_global('system_info', {})
    
    if not sys_info:
        sys_info = collect_basic_system_info()
    
    logger.info("=== FULL BASIC SYSTEM INFORMATION ===")
    
    # Основные поля
    logger.info(f"Operating System: {sys_info['os']} {sys_info['os_release']} (Version: {sys_info['os_version']})")
    logger.info(f"Architecture: {sys_info['architecture']}")
    logger.info(f"Hostname: {sys_info['hostname']}")
    logger.info(f"Username: {sys_info['username']}")
    logger.info(f"Current Time: {sys_info['current_time']}")
    logger.info(f"Service Mode: {'Yes' if sys_info['is_service'] else 'No'}")
    logger.info(f"Script Path: {sys_info['script_path']}")
    
    # Python информация
    logger.info("\nPython Information:")
    py_info = sys_info['python_info']
    logger.info(f"  Version: {py_info['version']}")
    logger.info(f"  Implementation: {py_info['implementation']}")
    logger.info(f"  Compiler: {py_info['compiler']}")
    logger.info(f"  Executable: {py_info['executable']}")
    
    # Переменные окружения
    logger.info("\nEnvironment Variables:")
    env_vars = sys_info['environment_vars']
    for var, value in env_vars.items():
        if value:  # Логируем только если значение не None/пустое
            logger.info(f"  {var}: {value}")
    
    # Дополнительно можно добавить логирование всех глобальных переменных
    logger.info("\nGlobal Variables Summary:")
    for key in sys_info.keys():
        if key not in ['python_info', 'environment_vars']:  # Эти уже логировались
            logger.info(f"  {key}: {sys_info[key]}")