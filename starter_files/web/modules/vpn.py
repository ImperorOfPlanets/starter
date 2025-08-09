import platform
from flask import render_template, request
from starter_files.utils.i18n import t
from starter_files.utils.vpn import get_available_clients, get_vpn_status

this_module_in_control_panel = True
module_icon = "bi-shield-lock"
module_name = "VPN"
module_order = 4

def index(data, session):
    clients = get_available_clients()
    active_client = request.args.get('client')
    
    return render_template(
        'modules/vpn/index.html',
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
        'modules/vpn/info.html',
        vpn_status=get_vpn_status(request.args.get('client')),
        current_os=platform.system().lower(),
        t=t
    )