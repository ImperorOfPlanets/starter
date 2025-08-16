import json
from pathlib import Path
from starter_files.utils.globalVars_utils import get_all_globals
from starter_files.utils.oss.module_loader import collect_modules_info

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
    """Возвращает информацию о модулях."""
    try:
        modules_data = collect_modules_info()
        
        # Упрощенная сериализация модулей
        def serialize_module(module):
            serialized = {
                "module_name": str(module.get("module_name", "")),
                "class_name": str(module.get("class_name", "")),
                "path": str(module.get("path", "")),
                "functions": []
            }
            
            for func in module.get("functions", []):
                serialized_func = {
                    "name": str(func.get("name", "")),
                    "kind": str(func.get("kind", "")),
                    "doc": str(func.get("doc", "")),
                    "comment": str(func.get("comment", ""))
                }
                serialized["functions"].append(serialized_func)
            
            return serialized
        
        serialized_data = [serialize_module(m) for m in modules_data]
        
        return {
            "status": "success",
            "data": serialized_data
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }