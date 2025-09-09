from starter_files.core.base_module import BaseModule
import json
import logging
import platform
import subprocess
import re
from pathlib import Path
import os
import time
from typing import Dict, List, Optional, Any
from starter_files.core.utils.loader_utils import get
from starter_files.core.utils.globalVars_utils import get_global, set_global
from datetime import datetime

LOG_PATH = Path("starter_files/logs/docker_module.log")
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger('docker_module')
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler(LOG_PATH, encoding='utf-8')
formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

class DockerModule(BaseModule):
    """Реализация Docker утилит"""

    # ---------------------------
    # Проверки установки Docker
    # ---------------------------
    @staticmethod
    def check_docker_installed() -> bool:
        """Проверяет установлен ли Docker и возвращает статус"""
        try:
            subprocess.run(['docker', '--version'], capture_output=True, text=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    @staticmethod
    def check_docker_compose_installed() -> bool:
        """Проверка наличия Docker Compose (v1 и v2)"""
        try:
            subprocess.check_output(["docker", "compose", "version"], stderr=subprocess.DEVNULL)
            return True
        except (FileNotFoundError, subprocess.CalledProcessError):
            try:
                subprocess.check_output(["docker-compose", "--version"], stderr=subprocess.DEVNULL)
                return True
            except (FileNotFoundError, subprocess.CalledProcessError):
                return False

    # ---------------------------
    # Установка Docker
    # ---------------------------
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

                log("Starting Docker installation...")
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
                docker_installed = DockerModule.check_docker_installed()
                set_global('docker_installed', docker_installed)
                docker_compose_installed = DockerModule.check_docker_compose_installed()
                set_global('docker_compose_installed', docker_compose_installed)

                if docker_installed:
                    log("Docker installed successfully!")
                    result['message'] = "Docker installed successfully!"
                else:
                    log("Installation completed but Docker not detected.")
                    result['status'] = 'warning'
                    result['message'] = "Installation completed but Docker not detected."

                if docker_compose_installed:
                    log("Docker Compose installed!")
                    result['message'] += " Docker Compose installed."
                else:
                    log("Docker Compose not detected.")

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

                log("Starting Docker Compose installation...")
                commands = get("docker", "return_commands_install_compose")
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
                docker_compose_installed = DockerModule.check_docker_compose_installed()
                set_global('docker_compose_installed', docker_compose_installed)
                if docker_compose_installed:
                    log("Docker Compose installed successfully!")
                    result['message'] = "Docker Compose installed successfully!"
                else:
                    log("Installation completed but Docker Compose not detected.")
                    result['status'] = 'warning'
                    result['message'] = "Installation completed but Docker Compose not detected."
                log("INSTALL FINISH!")
        except Exception as e:
            logger.exception("Docker Compose installation failed")
            result['status'] = 'error'
            result['message'] = f"Installation failed: {str(e)}"
        return result

    # ---------------------------
    # Работа с Dockerfile и compose
    # ---------------------------
    @staticmethod
    def check_dockerfiles(docker_dir: str) -> bool:
        required = [
            os.path.join("dockerfiles", "Dockerfile_other"),
            os.path.join("dockerfiles", "Dockerfile_php")
        ]
        for path in required:
            if not (Path(docker_dir) / path).exists():
                return False
        return True

    @staticmethod
    def replace_env_variables(content: str, env_vars: Dict[str, str]) -> str:
        def replace_match(match):
            return env_vars.get("PROJECTNAME", match.group(0))
        return re.sub(r'\$\{PROJECTNAME\}', replace_match, content)

    @staticmethod
    def process_service_blocks(content: str, enabled_services: List[str], env_vars: Dict[str, str]) -> str:
        pattern = re.compile(r'### START (.+?) ###(.*?)### END \1 ###', re.DOTALL)
        def replace_block(match):
            service_name = match.group(1).strip().upper()
            block_content = match.group(2)
            if service_name in enabled_services:
                replaced_content = DockerModule.replace_env_variables(block_content, env_vars)
                return f"### START {service_name} ###{replaced_content}### END {service_name} ###"
            return ''
        return pattern.sub(replace_block, content)

    @staticmethod
    def generate_compose(docker_dir: str, env_vars: Dict[str, str], pull_from_registry: bool = False) -> bool:
        docker_dir = Path(docker_dir)
        compose_example = docker_dir / "docker-compose.example"
        compose_output = docker_dir / "docker-compose.yml"
        try:
            content = compose_example.read_text(encoding='utf-8')
            if pull_from_registry:
                content = re.sub(r'\n\s+build:.?dockerfile:.?\n', '\n', content, flags=re.DOTALL)
            enabled_services = [
                s.strip().upper() for s in env_vars.get("ENABLED_SERVICES", "").split(",") if s.strip()
            ]
            content = DockerModule.process_service_blocks(content, enabled_services, env_vars)
            content = DockerModule.replace_env_variables(content, env_vars)
            compose_output.write_text(content, encoding='utf-8')
            return True
        except Exception as e:
            logger.error(f"Error generating compose: {str(e)}")
            return False

    # ---------------------------
    # Статус контейнеров и управление
    # ---------------------------
    @staticmethod
    def get_container_status(container_name: str) -> Optional[Dict]:
        try:
            result = subprocess.run(['docker', 'inspect', '--format', '{{json .}}', container_name],
                                    capture_output=True, text=True, check=True)
            return json.loads(result.stdout)
        except Exception as e:
            logger.error(f"Error getting container status: {str(e)}")
            return None

    @staticmethod
    def manage_container(container_name: str, action: str) -> bool:
        try:
            subprocess.run(['docker', action, container_name], check=True)
            return True
        except Exception as e:
            logger.error(f"Error managing container: {str(e)}")
            return False

    # ---------------------------
    # Сбор информации о Docker
    # ---------------------------
    @staticmethod
    def get_docker_info() -> Dict:
        info = {
            'version': 'N/A', 'containers': {'total': 0, 'running': 0, 'paused': 0, 'stopped': 0},
            'images': 0, 'system': {'cpu_usage': 'N/A', 'memory_usage': 'N/A', 'disk_usage': 'N/A'},
            'compose': {'projects': 0, 'services': 0}
        }
        try:
            result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                info['version'] = result.stdout.strip()
            result = subprocess.run(['docker', 'ps', '-a', '--format', '{{.State}}'], capture_output=True, text=True)
            if result.returncode == 0:
                states = result.stdout.splitlines()
                info['containers']['total'] = len(states)
                info['containers']['running'] = states.count('running')
                info['containers']['paused'] = states.count('paused')
                info['containers']['stopped'] = states.count('exited') + states.count('created')
            result = subprocess.run(['docker', 'images', '-q'], capture_output=True, text=True)
            if result.returncode == 0:
                info['images'] = len(result.stdout.splitlines())
        except Exception as e:
            logger.error(f"Error collecting Docker info: {str(e)}")
        return info

    # ---------------------------
    # Получение ресурсов Docker
    # ---------------------------
    @staticmethod
    def get_containers(all: bool = False) -> List[Dict]:
        containers = []
        try:
            cmd = ['docker', 'ps', '--format', '{{.ID}}|{{.Names}}|{{.Image}}|{{.Status}}|{{.Ports}}|{{.RunningFor}}|{{.Size}}']
            if all:
                cmd.append('-a')
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    parts = line.split('|')
                    if len(parts) >= 7:
                        containers.append({
                            'id': parts[0], 'name': parts[1], 'image': parts[2],
                            'status': parts[3], 'ports': parts[4], 'running_for': parts[5], 'size': parts[6]
                        })
        except Exception as e:
            logger.error(f"Error getting containers: {str(e)}")
        return containers

    @staticmethod
    def get_images() -> List[Dict]:
        images = []
        try:
            result = subprocess.run(['docker', 'images', '--format', '{{.ID}}|{{.Repository}}|{{.Tag}}|{{.CreatedSince}}|{{.CreatedAt}}|{{.Size}}'],
                                    capture_output=True, text=True)
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    parts = line.split('|')
                    if len(parts) >= 6:
                        images.append({
                            'id': parts[0], 'repository': parts[1], 'tag': parts[2],
                            'created_since': parts[3], 'created_at': parts[4], 'size': parts[5]
                        })
        except Exception as e:
            logger.error(f"Error getting images: {str(e)}")
        return images

    @staticmethod
    def get_logs(container_id: str, tail: int = 100) -> str:
        try:
            result = subprocess.run(['docker', 'logs', '--tail', str(tail), container_id],
                                    capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout
        except Exception as e:
            logger.error(f"Error getting logs: {str(e)}")
        return ""

    # ---------------------------
    # Сети и тома
    # ---------------------------
    @staticmethod
    def get_networks() -> List[Dict]:
        networks = []
        try:
            result = subprocess.run(['docker', 'network', 'ls', '--format', '{{.ID}}|{{.Name}}|{{.Driver}}|{{.Scope}}|{{.IPv6}}|{{.Internal}}|{{.Created}}'],
                                    capture_output=True, text=True)
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    parts = line.split('|')
                    if len(parts) >= 7:
                        networks.append({
                            'id': parts[0], 'name': parts[1], 'driver': parts[2],
                            'scope': parts[3], 'ipv6': parts[4], 'internal': parts[5], 'created': parts[6]
                        })
        except Exception as e:
            logger.error(f"Error getting networks: {str(e)}")
        return networks

    @staticmethod
    def get_volumes() -> List[Dict]:
        volumes = []
        try:
            result = subprocess.run(['docker', 'volume', 'ls', '--format', '{{.Name}}|{{.Driver}}|{{.Scope}}|{{.Mountpoint}}|{{.Labels}}|{{.CreatedAt}}'],
                                    capture_output=True, text=True)
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    parts = line.split('|')
                    if len(parts) >= 6:
                        volumes.append({
                            'name': parts[0], 'driver': parts[1], 'scope': parts[2],
                            'mountpoint': parts[3], 'labels': parts[4], 'created_at': parts[5]
                        })
        except Exception as e:
            logger.error(f"Error getting volumes: {str(e)}")
        return volumes

    # ---------------------------
    # Действия с контейнером и образом
    # ---------------------------
    @staticmethod
    def container_action(data: Dict) -> Dict:
        action = data.get('action')
        container_id = data.get('container_id')
        if not action or not container_id:
            return {'status': 'error', 'message': 'Invalid parameters'}
        try:
            subprocess.run(['docker', action, container_id], check=True)
            return {'status': 'success', 'message': f'Container {action}ed'}
        except subprocess.CalledProcessError as e:
            logger.error(f"Container action failed: {str(e)}")
            return {'status': 'error', 'message': f"Action failed: {str(e)}"}

    @staticmethod
    def image_action(data: Dict) -> Dict:
        action = data.get('action')
        image_id = data.get('image_id')
        if not action or not image_id:
            return {'status': 'error', 'message': 'Invalid parameters'}
        try:
            subprocess.run(['docker', 'rmi', image_id], check=True)
            return {'status': 'success', 'message': 'Image removed'}
        except subprocess.CalledProcessError as e:
            logger.error(f"Image action failed: {str(e)}")
            return {'status': 'error', 'message': f"Action failed: {str(e)}"}

    # ---------------------------
    # Перезапуск Docker
    # ---------------------------
    @staticmethod
    def restart_docker() -> Dict:
        try:
            use_sudo = get_global("use_sudo")
            if platform.system() == 'Windows':
                subprocess.run(['net', 'stop', 'docker'], check=True)
                subprocess.run(['net', 'start', 'docker'], check=True)
            else:
                cmd = ['systemctl', 'restart', 'docker']
                if use_sudo:
                    cmd.insert(0, 'sudo')
                subprocess.run(cmd, check=True)
            return {'status': 'success', 'message': 'Docker restarted successfully'}
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to restart Docker: {str(e)}")
            return {'status': 'error', 'message': f"Failed to restart Docker: {str(e)}"}
        except FileNotFoundError as e:
            logger.error(f"Command not found: {str(e)}")
            return {'status': 'error', 'message': f"Command not found: {str(e)}"}

    # ---------------------------
    # Очистка системы Docker
    # ---------------------------
    @staticmethod
    def prune_system() -> Dict:
        try:
            subprocess.run(['docker', 'system', 'prune', '-f'], check=True)
            return {'status': 'success', 'message': 'System pruned successfully'}
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to prune system: {str(e)}")
            return {'status': 'error', 'message': f"Failed to prune system: {str(e)}"}

    # ---------------------------
    # Глобальные переменные Docker
    # ---------------------------
    @staticmethod
    def set_globals():
        docker_installed = DockerModule.check_docker_installed()
        docker_compose_installed = DockerModule.check_docker_compose_installed()
        set_global('docker_installed', docker_installed)
        set_global('docker_compose_installed', docker_compose_installed)

    # ---------------------------
    # Проверка доступности Docker daemon
    # ---------------------------
    @staticmethod
    def is_docker_available() -> bool:
        try:
            subprocess.run(["docker", "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            return True
        except Exception:
            return False

    # ---------------------------
    # Генерация docker-compose.yml
    # ---------------------------
    @staticmethod
    def generate_docker_compose(settings: Dict[str, Any]) -> bool:
        try:
            docker_path = get_global("docker_path")
            env_path = docker_path / ".env"
            env_vars = DockerModule.read_env_file(env_path)

            content = DockerModule._generate_compose_content(settings, env_vars)
            compose_file = docker_path / "docker-compose.yml"
            with open(compose_file, "w", encoding="utf-8") as f:
                f.write(content)

            logger.info("docker-compose.yml generated successfully")
            return True
        except Exception as e:
            logger.error(f"Error generating docker-compose: {e}")
            return False

    @staticmethod
    def _generate_compose_content(settings: Dict[str, Any], env_vars: Dict[str, str]) -> str:
        project_name = env_vars.get("PROJECTNAME", "my_project")
        return f"""
version: '3.9'
services:
  app:
    image: {project_name}:latest
    build:
      context: {settings.get("project_path", ".")}
    environment:
      - ENVIRONMENT={settings.get("environment", "production")}
"""

    # ---------------------------
    # Запуск docker-compose
    # ---------------------------
    @staticmethod
    def run_compose(settings: Dict[str, Any] = None) -> bool:
        try:
            docker_path = get_global("docker_path")
            compose_file = docker_path / "docker-compose.yml"

            if not DockerModule.is_docker_available():
                RUNNING_IN_CONTAINER = Path("/.dockerenv").exists()
                if RUNNING_IN_CONTAINER:
                    logger.warning("Inside container without Docker. Compose skipped.")
                    return True
                else:
                    logger.error("Docker daemon not available. Compose cannot run.")
                    return False

            if not compose_file.exists():
                logger.warning("docker-compose.yml missing, generating...")
                if not DockerModule.generate_docker_compose(settings or {}):
                    return False

            try:
                subprocess.run(["docker", "compose", "version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                compose_cmd = ["docker", "compose"]
            except Exception:
                compose_cmd = ["docker-compose"]

            env_vars = os.environ.copy()
            logger.info(f"Running docker-compose with env: {env_vars}")

            use_sudo = get_global("use_sudo")
            RUNNING_IN_CONTAINER = Path("/.dockerenv").exists()
            if use_sudo and not RUNNING_IN_CONTAINER:
                compose_cmd.insert(0, "sudo")

            subprocess.run(
                compose_cmd + ["-f", str(compose_file), "up", "-d", "--build"],
                cwd=str(docker_path), check=True
            )
            logger.info("Docker Compose started successfully")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Docker Compose error: {e}")
            return False
        except Exception as e:
            logger.error(f"Error running docker-compose: {e}")
            return False
