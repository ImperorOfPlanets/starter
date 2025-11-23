import sys
import importlib.util
import inspect
import logging
import time
from pathlib import Path
from starter_files.core.utils.globalVars_utils import set_global, get_global
from typing import List, Dict, Any, Tuple, Optional
from starter_files.core.utils.log_utils import LogManager

LogManager.register_log_dir('modules', 'modules')
logger = LogManager.get_logger('modules')

_modules_cache = {}  # Формат: {module_name: [impl1, impl2, impl3]}

def load_modules(refresh: bool = False):
    """
    Сканирует все модули под текущую ОС и создаёт кеш функций с приоритетами.
    """
    global _modules_cache
    logger.info("\n=== ЗАГРУЗКА МОДУЛЕЙ ===")
    if _modules_cache and not refresh:
        return _modules_cache

    script_path = Path(get_global("script_path"))
    os_name = get_global("os")
    os_version = get_global("os_version")
    logger.info(f"Текущая ОС: {os_name} {os_version}")

    base_categories = [
        ("oss", script_path / "starter_files" / "core" / "oss"),
        ("software", script_path / "starter_files" / "core" / "software")
    ]

    # Словарь для сбора всех реализаций
    all_implementations = {}

    for category_name, base_dir in base_categories:
        logger.info(f"\nПоиск модулей в категории: {category_name.upper()}")
        
        search_paths = [
            base_dir / os_name / os_version,      # 1. Самая специфичная
            base_dir / os_name / "default",       # 2. Общая для ОС
            base_dir / "default",                 # 3. Общая реализация
        ]

        logger.info("Пути поиска (в порядке приоритета):")
        for i, base in enumerate(search_paths):
            priority = i + 1
            level = i  # Уровень приоритета
            exists = "НАЙДЕНА" if base.exists() else "не найдена"
            logger.info(f" {priority}. {base} [{exists}] (уровень {level})")

            if not base.exists():
                continue

            logger.info(f"  Сканирование файлов в: {base}")
            for py_file in base.glob("*.py"):
                module_name = py_file.stem  # Добавляем префикс категории
                
                # Инициализируем список для модуля, если нужно
                if module_name not in all_implementations:
                    all_implementations[module_name] = []
                    
                # Проверяем, есть ли уже реализация с таким же путем
                existing_paths = [impl["path"] for impl in all_implementations[module_name]]
                if py_file in existing_paths:
                    logger.info(f"      Пропуск (уже загружен ранее)")
                    continue

                try:
                    logger.info(f"      Попытка загрузки модуля...")
                    module_class = load_module_from_path(py_file, py_file.stem)

                    if module_class is None:
                        logger.info("      ❌ Не удалось загрузить класс модуля")
                        continue

                    funcs = {}
                    logger.info("      Поиск функций в классе:")
                    for name, member in inspect.getmembers(module_class):
                        if name.startswith("__"):
                            continue
                        if inspect.isfunction(member) or inspect.ismethod(member):
                            funcs[name] = member
                            logger.info(f"        - {name}")

                    # Добавляем реализацию в список
                    all_implementations[module_name].append({
                        "class": module_class,
                        "functions": funcs,
                        "path": py_file,
                        "level": level,
                        #"category": category_name
                    })
                    logger.info(f"      ✅ Реализация модуля '{module_name}' успешно загружена (уровень {level})")
                except Exception as e:
                    error_msg = f"      ❌ Ошибка загрузки: {str(e)}"
                    logger.info(error_msg)
                    logger.warning(f"[WARN] Не удалось загрузить {py_file}: {e}")

    # Сортируем реализации по приоритету для каждого модуля
    for module_name in all_implementations:
        all_implementations[module_name].sort(key=lambda x: x["level"])
    
    # Обновляем глобальный кеш
    _modules_cache = all_implementations

    # Выводим детальную информацию о загруженных модулях
    logger.info("\n=== ИТОГИ ЗАГРУЗКИ ===")
    logger.info(f"Всего модулей: {len(_modules_cache)}")
    
    priority_names = {
        0: "ВЕРСИЯ ОС (наивысший приоритет)",
        1: "ОС DEFAULT",
        2: "GLOBAL DEFAULT (низший приоритет)"
    }
    
    for module_name, implementations in _modules_cache.items():
        logger.info(f"\nМодуль: {module_name}")
        logger.info(f"Количество реализаций: {len(implementations)}")
        
        for impl in implementations:
            level_name = priority_names.get(impl["level"], f"Неизвестный уровень ({impl['level']})")
            logger.info(f"\n  Реализация (уровень {impl['level']} - {level_name}):")
            logger.info(f"    Путь: {impl['path']}")
            logger.info(f"    Функции ({len(impl['functions'])}):")
            
            # Выводим функции группами по 5
            funcs = list(impl["functions"].keys())
            for i in range(0, len(funcs), 5):
                logger.info("      " + ", ".join(funcs[i:i+5]))
    
    return _modules_cache

