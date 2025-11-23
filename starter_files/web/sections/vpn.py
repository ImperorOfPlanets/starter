import platform
from flask import render_template, request
from starter_files.core.utils.i18n_utils import t
from starter_files.core.utils.loader_utils import get

this_section_in_control_panel = True
section_icon = "bi-shield-lock"
section_name = "VPN"
section_order = 4

def get_available_clients():
    """Получает список доступных VPN клиентов"""
    clients = {}

    # Проверяем SoftEther VPN
    try:
        softether_installed = get('softether', 'check_softether_installed')
        clients['softether'] = {
            'name': 'SoftEther VPN',
            'installed': softether_installed,
            'status': 'available' if softether_installed else 'not_installed'
        }
    except Exception as e:
        clients['softether'] = {
            'name': 'SoftEther VPN',
            'installed': False,
            'status': 'error',
            'error': str(e)
        }

    return clients

def get_vpn_status(client_name=None):
    """Получает статус VPN подключения"""
    if not client_name:
        return {'status': 'disconnected', 'message': 'No client specified'}

    try:
        if client_name == 'softether':
            # Получаем статус SoftEther VPN
            status = get('softether', 'get_service_status')
            if status and isinstance(status, dict):
                return {
                    'status': status.get('status_text', 'unknown'),
                    'active': status.get('active', False),
                    'message': f"SoftEther VPN is {status.get('status_text', 'unknown')}"
                }
            else:
                return {'status': 'unknown', 'active': False, 'message': 'Unable to get SoftEther VPN status'}
        else:
            return {'status': 'unknown_client', 'message': f'Unknown VPN client: {client_name}'}
    except Exception as e:
        return {'status': 'error', 'message': f'Error getting VPN status: {str(e)}'}

def index(data, session):
    clients = get_available_clients()
    active_client = request.args.get('client')

    return render_template(
        'sections/vpn/index.html',
        vpn_status=get_vpn_status(active_client),
        clients=clients,
        active_client=active_client or next(
            (name for name, data in clients.items() if data['installed']),
            None
        ),
        t=t
    )

def info(data, session):
    return render_template(
        'sections/vpn/info.html',
        vpn_status=get_vpn_status(request.args.get('client')),
        current_os=platform.system().lower(),
        t=t
    )