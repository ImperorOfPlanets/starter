from flask import render_template, jsonify, request, send_file
from datetime import datetime
from pathlib import Path
import json
import logging
import threading

from files.core.utils.loader_utils import get
from files.core.oss.default.updates import UpdatesModule
from files.core.utils.log_utils import LogManager
from files.configs.starter_repos import STARTER_REPOSITORIES, UPDATE_CHECK_CONFIG

logger = LogManager.get_logger(__name__)

# Функция перевода
def t(key: str, **kwargs) -> str:
    i18n = get('i18n')
    if i18n and hasattr(i18n, 'translate'):
        return i18n.translate(key, **kwargs)
    return key


# =============================================================================
# ФУНКЦИИ ДЛЯ СТАРТЕРА
# =============================================================================

def get_starter_update_status():
    """Получает статус обновлений стартера"""
    config = UpdatesModule.get_updates_config()
    last_update = UpdatesModule.get_last_update_time('starter', config)
    seconds_passed = UpdatesModule.seconds_since_last_update('starter', config)
    
    status_info = {
        'status': 'never_updated',
        'color': 'secondary',
        'last_update': last_update,
        'has_update': False,
        'update_available': False,
        'current_repository': STARTER_REPOSITORIES[0] if STARTER_REPOSITORIES else {},
        'repositories': STARTER_REPOSITORIES,
        'settings': UPDATE_CHECK_CONFIG
    }
    
    if last_update:
        if seconds_passed < 3600:
            status_info['status'] = 'up_to_date'
            status_info['color'] = 'success'
        elif seconds_passed < 86400:
            status_info['status'] = 'recently_updated'
            status_info['color'] = 'warning'
        else:
            status_info['status'] = 'update_available'
            status_info['color'] = 'danger'
            status_info['update_available'] = True
        status_info['has_update'] = True
    
    return status_info


def check_starter_updates():
    """Проверяет обновления стартера"""
    config = UpdatesModule.get_updates_config()
    last_update = UpdatesModule.get_last_update_time('starter', config)
    seconds_passed = UpdatesModule.seconds_since_last_update('starter', config)
    
    return {
        'has_update': seconds_passed > 3600,
        'update_available': seconds_passed > 86400,
        'last_update': last_update
    }


def update_starter():
    """Обновляет стартер"""
    if not STARTER_REPOSITORIES:
        return {'status': 'error', 'message': 'No repositories configured'}
    
    starter_config = {
        'DOWNLOAD_URL': STARTER_REPOSITORIES[0]['url'],
        'TARGETS': [
            'README.md',
            'starter.py',
            'files/**',
            '.env.example',
            'requirements.txt'
        ],
        'IGNORED': [
            "files/update/**",
            "files/logs/**",
            "files/web/ssl/**",
            "files/web/sessions/**",
            "venv/**",
            "**/__pycache__/**",
            "**/*.pyc",
            "*.log",
            ".git/**"
        ],
        'CRITICAL_FILES': [
            'starter.py',
            'files/__init__.py',
            'files/core/__init__.py'
        ],
        'RESTART_AFTER_UPDATE': True,
        'MAX_RETRIES': 3,
        'TIMEOUT': 30
    }
    
    return UpdatesModule.update_project('starter', starter_config)


def get_starter_history():
    """Получает историю обновлений стартера"""
    history = UpdatesModule.get_update_history('starter')
    return history.get('history', [])


def get_starter_repositories():
    """Получает список репозиториев стартера"""
    return STARTER_REPOSITORIES


def get_starter_current_repository():
    """Получает текущий репозиторий стартера"""
    return STARTER_REPOSITORIES[0] if STARTER_REPOSITORIES else {}


def switch_starter_repository(repo_name):
    """Переключает репозиторий стартера"""
    # В будущем можно реализовать сохранение выбранного репозитория
    return True


def get_starter_settings():
    """Получает настройки обновлений"""
    return UPDATE_CHECK_CONFIG.copy()


