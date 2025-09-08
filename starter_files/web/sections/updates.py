from flask import render_template, jsonify, request, send_file
from datetime import datetime
from pathlib import Path
import json
import logging
import threading
import uuid

from starter_files.core.utils.i18n_utils import t
from starter_files.core.oss.default.updates import UpdatesModule
from starter_files.configs.configs import PROJECTS
from starter_files.core.utils.log_utils import LogManager

# Настройка логирования
logger = LogManager.get_logger(__name__)

# Конфигурация модуля для панели управления
this_section_in_control_panel = True
section_icon = "bi-cloud-arrow-down"
section_name = "Updates"
section_order = 10

# Путь к директории логов обновлений
UPDATE_LOGS_DIR = Path(__file__).parent.parent.parent.parent / 'starter_files' / 'logs' / 'updates'
UPDATE_LOGS_DIR.mkdir(parents=True, exist_ok=True)

def index(data, session):
    """Главная страница модуля обновлений"""
    update_status = get_update_status_list()
    return render_template(
        'sections/updates/index.html',
        t=t,
        update_status=update_status
    )

def get_update_status_list():
    """Получение статуса обновлений для всех проектов"""
    status = []
    config = get_updates_config()
    
    for project_name in PROJECTS.keys():
        last_update = UpdatesModule.get_last_update_time(project_name, config)
        seconds_passed = UpdatesModule.seconds_since_last_update(project_name, config)
        
        if last_update:
            if seconds_passed < 3600:  # Менее часа назад
                status_text = t('up_to_date')
                status_color = 'success'
            elif seconds_passed < 86400:  # Менее суток назад
                status_text = t('recently_updated')
                status_color = 'warning'
            else:
                status_text = t('update_available')
                status_color = 'danger'
        else:
            status_text = t('never_updated')
            status_color = 'secondary'
        
        status.append({
            'name': project_name,
            'last_update': last_update,
            'status': status_text,
            'status_color': status_color
        })
    
    return status

