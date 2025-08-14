import os
import sys
import importlib.util
import logging
import platform
from pathlib import Path

logger = logging.getLogger('module_loader')

def load_module_from_path(path: Path, module_name: str) -> object:
    """Загружает модуль из указанного пути"""
    try:
        module_spec = importlib.util.spec_from_file_location(
            f"oss.{module_name}", 
            path
        )
        module = importlib.util.module_from_spec(module_spec)
        sys.modules[module_spec.name] = module
        module_spec.loader.exec_module(module)
        
        class_name = f"{module_name.capitalize()}Module"
        module_class = getattr(module, class_name)
        
        if module_class.check():
            logger.info(f"Loaded module: {path}")
            return module_class
            
    except Exception as e:
        logger.error(f"Error loading module from {path}: {str(e)}", exc_info=True)
    
    return None

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

    # Убираем дубликаты и несуществующие пути
    valid_paths = []
    for path in search_paths:
        if path not in valid_paths and path.exists():
            valid_paths.append(path)
    
    logger.info(f"Searching for {module_name} module in paths: {valid_paths}")

    for path in search_paths:
        logger.info(f"Checking path: {path}")
        if not path.exists():
            logger.info(f"Path not found: {path}")
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

    # Создаем заглушку только в default для ОС
    default_path = _create_default_stub(module_name, os_name)
    logger.error(f"Module {module_name} not found! Created stub: {default_path}")
    
    # Пытаемся загрузить заглушку
    try:
        return load_module_from_path(default_path, module_name)
    except Exception as e:
        logger.critical(f"Failed to load stub module: {str(e)}")
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
        with open(stub_path, 'w', encoding='utf-8') as f:  # Явно указываем кодировку
            stub_content = f'''# -*- coding: utf-8 -*-
"""
ЗАГЛУШКА ДЛЯ МОДУЛЯ {module_name.upper()}
Требуется реализация для ОС: {os_name}
"""

class {module_name.capitalize()}Module:
    @staticmethod
    def check() -> bool:
        """Всегда возвращает False, так как модуль не реализован"""
        return False
'''
            f.write(stub_content)
    
    return stub_path