import os
import platform
import subprocess
from flask import render_template
from starter_files.utils.i18n import t
from starter_files.utils.logger import get_logger

logger = get_logger()

# Конфигурация модуля для панели управления
this_module_in_control_panel = True
module_icon = "bi-shield-lock"
module_name = "VPN (SoftEther)"
module_order = 4

def check_softether_installed():
    """Проверяет установлен ли SoftEther VPN Client"""
    system = platform.system().lower()
    
    if system == 'windows':
        # Проверка в реестре Windows
        try:
            result = subprocess.run(
                ['reg', 'query', 'HKLM\\SOFTWARE\\SoftEther VPN Client', '/v', 'InstallDir'],
                capture_output=True,
                text=True,
                check=True
            )
            return True
        except subprocess.CalledProcessError:
            return False
            
    elif system == 'linux':
        # Проверка наличия файлов или команд
        paths = [
            '/usr/local/vpnclient/',
            '/opt/softether/vpnclient/',
            '/usr/lib/softether/vpnclient/'
        ]
        return any(os.path.exists(path) for path in paths)
        
    elif system == 'darwin':
        # Проверка для macOS
        return os.path.exists('/Applications/SoftEther VPN Client.app')
        
    return False

def get_vpn_status():
    """Получает статус VPN соединения"""
    system = platform.system().lower()
    status = {
        'installed': check_softether_installed(),
        'connected': False,
        'version': 'N/A',
        'interfaces': []
    }
    
    if not status['installed']:
        return status
    
    try:
        if system == 'windows':
            # Для Windows проверяем процессы
            result = subprocess.run(
                ['tasklist', '/FI', 'IMAGENAME eq vpnclient.exe'],
                capture_output=True,
                text=True,
                check=True
            )
            status['connected'] = 'vpnclient.exe' in result.stdout
            
            # Получаем версию
            try:
                version = subprocess.run(
                    ['wmic', 'datafile', 'where', 'name="C:\\\\Program Files\\\\SoftEther VPN Client\\\\vpnclient.exe"', 'get', 'version'],
                    capture_output=True,
                    text=True,
                    check=True
                )
                status['version'] = version.stdout.split('\n')[1].strip()
            except:
                pass
                
        elif system in ['linux', 'darwin']:
            # Для Linux/macOS проверяем процесс
            result = subprocess.run(
                ['ps', 'aux'],
                capture_output=True,
                text=True,
                check=True
            )
            status['connected'] = 'vpnclient' in result.stdout
            
            # Получаем версию (пример для Linux)
            if system == 'linux':
                try:
                    version = subprocess.run(
                        ['/usr/local/vpnclient/vpnclient', 'version'],
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    status['version'] = version.stdout.split('\n')[0].strip()
                except:
                    pass
    
    except Exception as e:
        logger.error(f"Error checking VPN status: {str(e)}")
    
    return status

def index(data, session):
    """Главная страница модуля"""
    vpn_status = get_vpn_status()
    return render_template(
        'modules/vpn/index.html',
        vpn_status=vpn_status,
        t=t
    )

def info(data, session):
    """Страница информации о VPN"""
    vpn_status = get_vpn_status()
    system = platform.system().lower()
    
    # Инструкции для разных ОС
    instructions = {
        'windows': t('vpn_windows_instructions'),
        'linux': t('vpn_linux_instructions'),
        'darwin': t('vpn_mac_instructions')
    }
    
    return render_template(
        'modules/vpn/info.html',
        vpn_status=vpn_status,
        current_os=system,
        instructions=instructions,
        t=t
    )