def update_starter_settings(settings):
    """Обновляет настройки обновлений"""
    # В будущем можно сохранять в файл
    return True


# =============================================================================
# ФУНКЦИИ ДЛЯ СЕРВЕРНЫХ ПРОЕКТОВ
# =============================================================================

def get_server_updates_status():
    """Получает статус обновлений для всех серверов"""
    from files.configs.server_types import SERVER_TYPES
    from files.core.oss.default.serverupdates import ServerupdatesModule
    
    return ServerupdatesModule.get_all_server_updates_status()


def update_server(server_type):
    """Обновляет сервер"""
    from files.core.oss.default.serverupdates import ServerupdatesModule
    return ServerupdatesModule.update_server(server_type)


def check_server_updates(server_type):
    """Проверяет обновления сервера"""
    from files.core.oss.default.serverupdates import ServerupdatesModule
    return ServerupdatesModule.check_server_updates(server_type)


def get_server_update_history(server_type):
    """Получает историю обновлений сервера"""
    from files.core.oss.default.serverupdates import ServerupdatesModule
    return ServerupdatesModule.get_server_update_history(server_type)


# =============================================================================
# ОБЩИЕ ФУНКЦИИ
# =============================================================================

def get_update_log(update_id):
    """Получает лог обновления"""
    return UpdatesModule.get_update_log(update_id)


def download_update_log(update_id):
    """Скачивает лог обновления"""
    config = UpdatesModule.get_updates_config()
    log_file = Path(config['LOG_DIR']) / f"{update_id}.log"
    return log_file


def check_all_updates():
    """Проверяет обновления для всех компонентов"""
    starter_info = check_starter_updates()
    
    from files.configs.server_types import SERVER_TYPES
    from files.core.oss.default.serverupdates import ServerupdatesModule
    
    server_status = []
    for server_type in SERVER_TYPES.keys():
        status = ServerupdatesModule.check_server_updates(server_type)
        server_status.append({
            'type': server_type,
            'has_update': status.get('has_update', False),
            'update_available': status.get('update_available', False)
        })
    
    return {
        'starter': starter_info,
        'servers': server_status
    }


# =============================================================================
# РОУТЫ
# =============================================================================

this_section_in_control_panel = True
section_icon = "bi-cloud-arrow-down"
section_name = "Updates"
section_order = 10


def index(data, session):
    """Главная страница модуля обновлений"""
    starter_status = get_starter_update_status()
    repositories = get_starter_repositories()
    update_settings = get_starter_settings()
    
    return render_template(
        'sections/updates/index.html',
        t=t,
        starter_status=starter_status,
        repositories=repositories,
        update_settings=update_settings
    )


