import json
import string
import sys
import traceback

from types import TracebackType
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from starter_files.utils.globalVars_utils import get_global

class ExceptionHandler:
    """Класс для обработки и логирования необработанных исключений"""
    
    def __init__(self):
        """
        Инициализация обработчика исключений
        
        :param app_root: Корневая директория приложения
        """
        self.app_root = get_global('script_path')
        self.exceptions_dir = self.app_root / "starter_files" / "logs" / "exceptions"
        self.exceptions_dir.mkdir(parents=True, exist_ok=True)

    def handle_unhandled_exception(self, exc_type: type, exc_value: BaseException, exc_traceback: Optional[TracebackType]) -> None:
        """
        Обработчик необработанных исключений
        
        :param exc_type: Тип исключения
        :param exc_value: Объект исключения
        :param exc_traceback: Traceback исключения
        """
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
                "global_vars": get_global('__all__', {}),  # Можно добавить все глобальные переменные
                "last_operation": get_global('last_operation')
            }
        }
        
        error_path = self._save_error_report(error_data)
        print(f"\nCritical error logged to: {error_path}", file=sys.stderr)
        
        # Вызываем стандартный обработчик
        sys.__excepthook__(exc_type, exc_value, exc_traceback)

    def _save_error_report(self, error_data: Dict[str, Any]) -> Path:
        """Сохраняет отчет об ошибке в файл"""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        error_filename = self.exceptions_dir / f"error_{timestamp}.json"
        
        with open(error_filename, 'w', encoding='utf-8') as f:
            json.dump(error_data, f, ensure_ascii=False, indent=2)
            
        return error_filename