def get(module_name: str, func_name: str = None, *args, **kwargs):
    """
    Прокладка для вызова функции из модуля с fallback по уровням приоритета.
    """
    global _modules_cache
    
    logger.info(f"\n=== DEBUG: get({module_name}, {func_name}) ===")
    if not _modules_cache:
        logger.info("Кеш модулей пуст, выполняем загрузку...")
        load_modules()
        initialize_global_modules()
    else:
        logger.info("Кеш модулей уже загружен")
    
    # Диагностика: вывод всех реализаций модуля
    if module_name in _modules_cache:
        logger.info(f"Найдено реализаций модуля '{module_name}': {len(_modules_cache[module_name])}")
        for i, impl in enumerate(_modules_cache[module_name]):
            level_name = ["OS_VERSION", "OS_DEFAULT", "GLOBAL_DEFAULT"][impl["level"]]
            logger.info(f" Реализация #{i+1} ({level_name}):")
            logger.info(f"   Путь: {impl['path']}")
            logger.info(f"   Функции: {list(impl['functions'].keys())}")
    else:
        logger.info(f"⚠️ Модуль '{module_name}' не найден в кеше!")
        logger.error(f"[ERROR] Модуль {module_name} не найден!")
        return None
    
    # Если запрошен класс модуля - возвращаем самую специфичную реализацию
    if not func_name:
        logger.info("Возвращаем класс самой специфичной реализации")
        return _modules_cache[module_name][0]["class"]
    
    # Пытаемся найти и выполнить функцию по приоритету
    for impl in _modules_cache[module_name]:
        func = impl["functions"].get(func_name)
        if func:
            logger.info(f"Найдена функция '{func_name}' в реализации ({impl['path']})")
            try:
                logger.info(f"Выполнение функции...")
                return func(*args, **kwargs)
            except Exception as e:
                logger.info(f"❌ Ошибка выполнения: {str(e)}")
                logger.error(f"[ERROR] Ошибка в {module_name}.{func_name}: {e}")
                # Пробуем следующую реализацию
                continue
    
    logger.info(f"⚠️ Функция '{func_name}' не найдена ни в одной реализации!")
    logger.error(f"[ERROR] Функция {func_name} не найдена в модуле {module_name}")
    return None

def load_module_from_path(path: Path, module_name: str) -> object:
    """Загружает модуль из указанного пути"""
    logger.info(f"    [DEBUG] Загрузка модуля: {module_name} из {path}")
    
    try:
        module_spec = importlib.util.spec_from_file_location(
            f"oss.{module_name}", 
            str(path)
        )
        
        if module_spec is None:
            logger.info(f"    ❌ Не удалось создать spec для {path}")
            return None
            
        module = importlib.util.module_from_spec(module_spec)
        sys.modules[module_spec.name] = module
        module_spec.loader.exec_module(module)
        
        class_name = f"{module_name.capitalize()}Module"
        logger.info(f"    [DEBUG] Поиск класса: {class_name}")
        
        if not hasattr(module, class_name):
            logger.info(f"    ❌ Класс {class_name} не найден в модуле")
            return None
            
        module_class = getattr(module, class_name)
        logger.info(f"    ✅ Класс {class_name} найден")
        return module_class    

    except Exception as e:
        error_msg = f"    ❌ Критическая ошибка загрузки: {str(e)}"
        logger.info(error_msg)
        logger.error(f"Error loading module from {path}: {str(e)}", exc_info=True)
        return None

