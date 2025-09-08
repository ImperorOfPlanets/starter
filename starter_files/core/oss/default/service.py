from starter_files.core.base_module import BaseModule

import os
import platform
import subprocess
import sys
import time

from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from starter_files.core.utils.globalVars_utils import get_global, set_global
from starter_files.core.utils.loader_utils import get

from starter_files.core.oss.default.updates import UpdatesModule

SERVICE_NAME = "starter-service"

from starter_files.core.utils.log_utils import LogManager
logger = LogManager.get_logger('service')

class ServiceModule(BaseModule):
    """Модуль для работы с системными сервисами"""

    # SYSTEMD

    @staticmethod
    def is_systemd_installed():
        """Проверяет, установлен ли systemd"""
        try:
            subprocess.run(
                ['systemctl', '--version'],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            return False

    @staticmethod
    def install_systemd(log_file_path: str) -> Dict[str, Any]:
        """Устанавливает systemd и записывает логи в указанный файл"""
        result = {'status': 'success', 'message': '', 'logs': []}
        
        try:
            log_dir = Path(log_file_path).parent
            log_dir.mkdir(parents=True, exist_ok=True)
            
            with open(log_file_path, 'w') as log_file:
                def log(message):
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    log_entry = f"[{timestamp}] {message}"
                    log_file.write(log_entry + '\n')
                    log_file.flush()
                    result['logs'].append(log_entry)
                    logger.info(log_entry)
                
                log("Starting systemd installation...")

                # Определяем команды установки в зависимости от ОС
                os_family = get_global('os_family')
                if os_family == 'debian':
                    commands = [
                        'apt-get update',
                        'apt-get install -y systemd'
                    ]
                elif os_family == 'rhel':
                    commands = [
                        'yum install -y systemd'
                    ]
                else:
                    result['status'] = 'error'
                    result['message'] = f'Unsupported OS family: {os_family}'
                    return result

                for cmd in commands:
                    log(f"Executing: {cmd}")
                    process = subprocess.Popen(
                        cmd,
                        shell=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        bufsize=1,
                        universal_newlines=True
                    )
                    
                    for line in iter(process.stdout.readline, ''):
                        if line:
                            log(line.strip())
                    
                    return_code = process.wait()
                    if return_code != 0:
                        log(f"Command failed with exit code {return_code}")
                        result['status'] = 'error'
                        result['message'] = f"Command failed: {cmd}"
                        return result
                
                time.sleep(2)
                if ServiceModule.is_systemd_installed():
                    log("systemd installed successfully!")
                    result['message'] = "systemd installed successfully!"
                else:
                    log("Installation completed but systemd not detected.")
                    result['status'] = 'warning'
                    result['message'] = "Installation completed but systemd not detected."
        
        except Exception as e:
            error_msg = f"Installation failed: {str(e)}"
            result['status'] = 'error'
            result['message'] = error_msg
            logger.exception("systemd installation error")
        
        return result

    # SERVICE

    @staticmethod
    def install_service(log_file_path: str) -> Dict[str, Any]:
        """Устанавливает и настраивает сервис starter-service"""
        result = {'status': 'success', 'message': '', 'logs': []}
        
        try:
            log_dir = Path(log_file_path).parent
            log_dir.mkdir(parents=True, exist_ok=True)
            
            with open(log_file_path, 'w') as log_file:
                def log(message):
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    log_entry = f"[{timestamp}] {message}"
                    log_file.write(log_entry + '\n')
                    log_file.flush()
                    result['logs'].append(log_entry)
                    logger.info(log_entry)
                
                log("Starting starter-service installation...")

                # Используем глобальные переменные для определения путей
                script_path = get_global('script_path')
                python_path = get_global('python_path', sys.executable)
                venv_path = get_global('venv_path')
                
                log(f"Script path: {script_path}")
                log(f"Python path: {python_path}")
                log(f"Venv path: {venv_path}")

                # Создаем systemd service file с правильными путями
                service_content = f"""[Unit]
Description=Starter Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory={script_path}
Environment=PATH={venv_path}/bin:{os.environ.get('PATH', '')}
ExecStart={python_path} {script_path}/main.py --service
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""

                service_path = "/etc/systemd/system/starter-service.service"
                
                log(f"Creating service file: {service_path}")
                with open(service_path, 'w') as f:
                    f.write(service_content)
                
                # Reload systemd and enable service
                commands = [
                    'systemctl daemon-reload',
                    'systemctl enable starter-service',
                    'systemctl start starter-service'
                ]

                for cmd in commands:
                    log(f"Executing: {cmd}")
                    process = subprocess.Popen(
                        cmd,
                        shell=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        bufsize=1,
                        universal_newlines=True
                    )
                    
                    for line in iter(process.stdout.readline, ''):
                        if line:
                            log(line.strip())
                    
                    return_code = process.wait()
                    if return_code != 0:
                        log(f"Command failed with exit code {return_code}")
                        # Не прерываем выполнение полностью, а только записываем ошибку
                        result['status'] = 'warning'
                        result['message'] = f"Command completed with warnings: {cmd}"
                
                # Wait for service to start and verify installation
                log("Waiting for service to start...")
                time.sleep(3)
                
                # Verify service is installed and running
                status = ServiceModule.get_service_status()
                if status['installed']:
                    log("starter-service installed successfully!")
                    if status['running']:
                        log("starter-service is running!")
                        result['message'] = "starter-service installed and running successfully!"
                    else:
                        log("starter-service installed but not running")
                        result['message'] = "starter-service installed but not running"
                else:
                    log("starter-service installation failed")
                    result['status'] = 'error'
                    result['message'] = "starter-service installation failed"
        
        except Exception as e:
            error_msg = f"Installation failed: {str(e)}"
            result['status'] = 'error'
            result['message'] = error_msg
            logger.exception("starter-service installation error")
        
        return result

    @staticmethod
    def get_service_status() -> Dict[str, Any]:
        """Получает статус сервиса для текущей ОС"""
        system = platform.system().lower()
        status = {
            'installed': False,
            'running': False,
            'enabled': False,
            'os': system
        }

        try:
            if system == 'linux':
                # Проверяем, существует ли файл сервиса
                service_path = "/etc/systemd/system/starter-service.service"
                status['installed'] = os.path.exists(service_path)
                
                if status['installed']:
                    # Проверяем статус сервиса
                    result = subprocess.run(
                        ['systemctl', 'is-active', SERVICE_NAME],
                        capture_output=True,
                        text=True,
                        check=False
                    )
                    status['running'] = result.returncode == 0

                    result = subprocess.run(
                        ['systemctl', 'is-enabled', SERVICE_NAME],
                        capture_output=True,
                        text=True,
                        check=False
                    )
                    status['enabled'] = result.returncode == 0

        except Exception as e:
            logger.error(f"Error checking service status: {str(e)}")

        return status

    @staticmethod
    def uninstall_service(log_file_path: str) -> Dict[str, Any]:
        """Удаляет сервис starter-service"""
        result = {'status': 'success', 'message': '', 'logs': []}
        
        try:
            log_dir = Path(log_file_path).parent
            log_dir.mkdir(parents=True, exist_ok=True)
            
            with open(log_file_path, 'w') as log_file:
                def log(message):
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    log_entry = f"[{timestamp}] {message}"
                    log_file.write(log_entry + '\n')
                    log_file.flush()
                    result['logs'].append(log_entry)
                    logger.info(log_entry)
                
                log("Starting starter-service uninstallation...")

                # Останавливаем и отключаем сервис
                commands = [
                    'systemctl stop starter-service',
                    'systemctl disable starter-service',
                    'systemctl daemon-reload'
                ]

                for cmd in commands:
                    log(f"Executing: {cmd}")
                    process = subprocess.Popen(
                        cmd,
                        shell=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        bufsize=1,
                        universal_newlines=True
                    )
                    
                    for line in iter(process.stdout.readline, ''):
                        if line:
                            log(line.strip())
                    
                    process.wait()
                    # Не проверяем код возврата, так как сервис может быть уже остановлен

                # Удаляем файл сервиса
                service_path = "/etc/systemd/system/starter-service.service"
                if os.path.exists(service_path):
                    os.remove(service_path)
                    log(f"Removed service file: {service_path}")
                else:
                    log(f"Service file not found: {service_path}")

                log("starter-service uninstalled successfully!")
                result['message'] = "starter-service uninstalled successfully!"
        
        except Exception as e:
            error_msg = f"Uninstallation failed: {str(e)}"
            result['status'] = 'error'
            result['message'] = error_msg
            logger.exception("starter-service uninstallation error")
        
        return result

    @staticmethod
    def is_service_installed() -> bool:
        """Проверяет, установлен ли сервис starter-service"""
        status = ServiceModule.get_service_status()
        return status['installed']

    @staticmethod
    def service_action(data: Dict[str, Any]) -> Dict[str, Any]:
        """Выполняет действие с сервисом"""
        action = data.get('action')
        status = ServiceModule.get_service_status()
        system = status['os']

        try:
            if system == 'linux':
                if action in ('start', 'stop', 'restart', 'enable', 'disable'):
                    subprocess.run(['systemctl', action, SERVICE_NAME], check=True)
                    return {'status': 'success', 'message': f'Service {action} successfully'}
                else:
                    return {'status': 'error', 'message': f'Unknown action: {action}'}

        except subprocess.CalledProcessError as e:
            return {'status': 'error', 'message': f'Failed to {action} service: {str(e)}'}

    @staticmethod
    def restart_service() -> Dict[str, Any]:
        """Перезапускает сервис starter-service"""
        status = ServiceModule.get_service_status()
        
        if not status['installed']:
            return {'status': 'error', 'message': 'Service not installed'}
        
        try:
            if status['os'] == 'linux':
                subprocess.run(['systemctl', 'restart', SERVICE_NAME], check=True)
                return {'status': 'success', 'message': 'Service restarted successfully'}
            else:
                return {'status': 'error', 'message': f'Unsupported OS: {status["os"]}'}
        except subprocess.CalledProcessError as e:
            return {'status': 'error', 'message': f'Failed to restart service: {str(e)}'}

    @staticmethod
    def set_globals():
        """Устанавливает глобальные переменные для SERVICE"""
        systemd_installed = ServiceModule.is_systemd_installed()
        service_installed = ServiceModule.is_service_installed()
        service_status = ServiceModule.get_service_status()

        set_global('systemd_installed', systemd_installed)
        set_global('service_installed', service_installed)
        set_global('service_status', service_status)

    @staticmethod
    def handle_rollback(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Обрабатывает запрос на откат обновления
        """
        project_name = data.get('project_name', 'starter')
        update_id = data.get('update_id')
        
        if not update_id:
            # Если ID не указан, используем последнюю доступную версию
            rollbacks = UpdatesModule.get_available_rollbacks(project_name)
            if not rollbacks:
                return {'status': 'error', 'message': 'Нет доступных версий для отката'}
            update_id = rollbacks[0]['id']
        
        # Выполняем откат
        result = UpdatesModule.rollback_update(project_name, update_id)
        
        if result['status'] == 'success':
            # Перезапускаем сервис после отката
            service_result = ServiceModule.restart_service()
            result['service_restart'] = service_result
        
        return result