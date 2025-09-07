import json
import logging

from flask import render_template, jsonify, request
from datetime import datetime
from pathlib import Path

from starter_files.core.utils.i18n_utils import t
from starter_files.core.oss.default.updates import UpdatesModule
from starter_files.configs.configs import PROJECTS

# Настройка логирования
logger = logging.getLogger(__name__)

# Конфигурация модуля для панели управления
this_section_in_control_panel = True
section_icon = "bi-cloud-arrow-down"
section_name = "Updates"
section_order = 10

def index(data, session):
    """Главная страница модуля обновлений"""
    update_status = get_update_status_list()  # Changed here
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

def update_project(data, session):
    """Обновление конкретного проекта"""
    project_name = data.get('project')
    if project_name not in PROJECTS:
        return jsonify({'success': False, 'message': t('project_not_found')})
    
    try:
        # Получаем конфиг с правильным путем к файлу состояния
        config = get_updates_config()
        
        # Запускаем обновление и получаем update_id
        timestamp, updates, folders = UpdatesModule.start_updates_projects(
            projects_config={project_name: PROJECTS[project_name]},
            module_config=config,
            force_check=True  # Исправлено с force на force_check
        )
        
        return jsonify({
            'success': True, 
            'message': t('update_success'),
            'update_id': f"update_{timestamp}"
        })
    except Exception as e:
        logger.error(f"Error updating project {project_name}: {str(e)}")
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

def get_updates_config():
    """Получение конфигурации с правильным путем к файлу состояния"""
    config = UpdatesModule.DEFAULT_CONFIG.copy()
    
    # Устанавливаем правильные пути к файлам
    script_path = Path(__file__).resolve().parent.parent.parent.parent
    state_file_path = script_path / 'starter_files' / 'update_state.json'
    history_file_path = script_path / 'starter_files' / 'update_history.json'
    
    config['STATE_FILE'] = str(state_file_path)
    config['HISTORY_FILE'] = str(history_file_path)
    
    # Создаем директорию, если она не существует
    state_file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Создаем файлы, если они не существуют
    if not state_file_path.exists():
        with open(state_file_path, 'w') as f:
            json.dump({}, f)
    
    if not history_file_path.exists():
        with open(history_file_path, 'w') as f:
            json.dump([], f)
    
    return config

def get_update_logs(data, session):
    """Получение логов процесса обновления"""
    update_id = data.get('update_id')
    if not update_id:
        return jsonify({'success': False, 'message': 'Update ID required'})
    
    try:
        logs = UpdatesModule.get_update_logs(update_id)
        return jsonify({'success': True, 'logs': logs})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

def get_update_status(data, session):
    """Получение статуса процесса обновления"""
    update_id = data.get('update_id')
    if not update_id:
        return jsonify({'success': False, 'message': 'Update ID required'})
    
    try:
        status = UpdatesModule.get_update_status(update_id)
        return jsonify({'success': True, 'status': status})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

def start_update_all_async(data, session):
    """Асинхронный запуск обновления всех проектов"""
    try:
        from starter_files.configs.configs import PROJECTS
        update_id = UpdatesModule.start_update_in_thread(
            projects_config=PROJECTS,
            force_check=True
        )
        return jsonify({'success': True, 'update_id': update_id})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

def start_update_project_async(data, session):
    """Асинхронный запуск обновления конкретного проекта"""
    project_name = data.get('project')
    if project_name not in PROJECTS:
        return jsonify({'success': False, 'message': 'Project not found'})
    
    try:
        project_config = {project_name: PROJECTS[project_name]}
        update_id = UpdatesModule.start_update_in_thread(
            projects_config=project_config,
            force_check=True
        )
        return jsonify({'success': True, 'update_id': update_id, 'project': project_name})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

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

def get_update_log(data, session):
    """Получение лога конкретного обновления"""
    update_id = data.get('update_id')
    if not update_id:
        return jsonify({'success': False, 'message': 'Update ID required'})
    
    try:
        config = get_updates_config()
        log_content = UpdatesModule.get_update_log(update_id, config)
        return jsonify({'success': True, 'log': log_content})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})