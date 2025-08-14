import logging
from pathlib import Path
from starter_files.utils.oss.module_loader import load_module

logger = logging.getLogger('oss_utils')

def get(module_name: str, function_name: str, *args, **kwargs):
    """
    Универсальная функция вызова функции внутри модуля OSS с учетом fallback.
    
    Args:
        module_name (str): Имя модуля (например, 'network')
        function_name (str): Имя функции внутри модуля (например, 'get_ips')
        *args: Позиционные аргументы для функции
        **kwargs: Именованные аргументы для функции
    
    Returns:
        Любое: результат вызова функции или None в случае ошибки
    """
    try:
        module_class = load_module(module_name)
        
        if not module_class:
            logger.error(f"Модуль {module_name} не найден")
            return None

        if not hasattr(module_class, function_name):
            logger.warning(f"Функция '{function_name}' не найдена в модуле '{module_name}'")
            return None

        func = getattr(module_class, function_name)
        return func(*args, **kwargs)
    except Exception as e:
        logger.error(f"Ошибка вызова {module_name}.{function_name}: {e}")
        return None