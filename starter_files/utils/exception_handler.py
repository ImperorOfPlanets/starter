# starter_files/utils/exception_handler.py
import json
import sys
from types import TracebackType
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from starter_files.utils.global_vars import get_global

class ExceptionHandler:
    """Класс для обработки и логирования необработанных исключений"""
    
    def __init__(self):
        """
        Инициализация обработчика исключений
        
        :param app_root: Корневая директория приложения
        """
        self.app_root = Path(sys.argv[0]).absolute().parent
        self.exceptions_dir = self.app_root / "starter_files" / "exceptions"
        self.exceptions_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_system_info(self) -> Dict[str, Any]:
        """Получает системную информацию из глобальных переменных"""
        # Базовые системные данные
        system_info = {
            'os': get_global('os', 'N/A'),
            'os_version': get_global('os_version', 'N/A'),
            'os_release': get_global('os_release', 'N/A'),
            'architecture': get_global('architecture', 'N/A'),
            'hostname': get_global('hostname', 'N/A'),
            'username': get_global('username', 'N/A'),
            'current_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'is_service': get_global('is_service', False),
            'python_info': get_global('python_info', {})
        }
        
        # Добавляем дополнительную информацию, если есть
        additional_info = {
            'environment_vars': get_global('environment_vars', {}),
            'app_start_time': get_global('app_start_time'),
            'app_version': get_global('app_version'),
            'config_path': get_global('config_path')
        }
        
        # Фильтруем None значения
        for key, value in additional_info.items():
            if value is not None:
                system_info[key] = value
                
        return system_info
    
    def _save_error_report(self, error_data: Dict[str, Any]) -> Path:
        """Сохраняет отчет об ошибке в файл"""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        error_filename = self.exceptions_dir / f"error_{timestamp}.json"
        
        with open(error_filename, 'w', encoding='utf-8') as f:
            json.dump(error_data, f, ensure_ascii=False, indent=2)
            
        return error_filename
    
    def handle_unhandled_exception(self, 
                                 exc_type: type, 
                                 exc_value: BaseException, 
                                 exc_traceback: Optional[TracebackType]) -> None:
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
            "system_info": self._get_system_info(),
            "app_state": {
                "global_vars": get_global('__all__', {}),  # Можно добавить все глобальные переменные
                "last_operation": get_global('last_operation')
            }
        }
        
        error_path = self._save_error_report(error_data)
        print(f"\nCritical error logged to: {error_path}", file=sys.stderr)
        
        # Вызываем стандартный обработчик
        sys.__excepthook__(exc_type, exc_value, exc_traceback)