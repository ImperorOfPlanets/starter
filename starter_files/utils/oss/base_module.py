import abc
import logging

class BaseModule(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def check(cls) -> bool:
        """Проверяет доступность модуля в системе"""
        return True
    
    @classmethod
    def log_usage(cls, func_name: str):
        """Логирует использование функции"""
        logging.info(f"Используется {cls.__name__}.{func_name}")