from flask import render_template, jsonify, request, send_file
from datetime import datetime
from pathlib import Path
import json
import logging
import threading

from files.core.utils.i18n_utils import t
from files.core.oss.default.updates import UpdatesModule
from files.core.oss.default.starterupdates import StarterUpdates
from files.core.utils.log_utils import LogManager

# Настройка логирования
logger = LogManager.get_logger(__name__)

# Конфигурация модуля для панели управления
this_section_in_control_panel = True
section_icon = "bi-cloud-arrow-down"
section_name = "Updates"
section_order = 10

def index(data, session):
    """Главная страница модуля обновлений"""
    # Статус обновления стартера
    starter_status = StarterUpdates.get_update_status()
    
    # Доступные репозитории
    repositories = StarterUpdates.get_available_repositories()
    
    # Настройки обновлений
    update_settings = StarterUpdates.get_update_settings()
    
    return render_template(
        'sections/updates/index.html',
        t=t,
        starter_status=starter_status,
        repositories=repositories,
        update_settings=update_settings
    )

def check_starter_updates(data, session):
    """Проверяет обновления для стартера"""
    try:
        update_info = StarterUpdates.check_for_updates()
        return jsonify({
            'success': True,
            'has_update': update_info['has_update'],
            'update_available': update_info['update_available'],
            'last_update': update_info['last_update']
        })
    except Exception as e:
        logger.error(f"Error in check_starter_updates: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

def update_starter(data, session):
    """Выполняет обновление стартера"""
    try:
        result = StarterUpdates.update_starter()
        
        return jsonify({
            'success': result.get('status') != 'error',
            'message': result.get('message', 'Update completed'),
            'update_id': result.get('update_id')
        })
    except Exception as e:
        logger.error(f"Error in update_starter: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

def get_starter_history(data, session):
    """Получает историю обновлений стартера"""
    try:
        history = StarterUpdates.get_update_history()
        return jsonify({
            'success': True,
            'history': history
        })
    except Exception as e:
        logger.error(f"Error in get_starter_history: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

def get_update_log(data, session):
    """Получает лог обновления"""
    update_id = data.get('update_id')
    
    if not update_id:
        return jsonify({'success': False, 'message': 'Update ID required'})
    
    try:
        log_content = UpdatesModule.get_update_log(update_id)
        return jsonify({
            'success': True,
            'log': log_content
        })
    except Exception as e:
        logger.error(f"Error in get_update_log: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

def download_update_log(data, session):
    """Скачивает лог обновления"""
    update_id = data.get('update_id')
    
    if not update_id:
        return jsonify({'success': False, 'message': 'Update ID required'})
    
    try:
        config = UpdatesModule.get_updates_config()
        log_file = Path(config['LOG_DIR']) / f"{update_id}.log"
        
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

def get_repositories(data, session):
    """Получение списка доступных репозиториев"""
    try:
        repositories = StarterUpdates.get_available_repositories()
        current_repo = StarterUpdates.get_current_repository()
        
        return jsonify({
            'success': True,
            'repositories': repositories,
            'current_repository': current_repo
        })
    except Exception as e:
        logger.error(f"Error in get_repositories: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

def switch_repository(data, session):
    """Переключение репозитория"""
    repo_name = data.get('repo_name')
    
    if not repo_name:
        return jsonify({'success': False, 'message': 'Repository name required'})
    
    try:
        success = StarterUpdates.switch_repository(repo_name)
        
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

def get_update_settings(data, session):
    """Получение настроек обновлений"""
    try:
        settings = StarterUpdates.get_update_settings()
        return jsonify({'success': True, 'settings': settings})
    except Exception as e:
        logger.error(f"Error in get_update_settings: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

def update_settings(data, session):
    """Обновление настроек обновлений"""
    try:
        new_settings = {
            'AUTO_UPDATE': data.get('auto_update') == 'true',
            'NOTIFY_AVAILABLE': data.get('notify_available') == 'true',
            'CHECK_INTERVAL_MINUTES': int(data.get('check_interval', 60))
        }
        
        success = StarterUpdates.update_settings(new_settings)
        
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

def check_all(data, session):
    """Проверяет обновления для всех компонентов"""
    try:
        # Проверяем обновления стартера
        starter_info = StarterUpdates.check_for_updates()
        
        # Проверяем обновления серверов
        from files.core.oss.default.serverupdates import ServerUpdates
        server_status = ServerUpdates.get_all_server_updates_status()
        
        return jsonify({
            'success': True,
            'starter': {
                'has_update': starter_info['has_update'],
                'update_available': starter_info['update_available']
            },
            'servers': server_status
        })
    except Exception as e:
        logger.error(f"Error in check_all: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

# =============================================================================
# ФУНКЦИИ ДЛЯ СЕРВЕРНЫХ ОБНОВЛЕНИЙ
# =============================================================================

def get_server_updates_status(data, session):
    """Получает статус обновлений для всех серверов"""
    try:
        from files.core.oss.default.serverupdates import ServerUpdates
        server_status = ServerUpdates.get_all_server_updates_status()
        
        return jsonify({
            'success': True,
            'server_status': server_status
        })
    except Exception as e:
        logger.error(f"Error in get_server_updates_status: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

def update_server(data, session):
    """Выполняет обновление сервера"""
    server_type = data.get('server_type')
    
    if not server_type:
        return jsonify({'success': False, 'message': 'Server type required'})
    
    try:
        from files.core.oss.default.serverupdates import ServerUpdates
        result = ServerUpdates.update_server(server_type)
        
        return jsonify({
            'success': result.get('status') != 'error',
            'message': result.get('message', 'Update completed'),
            'update_id': result.get('update_id')
        })
    except Exception as e:
        logger.error(f"Error in update_server: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

def check_server_updates(data, session):
    """Проверяет обновления для сервера"""
    server_type = data.get('server_type')
    
    try:
        from files.core.oss.default.serverupdates import ServerUpdates
        result = ServerUpdates.check_server_updates(server_type)
        
        return jsonify({
            'success': True,
            'has_update': result.get('has_update', False),
            'update_available': result.get('update_available', False),
            'last_update': result.get('last_update')
        })
    except Exception as e:
        logger.error(f"Error in check_server_updates: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

def get_server_update_history(data, session):
    """Получает историю обновлений сервера"""
    server_type = data.get('server_type')
    
    try:
        from files.core.oss.default.serverupdates import ServerUpdates
        history = ServerUpdates.get_server_update_history(server_type)
        
        return jsonify({
            'success': True,
            'history': history,
            'server_type': server_type
        })
    except Exception as e:
        logger.error(f"Error in get_server_update_history: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

def get_server_update_log(data, session):
    """Получает лог обновления сервера"""
    update_id = data.get('update_id')
    
    if not update_id:
        return jsonify({'success': False, 'message': 'Update ID required'})
    
    try:
        log_content = UpdatesModule.get_update_log(update_id)
        return jsonify({
            'success': True,
            'log': log_content
        })
    except Exception as e:
        logger.error(f"Error in get_server_update_log: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

def rollback_server_update(data, session):
    """Откатывает обновление сервера"""
    server_type = data.get('server_type')
    update_id = data.get('update_id')
    
    if not server_type or not update_id:
        return jsonify({'success': False, 'message': 'Server type and update ID required'})
    
    try:
        result = UpdatesModule.rollback_update(f"server_{server_type}", update_id)
        
        return jsonify({
            'success': result.get('status') == 'success',
            'message': result.get('message', 'Rollback completed')
        })
    except Exception as e:
        logger.error(f"Error in rollback_server_update: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

def get_available_rollbacks(data, session):
    """Получает список доступных откатов для сервера"""
    server_type = data.get('server_type')
    
    if not server_type:
        return jsonify({'success': False, 'message': 'Server type required'})
    
    try:
        rollbacks = UpdatesModule.get_available_rollbacks(f"server_{server_type}")
        
        return jsonify({
            'success': True,
            'rollbacks': rollbacks,
            'server_type': server_type
        })
    except Exception as e:
        logger.error(f"Error in get_available_rollbacks: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})