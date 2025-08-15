# starter_files/web/sections/develop.py
from starter_files.utils.globalVars_utils import get_global
from starter_files.utils.oss.module_loader import get_modules_index

this_section_in_control_panel = False  # меню develop у тебя отдельно
section_name = "Develop"
section_icon = "bi-terminal"
section_order = 999

def globalVariables(data, session):
    """
    Возвращает все глобальные переменные.
    """
    try:
        globals_data = get_global(None)  # если get_global без ключа возвращает весь dict
        return {
            "status": "success",
            "data": globals_data
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
        modules_data = get_modules_index()
        return {
            "status": "success",
            "data": modules_data
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
