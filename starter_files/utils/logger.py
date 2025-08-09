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
        
        self.logs_dir = Path('starter_files/logs')
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

    def _setup_directories(self):
        """Создает необходимые директории для логов"""
        (self.logs_dir / self.mode).mkdir(parents=True, exist_ok=True)

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
        """Возвращает путь к файлу лога (один и тот же при перезагрузках)"""
        # Если это перезагрузка, ищем существующий лог
        if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
            log_files = list((self.logs_dir / self.mode).glob('*.log'))
            if log_files:
                return log_files[0]  # Берем первый найденный лог
        
        # Иначе создаем новый
        timestamp = self.start_time.strftime('%Y%m%d_%H%M%S')
        filename = f'log_{timestamp}_{self.run_id}.log'
        return self.logs_dir / self.mode / filename

    def _log_system_info(self):
        """Логирует системную информацию при старте"""
        system_info = {
            # Название операционной системы (Linux/Windows/Darwin)
            'OS': platform.system(),
            
            # Версия ядра ОС или сборки Windows
            'OS Version': platform.version(),
            
            # Сетевое имя компьютера в локальной сети
            'Hostname': socket.gethostname(),
            
            # Имя пользователя, под которым запущен процесс
            'Username': getpass.getuser(),
            
            # Версия интерпретатора Python в формате X.Y.Z
            'Python Version': platform.python_version(),
            
            # Директория, из которой был запущен скрипт
            'Working Directory': os.getcwd(),
            
            # Полная командная строка запуска приложения
            'Command Line': ' '.join(sys.argv),
            
            # ID процесса в операционной системе
            'PID': os.getpid(),
            
            # Уникальный идентификатор сеанса работы приложения
            'Run ID': self.run_id,
            
            # Время старта в ISO формате (YYYY-MM-DDTHH:MM:SS)
            'Start Time': self.start_time.isoformat(),
            
            # Режим работы: 'web' или 'service'
            'Mode': self.mode,
            
            # Флаг Werkzeug (None/true/false):
            # None - обычный запуск без Flask
            # 'true' - основной процесс Flask
            # 'false' - процесс-наблюдатель при --debug
            'WERKZEUG_RUN_MAIN': os.environ.get('WERKZEUG_RUN_MAIN', 'None'),
            
            # Режим отладки Flask (1/None):
            # '1' - debug mode включен
            # None - production режим
            'FLASK_DEBUG': os.environ.get('FLASK_DEBUG', 'None'),
            
            # Признак основного процесса:
            # True - это основной рабочий процесс
            # False - дочерний процесс или перезагрузчик
            'Is Main Process': str(os.environ.get('WERKZEUG_RUN_MAIN') == 'true')
        }
        
        self.logger.info("=== SYSTEM INFO ===")
        for key, value in system_info.items():
            self.logger.info(f"{key}: {value}")

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