def check_starter_updates_route(data, session):
    """Проверяет обновления для стартера"""
    try:
        update_info = check_starter_updates()
        return jsonify({
            'success': True,
            'has_update': update_info['has_update'],
            'update_available': update_info['update_available'],
            'last_update': update_info['last_update']
        })
    except Exception as e:
        logger.error(f"Error in check_starter_updates: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


def update_starter_route(data, session):
    """Выполняет обновление стартера"""
    try:
        result = update_starter()
        return jsonify({
            'success': result.get('status') != 'error',
            'message': result.get('message', 'Update completed'),
            'update_id': result.get('update_id')
        })
    except Exception as e:
        logger.error(f"Error in update_starter: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


def get_starter_history_route(data, session):
    """Получает историю обновлений стартера"""
    try:
        history = get_starter_history()
        return jsonify({
            'success': True,
            'history': history
        })
    except Exception as e:
        logger.error(f"Error in get_starter_history: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


def get_update_log_route(data, session):
    """Получает лог обновления"""
    update_id = data.get('update_id')
    
    if not update_id:
        return jsonify({'success': False, 'message': 'Update ID required'})
    
    try:
        log_content = get_update_log(update_id)
        return jsonify({
            'success': True,
            'log': log_content
        })
    except Exception as e:
        logger.error(f"Error in get_update_log: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


def download_update_log_route(data, session):
    """Скачивает лог обновления"""
    update_id = data.get('update_id')
    
    if not update_id:
        return jsonify({'success': False, 'message': 'Update ID required'})
    
    try:
        log_file = download_update_log(update_id)
        if not log_file.exists():
            return jsonify({'success': False, 'message': 'Log file not found'})
        
        return send_file(
            log_file,
            as_attachment=True,
            download_name=f"{update_id}.log",
            mimetype='text/plain'
        )
    except Exception as e:
        logger.error(f"Error in download_update_log: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


def get_repositories_route(data, session):
    """Получение списка доступных репозиториев"""
    try:
        repositories = get_starter_repositories()
        current_repo = get_starter_current_repository()
        
        return jsonify({
            'success': True,
            'repositories': repositories,
            'current_repository': current_repo
        })
    except Exception as e:
        logger.error(f"Error in get_repositories: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


def switch_repository_route(data, session):
    """Переключение репозитория"""
    repo_name = data.get('repo_name')
    
    if not repo_name:
        return jsonify({'success': False, 'message': 'Repository name required'})
    
    try:
        success = switch_starter_repository(repo_name)
        if success:
            return jsonify({
                'success': True,
                'message': f'Repository switched to {repo_name}'
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Repository {repo_name} not found'
            })
    except Exception as e:
        logger.error(f"Error in switch_repository: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


def get_update_settings_route(data, session):
    """Получение настроек обновлений"""
    try:
        settings = get_starter_settings()
        return jsonify({'success': True, 'settings': settings})
    except Exception as e:
        logger.error(f"Error in get_update_settings: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


def update_settings_route(data, session):
    """Обновление настроек обновлений"""
    try:
        new_settings = {
            'AUTO_UPDATE': data.get('auto_update') == 'true',
            'NOTIFY_AVAILABLE': data.get('notify_available') == 'true',
            'CHECK_INTERVAL_MINUTES': int(data.get('check_interval', 60))
        }
        
        success = update_starter_settings(new_settings)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Settings updated successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to update settings'
            })
    except Exception as e:
        logger.error(f"Error in update_settings: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


def check_all_route(data, session):
    """Проверяет обновления для всех компонентов"""
    try:
        result = check_all_updates()
        return jsonify({
            'success': True,
            'starter': result['starter'],
            'servers': result['servers']
        })
    except Exception as e:
        logger.error(f"Error in check_all: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


def get_server_updates_status_route(data, session):
    """Получает статус обновлений для всех серверов"""
    try:
        server_status = get_server_updates_status()
        return jsonify({
            'success': True,
            'server_status': server_status
        })
    except Exception as e:
        logger.error(f"Error in get_server_updates_status: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


def update_server_route(data, session):
    """Выполняет обновление сервера"""
    server_type = data.get('server_type')
    
    if not server_type:
        return jsonify({'success': False, 'message': 'Server type required'})
    
    try:
        result = update_server(server_type)
        return jsonify({
            'success': result.get('status') != 'error',
            'message': result.get('message', 'Update completed'),
            'update_id': result.get('update_id')
        })
    except Exception as e:
        logger.error(f"Error in update_server: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


def check_server_updates_route(data, session):
    """Проверяет обновления для сервера"""
    server_type = data.get('server_type')
    
    try:
        result = check_server_updates(server_type)
        return jsonify({
            'success': True,
            'has_update': result.get('has_update', False),
            'update_available': result.get('update_available', False),
            'last_update': result.get('last_update')
        })
    except Exception as e:
        logger.error(f"Error in check_server_updates: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


def get_server_update_history_route(data, session):
    """Получает историю обновлений сервера"""
    server_type = data.get('server_type')
    
    try:
        history = get_server_update_history(server_type)
        return jsonify({
            'success': True,
            'history': history,
            'server_type': server_type
        })
    except Exception as e:
        logger.error(f"Error in get_server_update_history: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})