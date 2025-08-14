import os
import sys
import importlib.util
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
    """
    os_name = get_global('os')
    logger.debug(f"[DEBUG VAR] os_name = {os_name}")

    os_version = get_global('os_version')
    logger.debug(f"[DEBUG VAR] os_version = {os_version}")

    if os_name not in _loaded_modules_cache:
        _loaded_modules_cache[os_name] = {}

    if module_name in _loaded_modules_cache[os_name]:
        cached = _loaded_modules_cache[os_name][module_name]
        logger.debug(f"[DEBUG VAR] cached = {cached}")
        if cached is None:
            logger.warning(f"[CACHE] Модуль {module_name} в кеше = None!")
        else:
            logger.debug(f"[CACHE] Модуль {module_name} загружен из кеша для ОС {os_name}")
        return cached

    script_path = Path(get_global('script_path'))
    search_paths = [
        script_path / 'starter_files' / 'utils' / 'oss' / os_name / os_version / f"{module_name}.py",
        script_path / 'starter_files' / 'utils' / 'oss' / os_name / 'default' / f"{module_name}.py",
        script_path / 'starter_files' / 'utils' / 'oss' / 'default' / f"{module_name}.py"
    ]
    logger.debug(f"[DEBUG VAR] search_paths = {search_paths}")

    logger.info(f"[SEARCH] Ищем модуль '{module_name}' для ОС '{os_name}'")
    found = False
    for path in search_paths:
        logger.debug(f"[DEBUG VAR] path check = {path}")
        if path.exists():
            found = True
            logger.info(f"[FOUND] Найден файл модуля: {path}")
            module_class = load_module_from_path(path, module_name)
            logger.debug(f"[DEBUG VAR] module_class = {module_class}")

            if module_class:
                check_result = getattr(module_class, 'check', lambda: False)()
                logger.debug(f"[DEBUG VAR] check_result = {check_result}")
                logger.info(f"[CHECK] check() -> {check_result} для {module_name}")

                if check_result:
                    _loaded_modules_cache[os_name][module_name] = module_class
                    logger.info(f"[LOAD] Загружен модуль: {path}")
                    return module_class
                else:
                    logger.warning(f"[CHECK FAILED] check() вернул False для {module_name}")
        else:
            logger.debug(f"[NOT FOUND] Путь не найден: {path}")

    if not found:
        logger.warning(f"[WARN] Модуль {module_name} не найден ни в одном пути, будет создан stub.")

    default_stub_dir = Path(__file__).parent / 'oss' / os_name / 'default'
    logger.debug(f"[DEBUG VAR] default_stub_dir = {default_stub_dir}")

    default_stub_dir.mkdir(parents=True, exist_ok=True)
    stub_path = default_stub_dir / f"{module_name}.py"
    logger.debug(f"[DEBUG VAR] stub_path = {stub_path}")

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
    logger.debug(f"[DEBUG VAR] stub module_class = {module_class}")

    _loaded_modules_cache[os_name][module_name] = module_class
    logger.error(f"[ERROR] Module {module_name} not found! Stub используется: {stub_path}")
    return module_class
