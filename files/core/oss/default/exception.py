# files/core/oss/default/exception.py
"""
Модуль обработки исключений
"""

import json
import sys
import traceback
from types import TracebackType
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from files.core.base_module import BaseModule
from files.core.utils.globalVars_utils import get_global, set_global
from files.core.utils.log_utils import LogManager

logger = LogManager.get_logger('exception')


class ExceptionModule(BaseModule):
    """Модуль обработки исключений"""
    
    @staticmethod
    def check() -> bool:
        return True
    
    @staticmethod
    def set_globals():
        """Устанавливает глобальные переменные"""
        starter_path = get_global('starter_path')
        if starter_path:
            exceptions_dir = starter_path / "files" / "logs" / "exceptions"
            set_global('exceptions_dir', exceptions_dir)
            logger.debug(f"Exceptions directory set to: {exceptions_dir}")
    
    @staticmethod
    def handle_unhandled_exception(exc_type: type, exc_value: BaseException, 
                                    exc_traceback: Optional[TracebackType]) -> None:
        """Обработчик необработанных исключений"""
        logger.critical("Unhandled exception occurred", exc_info=(exc_type, exc_value, exc_traceback))
        
        if exc_traceback is None:
            exc_traceback = exc_value.__traceback__
        
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        error_data = {
            "timestamp": datetime.now().isoformat(),
            "type": exc_type.__name__,
            "message": str(exc_value),
            "traceback": traceback.format_exception(exc_type, exc_value, exc_traceback),
            "app_state": {
                "global_vars": get_global('__all__', {}),
                "last_operation": get_global('last_operation')
            }
        }
        
        error_path = ExceptionModule._save_error_report(error_data)
        logger.info(f"Critical error logged to: {error_path}")
        
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
    
    @staticmethod
    def _save_error_report(error_data: Dict[str, Any]) -> Path:
        """Сохраняет отчет об ошибке в файл"""
        exceptions_dir = get_global('exceptions_dir')
        if exceptions_dir is None:
            starter_path = get_global('starter_path')
            if starter_path:
                exceptions_dir = starter_path / "files" / "logs" / "exceptions"
            else:
                exceptions_dir = Path.cwd() / "logs" / "exceptions"
        
        exceptions_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        error_filename = exceptions_dir / f"error_{timestamp}.json"
        
        try:
            with open(error_filename, 'w', encoding='utf-8') as f:
                json.dump(error_data, f, ensure_ascii=False, indent=2)
            logger.debug(f"Error report saved: {error_filename}")
        except Exception as e:
            logger.error(f"Failed to save error report: {e}")
        
        return error_filename