def initialize_global_modules():
    """
    Вызывает set_globals для всех модулей в порядке от общего к специфичному
    (GLOBAL DEFAULT -> OS DEFAULT -> OS VERSION)
    """
    global _modules_cache
    logger.info("=====ПЕРВОНАЧАЛЬНАЯ УСТАНОВКА ГЛОБАЛЬНЫХ ПЕРЕМЕННЫХ ОТ МОДУЛЕЙ=====")
    if not _modules_cache:
        logger.info("Кеш модулей пуст, сначала выполните load_modules()")
        return
        
    logger.info("\n=== ИНИЦИАЛИЗАЦИЯ GLOBAL MODULES ===")
    
    # Собираем все реализации (уровни 0-2)
    all_impls = []
    for module_name, implementations in _modules_cache.items():
        all_impls.extend(implementations)
    
    # Сортируем по уровню ОБРАТНО приоритету (от общего к специфичному)
    # Уровень 2 (GLOBAL DEFAULT) -> Уровень 1 (OS DEFAULT) -> Уровень 0 (OS VERSION)
    all_impls.sort(key=lambda x: x["level"], reverse=True)
    
    # Словарь для человеко-читаемых имен уровней
    level_names = {
        0: "OS_VERSION (самый специфичный)",
        1: "OS_DEFAULT",
        2: "GLOBAL DEFAULT (самый общий)"
    }
    
    logger.info("Порядок инициализации: от общего к специфичному")
    for impl in all_impls:
        module_name = impl["path"].stem
        module_class = impl["class"]
        level = impl["level"]
        level_name = level_names.get(level, f"Неизвестный уровень ({level})")
        
        try:
            if hasattr(module_class, 'set_globals') and callable(module_class.set_globals):
                logger.info(f"  [{level_name}] {module_name}:")
                logger.info(f"      Путь: {impl['path']}")
                module_class.set_globals()
                logger.info(f"      ✅ set_globals успешно выполнена")
        except Exception as e:
            error_msg = f"      ❌ Ошибка при вызове set_globals: {str(e)}"
            logger.info(error_msg)
            logger.error(f"Error calling set_globals for {module_name} ({impl['path']}): {e}")
    logger.info("=====ПЕРВОНАЧАЛЬНАЯ УСТАНОВКА ГЛОБАЛЬНЫХ ПЕРЕМЕННЫХ ЗАКОНЧЕНА=====")

#===== Это уже касаеться сюорки комментариев и прочего для раздела разработчиков#

def _get_oss_tree() -> List[Tuple[Path, str, Optional[str], int]]:
    """
    Возвращает все файлы реализации в дереве OSS с их метаданными.
    Формат: (путь_к_файлу, os_name, os_version, уровень)
    """
    script_path = Path(get_global('script_path'))
    base_dir = script_path / 'starter_files' / 'core' / 'oss'
    items = []
    
    # Глобальные реализации по умолчанию
    default_dir = base_dir / 'default'
    if default_dir.exists():
        for py_file in default_dir.glob("*.py"):
            items.append((py_file, None, None, 2))  # Уровень 2
    
    # Реализации для конкретных ОС
    for os_dir in base_dir.iterdir():
        if os_dir.is_dir() and os_dir.name != 'default':
            os_name = os_dir.name
            
            # Версия по умолчанию для ОС
            os_default_dir = os_dir / 'default'
            if os_default_dir.exists():
                for py_file in os_default_dir.glob("*.py"):
                    items.append((py_file, os_name, None, 1))  # Уровень 1
            
            # Специфичные версии ОС
            for version_dir in os_dir.iterdir():
                if version_dir.is_dir() and version_dir.name != 'default':
                    os_version = version_dir.name
                    for py_file in version_dir.glob("*.py"):
                        items.append((py_file, os_name, os_version, 0))  # Уровень 0
    return items

