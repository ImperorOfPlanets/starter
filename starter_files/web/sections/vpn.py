import platform
from flask import render_template, request
from starter_files.core.utils.i18n_utils import t

this_section_in_control_panel = True
section_icon = "bi-shield-lock"
section_name = "VPN"
section_order = 4

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