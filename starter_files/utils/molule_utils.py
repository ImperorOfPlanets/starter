import logging
from pathlib import Path
from starter_files.utils.oss.module_loader import load_module
from starter_files.utils.oss.module_loader import _create_default_stub  # приватная, но используем

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
        # Загружаем модуль с учетом ОС, версии, дефолтов
        module_class = load_module(module_name)
        if not module_class:
            logger.error(f"Модуль {module_name} не найден для текущей ОС")
            return None
        
        # Класс или инстанс - в вашем коде это класс, у которого есть статические/классовые методы
        # Проверяем функцию
        if not hasattr(module_class, function_name):
            logger.warning(f"Функция '{function_name}' не найдена в модуле '{module_name}'")
            
            # Создадим stub в папке OS/default для данного модуля, если ещё нет
            system = module_class.__module__.split('.')[2] if '.' in module_class.__module__ else 'default'
            
            created_stub_path = _create_default_stub(module_name, system)
            
            logger.info(f"Создан stub для модуля {module_name} по пути: {created_stub_path}")
            return None
        
        func = getattr(module_class, function_name)
        
        # Вызываем функцию, предполагая, что она статическая или классовая
        result = func(*args, **kwargs)
        
        # Логируем использование
        if hasattr(module_class, 'log_usage'):
            module_class.log_usage(function_name)
        
        return result
    
    except Exception as e:
        logger.error(f"Ошибка вызова {module_name}.{function_name}: {e}")
        
        # Попытка создать stub при критической ошибке
        try:
            system = kwargs.get('os_name')
            if not system:
                import platform
                system = platform.system().lower()
            created_stub_path = _create_default_stub(module_name, system)
            logger.info(f"Создан stub для модуля {module_name} по пути: {created_stub_path}")
        except Exception as stub_exc:
            logger.error(f"Ошибка при создании stub: {stub_exc}")

        return None
