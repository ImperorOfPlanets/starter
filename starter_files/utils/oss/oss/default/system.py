import os
import platform
import socket
import subprocess
import sys
import ctypes

from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Tuple

from starter_files.utils.globalVars_utils import set_global, get_global
from starter_files.utils.log_utils import get_logger

logger = get_logger()

class SystemModule:
    @staticmethod
    def check() -> bool:
        return True

    @staticmethod
    def collect_basic_system_info() -> Dict[str, Any]:
        """Собирает базовую информацию о системе (без зависимостей от внешних утилит)"""
        # Получаем информацию о привилегиях
        privilege_info = SystemModule.get_privilege_info()
        
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
            'script_path': Path(sys.argv[0]).absolute().parent,
            'privilege_info': privilege_info  # Добавляем информацию о привилегиях
        }

        # Записываем все ключи из sys_info в глобальные переменные
        for key, value in sys_info.items():
            set_global(key, value)
        
        # Устанавливаем плоские ключи для удобства
        set_global('is_root', privilege_info['is_root'])
        set_global('has_sudo', privilege_info['has_sudo'])
        set_global('use_sudo', privilege_info['use_sudo'])

        return sys_info

    @staticmethod
    def log_basic_system_info() -> None:
        """Логирует полную базовую системную информацию"""
        sys_info = get_global('system_info', {})
        
        if not sys_info:
            sys_info = SystemModule.collect_basic_system_info()  # Исправлено: вызов через класс
        
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
        
        # Информация о привилегиях
        logger.info("\nPrivilege Information:")
        priv_info = sys_info.get('privilege_info', {})
        logger.info(f"  Is root: {priv_info.get('is_root', 'N/A')}")
        logger.info(f"  Has sudo: {priv_info.get('has_sudo', 'N/A')}")
        logger.info(f"  Use sudo: {priv_info.get('use_sudo', 'N/A')}")
        
        # Дополнительно можно добавить логирование всех глобальных переменных
        logger.info("\nGlobal Variables Summary:")
        for key in sys_info.keys():
            if key not in ['python_info', 'environment_vars', 'privilege_info']:
                logger.info(f"  {key}: {sys_info[key]}")

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
            logger.error(f"Error checking root: {e}")
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
                logger.error(f"Error checking sudo: {e}")
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