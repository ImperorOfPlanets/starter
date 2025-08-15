# starter_files/web/sections/develop.py
from starter_files.utils.globalVars_utils import get_all_globals
from starter_files.utils.oss.module_loader import collect_modules_info

this_section_in_control_panel = False  # меню develop у тебя отдельно
section_name = "Develop"
section_icon = "bi-terminal"
section_order = 999

def globalVariables(data, session):
    """Возвращает все глобальные переменные."""
    try:
        globals_data = get_all_globals()
        
        # Преобразуем все объекты Path в строки
        def convert_paths(obj):
            if isinstance(obj, Path):
                return str(obj)
            elif isinstance(obj, dict):
                return {k: convert_paths(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_paths(item) for item in obj]
            elif isinstance(obj, tuple):
                return tuple(convert_paths(item) for item in obj)
            elif isinstance(obj, set):
                return {convert_paths(item) for item in obj}
            else:
                return obj
        
        serializable_data = convert_paths(globals_data)
        
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
    """
    Возвращает список модулей с функциями и описаниями.
    """
    try:
        modules_data = collect_modules_info()
        return {
            "status": "success",
            "data": modules_data
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
