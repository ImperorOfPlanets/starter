import sys
import importlib.util
import inspect
import logging
import time
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
    for path in search_paths:
        if path.exists():
            logger.info(f"  [FOUND FILE] {path}")
        else:
            logger.info(f"  [NOT FOUND] {path}")

    # Перебор путей для загрузки первого рабочего модуля
    for path in search_paths:
        if not path.exists():
            continue

        module_class = load_module_from_path(path, module_name)
        if module_class is not None:
            _loaded_modules_cache[os_name][module_name] = module_class
            logger.info(f"[LOAD] Модуль {module_name} успешно загружен из {path}")
            return module_class
        else:
            logger.warning(f"[WARNING] Не удалось загрузить класс из {path}")

    # Если модуль не найден — создаём stub
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
    pass
''')
        logger.info(f"[STUB] Создан stub: {stub_path}")

    module_class = load_module_from_path(stub_path, module_name)
    _loaded_modules_cache[os_name][module_name] = module_class
    logger.error(f"[ERROR] Module {module_name} not found! Stub используется: {stub_path}")
    return module_class

#===== Это уже касаеться сюорки комментариев и прочего для раздела разработчиков#

def _method_kind(cls, name: str) -> str:
    """static | class | instance"""
    attr = inspect.getattr_static(cls, name)
    if isinstance(attr, staticmethod):
        return "static"
    if isinstance(attr, classmethod):
        return "class"
    return "instance"

def _extract_inline_comment_after_signature(func_obj) -> str:
    """
    Забирает комментарии сразу ПОСЛЕ строки def ...:
    Останавливается на первой непустой некомментарной строке.
    """
    try:
        src = inspect.getsource(func_obj)
    except OSError:
        return ""
    lines = src.splitlines()
    # найти строку с "def" (пропуская декораторы)
    i = 0
    while i < len(lines) and lines[i].lstrip().startswith("@"):
        i += 1
    # теперь i указывает на строку def
    i += 1
    comment_lines = []
    while i < len(lines):
        s = lines[i].lstrip()
        if not s:
            i += 1
            continue
        if s.startswith("#"):
            # удаляем ведущие "# " или "#"
            comment_lines.append(s[1:].lstrip())
            i += 1
            continue
        break
    return "\n".join(comment_lines).strip()

def _base_paths() -> List[Path]:
    script_path = Path(get_global('script_path'))
    os_name = get_global('os')
    os_version = get_global('os_version')
    return [
        script_path / 'starter_files' / 'utils' / 'oss' / os_name / os_version,
        script_path / 'starter_files' / 'utils' / 'oss' / os_name / 'default',
        script_path / 'starter_files' / 'utils' / 'oss' / 'default',
    ]

def _scan_files() -> List[Path]:
    files = []
    seen = set()
    for base in _base_paths():
        if not base.exists():
            continue
        for p in sorted(base.glob("*.py")):
            # приоритет: первый найденный модуль с этим именем
            key = p.stem
            if key in seen:
                continue
            seen.add(key)
            files.append(p)
    return files

def collect_modules_info(refresh: bool = False) -> List[Dict[str, Any]]:
    """
    Возвращает кэшированный список модулей с функциями и описаниями.
    Кэш в get_global('modules_info_cache').
    Инвалидируем, если изменился mtime любого исходника или OS/os_version/script_path.
    """
    os_name = get_global('os')
    os_version = get_global('os_version')
    script_path = str(get_global('script_path'))

    cache = get_global('modules_info_cache') or {}
    sig = {"os": os_name, "os_version": os_version, "script_path": script_path}

    files = _scan_files()
    files_state = {str(p): p.stat().st_mtime for p in files}

    if (not refresh
        and cache.get("sig") == sig
        and cache.get("files_state") == files_state
        and "items" in cache):
        return cache["items"]

    items: List[Dict[str, Any]] = []
    for py_file in files:
        module_name = py_file.stem
        module_class = load_module_from_path(py_file, module_name)
        if not module_class:
            continue

        # Имя класса по вашей конвенции уже загружено load_module_from_path
        class_name = module_class.__name__

        funcs = []
        for name, member in inspect.getmembers(module_class):
            if name.startswith("__"):
                continue
            if inspect.isfunction(member) or inspect.ismethod(member):
                doc = inspect.getdoc(member) or ""
                inline_comment = _extract_inline_comment_after_signature(member)
                kind = _method_kind(module_class, name)
                funcs.append({
                    "name": name,
                    "kind": kind,  # static | class | instance
                    "doc": doc,
                    "comment": inline_comment,
                })

        items.append({
            "module_name": module_name,
            "class_name": class_name,
            "path": str(py_file),
            "functions": funcs,
        })

    cache = {
        "sig": sig,
        "files_state": files_state,
        "items": items,
        "cached_at": int(time.time()),
    }
    set_global('modules_info_cache', cache)
    return items
