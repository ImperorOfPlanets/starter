# files/core/utils/loader_utils.py
import sys
import importlib.util
import inspect
import time
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

from files.core.utils.globalVars_utils import set_global, get_global
from files.core.utils.log_utils import LogManager

LogManager.register_log_dir('modules', 'modules')
logger = LogManager.get_logger('modules')

_modules_cache = {}  # Формат: {module_name: [impl1, impl2, impl3]}


def load_modules(refresh: bool = False):
    """
    Сканирует все модули под текущую ОС и создаёт кеш функций с приоритетами.
    """
    global _modules_cache
    
    print("\n" + "═" * 70)
    print("🔍 ЗАГРУЗКА МОДУЛЕЙ")
    print("═" * 70)
    
    logger.info("\n=== ЗАГРУЗКА МОДУЛЕЙ ===")
    if _modules_cache and not refresh:
        print(f"   ✅ Используем кеш: {len(_modules_cache)} модулей")
        return _modules_cache

    # ИСПОЛЬЗУЕМ starter_path из глобальных переменных (установлен в SystemModule)
    starter_path = get_global("starter_path")
    if starter_path is None:
        print("❌ starter_path не установлен! Сначала выполните SystemModule.collect_basic_system_info()")
        return {}
    
    os_name = get_global("os")
    os_version = get_global("os_version")
    
    print(f"📁 starter_path: {starter_path}")
    print(f"🖥️ Текущая ОС: {os_name} {os_version}")
    print("")
    
    logger.info(f"Текущая ОС: {os_name} {os_version}")

    base_categories = [
        ("oss", starter_path / "files" / "core" / "oss"),
        ("software", starter_path / "files" / "core" / "software")
    ]

    # Словарь для сбора всех реализаций
    all_implementations = {}

    for category_name, base_dir in base_categories:
        print(f"\n📂 Категория: {category_name.upper()}")
        print(f"   Базовая директория: {base_dir}")
        print(f"   Существует: {'✅' if base_dir.exists() else '❌ НЕТ!'}")
        
        logger.info(f"\nПоиск модулей в категории: {category_name.upper()}")
        
        search_paths = [
            (0, base_dir / os_name / os_version),      # 1. Самая специфичная
            (1, base_dir / os_name / "default"),       # 2. Общая для ОС
            (2, base_dir / "default"),                 # 3. Общая реализация
        ]

        print(f"\n   Пути поиска (в порядке приоритета):")
        for level, search_path in search_paths:
            exists = "✅ НАЙДЕН" if search_path.exists() else "❌ не найден"
            print(f"      [{level}] {search_path} [{exists}]")
            
            logger.info(f"   Уровень {level}: {search_path} [{exists}]")

            if not search_path.exists():
                continue

            print(f"\n   Сканирование файлов в: {search_path}")
            py_files = list(search_path.glob("*.py"))
            print(f"      Найдено .py файлов: {len(py_files)}")
            
            for py_file in py_files:
                if py_file.name.startswith("__"):
                    print(f"         ⏭️ Пропускаем: {py_file.name} (__init__)")
                    continue
                    
                module_name = py_file.stem
                print(f"\n      📄 Обработка: {py_file.name} -> модуль '{module_name}'")
                
                # Инициализируем список для модуля, если нужно
                if module_name not in all_implementations:
                    all_implementations[module_name] = []
                    
                # Проверяем, есть ли уже реализация с таким же путем
                existing_paths = [str(impl["path"]) for impl in all_implementations[module_name]]
                if str(py_file) in existing_paths:
                    print(f"         ⏭️ Пропускаем (уже загружен)")
                    continue

                try:
                    print(f"         🔄 Загрузка модуля...")
                    module_class = load_module_from_path(py_file, py_file.stem)

                    if module_class is None:
                        print(f"         ❌ Не удалось загрузить класс модуля")
                        continue

                    # Собираем методы
                    methods = {}
                    method_count = 0
                    for name, member in inspect.getmembers(module_class):
                        if name.startswith("__"):
                            continue
                        if inspect.isfunction(member) or inspect.ismethod(member):
                            methods[name] = member
                            method_count += 1

                    # Добавляем реализацию в список
                    all_implementations[module_name].append({
                        "class": module_class,
                        "methods": methods,
                        "path": py_file,
                        "level": level,
                    })
                    print(f"         ✅ Модуль '{module_name}' загружен (уровень {level}, методов: {method_count})")
                    
                except Exception as e:
                    print(f"         ❌ Ошибка загрузки: {e}")
                    logger.error(f"Ошибка загрузки {py_file}: {e}")

    # Сортируем реализации по приоритету для каждого модуля
    for module_name in all_implementations:
        all_implementations[module_name].sort(key=lambda x: x["level"])
    
    _modules_cache = all_implementations

    # Выводим итоги
    print("\n" + "═" * 70)
    print("📊 ИТОГИ ЗАГРУЗКИ МОДУЛЕЙ")
    print("═" * 70)
    print(f"   ✅ Всего загружено модулей: {len(_modules_cache)}")
    
    if _modules_cache:
        print(f"\n   📋 Список загруженных модулей:")
        for module_name in sorted(_modules_cache.keys()):
            implementations = _modules_cache[module_name]
            print(f"      - {module_name} ({len(implementations)} реализаций)")
            for impl in implementations:
                level_name = ["SPECIFIC", "OS_DEFAULT", "GLOBAL_DEFAULT"][impl["level"]]
                print(f"          └─ [{level_name}] {impl['path'].name}")
    else:
        print(f"\n   ❌ НЕ ЗАГРУЖЕНО НИ ОДНОГО МОДУЛЯ!")
        print(f"\n   🔍 ВОЗМОЖНЫЕ ПРИЧИНЫ:")
        print(f"      1. Неверный путь к модулям (проверьте starter_path)")
        print(f"      2. Отсутствуют файлы модулей в директориях")
        print(f"      3. Ошибка в названиях классов (должны быть ИмяМодуляModule)")
        print(f"      4. Ошибки импорта внутри модулей")
        print(f"\n   📁 Проверьте существование пути: {starter_path / 'files' / 'core' / 'oss'}")
    
    print("═" * 70 + "\n")
    
    return _modules_cache


