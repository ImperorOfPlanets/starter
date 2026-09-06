import subprocess
import json
from typing import Optional
from files.core.base_module import BaseModule
from files.core.utils.globalVars_utils import get_global, set_global
from files.core.utils.log_utils import LogManager

logger = LogManager.get_logger('docker_windows')


class DockerModule(BaseModule):
    """Windows Docker Desktop — скрытие окон через startupinfo"""

    @staticmethod
    def set_globals():
        """Инициализация глобальных переменных Docker"""
        installed = DockerModule.check_docker_installed()
        set_global('docker_installed', installed)
        set_global('docker_compose_installed', DockerModule.check_docker_compose_installed() if installed else False)

    @staticmethod
    def check_docker_installed() -> bool:
        cached = get_global('docker_installed')
        if cached is not None:
            return cached
        try:
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = subprocess.SW_HIDE
            result = subprocess.run(['docker', '--version'], capture_output=True, text=True, timeout=10, startupinfo=si)
            ok = result.returncode == 0
            set_global('docker_installed', ok)
            return ok
        except Exception:
            set_global('docker_installed', False)
            return False

    @staticmethod
    def check_docker_compose_installed() -> bool:
        cached = get_global('docker_compose_installed')
        if cached is not None:
            return cached
        try:
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = subprocess.SW_HIDE
            result = subprocess.run(['docker', 'compose', 'version'], capture_output=True, text=True, timeout=10, startupinfo=si)
            ok = result.returncode == 0
            set_global('docker_compose_installed', ok)
            return ok
        except Exception:
            try:
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                si.wShowWindow = subprocess.SW_HIDE
                result = subprocess.run(['docker-compose', '--version'], capture_output=True, text=True, timeout=10, startupinfo=si)
                ok = result.returncode == 0
                set_global('docker_compose_installed', ok)
                return ok
            except Exception:
                set_global('docker_compose_installed', False)
                return False

    @staticmethod
    def get_container_status(container_name: str) -> Optional[dict]:
        try:
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = subprocess.SW_HIDE
            result = subprocess.run(
                ['docker', 'inspect', '--format', '{{json .}}', container_name],
                capture_output=True, text=True, check=True, timeout=10, startupinfo=si
            )
            return json.loads(result.stdout)
        except Exception:
            return None

    @staticmethod
    def manage_container(container_name: str, action: str) -> bool:
        try:
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = subprocess.SW_HIDE
            subprocess.run(['docker', action, container_name], check=True, timeout=30, startupinfo=si)
            return True
        except Exception:
            return False