def collect_modules_info(refresh: bool = False) -> List[Dict[str, Any]]:
    """
    Собирает полную информацию о всех модулях для всех ОС и реализаций.
    """
    script_path = str(Path(get_global('script_path'))).lower()
    cache = get_global('modules_info_cache') or {}
    files = _get_oss_tree()
    
    # Подпись кеша: хеш всех путей + mtime
    files_state = {str(p): p.stat().st_mtime for p, _, _, _ in files}
    sig = {
        "script_path": script_path,
        "files_hash": hash(tuple(sorted(files_state.keys()))),
        "files_count": len(files_state)
    }

    if (not refresh
        and cache.get("sig") == sig
        and cache.get("files_state") == files_state
        and "items" in cache):
        return cache["items"]

    items: List[Dict[str, Any]] = []
    
    for py_file, os_name, os_version, level in files:
        module_name = py_file.stem
        try:
            logger.debug(f"Processing module: {module_name} from {py_file}")
            module_class = load_module_from_path(py_file, module_name)
            if not module_class:
                logger.warning(f"Failed to load class for module: {module_name}")
                continue

            class_name = module_class.__name__
            funcs = []
            
            for name, member in inspect.getmembers(module_class):
                if name.startswith("__"):
                    continue
                if inspect.isfunction(member) or inspect.ismethod(member):
                    doc = inspect.getdoc(member) or ""
                    inline_comment = _extract_inline_comment_after_signature(member)
                    kind = _method_kind(module_class, name)
                    
                    logger.debug(f"  Found function: {name} ({kind})")
                    
                    funcs.append({
                        "name": name,
                        "kind": kind,
                        "doc": doc,
                        "comment": inline_comment,
                        "signature": str(inspect.signature(member))
                    })

            items.append({
                "module_name": module_name,
                "class_name": class_name,
                "path": str(py_file),
                "os": os_name,
                "os_version": os_version,
                "level": level,
                "functions": funcs,
            })
        except Exception as e:
            logger.error(f"Error processing {py_file}: {str(e)}", exc_info=True)

    cache = {
        "sig": sig,
        "files_state": files_state,
        "items": items,
        "cached_at": int(time.time()),
    }
    set_global('modules_info_cache', cache)
    logger.info(f"Collected {len(items)} module implementations")
    return items

def _extract_inline_comment_after_signature(func) -> str:
    """
    Извлекает однострочный комментарий, следующий сразу после сигнатуры функции.
    Возвращает строку без символов комментария. Если комментария нет, возвращает пустую строку.
    """
    try:
        # Получаем исходный код функции
        source_lines = inspect.getsourcelines(func)[0]
        
        # Находим строку с определением функции (def ...)
        def_line_index = -1
        for i, line in enumerate(source_lines):
            if line.strip().startswith('def '):
                def_line_index = i
                break
        
        if def_line_index == -1:
            return ""
        
        # Смотрим следующую строку после определения функции
        next_line_index = def_line_index + 1
        if next_line_index >= len(source_lines):
            return ""
        
        next_line = source_lines[next_line_index].strip()
        
        # Проверяем, является ли следующая строка комментарием
        if next_line.startswith('#'):
            # Убираем символ комментария и ведущие пробелы
            return next_line[1:].strip()
        else:
            return ""
    except Exception as e:
        logger.debug(f"Could not extract inline comment for {func.__name__}: {str(e)}")
        return ""

def _method_kind(cls, method_name: str) -> str:
    """
    Определяет тип метода: 'instance', 'class' или 'static'
    """
    method = getattr(cls, method_name)
    
    if isinstance(method, staticmethod):
        return "static"
    elif isinstance(method, classmethod):
        return "class"
    else:
        return "instance"