def get(module_name: str, func_name: str = None, *args, **kwargs):
    """
    Прокладка для вызова функции из модуля с fallback по уровням приоритета.
    """
    global _modules_cache
    
    if not _modules_cache:
        print(f"\n⚠️ get({module_name}, {func_name}) - кеш модулей пуст!")
        print(f"   Выполняем загрузку модулей...")
        load_modules()
        initialize_global_modules()
    
    # Диагностика: вывод всех реализаций модуля
    if module_name in _modules_cache:
        if func_name:
            print(f"🔍 get({module_name}, {func_name}) - найдено {len(_modules_cache[module_name])} реализаций")
    else:
        print(f"❌ get({module_name}, {func_name}) - МОДУЛЬ НЕ НАЙДЕН!")
        print(f"   Доступные модули: {list(_modules_cache.keys())}")
        return None
    
    # Если запрошен класс модуля - возвращаем самую специфичную реализацию
    if not func_name:
        return _modules_cache[module_name][0]["class"]
    
    # Пытаемся найти и выполнить функцию по приоритету
    for impl in _modules_cache[module_name]:
        func = impl["methods"].get(func_name) if "methods" in impl else impl["functions"].get(func_name)
        if func:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                print(f"⚠️ Ошибка в {module_name}.{func_name}: {e}")
                continue
    
    print(f"❌ Функция {func_name} не найдена в модуле {module_name}")
    return None


def load_module_from_path(path: Path, module_name: str) -> object:
    """Загружает модуль из указанного пути"""
    try:
        module_spec = importlib.util.spec_from_file_location(
            f"loaded.{module_name}", 
            str(path)
        )
        
        if module_spec is None:
            print(f"         ❌ Не удалось создать spec для {path}")
            return None
            
        module = importlib.util.module_from_spec(module_spec)
        sys.modules[module_spec.name] = module
        module_spec.loader.exec_module(module)
        
        class_name = f"{module_name.capitalize()}Module"
        
        if not hasattr(module, class_name):
            print(f"         ❌ Класс {class_name} не найден в модуле")
            print(f"            Доступные классы: {[x for x in dir(module) if not x.startswith('_')]}")
            return None
            
        module_class = getattr(module, class_name)
        return module_class    

    except Exception as e:
        print(f"         ❌ Критическая ошибка загрузки: {e}")
        import traceback
        traceback.print_exc()
        return None


