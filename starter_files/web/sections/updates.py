from flask import render_template, jsonify, request, send_file
from datetime import datetime
from pathlib import Path
import json
import logging
import threading

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

def index(data, session):
    """Главная страница модуля обновлений"""
    update_status = get_update_status_list()
    return render_template(
        'sections/updates/index.html',
        t=t,
        update_status=update_status
    )

def get_update_status_list():
    """Получение статуса обновлений для всех проектов из логов"""
    status = []
    config = UpdatesModule.get_updates_config()
    
    for project_name in PROJECTS.keys():
        last_update = UpdatesModule.get_last_update_time(project_name, config)
        seconds_passed = UpdatesModule.seconds_since_last_update(project_name, config)
        
        # Определяем статус на основе времени последнего обновления
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
        # Запускаем обновление каждого проекта в отдельном потоке
        for project_name in PROJECTS.keys():
            thread = threading.Thread(
                target=UpdatesModule.update_project,
                args=(project_name, PROJECTS[project_name])
            )
            thread.daemon = True
            thread.start()
        
        return jsonify({'success': True, 'message': t('updates_check_started')})
    except Exception as e:
        logger.error(f"Error in check_all: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

def get_project_details(data, session):
    """Получение детальной информации о проекте"""
    project_name = data.get('project')
    if project_name not in PROJECTS:
        return jsonify({'success': False, 'message': t('project_not_found')})
    
    project_config = PROJECTS[project_name]
    config = UpdatesModule.get_updates_config()
    
    # Получаем информацию о последнем обновлении из логов
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
    
    if not update_id:
        return jsonify({'success': False, 'message': 'Update ID required'})
    
    try:
        log_content = UpdatesModule.get_update_log(update_id)
        return jsonify({'success': True, 'log': log_content})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

def download_update_log(data, session):
    """Скачивание лога обновления"""
    update_id = data.get('update_id')
    
    if not update_id:
        return "Update ID required", 400
    
    config = UpdatesModule.get_updates_config()
    log_file = Path(config['LOG_DIR']) / f"{update_id}.log"
    
    if not log_file.exists():
        return "Log file not found", 404
    
    try:
        return send_file(
            log_file,
            as_attachment=True,
            download_name=f"{update_id}.log",
            mimetype='text/plain'
        )
    except Exception as e:
        return str(e), 500

def get_project_history(data, session):
    """Получение истории обновлений проекта из логов"""
    project_name = data.get('project')
    
    try:
        history = UpdatesModule.get_update_history(project_name)
        return jsonify({'success': True, 'history': history['history']})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

def update_project(data, session):
    """Обновление конкретного проекта"""
    project_name = data.get('project')
    if project_name not in PROJECTS:
        return jsonify({'success': False, 'message': t('project_not_found')})
    
    # Запуск обновления в отдельном потоке
    def run_update():
        try:
            update_id = UpdatesModule.update_project(project_name, PROJECTS[project_name])
            logger.info(f"Обновление {project_name} завершено, ID: {update_id}")
        except Exception as e:
            logger.error(f"Ошибка при обновлении {project_name}: {str(e)}")

    thread = threading.Thread(target=run_update)
    thread.daemon = True
    thread.start()
    
    # Создаем ID для отслеживания (будет использовано в логах)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    update_id = f"{project_name}_{timestamp}"
    
    return jsonify({
        'success': True, 
        'message': t('update_started'),
        'update_id': update_id,
        'project': project_name
    })