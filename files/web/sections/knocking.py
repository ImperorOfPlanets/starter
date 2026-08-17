import platform
from flask import render_template, jsonify
from files.core.utils.loader_utils import get
from files.core.utils.globalVars_utils import get_global
from files.core.utils.log_utils import LogManager

logger = LogManager.get_logger()

def t(key: str, **kwargs) -> str:
    i18n = get('i18n')
    if i18n and hasattr(i18n, 'translate'):
        return i18n.translate(key, **kwargs)
    return key

this_section_in_control_panel = True
section_icon = "bi-shield-lock"
section_name = "Port Knocking"
section_order = 2
section_group = "software"
section_group_name = "Software"
section_group_icon = "bi-box-seam"

IS_WINDOWS = platform.system() == 'Windows'


def get_knocking_status():
    """Get current knocking status for display"""
    config = get('knocking', 'get_knocking_config') or {}
    is_active = get('knocking', 'is_knocking_active') or False
    installed = get('knocking', 'is_knocking_installed') or False

    result = {
        'installed': installed,
        'enabled': is_active,
        'is_windows': IS_WINDOWS,
        'ports': config.get('ports', []),
        'timeout': config.get('timeout', 5),
        'target_port': config.get('target_port', 22),
        'auto_close_seconds': config.get('auto_close_seconds', 30),
        'open_ports': []
    }

    if IS_WINDOWS and is_active:
        open_ports = get('knocking', 'get_open_knock_ports') or []
        result['open_ports'] = open_ports

    return result


def index(data, session):
    """Main section page"""
    status = get_knocking_status()
    return render_template(
        'sections/knocking/index.html',
        status=status,
        t=t
    )


def info(data, session):
    """Information page"""
    status = get_knocking_status()
    return render_template(
        'sections/knocking/info.html',
        status=status,
        t=t
    )


def settings_page(data, session):
    """Settings page"""
    status = get_knocking_status()
    return render_template(
        'sections/knocking/settings.html',
        status=status,
        t=t
    )


def toggle_service(data, session):
    """Toggle service state"""
    try:
        action = data.get('action')
        if IS_WINDOWS:
            if action == 'stop':
                success = get('knocking', 'close_all_knock_rules')
            else:
                success = True
        else:
            if action == 'start':
                success = get('knocking', 'start_knocking_service')
            elif action == 'stop':
                success = get('knocking', 'stop_knocking_service')
            else:
                return jsonify({'status': 'error', 'message': 'Invalid action'})
                success = False

        if success:
            return jsonify({'status': 'success', 'message': t('sections.knocking.index.service_updated')})
        return jsonify({'status': 'error', 'message': t('sections.knocking.index.service_update_failed')})
    except Exception as e:
        logger.error(f"Error toggling knocking: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)})


def update_settings(data, session):
    """Update knocking settings"""
    try:
        ports_str = data.get('ports', '')
        timeout = int(data.get('timeout', 5))
        target_port = int(data.get('target_port', 22))
        auto_close = int(data.get('auto_close_seconds', 30))

        ports = [int(p.strip()) for p in ports_str.split(',') if p.strip()]

        if len(ports) < 2:
            return jsonify({'status': 'error', 'message': 'Need at least 2 ports'})

        if timeout < 1 or timeout > 30:
            return jsonify({'status': 'error', 'message': 'Timeout must be 1-30 seconds'})

        config = {
            'ports': ports,
            'timeout': timeout,
            'target_port': target_port,
            'auto_close_seconds': auto_close
        }

        success = get('knocking', 'save_knocking_config', config)

        if success:
            return jsonify({'status': 'success', 'message': 'Settings saved'})
        return jsonify({'status': 'error', 'message': 'Failed to save settings'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})


def knock_test(data, session):
    """Test knocking sequence"""
    try:
        host = data.get('host', '127.0.0.1')
        config = get('knocking', 'get_knocking_config')
        result = get('knocking', 'knock_and_open', host, config)

        if result and result.get('status') == 'success':
            return jsonify(result)
        return jsonify({'status': 'error', 'message': result.get('message', 'Test failed')})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})


def open_port_manual(data, session):
    """Manually open a port"""
    try:
        port = int(data.get('port', 0))
        if port < 1 or port > 65535:
            return jsonify({'status': 'error', 'message': 'Invalid port'})

        success = get('knocking', 'open_firewall_rule', port)
        if success:
            return jsonify({'status': 'success', 'message': f'Port {port} opened'})
        return jsonify({'status': 'error', 'message': 'Failed to open port'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})


def close_port_manual(data, session):
    """Manually close a port"""
    try:
        port = int(data.get('port', 0))
        if port < 1 or port > 65535:
            return jsonify({'status': 'error', 'message': 'Invalid port'})

        success = get('knocking', 'close_firewall_rule', port)
        if success:
            return jsonify({'status': 'success', 'message': f'Port {port} closed'})
        return jsonify({'status': 'error', 'message': 'Failed to close port'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})


def close_all_ports(data, session):
    """Close all knock-opened ports"""
    try:
        success = get('knocking', 'close_all_knock_rules')
        if success:
            return jsonify({'status': 'success', 'message': 'All knock ports closed'})
        return jsonify({'status': 'error', 'message': 'Failed to close ports'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})


def get_open_ports(data, session):
    """Get list of currently open knock ports"""
    try:
        ports = get('knocking', 'get_open_knock_ports') or []
        return jsonify({'status': 'success', 'ports': ports})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})
