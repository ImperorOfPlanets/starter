import os
import sys
import importlib.util
import inspect
import logging
import platform
from pathlib import Path
from starter_files.utils.globalVars_utils import set_global, get_global
from typing import List, Dict, Any

logger = logging.getLogger('module_loader')

# === Глобальный кеш загруженных модулей ===
# Структура: {os_name: {module_name: module_class}}
_loaded_modules_cache = {}

def load_module_from_path(path: Path, module_name: str) -> object:
    """Загружает модуль из указанного пути"""
    logger.debug(f"[DEBUG VAR] path = {path}")
    logger.debug(f"[DEBUG VAR] module_name = {module_name}")

    try:
        module_spec = importlib.util.spec_from_file_location(
            f"oss.{module_name}", 
            path
        )
        logger.debug(f"[DEBUG VAR] module_spec = {module_spec}")

        module = importlib.util.module_from_spec(module_spec)
        sys.modules[module_spec.name] = module
        module_spec.loader.exec_module(module)

        class_name = f"{module_name.capitalize()}Module"
        logger.debug(f"[DEBUG VAR] class_name = {class_name}")

        module_class = getattr(module, class_name)
        logger.debug(f"[DEBUG VAR] module_class = {module_class}")

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
    При первой загрузке выводит список всех найденных файлов модулей.
    """
    os_name = get_global('os')
    os_version = get_global('os_version')

    if os_name not in _loaded_modules_cache:
        _loaded_modules_cache[os_name] = {}

    if module_name in _loaded_modules_cache[os_name]:
        return _loaded_modules_cache[os_name][module_name]

    script_path = Path(get_global('script_path'))
    search_paths = [
        script_path / 'starter_files' / 'utils' / 'oss' / os_name / os_version / f"{module_name}.py",
        script_path / 'starter_files' / 'utils' / 'oss' / os_name / 'default' / f"{module_name}.py",
        script_path / 'starter_files' / 'utils' / 'oss' / 'default' / f"{module_name}.py"
    ]

    # === Логируем все найденные пути ===
    logger.info(f"[INFO] Проверка путей для модуля '{module_name}':")
    found_paths = []
    for path in search_paths:
        if path.exists():
            logger.info(f"  [FOUND FILE] {path}")
            found_paths.append(path)
        else:
            logger.info(f"  [NOT FOUND] {path}")

    # Перебор для загрузки первого рабочего модуля
    for path in search_paths:
        logger.debug(f"[DEBUG] Проверяем путь: {path}")

        if not path.exists():
            logger.debug(f"[DEBUG] Файл не найден: {path}")
            continue

        logger.info(f"[FOUND] Файл модуля найден: {path}")

        module_class = load_module_from_path(path, module_name)
        if module_class is None:
            logger.warning(f"[WARNING] Не удалось загрузить класс из {path}")
            continue

        logger.debug(f"[DEBUG] Загруженный класс: {module_class}")

        check_method = getattr(module_class, 'check', None)
        if check_method is None:
            logger.warning(f"[WARNING] В классе {module_class} отсутствует метод check()")
            continue

        logger.debug(f"[DEBUG] Вызываем check() для {module_class}")
        try:
            check_result = check_method()
        except Exception as e:
            logger.error(f"[ERROR] Ошибка при вызове check() для {module_class}: {e}", exc_info=True)
            continue

        logger.info(f"[CHECK] check() -> {check_result} для {module_name}")

        if check_result:
            _loaded_modules_cache[os_name][module_name] = module_class
            logger.info(f"[LOAD] Модуль {module_name} успешно загружен из {path}")
            return module_class
        else:
            logger.warning(f"[CHECK FAILED] check() вернул False для {module_name} в {path}")
    
    # Если модуль не найден — создаем stub
    default_stub_dir = script_path / 'starter_files' / 'utils' / 'oss' / os_name / 'default'
    default_stub_dir.mkdir(parents=True, exist_ok=True)
    stub_path = default_stub_dir / f"{module_name}.py"

    if not stub_path.exists():
        with open(stub_path, 'w', encoding='utf-8') as f:
            f.write(f'''# -*- coding: utf-8 -*-
"""
Stub для модуля {module_name.upper()} для ОС {os_name}
"""
class {module_name.capitalize()}Module:
    @staticmethod
    def check() -> bool:
        return False
''')
        logger.info(f"[STUB] Создан stub: {stub_path}")

    module_class = load_module_from_path(stub_path, module_name)
    _loaded_modules_cache[os_name][module_name] = module_class
    logger.error(f"[ERROR] Module {module_name} not found! Stub используется: {stub_path}")
    return module_class