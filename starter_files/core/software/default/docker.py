from starter_files.core.base_module import BaseModule

import json
import logging
import os
import platform
import re
import subprocess
import time

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union

from starter_files.core.utils.loader_utils import get
from starter_files.core.utils.globalVars_utils import get_global, set_global
from starter_files.core.utils.log_utils import LogManager

logger = LogManager.get_logger('docker_module')


class DockerModule(BaseModule):
    """Реализация Docker утилит (включая генерацию .env и docker-compose.yml)"""

    # ---------------------------
    # Проверки установки Docker
    # ---------------------------
    @staticmethod
    def check_docker_installed() -> bool:
        try:
            subprocess.run(['docker', '--version'], capture_output=True, text=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    @staticmethod
    def check_docker_compose_installed() -> bool:
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
    # Установка Docker / Compose
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
    # Работа с Dockerfile и compose (legacy helper)
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

    # ---------------------------
    # Общие утилиты для подстановки переменных и блоков
    # ---------------------------
    @staticmethod
    def replace_env_variables(content: str, env_vars: Dict[str, str]) -> str:
        """Заменяет ${VAR} на значение из env_vars (если есть)"""
        def repl(match):
            var = match.group(1)
            return env_vars.get(var, match.group(0))
        return re.sub(r'\$\{(\w+)\}', repl, content)

    @staticmethod
    def process_service_blocks(content: str, enabled_services: List[str], env_vars: Dict[str, str], remove_markers: bool = False) -> str:
        """
        Обрабатывает блоки ### START SERVICE ### ... ### END SERVICE ###
        - Подставляет переменные окружения
        - Убирает полностью блоки для не включенных сервисов
        - Если remove_markers=True, то активные блоки тоже очищают маркеры
        """
        pattern = re.compile(r'### START (\w+) ###(.*?)### END \1 ###', re.DOTALL | re.IGNORECASE)

        def replace_block(match):
            service_name = match.group(1).strip().upper()
            block_content = match.group(2)
            if service_name in [s.upper() for s in enabled_services]:
                # логируем включённый сервис
                logger.info(f"Including service block: {service_name}")
                # подставляем переменные
                block_content = DockerModule.replace_env_variables(block_content, env_vars)
                if remove_markers:
                    return block_content
                else:
                    return match.group(0).replace(match.group(2), block_content)
            # логируем пропуск сервиса
            logger.info(f"Skipping service block: {service_name}")
            return ''

        return pattern.sub(replace_block, content)

    @staticmethod
    def remove_build_sections(content: str) -> str:
        """
        Убирает блоки 'build:' и вложенные отступленные строки.
        Регулярка удаляет 'build:' и все последующие строк с большим отступом.
        """
        # Удаляем секции build: вместе с их вложенными строками
        content = re.sub(r'(?m)^[ \t]*build:.*(?:\n[ \t]+.*)*', '', content)
        return content

    # ---------------------------
    # Генерация docker-compose (низкоуровневая и высокоуровневая)
    # ---------------------------
    @staticmethod
    def generate_compose(docker_dir: Union[str, Path], env_vars: Dict[str, str], pull_from_registry: bool = False) -> bool:
        try:
            docker_dir = Path(docker_dir)
            compose_example = docker_dir / "docker-compose.example"
            if not compose_example.exists():
                compose_example = docker_dir / "docker-compose.template"
            compose_output = docker_dir / "docker-compose.yml"

            # Добавил для замены DOCKER_PATH на пути
            env_vars["DOCKER_PATH"] = str(docker_dir)

            if not compose_example.exists():
                logger.error(f"[generate_compose] Compose template not found: {compose_example}")
                return False

            content = compose_example.read_text(encoding='utf-8')
            logger.info(f"[generate_compose] Read compose template ({compose_example}): {len(content)} chars")

            if pull_from_registry:
                content = DockerModule.remove_build_sections(content)
                logger.info("[generate_compose] Removed build sections (pull_from_registry=True)")

            enabled_services = [s.strip().upper() for s in env_vars.get("ENABLED_SERVICES", "").split(",") if s.strip()]
            logger.info(f"[generate_compose] Enabled services: {enabled_services}")

            # Логируем весь исходный контент до обработки блоков
            logger.debug(f"[generate_compose] Template content before processing:\n{content[:1000]}...")

            # Обрабатываем блоки сервисов
            content = DockerModule.process_service_blocks(content, enabled_services, env_vars, remove_markers=True)
            logger.info("[generate_compose] Processed service blocks")

            # Логируем контент после подстановки переменных
            logger.debug(f"[generate_compose] Content after processing:\n{content[:1000]}...")

            # Заменяем переменные окружения вне блоков
            content = DockerModule.replace_env_variables(content, env_vars)
            logger.info("[generate_compose] Replaced environment variables")

            # Убедимся, что папка существует
            compose_output.parent.mkdir(parents=True, exist_ok=True)

            # Сохраняем файл
            compose_output.write_text(content, encoding='utf-8')
            logger.info(f"[generate_compose] docker-compose.yml generated at {compose_output}")

            return True

        except Exception as e:
            logger.exception(f"[generate_compose] Error generating compose: {str(e)}")
            return False

    @staticmethod
    def generate_docker_compose(settings: Dict[str, Any]) -> bool:
        """
        Высокоуровневая обёртка: берёт docker_path из глобальных, обновляет .env (ensure_docker_env),
        читает env и генерирует compose.
        """
        try:
            docker_path = Path(get_global("docker_path"))
            # если директории нет — создадим (не критично)
            docker_path.mkdir(parents=True, exist_ok=True)

            # Обновим/создадим .env на основе .env.example
            env_vars = DockerModule.ensure_docker_env(docker_path)
            logger.info(f"Generated env_vars: {env_vars}")

            # pull_from_registry можно передавать через settings
            pull = False
            if isinstance(settings, dict):
                pull = settings.get("pull_from_registry", False)

            if not DockerModule.generate_compose(docker_path, env_vars, pull_from_registry=pull):
                logger.error("Failed to generate compose file")
                return False

            logger.info("docker-compose.yml generated successfully")
            return True
        except Exception as e:
            logger.error(f"Error generating docker-compose: {e}")
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
        image_id = data.get('image_id')
        if not image_id:
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
    # Запуск docker-compose (включая подготовку .env и compose)
    # ---------------------------
    @staticmethod
    def run_compose(settings: Dict[str, Any] = None) -> bool:
        file_handler = None
        orig_handlers = []
        orig_level = logger.level
        try:
            docker_path = Path(get_global("docker_path"))
            compose_file = docker_path / "docker-compose.yml"

            logs_path = docker_path / "logs"
            if not logs_path.exists():
                logger.info(f"[run_compose] Creating missing logs directory: {logs_path}")
                logs_path.mkdir(parents=True, exist_ok=True)

            sp = get_global('script_path')
            script_path = Path(sp) if sp else Path.cwd()
            starts_log_dir = script_path / 'starter_files' / 'logs' / 'starts'
            starts_log_dir.mkdir(parents=True, exist_ok=True)
            log_file_path = starts_log_dir / f"start_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

            # сохраняем хэндлеры
            orig_handlers = logger.handlers[:]
            orig_level = logger.level
            for h in orig_handlers:
                logger.removeHandler(h)

            # новый файловый хэндлер
            file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
            file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            logger.addHandler(file_handler)
            logger.setLevel(logging.DEBUG)
            logger.propagate = False

            logger.info(f"[run_compose] Logging output to {log_file_path}")
            
            # ДОБАВЛЯЕМ ПРОВЕРКУ РАБОЧЕЙ ПАПКИ
            logger.info(f"[run_compose] ===== START DOCKER COMPOSE =====")
            logger.info(f"[run_compose] Docker path: {docker_path}")
            logger.info(f"[run_compose] Absolute path: {docker_path.absolute()}")
            logger.info(f"[run_compose] Compose file exists: {compose_file.exists()}")
            
            # Проверяем содержимое директории
            if docker_path.exists():
                logger.info(f"[run_compose] Contents of {docker_path}:")
                for item in docker_path.iterdir():
                    if item.is_dir():
                        logger.info(f"[run_compose]   DIR:  {item.name}/")
                    else:
                        logger.info(f"[run_compose]   FILE: {item.name}")

            # ВОССТАНАВЛИВАЕМ ПРАВА ПЕРЕД ЗАПУСКОМ
            permission_result = DockerModule.fix_executable_permissions(docker_path)
            if permission_result['status'] == 'error':
                logger.warning(f"[run_compose] Ошибка при восстановлении прав: {permission_result['message']}")
            else:
                logger.info(f"[run_compose] Восстановление прав: {permission_result['message']}")

            # Проверка: внутри контейнера
            running_in_container = Path("/.dockerenv").exists()
            if running_in_container:
                logger.info("[run_compose] Running inside a Docker container.")

                container_name = DockerModule.get_current_container_name()
                if container_name:
                    logger.info(f"[run_compose] Current container name: {container_name}")
                    mounts = DockerModule.get_container_mounts(container_name)
                    logger.info(f"[run_compose] Detected mounts: {mounts}")

                    # Подставляем mounts в env_vars
                    env_vars = DockerModule.ensure_docker_env(docker_path)
                    for container_path, host_path in mounts.items():
                        # Преобразуем путь контейнера в переменную окружения, пример:
                        var_name = f"PATH_{container_path.strip('/').upper().replace('/', '_')}"
                        env_vars[var_name] = host_path

                    # Перезаписываем .env с новыми переменными
                    DockerModule.write_docker_env(docker_path, env_vars)
                    logger.info("[run_compose] .env updated with container mounts")
                else:
                    logger.warning("[run_compose] Could not determine container name.")

            # Генерация .env и compose
            logger.info("[run_compose] Generating .env and docker-compose.yml...")
            env_vars = DockerModule.ensure_docker_env(docker_path)
            if not DockerModule.generate_docker_compose(settings or {}):
                logger.error("[run_compose] Failed to generate docker-compose.yml")
                return False

            # Проверяем что compose файл создался
            if compose_file.exists():
                compose_size = compose_file.stat().st_size
                logger.info(f"[run_compose] Compose file generated: {compose_size} bytes")
            else:
                logger.error("[run_compose] Compose file was not generated!")
                return False

            # Определяем команду docker compose
            try:
                subprocess.run(["docker", "compose", "version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                compose_cmd = ["docker", "compose"]
                logger.info("[run_compose] Using: docker compose")
            except Exception:
                compose_cmd = ["docker-compose"]
                logger.info("[run_compose] Using: docker-compose")

            # Используем sudo, если нужно
            use_sudo = get_global("use_sudo")
            if use_sudo and not Path("/.dockerenv").exists():
                compose_cmd.insert(0, "sudo")
                logger.info("[run_compose] Using sudo for docker commands")

            # -------------------------------
            # 1. Очищаем старые контейнеры и сети
            # -------------------------------

            logger.info("[run_compose] Cleaning up old containers...")
            down_cmd = compose_cmd + ["-f", str(compose_file), "down", "--remove-orphans"]
            logger.info(f"[run_compose] Running: {' '.join(down_cmd)}")
            logger.info(f"[run_compose] Working directory: {docker_path}")
            
            subprocess.run(down_cmd, cwd=str(docker_path), check=True)

            # -------------------------------
            # 2. Получаем список образов из docker-compose
            # -------------------------------
            try:
                logger.info("[run_compose] Checking existing images...")
                result = subprocess.run(compose_cmd + ["-f", str(compose_file), "images", "-q"],
                                        cwd=str(docker_path), capture_output=True, text=True, check=True)
                image_ids = [i.strip() for i in result.stdout.splitlines() if i.strip()]
                logger.info(f"[run_compose] Found {len(image_ids)} existing images")
                for img_id in image_ids:
                    logger.info(f"[run_compose] Removing old image: {img_id}")
                    subprocess.run(["docker", "rmi", "-f", img_id], check=False)
            except Exception as e:
                logger.warning(f"[run_compose] Failed to list/remove images: {e}")

            # -------------------------------
            # 3. Запуск docker-compose с билдом и логами в реальном времени
            # -------------------------------

            logger.info("[run_compose] Starting docker-compose...")
            up_cmd = compose_cmd + ["-f", str(compose_file), "up", "--build", "--force-recreate"]
            logger.info(f"[run_compose] Command: {' '.join(up_cmd)}")
            logger.info(f"[run_compose] Working dir: {docker_path}")
            
            process = subprocess.Popen(
                up_cmd,
                cwd=str(docker_path),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            logger.info("[run_compose] === DOCKER COMPOSE OUTPUT ===")
            for line in iter(process.stdout.readline, ''):
                if line:
                    logger.info(f"[compose] {line.strip()}")

            return_code = process.wait()

            if return_code != 0:
                logger.error(f"[run_compose] docker-compose exited with code {return_code}")
                return False

            logger.info("[run_compose] Docker Compose started successfully")

            return True

        except Exception as e:
            logger.error(f"[run_compose] Unexpected error: {e}", exc_info=True)
            return False

        finally:
            if file_handler:
                logger.removeHandler(file_handler)
            for h in orig_handlers:
                logger.addHandler(h)
            logger.setLevel(orig_level)
            logger.propagate = True

    @staticmethod
    def fix_executable_permissions(project_path: Path) -> Dict[str, Any]:
        """
        Восстанавливает права на выполнение для всех скриптов и исполняемых файлов
        """
        result = {'status': 'success', 'fixed_files': [], 'errors': []}
        
        # Получаем настройку use_sudo из глобальных переменных
        use_sudo = get_global("use_sudo", False)
        
        # Проверяем, установлен ли sudo если он нужен
        if use_sudo:
            try:
                # Проверяем доступность sudo
                subprocess.run(['sudo', '--version'], capture_output=True, check=True)
                sudo_available = True
            except (subprocess.CalledProcessError, FileNotFoundError):
                sudo_available = False
                logger.warning("sudo requested but not available, continuing without sudo")
                use_sudo = False
        else:
            sudo_available = False

        # Паттерны для определения исполняемых файлов
        executable_extensions = {'.sh', '.py', '.pl', '.rb', '.js', '.php', '.bash'}
        executable_names = {
            'start', 'stop', 'restart', 'init', 'setup', 'install', 'configure',
            'entrypoint', 'docker-entrypoint', 'run', 'main', 'app'
        }
        script_directories = {
            'configs/init', 'configs/scripts', 'bin', 'scripts', 
            'dockerfiles', 'entrypoints', 'starters'
        }
        
        try:
            logger.info(f"Восстановление прав на исполняемые файлы (use_sudo={use_sudo})...")
            
            fixed_count = 0
            for root, dirs, files in os.walk(project_path):
                for file in files:
                    file_path = Path(root) / file
                    rel_path = file_path.relative_to(project_path)
                    rel_path_str = str(rel_path).replace('\\', '/')
                    file_lower = file.lower()
                    
                    # Проверяем критерии для исполняемого файла
                    is_executable = (
                        file_path.suffix.lower() in executable_extensions or
                        any(name in file_lower for name in executable_names) or
                        any(script_dir in rel_path_str for script_dir in script_directories)
                    )
                    
                    if is_executable:
                        try:
                            # Проверяем текущие права
                            current_mode = file_path.stat().st_mode
                            is_currently_executable = bool(current_mode & 0o111)  # Проверяем +x
                            
                            if not is_currently_executable:
                                # Устанавливаем права на выполнение
                                if use_sudo and sudo_available:
                                    # Используем sudo если нужно и доступен
                                    subprocess.run(
                                        ['sudo', 'chmod', '+x', str(file_path)], 
                                        check=True, 
                                        capture_output=True
                                    )
                                else:
                                    # Без sudo или если sudo недоступен
                                    new_mode = current_mode | 0o111  # Добавляем +x для всех
                                    file_path.chmod(new_mode)
                                
                                result['fixed_files'].append(rel_path_str)
                                fixed_count += 1
                                logger.debug(f"Установлены права на выполнение: {rel_path_str}")
                                
                        except Exception as e:
                            error_msg = f"Не удалось установить права для {rel_path_str}: {e}"
                            result['errors'].append(error_msg)
                            logger.warning(error_msg)
            
            logger.info(f"Восстановлены права для {fixed_count} файлов")
            if result['errors']:
                result['status'] = 'warning'
                result['message'] = f"Восстановлены права для {fixed_count} файлов, но были ошибки"
            else:
                result['message'] = f"Восстановлены права для {fixed_count} файлов"
                
        except Exception as e:
            error_msg = f"Ошибка при восстановлении прав: {e}"
            result['status'] = 'error'
            result['message'] = error_msg
            result['errors'].append(error_msg)
            logger.error(error_msg)
        
        return result

    @staticmethod
    def get_container_mounts(container_name: str) -> dict:
        """
        Возвращает словарь монтирований контейнера:
        {
            '/container/path': '/host/source/path',
            ...
        }
        """
        mounts_map = {}
        try:
            result = subprocess.run(
                ['docker', 'inspect', '--format', '{{json .Mounts}}', container_name],
                capture_output=True, text=True, check=True
            )
            mounts = json.loads(result.stdout)
            for m in mounts:
                container_path = m.get('Destination')
                host_path = m.get('Source')
                if container_path and host_path:
                    mounts_map[container_path] = host_path
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to inspect container {container_name}: {e}")
        except Exception as e:
            logger.exception(f"Unexpected error in get_container_mounts: {e}")
        return mounts_map

    @staticmethod
    def get_current_container_name() -> str:
        """
        Возвращает имя контейнера самого же себя где запущен
        """
        cgroup_path = "/proc/self/cgroup"
        if os.path.exists(cgroup_path):
            with open(cgroup_path) as f:
                for line in f:
                    # ищем docker/<container_id> (обычно)
                    parts = line.strip().split('/')
                    if 'docker' in parts:
                        container_id = parts[-1]
                        # docker inspect для имени
                        try:
                            result = subprocess.run(
                                ['docker', 'inspect', '--format', '{{.Name}}', container_id],
                                capture_output=True, text=True, check=True
                            )
                            name = result.stdout.strip()
                            return name.lstrip('/')  # убираем ведущий /
                        except Exception:
                            pass
        return None

    # ---------------------------
    # Проверка запуска проекта
    # ---------------------------
    @staticmethod
    def is_project_running(project_name: str) -> bool:
        from starter_files.core.utils.loader_utils import get
        containers = get('docker', 'get_containers', all=True) or []
        project_container_name = f"php-{project_name}"
        return any(c['name'] == project_container_name and 'running' in c['status'].lower() for c in containers)

    # ---------------------------
    # ENV: парсинг, генерация и работа с .env
    # ---------------------------
    @staticmethod
    def parse_env_content(content: str) -> Tuple[Dict[str, str], List[Union[str, Tuple[str, str]]]]:
        """
        Парсит .env (или .env.example) и возвращает (variables_dict, template_lines)
        template_lines — список строк и (key, original_line) для сохранения структуры.
        """
        variables: Dict[str, str] = {}
        lines: List[Union[str, Tuple[str, str]]] = []
        for line in content.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                lines.append(line)
                continue

            if '=' in stripped:
                key, value = stripped.split('=', 1)
                key = key.strip()
                variables[key] = value.strip()
                lines.append((key, line))
            else:
                lines.append(line)
        return variables, lines

    @staticmethod
    def generate_env_content(vars_dict: Dict[str, str],
                             template_lines: List[Union[str, Tuple[str, str]]]) -> str:
        """
        Генерирует текст .env:
         - сначала по порядку template_lines (заменяет значения, если ключ есть в vars_dict)
         - затем добавляет оставшиеся ключи из vars_dict (в порядке, в котором они в vars_dict) как Custom variables
        """
        result: List[str] = []
        template_keys: List[str] = []
        # Копия dict чтобы не менять исходный порядок вне этой функции
        vars_copy = dict(vars_dict)

        for line in template_lines:
            if isinstance(line, tuple):
                key, original_line = line
                template_keys.append(key)
                if key in vars_copy:
                    result.append(f"{key}={vars_copy.pop(key)}")
                else:
                    # оставляем оригинальную строку если в vars_dict нет такого ключа
                    result.append(original_line)
            else:
                result.append(line)

        # Оставшиеся ключи — кастомные, добавляем в порядке vars_dict
        custom_items = [(k, v) for k, v in vars_dict.items() if k not in template_keys]
        if custom_items:
            result.append('')  # пустая строка перед блоком
            result.append('# Custom variables')
            for k, v in custom_items:
                result.append(f"{k}={v}")

        return '\n'.join(result)

    @staticmethod
    def ensure_docker_env(project_path: Path) -> Dict[str, str]:
        """
        Создаёт/обновляет .env в project_path на основе .env.example.
        Возвращает итоговый словарь переменных.
        """
        env_example_path = project_path / '.env.example'
        env_path = project_path / '.env'

        if not env_example_path.exists():
            logger.debug(".env.example not found, skipping ensure_docker_env")
            return {}

        example_vars, example_lines = DockerModule.parse_env_content(env_example_path.read_text(encoding='utf-8'))

        if env_path.exists():
            current_vars, _ = DockerModule.parse_env_content(env_path.read_text(encoding='utf-8'))
        else:
            current_vars = {}

        # merged: сначала example keys (to preserve example order), затем current overrides/extra keys
        merged_vars = example_vars.copy()
        # current_vars overrides example_vars and appends extra keys in their order
        merged_vars.update(current_vars)

        content = DockerModule.generate_env_content(merged_vars, example_lines)
        env_path.write_text(content, encoding='utf-8')
        return merged_vars

    @staticmethod
    def read_docker_env(project_path: Path) -> Dict[str, str]:
        env_path = project_path / '.env'
        if not env_path.exists():
            return {}
        vars_dict, _ = DockerModule.parse_env_content(env_path.read_text(encoding='utf-8'))
        return vars_dict

    @staticmethod
    def write_docker_env(project_path: Path, vars_dict: Dict[str, str]):
        """
        Перезаписывает .env используя порядок из .env.example если он есть,
        иначе создаёт .env по порядку vars_dict.
        """
        env_example_path = project_path / '.env.example'
        env_path = project_path / '.env'

        if env_example_path.exists():
            _, template_lines = DockerModule.parse_env_content(env_example_path.read_text(encoding='utf-8'))
        else:
            # Создаём шаблонные строки на основе переданного словаря (сохранится порядок vars_dict)
            template_lines = [(k, f"{k}={v}") for k, v in vars_dict.items()]

        content = DockerModule.generate_env_content(vars_dict, template_lines)
        env_path.write_text(content, encoding='utf-8')