def initialize_global_modules():
    """
    Вызывает set_globals для всех модулей в порядке от общего к специфичному
    """
    global _modules_cache
    
    print("\n" + "═" * 70)
    print("🔧 ИНИЦИАЛИЗАЦИЯ ГЛОБАЛЬНЫХ ПЕРЕМЕННЫХ МОДУЛЕЙ")
    print("═" * 70)
    
    if not _modules_cache:
        print("   ❌ Кеш модулей пуст, сначала выполните load_modules()")
        return
        
    logger.info("=====ПЕРВОНАЧАЛЬНАЯ УСТАНОВКА ГЛОБАЛЬНЫХ ПЕРЕМЕННЫХ ОТ МОДУЛЕЙ=====")
    
    # Собираем все реализации (уровни 0-2)
    all_impls = []
    for module_name, implementations in _modules_cache.items():
        for impl in implementations:
            all_impls.append(impl)
    
    # Сортируем по уровню ОБРАТНО приоритету (от общего к специфичному)
    all_impls.sort(key=lambda x: x["level"], reverse=True)
    
    level_names = {
        0: "🔴 SPECIFIC (версия ОС)",
        1: "🟡 OS_DEFAULT",
        2: "🟢 GLOBAL_DEFAULT"
    }
    
    initialized_count = 0
    error_count = 0
    
    print(f"\n   Порядок инициализации (от общего к специфичному):")
    for impl in all_impls:
        module_name = impl["path"].stem
        module_class = impl["class"]
        level = impl["level"]
        level_name = level_names.get(level, f"Неизвестный уровень ({level})")
        
        try:
            if hasattr(module_class, 'set_globals') and callable(module_class.set_globals):
                print(f"      {level_name} - {module_name}")
                module_class.set_globals()
                initialized_count += 1
                logger.info(f"set_globals для {module_name}")
        except Exception as e:
            print(f"      ❌ Ошибка в {module_name}.set_globals(): {e}")
            error_count += 1
            logger.error(f"Error calling set_globals for {module_name}: {e}")
    
    print(f"\n   📊 Результат: инициализировано {initialized_count} модулей, ошибок: {error_count}")
    print("═" * 70 + "\n")
    logger.info("=====ПЕРВОНАЧАЛЬНАЯ УСТАНОВКА ГЛОБАЛЬНЫХ ПЕРЕМЕННЫХ ЗАКОНЧЕНА=====")


# ===== Остальные функции =====

def _get_oss_tree() -> List[Tuple[Path, str, Optional[str], int]]:
    """Возвращает все файлы реализации в дереве OSS с их метаданными."""
    starter_path = get_global('starter_path')
    if starter_path is None:
        return []
    base_dir = starter_path / 'files' / 'core' / 'oss'
    items = []
    
    default_dir = base_dir / 'default'
    if default_dir.exists():
        for py_file in default_dir.glob("*.py"):
            items.append((py_file, None, None, 2))
    
    for os_dir in base_dir.iterdir():
        if os_dir.is_dir() and os_dir.name != 'default':
            os_name = os_dir.name
            
            os_default_dir = os_dir / 'default'
            if os_default_dir.exists():
                for py_file in os_default_dir.glob("*.py"):
                    items.append((py_file, os_name, None, 1))
            
            for version_dir in os_dir.iterdir():
                if version_dir.is_dir() and version_dir.name != 'default':
                    os_version = version_dir.name
                    for py_file in version_dir.glob("*.py"):
                        items.append((py_file, os_name, os_version, 0))
    return items


def collect_modules_info(refresh: bool = False) -> List[Dict[str, Any]]:
    """Собирает информацию о модулях"""
    starter_path = get_global('starter_path')
    if starter_path is None:
        return []
    
    cache = get_global('modules_info_cache') or {}
    files = _get_oss_tree()
    
    files_state = {str(p): p.stat().st_mtime for p, _, _, _ in files}
    sig = {
        "starter_path": str(starter_path).lower(),
        "files_hash": hash(tuple(sorted(files_state.keys()))),
        "files_count": len(files_state)
    }

    if (not refresh and cache.get("sig") == sig and 
        cache.get("files_state") == files_state and "items" in cache):
        return cache["items"]

    items = []
    for py_file, os_name, os_version, level in files:
        module_name = py_file.stem
        try:
            logger.debug(f"Processing module: {module_name} from {py_file}")
            module_class = load_module_from_path(py_file, module_name)
            if not module_class:
                logger.warning(f"Failed to load class for module: {module_name}")
                continue

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
                        "kind": kind,
                        "doc": doc,
                        "comment": inline_comment,
                        "signature": str(inspect.signature(member))
                    })

            items.append({
                "module_name": module_name,
                "class_name": module_class.__name__,
                "path": str(py_file),
                "os": os_name,
                "os_version": os_version,
                "level": level,
                "functions": funcs,
            })
        except Exception as e:
            logger.error(f"Error processing {py_file}: {str(e)}")

    cache = {
        "sig": sig,
        "files_state": files_state,
        "items": items,
        "cached_at": int(time.time()),
    }
    set_global('modules_info_cache', cache)
    return items


def _extract_inline_comment_after_signature(func) -> str:
    """Извлекает комментарий после сигнатуры функции"""
    try:
        source_lines = inspect.getsourcelines(func)[0]
        def_line_index = -1
        for i, line in enumerate(source_lines):
            if line.strip().startswith('def '):
                def_line_index = i
                break
        
        if def_line_index == -1:
            return ""
        
        next_line_index = def_line_index + 1
        if next_line_index >= len(source_lines):
            return ""
        
        next_line = source_lines[next_line_index].strip()
        if next_line.startswith('#'):
            return next_line[1:].strip()
        return ""
    except Exception:
        return ""


def _method_kind(cls, method_name: str) -> str:
    """Определяет тип метода"""
    method = getattr(cls, method_name)
    if isinstance(method, staticmethod):
        return "static"
    elif isinstance(method, classmethod):
        return "class"
    else:
        return "instance"