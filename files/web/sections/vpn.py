import platform
from flask import render_template, request, jsonify, session
from files.core.utils.loader_utils import get
from files.core.utils.globalVars_utils import get_global


def t(key: str, **kwargs) -> str:
    i18n = get('i18n')
    if i18n and hasattr(i18n, 'translate'):
        return i18n.translate(key, **kwargs)
    return key


this_section_in_control_panel = True
section_icon = "bi-shield-lock"
section_name = "VPN"
section_order = 3
section_group = "software"
section_group_name = "Software"
section_group_icon = "bi-box-seam"


def index(data, session_obj):
    tailscale_installed = False
    tailscale_status = {'connected': False, 'status_text': 'Not available', 'ip': None,
                        'hostname': None, 'version': None, 'backend_state': None}
    tailscale_peers = []
    login_server = get_global('headscale_login_server', '')

    try:
        tailscale_installed = get('tailscale', 'check_tailscale_installed') or False
    except:
        pass

    if tailscale_installed:
        try:
            tailscale_status = get('tailscale', 'get_tailscale_status') or tailscale_status
        except:
            pass
        try:
            tailscale_peers = get('tailscale', 'get_tailscale_peers') or []
        except:
            pass

    return render_template(
        'sections/vpn/index.html',
        tailscale_installed=tailscale_installed,
        tailscale_status=tailscale_status,
        tailscale_peers=tailscale_peers,
        login_server=login_server,
        t=t
    )


def info(data, session_obj):
    tailscale_installed = False
    tailscale_status = {'connected': False, 'status_text': 'Not available', 'ip': None,
                        'hostname': None, 'version': None, 'backend_state': None}
    login_server = get_global('headscale_login_server', '')

    try:
        tailscale_installed = get('tailscale', 'check_tailscale_installed') or False
    except:
        pass

    if tailscale_installed:
        try:
            tailscale_status = get('tailscale', 'get_tailscale_status') or tailscale_status
        except:
            pass

    return render_template(
        'sections/vpn/info.html',
        tailscale_installed=tailscale_installed,
        tailscale_status=tailscale_status,
        login_server=login_server,
        current_os=platform.system().lower(),
        t=t
    )


def request_vpn(data, session_obj):
    login_server = data.get('login_server') or get_global('headscale_login_server', '')
    auth_key = data.get('auth_key')

    if not login_server:
        return jsonify({'status': 'error', 'message': 'HEADSCALE_LOGIN_SERVER not configured'})

    try:
        result = get('tailscale', 'connect_tailscale', login_server, auth_key)
        return jsonify(result)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})


def disconnect_vpn(data, session_obj):
    try:
        result = get('tailscale', 'disconnect_tailscale')
        return jsonify(result)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})


def check_vpn_status(data, session_obj):
    try:
        status = get('tailscale', 'get_tailscale_status')
        return jsonify(status)
    except Exception as e:
        return jsonify({'connected': False, 'status_text': 'Error', 'ip': None,
                        'hostname': None, 'version': None, 'backend_state': None})
