# starter_files/logger.py
import os
import sys
import platform
from pathlib import Path
from datetime import datetime
import uuid
import shutil
import zipfile
import getpass
import socket

class ProjectLogger:
    def __init__(self):
        self.logs_dir = Path('logs')
        self.archive_dir = self.logs_dir / 'archive'
        self.current_log = None
        self.run_id = str(uuid.uuid4())[:8]  # Короткий UUID
        self.start_time = datetime.now()
        
        # Создаем директории если их нет
        self.logs_dir.mkdir(exist_ok=True)
        self.archive_dir.mkdir(exist_ok=True)
        
        # Инициализируем лог
        self._init_log_file()
        self._cleanup_old_logs()
        
    def _init_log_file(self):
        """Инициализирует файл лога для текущего запуска"""
        timestamp = self.start_time.strftime('%Y%m%d_%H%M%S')
        self.current_log = self.logs_dir / f"log_{timestamp}_{self.run_id}.txt"
        
        # Получаем системную информацию
        system_info = {
            'OS': platform.system(),
            'OS Version': platform.version(),
            'Hostname': socket.gethostname(),
            'Username': getpass.getuser(),
            'Python Version': platform.python_version(),
            'Working Directory': os.getcwd(),
            'Command Line': ' '.join(sys.argv),
            'PID': os.getpid()
        }
        
        # Записываем заголовок лога
        with open(self.current_log, 'a', encoding='utf-8') as f:
            f.write(f"=== RUN ID: {self.run_id} ===\n")
            f.write(f"=== START TIME: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')} ===\n\n")
            
            f.write("=== SYSTEM INFO ===\n")
            for key, value in system_info.items():
                f.write(f"{key}: {value}\n")
            
            f.write("\n=== COMMAND LINE PARAMETERS ===\n")
            for i, arg in enumerate(sys.argv):
                f.write(f"Argument {i}: {arg}\n")
            
            f.write("\n=== ENVIRONMENT VARIABLES ===\n")
            for key in sorted(os.environ.keys()):
                if key.startswith(('DOCKER_', 'PATH', 'PYTHON', 'HOME', 'USER')):
                    f.write(f"{key}: {os.environ[key]}\n")
            
            f.write("\n=== LOG ENTRIES ===\n")
    
    def _cleanup_old_logs(self):
        """Управляет количеством лог-файлов"""
        # Получаем все лог-файлы, отсортированные по дате
        log_files = sorted(self.logs_dir.glob('log_*.txt'), key=os.path.getmtime)
        
        # Если больше 10 файлов - перемещаем старые в архив
        if len(log_files) > 10:
            files_to_move = log_files[:-10]  # Все кроме последних 10
            
            # Проверяем архив на количество файлов
            archived_logs = sorted(self.archive_dir.glob('log_*.txt'), key=os.path.getmtime)
            if len(archived_logs) >= 100:
                self._create_archive_bundle(archived_logs)
            
            # Перемещаем файлы в архив
            for file in files_to_move:
                shutil.move(file, self.archive_dir / file.name)
    
    def _create_archive_bundle(self, files):
        """Создает архивный bundle из старых логов"""
        oldest_date = files[0].stem.split('_')[1]
        newest_date = files[-1].stem.split('_')[1]
        archive_name = f"logs_{oldest_date}_to_{newest_date}.zip"
        
        # Создаем zip-архив
        with zipfile.ZipFile(self.archive_dir / archive_name, 'w') as zipf:
            for file in files:
                zipf.write(file, file.name)
                file.unlink()
    
    def log(self, message: str, level: str = "INFO", print_to_console: bool = True):
        """Основная функция логирования"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] [{level}] {message}\n"
        
        # Запись в файл (всегда)
        with open(self.current_log, 'a', encoding='utf-8') as f:
            f.write(log_entry)
        
        # Вывод в консоль
        if print_to_console:
            print(log_entry.strip())
    
    def log_command(self, command: list, description: str = None):
        """Специальное логирование для команд"""
        cmd_str = ' '.join(command)
        if description:
            self.log(f"{description}: {cmd_str}", "COMMAND")
        else:
            self.log(f"Выполняю команду: {cmd_str}", "COMMAND")
    
    def log_system_info(self):
        """Логирует дополнительную системную информацию"""
        try:
            ips = ', '.join(socket.gethostbyname_ex(socket.gethostname())[2])
            self.log(f"IP Addresses: {ips}", "SYSTEM")
        except Exception as e:
            self.log(f"Failed to get IPs: {str(e)}", "WARNING")

# Глобальный экземпляр логгера
logger = ProjectLogger()