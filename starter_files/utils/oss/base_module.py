import abc
import logging

class BaseModule(abc.ABC):
    @classmethod
    def log_usage(cls, func_name: str):
        """Логирует использование функции"""
        logging.info(f"Используется {cls.__name__}.{func_name}")