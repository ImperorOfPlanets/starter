import json
from pathlib import Path
from starter_files.core.utils.globalVars_utils import get_all_globals
from starter_files.core.utils.loader_utils import get, collect_modules_info

this_section_in_control_panel = False
section_name = "Develop"
section_icon = "bi-terminal"
section_order = 999

def globalVariables(data, session):
    """Возвращает все глобальные переменные с обработкой специальных типов."""
    try:
        globals_data = get_all_globals()
        
        # Рекурсивно применяем сериализатор ко всем данным
        def serialize_data(data):
            if isinstance(data, (int, float, str, bool, type(None))):
                return data
            elif isinstance(data, Path):
                return str(data)
            elif isinstance(data, dict):
                return {k: serialize_data(v) for k, v in data.items()}
            elif isinstance(data, (list, tuple, set)):
                return [serialize_data(item) for item in data]
            elif hasattr(data, '__dict__'):
                return serialize_data(data.__dict__)
            elif callable(data):
                return f"<function {data.__name__}>"
            else:
                try:
                    return str(data)
                except:
                    return f"<{type(data).__name__} object>"
        
        serializable_data = serialize_data(globals_data)
        
        return {
            "status": "success",
            "data": serializable_data
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

def modules(data, session):
    """Возвращает информацию о модулях со всеми реализациями."""
    try:
        logger.info("Starting modules collection")
        
        # Собираем информацию о модулях
        modules_data = collect_modules_info()
        logger.info(f"Received {len(modules_data)} raw module records")
        
        # Логируем первые 3 записи для диагностики
        for i, module in enumerate(modules_data[:3]):
            logger.info(f"Module #{i+1}: {module.get('module_name')} | "
                         f"Path: {module.get('path')} | "
                         f"OS: {module.get('os')} | "
                         f"Functions: {len(module.get('functions', []))}")
        
        # Группируем реализации по имени модуля
        grouped_modules = {}
        for module in modules_data:
            module_name = module["module_name"]
            
            if not module_name:
                logger.info("Skipping module with empty name")
                continue
                
            if module_name not in grouped_modules:
                logger.info(f"New module group: {module_name}")
                grouped_modules[module_name] = {
                    "module_name": module_name,
                    "implementations": []
                }
                
            grouped_modules[module_name]["implementations"].append(module)
        
        logger.info(f"Created {len(grouped_modules)} module groups")
        
        # Преобразуем в список и сортируем реализации
        result = []
        for module_name, module_data in grouped_modules.items():
            # Сортируем реализации по уровню приоритета (0 - высший)
            module_data["implementations"].sort(key=lambda x: x["level"])
            result.append(module_data)
            
            # Логируем информацию о реализациях
            impls = module_data["implementations"]
            logger.info(f"Module '{module_name}' has {len(impls)} implementations:")
            for i, impl in enumerate(impls):
                logger.info(f"  Impl #{i+1}: Level={impl['level']} | "
                             f"OS={impl.get('os')} | "
                             f"Path={impl.get('path')}")
        
        logger.info(f"Returning {len(result)} module groups")
        
        return {
            "status": "success",
            "data": result
        }
        
    except Exception as e:
        logger.info("Critical error in modules endpoint")
        return {
            "status": "error",
            "message": f"{str(e)} (See server logs for details)"
        }