import sys
from typing import Any, Dict

class GlobalVars:
    """Класс для управления глобальными переменными приложения"""
    _instance = None
    _vars: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GlobalVars, cls).__new__(cls)
        return cls._instance

    @classmethod
    def set_var(cls, name: str, value: Any) -> None:
        """Установка глобальной переменной"""
        cls._vars[name] = value

    # Добавляем новый метод в класс GlobalVars
    @classmethod
    def get_all_vars(cls) -> Dict[str, Any]:
        """Получение всех глобальных переменных"""
        return cls._vars.copy()

    @classmethod
    def get_var(cls, name: str, default: Any = None) -> Any:
        """Получение глобальной переменной"""
        return cls._vars.get(name, default)

    @classmethod
    def del_var(cls, name: str) -> None:
        """Удаление глобальной переменной"""
        if name in cls._vars:
            del cls._vars[name]

    @classmethod
    def clear_all(cls) -> None:
        """Очистка всех глобальных переменных"""
        cls._vars.clear()

# Создаем алиасы для удобного использования
def set_global(name: str, value: Any) -> None:
    """Установка глобальной переменной (удобный алиас)"""
    GlobalVars.set_var(name, value)

def get_global(name: str, default: Any = None) -> Any:
    """Получение глобальной переменной (удобный алиас)"""
    return GlobalVars.get_var(name, default)

def del_global(name: str) -> None:
    """Удаление глобальной переменной (удобный алиас)"""
    GlobalVars.del_var(name)

# Добавляем алиас
def get_all_globals() -> Dict[str, Any]:
    """Получение всех глобальных переменных (удобный алиас)"""
    return GlobalVars.get_all_vars()