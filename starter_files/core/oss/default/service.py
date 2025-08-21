from starter_files.core.base_module import BaseModule

import platform
import subprocess
import os
from starter_files.core.utils.globalVars_utils import get_global, set_global
from starter_files.core.utils.loader_utils import get

SERVICE_NAME = "starter-service"

class ServiceModule(BaseModule):
    """Модуль для работы с системными сервисами"""

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
    def get_service_status(self) -> dict:
        """Получает статус сервиса для текущей ОС"""
        system = platform.system().lower()
        status = {
            'installed': False,
            'running': False,
            'enabled': False,
            'os': system
        }

        try:
            if system == 'windows':
                result = subprocess.run(
                    ['sc', 'query', SERVICE_NAME],
                    capture_output=True,
                    text=True,
                    check=False
                )

                status['installed'] = SERVICE_NAME in result.stdout
                if status['installed']:
                    status['running'] = 'RUNNING' in result.stdout

                    start_type = subprocess.run(
                        ['sc', 'qc', SERVICE_NAME],
                        capture_output=True,
                        text=True,
                        check=False
                    )
                    status['enabled'] = 'AUTO_START' in start_type.stdout

            elif system == 'linux':
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
                status['installed'] = status['running'] or status['enabled']

            elif system == 'darwin':
                result = subprocess.run(
                    f'launchctl list | grep {SERVICE_NAME}',
                    shell=True,
                    capture_output=True,
                    text=True,
                    check=False
                )
                status['installed'] = SERVICE_NAME in result.stdout
                status['running'] = status['installed']

                result = subprocess.run(
                    ['launchctl', 'logger.info', f'gui/{os.getuid()}/{SERVICE_NAME}'],
                    capture_output=True,
                    text=True,
                    check=False
                )
                status['enabled'] = 'enabled' in result.stdout.lower()

        except Exception as e:
            logger.error(f"Error checking service status: {str(e)}")

        return status

    @staticmethod
    def service_action(self, data: dict, session: dict) -> dict:
        """Выполняет действие с сервисом"""
        action = data.get('action')
        status = self.get_service_status()
        system = status['os']

        try:
            if system == 'windows':
                if action == 'start':
                    subprocess.run(['sc', 'start', SERVICE_NAME], check=True)
                elif action == 'stop':
                    subprocess.run(['sc', 'stop', SERVICE_NAME], check=True)
                elif action == 'restart':
                    subprocess.run(['sc', 'stop', SERVICE_NAME], check=True)
                    subprocess.run(['sc', 'start', SERVICE_NAME], check=True)

            elif system == 'linux':
                if action in ('start', 'stop', 'restart', 'enable', 'disable'):
                    subprocess.run(['systemctl', action, SERVICE_NAME], check=True)

            elif system == 'darwin':
                plist_path = f'/Library/LaunchDaemons/{SERVICE_NAME}.plist'
                if action == 'start':
                    subprocess.run(['launchctl', 'load', plist_path], check=True)
                elif action == 'stop':
                    subprocess.run(['launchctl', 'unload', plist_path], check=True)
                elif action == 'restart':
                    subprocess.run(['launchctl', 'unload', plist_path], check=True)
                    subprocess.run(['launchctl', 'load', plist_path], check=True)

            return {'status': 'success', 'message': f'Service {action} successfully'}

        except subprocess.CalledProcessError as e:
            return {'status': 'error', 'message': f'Failed to {action} service: {str(e)}'}

    @staticmethod
    def set_globals():
        """Устанавливает глобальные для SERVICE"""
        systemd_installed = get('service',"is_systemd_installed")
        set_global('systemd_installed', systemd_installed)
