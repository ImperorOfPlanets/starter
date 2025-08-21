import os
import re
from pathlib import Path
from flask import render_template, send_from_directory
from starter_files.core.utils.i18n_utils import t
from starter_files.core.utils.log_utils import LogManager
logger = LogManager.get_logger()

# Конфигурация модуля для панели управления
this_section_in_control_panel = True
section_icon = "bi-journal-text"
section_name = "Logs"
section_order = 5

# Пути к логам
LOG_DIR = Path('starter_files/logs')
LOG_TYPES = {
    'web': 'Web Application Logs',
    'service': 'Service Logs',
    'system': 'System Logs',
    'docker': 'Docker Logs'
}

def get_log_files(log_type):
    """Возвращает список файлов логов для указанного типа"""
    log_path = LOG_DIR / log_type
    if not log_path.exists():
        logger.warning(f"Log directory not found: {log_path}")
        return []
    
    log_files = []
    for f in log_path.glob('*.log'):
        if f.is_file():
            try:
                # Получаем информацию о файле
                stat = f.stat()
                log_files.append({
                    'name': f.name,
                    'path': str(f),
                    'size': stat.st_size,
                    'mtime': stat.st_mtime,
                    'stat': stat
                })
            except Exception as e:
                logger.error(f"Error getting file info for {f}: {e}")
    
    # Сортируем по времени изменения (новые сначала)
    return sorted(log_files, key=lambda x: x['mtime'], reverse=True)

def read_log_file(log_path, lines=100):
    """Читает последние строки из файла лога"""
    try:
        with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
            # Читаем последние N строк более эффективно
            from collections import deque
            content = deque(maxlen=lines)
            for line in f:
                content.append(line)
            return ''.join(content)
    except FileNotFoundError:
        logger.error(f"Log file not found: {log_path}")
        return f"Log file not found: {Path(log_path).name}"
    except Exception as e:
        logger.error(f"Error reading log file {log_path}: {e}")
        return f"Error reading log file: {str(e)}"

def parse_log_line(line):
    """Парсит строку лога в структурированный объект"""
    # Пример формата: [2023-01-01 12:00:00] [INFO] [section:123] message
    match = re.match(
        r'^\[(?P<timestamp>.+?)\] \[(?P<level>.+?)\] \[(?P<source>.+?)\] (?P<message>.+)$', 
        line.strip()
    )
    if match:
        return {
            'timestamp': match.group('timestamp'),
            'level': match.group('level'),
            'source': match.group('source'),
            'message': match.group('message'),
            'raw': line
        }
    return {'raw': line}

def filter_logs(content, level=None, source=None, search=None):
    """Фильтрует логи по уровню, источнику или тексту"""
    filtered = []
    for line in content.split('\n'):
        if not line.strip():
            continue
            
        parsed = parse_log_line(line)
        match = True
        
        if level and parsed.get('level', '').upper() != level.upper():
            match = False
        if source and source.lower() not in parsed.get('source', '').lower():
            match = False
        if search and search.lower() not in line.lower():
            match = False
            
        if match:
            filtered.append(parsed)
    
    return filtered

def get_log_file_path(log_type, filename):
    """Возвращает полный путь к файлу лога с проверкой безопасности"""
    try:
        log_path = (LOG_DIR / log_type).resolve()
        file_path = (log_path / filename).resolve()
        
        # Проверяем, что файл находится внутри разрешенной директории
        if not file_path.is_relative_to(log_path):
            logger.error(f"Attempt to access file outside log directory: {filename}")
            return None
            
        if not file_path.exists():
            logger.error(f"Log file not found: {file_path}")
            return None
            
        return file_path
    except Exception as e:
        logger.error(f"Error getting log file path: {e}")
        return None

# Основные функции модуля
def index(data, session):
    """Главная страница модуля"""
    return render_template(
        'sections/logs/index.html',
        log_types=LOG_TYPES,
        t=t,
        get_log_files=get_log_files  # Передаем функцию в шаблон
    )

def view(data, session):
    """Просмотр логов определенного типа"""
    log_type = data.get('type', 'web')
    
    # Получаем список доступных файлов логов
    log_files = get_log_files(log_type)
    
    # Обрабатываем выбранный файл
    current_file = None
    log_content = ''
    filename = data.get('file')
    
    if filename:
        # Безопасно получаем путь к файлу
        file_path = get_log_file_path(log_type, filename)
        if file_path:
            current_file = {'name': filename, 'path': str(file_path)}
            log_content = read_log_file(file_path, 500)
    
    # Если файл не указан, берем самый свежий
    elif log_files:
        current_file = log_files[0]
        log_content = read_log_file(current_file['path'], 500)
    
    # Применяем фильтры
    filtered_logs = filter_logs(
        log_content,
        level=data.get('level'),
        source=data.get('source'),
        search=data.get('search')
    )
    
    return render_template(
        'sections/logs/view.html',
        log_type=log_type,
        log_types=LOG_TYPES,
        log_files=log_files,
        current_file=current_file['name'] if current_file else None,
        logs=filtered_logs,
        t=t
    )

def download(data, session):
    """Скачивание файла лога"""
    log_type = data.get('type')
    filename = data.get('file')
    
    if not log_type or not filename:
        return {'status': 'error', 'message': 'Missing parameters'}
    
    file_path = get_log_file_path(log_type, filename)
    if not file_path:
        return {'status': 'error', 'message': 'File not found or access denied'}
    
    try:
        directory = file_path.parent
        return send_from_directory(
            directory=directory,
            path=file_path.name,
            as_attachment=True,
            download_name=f"log_{log_type}_{filename}"
        )
    except Exception as e:
        logger.error(f"Error downloading log file: {e}")
        return {'status': 'error', 'message': str(e)}