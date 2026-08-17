import subprocess
import time
from typing import List, Dict, Any
from datetime import datetime
from pathlib import Path
from files.core.base_module import BaseModule
from files.core.utils.globalVars_utils import get_global, set_global
from files.core.utils.loader_utils import get
from files.core.utils.log_utils import LogManager

logger = LogManager.get_logger('docker_windows')


class DockerModule(BaseModule):
    """Windows Docker Desktop installation via winget"""

    @staticmethod
    def check_docker_installed() -> bool:
        """Check if Docker is installed on Windows"""
        try:
            result = subprocess.run(['docker', '--version'], capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except Exception:
            return False

    @staticmethod
    def check_docker_compose_installed() -> bool:
        """Check if Docker Compose is installed on Windows"""
        try:
            result = subprocess.run(['docker', 'compose', 'version'], capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except Exception:
            try:
                result = subprocess.run(['docker-compose', '--version'], capture_output=True, text=True, timeout=5)
                return result.returncode == 0
            except Exception:
                return False

    @staticmethod
    def return_commands_install_docker() -> List[str]:
        """Returns commands to install Docker Desktop on Windows"""
        return [
            'winget install --id Docker.DockerDesktop -e --accept-source-agreements --accept-package-agreements'
        ]

    @staticmethod
    def return_commands_install_compose() -> List[str]:
        """Docker Compose comes with Docker Desktop on Windows"""
        return [
            'echo Docker Compose is included with Docker Desktop'
        ]

    @staticmethod
    def install_docker(log_file_path: str) -> Dict[str, Any]:
        result = {'status': 'success', 'message': '', 'logs': []}
        try:
            with open(log_file_path, 'w') as log_file:
                def log(msg: str):
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    entry = f"[{timestamp}] {msg}"
                    log_file.write(entry + '\n')
                    log_file.flush()
                    result['logs'].append(entry)
                    logger.info(entry)

                log("Starting Docker Desktop installation on Windows...")
                commands = get("docker", "return_commands_install_docker")
                for cmd in commands:
                    log(f"Executing: {cmd}")
                    process = subprocess.Popen(
                        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        text=True, bufsize=1, universal_newlines=True
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
                docker_installed = get('docker', 'check_docker_installed')
                set_global('docker_installed', docker_installed)

                if docker_installed:
                    log("Docker Desktop installed successfully!")
                    result['message'] = "Docker Desktop installed successfully!"
                else:
                    log("Installation completed but Docker not detected.")
                    result['status'] = 'warning'
                    result['message'] = "Installation completed but Docker not detected. You may need to restart."

                log("INSTALL FINISH!")
        except Exception as e:
            logger.exception("Docker installation failed")
            result['status'] = 'error'
            result['message'] = f"Installation failed: {str(e)}"
        return result

    @staticmethod
    def install_docker_compose(log_file_path: str) -> Dict[str, Any]:
        result = {'status': 'success', 'message': '', 'logs': []}
        try:
            with open(log_file_path, 'w') as log_file:
                def log(msg: str):
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    entry = f"[{timestamp}] {msg}"
                    log_file.write(entry + '\n')
                    log_file.flush()
                    result['logs'].append(entry)
                    logger.info(entry)

                log("Docker Compose is included with Docker Desktop on Windows.")
                log("Checking if Docker Compose is available...")

                docker_compose_installed = get('docker', 'check_docker_compose_installed')
                set_global('docker_compose_installed', docker_compose_installed)

                if docker_compose_installed:
                    log("Docker Compose is available!")
                    result['message'] = "Docker Compose is available!"
                else:
                    log("Docker Compose not detected. Please restart after Docker Desktop installation.")
                    result['status'] = 'warning'
                    result['message'] = "Docker Compose not detected. Restart may be required."

                log("INSTALL FINISH!")
        except Exception as e:
            logger.exception("Docker Compose check failed")
            result['status'] = 'error'
            result['message'] = f"Check failed: {str(e)}"
        return result
