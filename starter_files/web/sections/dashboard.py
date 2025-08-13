import os
import platform
import socket

from datetime import datetime, timedelta
from flask import render_template

from starter_files.utils.i18n_utils import t
from starter_files.utils.sysinfo_utils import collect_system_info

from starter_files.utils.logger import get_logger
logger = get_logger()

this_section_in_control_panel = True
section_icon = "bi-speedometer2"
section_name = "Dashboard"
section_order = 1

def index(data, session):
    sys_info = collect_system_info()
    
    return render_template(
        'sections/dashboard/index.html',
        sys_info=sys_info,
        hostname=sys_info['hostname'],
        username=sys_info['username'],
        current_time=sys_info['current_time'],
        uptime=sys_info['uptime'],
        python_info=sys_info['python_info'],
        disk_info=sys_info['disk'],
        cpu_info=sys_info['cpu'],
        memory_info=sys_info['memory'],
        t=t
    )