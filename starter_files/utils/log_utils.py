import getpass
import logging
import os
import platform
import socket
import sys
import uuid

from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path
from starter_files.utils.globalVars_utils import get_global

def cleanup_previous_logs(logs_dir: Path, current_run_id: str):
    """Удаляет предыдущие лог-файлы из debug-сессии"""
    try:
        # Получаем все файлы логов
        for log_file in logs_dir.glob('*.log'):
            # Удаляем все логи, кроме текущего
            if current_run_id not in log_file.name:
                try:
                    # Проверяем, что файл принадлежит текущей debug-сессии
                    file_time_str = log_file.stem.split('_')[1]  # Получаем timestamp из имени
                    file_time = datetime.strptime(file_time_str, '%Y%m%d_%H%M%S')
                    
                    # Удаляем только свежие логи (созданные в последние 30 минут)
                    if (datetime.now() - file_time) < timedelta(minutes=30):
                        os.remove(log_file)
                        print(f"Удален предыдущий лог-файл: {log_file}")
                except (IndexError, ValueError) as e:
                    # Если не удалось разобрать имя файла, пропускаем его
                    continue
                except Exception as e:
                    print(f"Не удалось удалить {log_file}: {e}")
    except Exception as e:
        print(f"Ошибка при очистке логов: {e}")

def get_logger():
    """Фабрика логгеров. Автоматически определяет режим работы."""

    # Проверяем, не создан ли уже логгер
    existing_logger = logging.getLogger('starter_web')
    if existing_logger.handlers:
        return existing_logger
        
    is_service = any(arg in sys.argv for arg in ['--service', '--service-run'])
    mode = 'service' if is_service else 'web'
    
    # В debug-режиме Flask создает дочерний процесс, нам нужен только основной
    # Используем os.environ для проверки debug режима вместо app.debug
    is_debug = os.environ.get('FLASK_DEBUG') == '1'
    if mode == 'web' and is_debug and os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        return existing_logger
        
    return ProjectLogger(mode)

class ProjectLogger:
    def __init__(self, mode='web'):
        self.mode = mode
        self.run_id = self._get_run_id()  # Генерируем run_id по-новому
        self.start_time = datetime.now()
        
        self.base_dir = Path(os.path.dirname(os.path.abspath(__file__))).parent.parent
        self.logs_dir = self.base_dir / "starter_files" / "logs"
        self._setup_directories()

        # Настройка логгера
        self.logger = logging.getLogger(f'starter_{mode}')
        self._configure_logger()
        
        # Логирование системной информации (только при первом запуске)
        if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
            self._log_system_info()

    def _get_run_id(self):
        """Генерирует run_id, который сохраняется при перезагрузках"""
        # Если это перезагрузка (debug-режим), берем run_id из переменной окружения
        if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
            return os.environ.get('FLASK_RUN_ID', str(uuid.uuid4())[:8])
        return str(uuid.uuid4())[:8]

    # Добавлена обработка ошибок и установка прав:
    def _setup_directories(self):
        try:
            (self.logs_dir / self.mode).mkdir(parents=True, exist_ok=True)
            if hasattr(os, 'chmod'):
                os.chmod(self.logs_dir, 0o755)
                os.chmod(self.logs_dir / self.mode, 0o755)
        except Exception as e:
            print(f"Ошибка создания директории логов: {e}")
            raise

    def _configure_logger(self):
        """Настраивает логгер (использует один файл при перезагрузках)"""
        self.logger.handlers.clear()
        self.logger.setLevel(logging.DEBUG)
        
        formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] [%(module)s:%(lineno)d] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Имя файла лога (одинаковое при перезагрузках)
        log_file = self._get_log_file_path()
        
        # Обработчик файла с ротацией
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=5 * 1024 * 1024,  # 5 MB
            backupCount=10,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        # Вывод в консоль (только для web-режима)
        if self.mode == 'web':
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

    def _get_log_file_path(self):
        """Возвращает абсолютный путь к файлу лога"""
        try:
            # Если это перезагрузка, ищем существующий лог
            if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
                existing_logs = list((self.logs_dir / self.mode).glob('*.log'))
                if existing_logs:
                    return existing_logs[0].absolute()  # Возвращаем абсолютный путь

            # Создаем новый файл лога
            timestamp = self.start_time.strftime('%Y%m%d_%H%M%S')
            filename = f'log_{timestamp}_{self.run_id}.log'
            log_path = (self.logs_dir / self.mode / filename).absolute()
            
            # Проверяем, что путь валидный
            if not log_path.parent.exists():
                log_path.parent.mkdir(parents=True, exist_ok=True)
                
            return log_path
            
        except Exception as e:
            print(f"Ошибка при определении пути к лог-файлу: {e}")
            raise

    def _log_system_info(self):
        """Логирует системную информацию при старте, используя глобальные переменные"""
        self.logger.info("=== SYSTEM INFO ===")
        
        # Основные системные переменные
        main_keys = [
            'core', 'core_version', 'core_release',
            'os', 'os_version', 'architecture',
            'hostname', 'username', 'current_time',
            'is_service', 'script_path'
        ]
        
        # Сложные структуры (словари)
        dict_keys = ['python_info', 'environment_vars', 'privilege_info']
        
        # Логируем основные значения
        for key in main_keys:
            value = get_global(key, "N/A")
            # Особый случай для script_path (может быть Path-объектом)
            if key == 'script_path' and not isinstance(value, str):
                value = str(value) if value else "N/A"
            self.logger.info(f"{key}: {value}")
        
        # Логируем сложные словарные структуры
        for key in dict_keys:
            data = get_global(key, {})
            
            if not data:
                self.logger.info(f"{key}: N/A")
                continue
                
            self.logger.info(f"{key}:")
            for sub_key, sub_value in data.items():
                # Особые обработки для разных типов данных
                if isinstance(sub_value, list):
                    # Для списков выводим каждый элемент
                    self.logger.info(f"  {sub_key}:")
                    for i, item in enumerate(sub_value):
                        self.logger.info(f"    [{i}]: {item}")
                elif isinstance(sub_value, dict):
                    # Для вложенных словарей делаем дополнительный уровень
                    self.logger.info(f"  {sub_key}:")
                    for k, v in sub_value.items():
                        self.logger.info(f"    {k}: {v}")
                else:
                    # Стандартный вывод
                    self.logger.info(f"  {sub_key}: {sub_value}")

    # Стандартные методы логирования
    def debug(self, message):
        self.logger.debug(message)
        
    def info(self, message):
        self.logger.info(message)
        
    def warning(self, message):
        self.logger.warning(message)
        
    def error(self, message):
        self.logger.error(message)
        
    def critical(self, message):
        self.logger.critical(message)
        
    def exception(self, message):
        self.logger.exception(message)

