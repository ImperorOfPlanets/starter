import abc
import logging

class BaseModule(abc.ABC):

    @staticmethod
    @abc.abstractmethod
    def check() -> bool:
        return True
    
    @classmethod
    def log_usage(cls, func_name: str):
        """Логирует использование функции"""
        logging.info(f"Используется {cls.__name__}.{func_name}")