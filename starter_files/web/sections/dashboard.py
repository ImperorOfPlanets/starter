import os
import platform
import socket
import sys

from datetime import datetime, timedelta
from flask import render_template

from starter_files.utils.i18n_utils import t
from starter_files.utils.globalVars_utils import get_global

from starter_files.utils.log_utils import get_logger
logger = get_logger()

this_section_in_control_panel = True
section_icon = "bi-speedometer2"
section_name = "Dashboard"
section_order = 1

def index(data, session):
    # Get system info from global variables with proper fallbacks
    sys_info = {
        'os': get_global('os', platform.system()),
        'os_version': get_global('os_version', platform.version()),
        'os_release': get_global('os_release', platform.release()),
        'architecture': get_global('architecture', platform.machine()),
        'hostname': get_global('hostname', socket.gethostname()),
        'username': get_global('username', os.getenv('USER') or os.getenv('USERNAME') or 'N/A'),
        'current_time': get_global('current_time', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
        'uptime': get_global('uptime', 'N/A'),
        'docker_installed': get_global('docker_installed', False),
        'docker_compose_installed': get_global('docker_compose_installed', False),
        'python_info': {
            'version': get_global('python_version', platform.python_version()),
            'implementation': get_global('python_implementation', platform.python_implementation()),
            'compiler': get_global('python_compiler', platform.python_compiler()),
            'executable': get_global('python_executable', sys.executable)
        },
        'cpu': {
            'name': get_global('cpu_model', 'N/A'),
            'cores': get_global('cpu_cores', 'N/A'),
            'logical_cores': get_global('cpu_logical_cores', 'N/A'),
            'usage': get_global('cpu_usage', 'N/A')
        },
        'memory': {
            'total': get_global('memory_total', 'N/A'),
            'used': get_global('memory_used', 'N/A'),
            'percent': get_global('memory_percent', 'N/A'),
            'available': get_global('memory_available', 'N/A')
        },
        'disk': {
            'total': get_global('disk_total', 'N/A'),
            'used': get_global('disk_used', 'N/A'),
            'percent': get_global('disk_percent', 'N/A'),
            'free': get_global('disk_free', 'N/A')
        }
    }
    
    return render_template(
        'sections/dashboard/index.html',
        sys_info=sys_info,
        hostname=sys_info['hostname'],
        username=sys_info['username'],
        current_time=sys_info['current_time'],
        uptime=sys_info['uptime'],
        python_info=sys_info['python_info'],
        cpu_info=sys_info['cpu'],
        memory_info=sys_info['memory'],
        disk_info=sys_info['disk'],
        t=t
    )