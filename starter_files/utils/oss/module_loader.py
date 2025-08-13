import os
import sys
import importlib.util
import logging
import platform
from pathlib import Path

logger = logging.getLogger('module_loader')

def load_module(module_name: str) -> object:
    """
    Загружает модуль по приоритету:
    1. Конкретная версия ОС
    2. Default для ОС
    3. Общий default
    """
    os_name = platform.system().lower()
    os_version = _get_os_version(os_name)
    
    # Пути для поиска
    search_paths = [
        Path(__file__).parent / 'oss' / os_name / os_version / f"{module_name}.py",
        Path(__file__).parent / 'oss' / os_name / 'default' / f"{module_name}.py",
        Path(__file__).parent / 'oss' / 'default' / f"{module_name}.py"
    ]
    
    for path in search_paths:
        if not path.exists():
            continue
            
        try:
            # Динамическая загрузка модуля
            module_spec = importlib.util.spec_from_file_location(
                f"oss.{os_name}.{module_name}", 
                path
            )
            module = importlib.util.module_from_spec(module_spec)
            sys.modules[module_spec.name] = module
            module_spec.loader.exec_module(module)
            
            # Ищем класс модуля
            class_name = f"{module_name.capitalize()}Module"
            module_class = getattr(module, class_name)
            
            if module_class.check():
                logger.info(f"Загружен модуль: {path}")
                return module_class
                
        except Exception as e:
            logger.error(f"Ошибка загрузки модуля {path}: {str(e)}")
    
    # Создаем заглушку в default для ОС
    default_path = _create_default_stub(module_name, os_name)
    logger.error(f"Модуль {module_name} не найден! Создана заглушка: {default_path}")
    
    # Пытаемся загрузить заглушку
    try:
        from starter_files.utils.oss.oss.default import network
        return network.NetworkModule
    except ImportError:
        logger.critical("Не удалось загрузить даже заглушку!")
        return None

def _get_os_version(os_name: str) -> str:
    """Получает нормализованную версию ОС"""
    if os_name == "windows":
        return platform.release()
    
    try:
        # Для Linux систем
        if os_name in ["linux", "ubuntu", "debian"]:
            with open('/etc/os-release') as f:
                for line in f:
                    if line.startswith('VERSION_ID='):
                        return line.split('=')[1].strip().strip('"')
    except Exception:
        pass
    
    return platform.release()

def _create_default_stub(module_name: str, os_name: str) -> Path:
    """Создает заглушку в default для ОС"""
    default_dir = Path(__file__).parent / 'oss' / os_name / 'default'
    default_dir.mkdir(parents=True, exist_ok=True)
    
    stub_path = default_dir / f"{module_name}.py"
    
    if not stub_path.exists():
        with open(stub_path, 'w') as f:
            stub_content = f'''"""
ЗАГЛУШКА ДЛЯ МОДУЛЯ {module_name.upper()}
Требуется реализация для ОС: {os_name}
"""

from starter_files.utils.oss.base_module import BaseModule

class {module_name.capitalize()}Module(BaseModule):
    @classmethod
    def check(cls) -> bool:
        """Всегда возвращает False, так как модуль не реализован"""
        return False
    
    @staticmethod
    def get_ips() -> list:
        """Заглушка для получения IP-адресов"""
        from starter_files.utils.oss.oss.default.network import NetworkModule
        return NetworkModule.get_ips()
'''
            f.write(stub_content)
    
    return stub_path