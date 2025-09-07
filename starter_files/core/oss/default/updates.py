from flask import render_template, jsonify
from datetime import datetime
from starter_files.core.utils.i18n_utils import t
from starter_files.core.oss.default.updates import UpdatesModule
from starter_files.configs.configs import PROJECTS

# Конфигурация модуля для панели управления
this_section_in_control_panel = True
section_icon = "bi-cloud-arrow-down"
section_name = "Updates"
section_order = 10

def index(data, session):
    """Главная страница модуля обновлений"""
    update_status = get_update_status()
    return render_template(
        'sections/updates/index.html',
        t=t,
        update_status=update_status
    )

def info(data, session):
    """Страница информации об обновлениях"""
    return render_template(
        'sections/updates/info.html',
        t=t,
        message=t('updates_placeholder_info')
    )

def check_all(data, session):
    """Проверка всех обновлений"""
    try:
        timestamp, updates, folders = UpdatesModule.start_updates_projects(
            projects_config=PROJECTS,
            force_check=True
        )
        return jsonify({'success': True, 'message': t('updates_check_success')})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

def update_project(data, session):
    """Обновление конкретного проекта"""
    project_name = data.get('project')
    if project_name not in PROJECTS:
        return jsonify({'success': False, 'message': t('project_not_found')})
    
    try:
        success = UpdatesModule.check_and_update_project(
            project_name=project_name,
            projects_config=PROJECTS,
            force=True
        )
        if success:
            return jsonify({'success': True, 'message': t('update_success')})
        else:
            return jsonify({'success': False, 'message': t('update_failed')})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

def get_update_status():
    """Получение статуса обновлений для всех проектов"""
    status = []
    config = UpdatesModule.DEFAULT_CONFIG
    
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