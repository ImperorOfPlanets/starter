import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from starter_files.utils.globalVars_utils import get_global

class LogManager:
    _initialized = False
    _loggers = {}
    
    @classmethod
    def initialize(cls, debug_mode=False, service_mode=False):
        if cls._initialized:
            return
            
        base_dir = get_global('script_path')
        log_dir = base_dir / "starter_files" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Основной логгер приложения
        main_logger = logging.getLogger('starter')
        main_logger.setLevel(logging.DEBUG)
        
        # Формат логов
        formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)-7s] [%(name)s:%(lineno)d] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Обработчик для файла
        log_file = log_dir / "application.log"
        file_handler = RotatingFileHandler(
            log_file, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        main_logger.addHandler(file_handler)
        
        # Консольный обработчик (только для отладки)
        if debug_mode and not service_mode:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            console_handler.setLevel(logging.DEBUG)
            main_logger.addHandler(console_handler)
        
        cls._initialized = True
        main_logger.info("Logger system initialized")
    
    @classmethod
    def get_logger(cls, name=None):
        if not cls._initialized:
            raise RuntimeError("Logger not initialized. Call LogManager.initialize() first.")
        
        # Если имя не указано, используем имя вызывающего модуля
        if not name:
            frame = sys._getframe(1)
            module = frame.f_globals.get('__name__', 'unknown')
            name = module.split('.')[-1]
        
        if name not in cls._loggers:
            logger = logging.getLogger(f"starter.{name}")
            logger.propagate = True
            cls._loggers[name] = logger
        
        return cls._loggers[name]