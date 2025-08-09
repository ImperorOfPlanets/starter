# knocking.py
from flask import render_template
from starter_files.utils.i18n import t
from starter_files.utils.logger import get_logger
from starter_files.utils.knocking_utils import (
    is_knocking_installed,
    get_knocking_config,
    is_knocking_active,
    start_knocking_service,
    stop_knocking_service,
    update_knocking_config,
    install_knocking
)

logger = get_logger()

# Module configuration for control panel
this_module_in_control_panel = True
module_icon = "bi-shield-lock"
module_name = "Port Knocking"
module_order = 3

def get_knocking_status():
    """Get current knocking status for display"""
    installed = is_knocking_installed()
    if not installed:
        return {
            'installed': False,
            'enabled': False,
            'ports': [],
            'timeout': 0
        }
    
    config = get_knocking_config() or {
        'ports': [],
        'timeout': 0
    }
    
    return {
        'installed': True,
        'enabled': is_knocking_active(),
        'ports': config.get('ports', []),
        'timeout': config.get('timeout', 0)
    }

def index(data, session):
    """Main module page"""
    status = get_knocking_status()
    return render_template(
        'modules/knocking/index.html',
        status=status,
        t=t
    )

def info(data, session):
    """Information page"""
    status = get_knocking_status()
    return render_template(
        'modules/knocking/info.html',
        status=status,
        t=t
    )

def settings(data, session):
    """Settings page"""
    status = get_knocking_status()
    return render_template(
        'modules/knocking/settings.html',
        status=status,
        t=t
    )

def toggle_service(data, session):
    """Toggle service state"""
    try:
        action = data.get('action')
        if action == 'start':
            success = start_knocking_service()
        elif action == 'stop':
            success = stop_knocking_service()
        else:
            return {'status': 'error', 'message': t('invalid_action')}
        
        if success:
            return {'status': 'success', 'message': t('knocking_service_updated')}
        return {'status': 'error', 'message': t('knocking_service_update_failed')}
    except Exception as e:
        logger.error(f"Error toggling knocking service: {str(e)}")
        return {'status': 'error', 'message': str(e)}

def update_settings(data, session):
    """Update knocking settings"""
    try:
        ports = [int(p.strip()) for p in data.get('ports', '').split(',') if p.strip()]
        timeout = int(data.get('timeout', 0))
        
        if len(ports) < 2:
            return {'status': 'error', 'message': t('modules.knocking.settings.min_ports')}
        
        if timeout < 1 or timeout > 10:
            return {'status': 'error', 'message': t('modules.knocking.settings.invalid_timeout')}
        
        success = update_knocking_config(ports, timeout)
        
        if success:
            return {
                'status': 'success', 
                'message': t('modules.knocking.settings.save_success')
            }
        return {
            'status': 'error', 
            'message': t('modules.knocking.settings.save_error')
        }
    except Exception as e:
        logger.error(f"Error updating knocking settings: {str(e)}")
        return {
            'status': 'error', 
            'message': f"{t('modules.knocking.settings.save_error')}: {str(e)}"
        }

def installKnocking(data, session):
    """Handle knocking installation request"""
    try:
        if is_knocking_installed():
            return {
                'status': 'warning',
                'message': t('knocking_already_installed')
            }
        
        success, message = install_knocking()
        
        if success:
            # После установки активируем сервис
            start_knocking_service()
            return {
                'status': 'success',
                'message': t('knocking_install_success') + ": " + message
            }
        else:
            return {
                'status': 'error',
                'message': t('knocking_install_failed') + ": " + message
            }
    
    except Exception as e:
        logger.error(f"Error installing knocking: {str(e)}")
        return {
            'status': 'error',
            'message': t('knocking_install_error') + ": " + str(e)
        }