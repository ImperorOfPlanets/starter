import platform
import socket
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
    
    # Получаем назначенные Tailscale домены из заявок пользователя
    assigned_domains = session_obj.get('tailscale_domains', [])
    user_applications = session_obj.get('user_applications', [])
    
    # Проверяем статус заявки на смену железа
    hardware_change_status = {'has_pending': False}
    oauth_token = session_obj.get('oauth_token')
    if oauth_token:
        try:
            from files.core.software.default.installation_lock import InstallationLockModule
            hardware_change_status = InstallationLockModule.get_hardware_change_status(oauth_token)
        except Exception as e:
            logger.warning(f"Failed to get hardware change status: {e}")

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
        assigned_domains=assigned_domains,
        user_applications=user_applications,
        hardware_change_status=hardware_change_status,
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

    # Если нет auth_key — пробуем получить из сессии (получен при логине)
    if not auth_key:
        auth_key = session_obj.get('tailscale_auth_key')
        if auth_key:
            logger.info("Using auth_key from session (obtained at login)")

    # Если всё ещё нет — пробуем получить из одобренной заявки
    if not auth_key:
        user_applications = session_obj.get('user_applications', [])
        for app in user_applications:
            if app.get('type') == 'tailscale' and app.get('status') == 'approved':
                oauth_token = session_obj.get('oauth_token')
                if oauth_token:
                    try:
                        import requests
                        from files.core.utils.globalVars_utils import get_global
                        
                        app_id = app.get('id')
                        response = requests.post(
                            f"https://myidon.site/api/tailscale/auth-key",
                            headers={
                                'Authorization': f'Bearer {oauth_token}',
                                'Accept': 'application/json',
                                'Content-Type': 'application/json',
                            },
                            json={
                                'application_id': app_id,
                                'server_type': 'starter',
                                'server_name': socket.gethostname(),
                            },
                            timeout=10
                        )
                        
                        if response.status_code == 200:
                            result = response.json()
                            if result.get('success'):
                                auth_key = result.get('auth_key')
                                session_obj['tailscale_auth_key'] = auth_key
                                logger.info(f"Got auth_key from application #{app_id}")
                    except Exception as e:
                        logger.warning(f"Failed to get auth_key from application: {e}")
                break

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