def check_all(data, session):
    """Проверка всех обновлений"""
    try:
        # Получаем конфиг с правильным путем к файлу состояния
        config = get_updates_config()
        
        timestamp, updates, folders = UpdatesModule.start_updates_projects(
            projects_config=PROJECTS,
            module_config=config,
            force_check=True
        )
        return jsonify({'success': True, 'message': t('updates_check_success')})
    except Exception as e:
        logger.error(f"Error in check_all: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

def get_project_details(data, session):
    """Получение детальной информации о проекте"""
    project_name = data.get('project')
    if project_name not in PROJECTS:
        return jsonify({'success': False, 'message': t('project_not_found')})
    
    project_config = PROJECTS[project_name]
    config = get_updates_config()
    
    # Получаем информацию о последнем обновлении
    last_update = UpdatesModule.get_last_update_time(project_name, config)
    seconds_passed = UpdatesModule.seconds_since_last_update(project_name, config)
    
    # Форматируем информацию о проекте
    project_info = {
        'name': project_name,
        'download_url': project_config['DOWNLOAD_URL'],
        'base_path': project_config['BASE_PATH'],
        'targets': project_config['TARGETS'],
        'ignored': project_config.get('IGNORED', []),
        'critical_files': project_config.get('CRITICAL_FILES', []),
        'add_in_backups': project_config.get('ADD_IN_BACKUPS', []),
        'functions_if_update': project_config.get('FUNCTIONS_IF_UPDATE', {}),
        'restart_after_update': project_config.get('RESTART_AFTER_UPDATE', False),
        'last_update': last_update.isoformat() if last_update else None,
        'seconds_since_update': seconds_passed
    }
    
    return jsonify({'success': True, 'project_info': project_info})

def get_update_log(data, session):
    """Получение лога обновления"""
    update_id = data.get('update_id')
    project_name = data.get('project')
    
    if not update_id or not project_name:
        return jsonify({'success': False, 'message': 'Update ID and project required'})
    
    try:
        config = get_updates_config()
        log_file = Path(config['LOG_DIR']) / f"{update_id}.log"
        
        if not log_file.exists():
            return jsonify({'success': False, 'message': 'Log file not found'})
        
        with open(log_file, 'r', encoding='utf-8') as f:
            log_content = f.read()
        
        return jsonify({'success': True, 'log': log_content})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

def download_update_log(data, session):
    """Скачивание лога обновления"""
    update_id = data.get('update_id')
    project = data.get('project')
    
    if not update_id or not project:
        return "Update ID and project required", 400
    
    log_file_path = UPDATE_LOGS_DIR / f"update_{project}_{update_id}.log"
    
    if not log_file_path.exists():
        return "Log file not found", 404
    
    try:
        return send_file(
            log_file_path,
            as_attachment=True,
            download_name=f"update_{project}_{update_id}.log",
            mimetype='text/plain'
        )
    except Exception as e:
        return str(e), 500

def get_project_history(data, session):
    """Получение истории обновлений проекта"""
    project_name = data.get('project')
    
    # Обработка значения 'all' для получения всей истории
    if project_name == 'all':
        project_name = None
    
    try:
        config = get_updates_config()
        history = UpdatesModule.get_update_history(project_name, config)
        return jsonify({'success': True, 'history': history})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

def download_update_log(data, session):
    """Скачивание файла лога обновления"""
    update_id = data.get('update_id')
    project_name = data.get('project')
    
    if not update_id or not project_name:
        return "Update ID and project required", 400
    
    try:
        config = get_updates_config()
        log_file = Path(config['LOG_DIR']) / f"{update_id}.log"
        
        if not log_file.exists():
            return "Log file not found", 404
        
        # Отправляем файл для скачивания
        from flask import send_file
        return send_file(
            log_file,
            as_attachment=True,
            download_name=f"update_{project_name}_{update_id}.log",
            mimetype='text/plain'
        )
    except Exception as e:
        return str(e), 500

def get_updates_config():
    """Получение конфигурации с правильным путем к файлу состояния"""
    config = UpdatesModule.DEFAULT_CONFIG.copy()
    
    # Устанавливаем правильные пути к файлам
    script_path = Path(__file__).resolve().parent.parent.parent.parent
    update_files_dir = script_path / 'starter_files' / 'update_files'
    
    # Создаем директорию, если она не существует
    update_files_dir.mkdir(parents=True, exist_ok=True)
    
    state_file_path = update_files_dir / 'update_state.json'
    history_file_path = update_files_dir / 'update_history.json'
    
    config['STATE_FILE'] = str(state_file_path)
    config['HISTORY_FILE'] = str(history_file_path)
    
    # Создаем файлы состояния и истории, если они не существуют
    if not state_file_path.exists():
        with open(state_file_path, 'w') as f:
            json.dump({}, f)
    
    if not history_file_path.exists():
        with open(history_file_path, 'w') as f:
            json.dump([], f)
    
    return config

def update_project(data, session):
    """Обновление конкретного проекта"""
    project_name = data.get('project')
    if project_name not in PROJECTS:
        return jsonify({'success': False, 'message': t('project_not_found')})
    
    # Создание уникального ID обновления с временной меткой
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    update_id = f"{project_name}_{timestamp}"
    
    # Запуск обновления в отдельном потоке
    def run_update():
        try:
            config = get_updates_config()
            
            # Настраиваем специальный логгер для этого обновления
            logger = setup_update_logger(update_id, config)
            
            logger.info(f"=== Начало обновления проекта {project_name} ===")
            logger.info(f"Время начала: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"Базовая директория: {PROJECTS[project_name]['BASE_PATH']}")
            logger.info(f"URL загрузки: {PROJECTS[project_name]['DOWNLOAD_URL']}")
            
            # Запускаем обновление
            timestamp, updates, folders = UpdatesModule.start_updates_projects(
                projects_config={project_name: PROJECTS[project_name]},
                module_config=config,
                force_check=True,
                custom_logger=logger  # Передаем кастомный логгер
            )
            
            logger.info(f"=== Обновление завершено успешно ===")
            logger.info(f"Время завершения: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                
        except Exception as e:
            logger.error(f"ОШИБКА: {str(e)}")
            logger.error("=== Обновление завершено с ошибками ===")

    thread = threading.Thread(target=run_update)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'success': True, 
        'message': t('update_started'),
        'update_id': update_id,
        'project': project_name
    })

def setup_update_logger(update_id, config):
    """Настройка специального логгера для обновления"""
    log_dir = Path(config['LOG_DIR'])
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Создаем логгер
    logger = logging.getLogger(f'update_{update_id}')
    logger.setLevel(logging.INFO)
    
    # Удаляем существующие обработчики
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Файловый обработчик
    log_file = log_dir / f"{update_id}.log"
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    
    # Форматирование с детальной информацией
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Консольный обработчик (для отладки)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger
