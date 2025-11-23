import os
import platform
import socket
import sys
import uuid
import threading

from datetime import datetime, timedelta
from flask import render_template, jsonify

from starter_files.core.utils.i18n_utils import t
from starter_files.core.utils.globalVars_utils import get_global
from starter_files.core.utils.loader_utils import get

from starter_files.core.utils.log_utils import LogManager
logger = LogManager.get_logger()

this_section_in_control_panel = True
section_icon = "bi-speedometer2"
section_name = "Dashboard"
section_order = 1

# Конфигурация компонентов для универсальной установки
COMPONENT_CONFIG = {
    'docker': {
        'module': 'docker',
        'check': 'check_docker_installed',
        'install': 'install_docker'
    },
    'docker-compose': {
        'module': 'docker',
        'check': 'check_docker_compose_installed',
        'install': 'install_docker_сompose'
    },
    'port-knocking': {
        'module': 'knocking',
        'check': 'is_knocking_installed',
        'install': 'install_port_knocking'
    },
    'git': {
        'module': 'git',
        'check': 'check_git_installed',
        'install': 'install_git'
    },
    'systemd': {
        'module': 'service',
        'check': 'is_systemd_installed',
        'install': 'install_systemd'
    },
    'starter-service': {
        'module': 'service',
        'check': 'is_service_installed',
        'install': 'install_service'
    },
    'vpnEther': {
        'module': 'softether',
        'check': 'check_softether_installed',
        'install': 'install_softether'
    },
}

# Путь к директории логов установки
INSTALL_LOGS_DIR = get_global('path_log_install')
INSTALL_LOGS_DIR.mkdir(parents=True, exist_ok=True)

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
        },
        'docker':{
            "docker_installed": get_global('docker_installed',False),
            "docker_compose_installed": get_global('docker_compose_installed',False)
        },
        'knocking':{
            "knocking_installed ": get_global('knocking_installed',False),
        },
        'git':{
            'git_installed': get_global('git_installed',False),
            'git_authentication': get_global('git_authentication', 'N/A'),
        },
        'systemd':{
            'systemd_installed': get_global('systemd_installed', False),
            'service_installed': get_global('service_installed', False),
            'service_status': get_global('service_status', 'unknown')
        },
        'vpnEther':{
            'vpnEther_installed': get_global('vpnEther_installed',False)
        },
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
        docker_info = sys_info['docker'],
        t=t
    )
# ===================УСТАНОВКА ===============================

def install_package(data, session):
    """Универсальный обработчик установки пакетов"""
    package = data.get('package')
    
    if not package or package not in COMPONENT_CONFIG:
        return jsonify({'status': 'error', 'message': 'Invalid package name'})
    
    config = COMPONENT_CONFIG[package]
    
    try:
        # Проверка установлен ли компонент
        check = get(config['module'], config['check'])
        if check:
            return jsonify({'status': 'info', 'message': f'{package} is already installed'})
    except Exception as e:
        logger.error(f"Component check failed: {str(e)}")
        return jsonify({'status': 'error', 'message': f'Installation check failed: {str(e)}'})
    
    # Создание уникального ID установки
    install_id = str(uuid.uuid4())
    log_file_path = INSTALL_LOGS_DIR / f"install_{package}_{install_id}.log"
    
    def run_installation():
        try:
            result = get(config['module'], config['install'], log_file_path=str(log_file_path))

            # Просто записываем финальный статус
            
            if result['status'] == 'error':
                raise Exception(result['message'])
                    
        except Exception as e:
            with open(log_file_path, 'a') as f:
                f.write(f"\nFATAL ERROR: {str(e)}\n")
                f.write("INSTALL FINISH!\n")
            logger.error(f"{package} installation failed: {str(e)}")
    
    thread = threading.Thread(target=run_installation)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'status': 'started',
        'message': f'{package} installation started',
        'install_id': install_id
    })

def download_install_logs(data, session):
    """Отправка файла логов для скачивания"""
    package = data.get('package')
    install_id = data.get('install_id')
    if not install_id:
        return "Installation ID required", 400
    
    log_file_path = INSTALL_LOGS_DIR / f"install_{package}_{install_id}.log"
    
    if not log_file_path.exists():
        return "Log file not found", 404
    
    try:
        from flask import send_file
        return send_file(
            log_file_path,
            as_attachment=True,
            download_name=f"install_{install_id}.log",
            mimetype='text/plain'
        )
    except Exception as e:
        return str(e), 500

def get_install_logs(data, session):
    """Возвращает содержимое лог-файла установки"""
    package = data.get('package')
    install_id = data.get('install_id')
    if not install_id:
        return jsonify({
            'status': 'error',
            'message': 'Installation ID required',
            'logs': '',
            'completed': False,
            'installed': False
        })
    
    log_file_path = INSTALL_LOGS_DIR / f"install_{package}_{install_id}.log"
    
    if not log_file_path.exists():
        return jsonify({
            'status': 'error',
            'message': 'Log file not found',
            'logs': '',
            'completed': False,
            'installed': False
        })
    
    try:
        with open(log_file_path, 'r') as f:
            logs = f.read()
        
        # КРИТИЧЕСКИ ВАЖНО: проверяем наличие маркера завершения
        completed = "INSTALL FINISH!" in logs
        installed = completed and "ERROR" not in logs.upper() and "FATAL ERROR" not in logs.upper()
        
        return jsonify({
            'status': 'success',
            'logs': logs,
            'completed': completed,  # ← JS проверяет это поле
            'installed': installed   # ← JS проверяет это поле
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'logs': '',
            'completed': False,
            'installed': False
        })
        return jsonify({
            'status': 'error',
            'message': str(e),
            'logs': ''
        })