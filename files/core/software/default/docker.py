from files.core.base_module import BaseModule

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
from files.core.utils.loader_utils import get
from files.core.utils.globalVars_utils import get_global, set_global
from files.core.utils.log_utils import LogManager

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
    def remove_build_sections(content: str) -> str:
        """
        Убирает блоки 'build:' и вложенные отступленные строки.
        Регулярка удаляет 'build:' и все последующие строк с большим отступом.
        """
        # Удаляем секции build: вместе с их вложенными строками
        content = re.sub(r'(?m)^[ \t]*build:.*(?:\n[ \t]+.*)*', '', content)
        return content

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
    def run_compose(log_path: Path = None) -> bool:
        """
        Запускает docker-compose с логированием всех этапов.
        """
        file_handler = None
        orig_handlers = []
        orig_level = logger.level
        try:
            docker_path = Path(get_global("docker_path"))
            compose_file = docker_path / "docker-compose.yml"

            sp = get_global('script_path')
            script_path = Path(sp) if sp else Path.cwd()
            starts_log_dir = script_path / 'files' / 'logs' / 'starts'
            starts_log_dir.mkdir(parents=True, exist_ok=True)

            # если передан log_path – используем его, иначе создаём новый по дате
            if log_path:
                log_file_path = Path(log_path)
            else:
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
            
            logger.info(f"[run_compose] ===== START DOCKER COMPOSE =====")
            # ==================== АВТОГЕНЕРАЦИЯ SSL СЕРТИФИКАТОВ (ЧИСТЫЙ PYTHON) ====================
            logger.info("[run_compose] Проверка и автогенерация SSL сертификатов (на Python)...")
            certs_dir = docker_path / "configs" / "nginx" / "certs"
            fullchain_path = certs_dir / "fullchain.pem"
            privkey_path = certs_dir / "privkey.pem"

            certs_dir.mkdir(parents=True, exist_ok=True)

            # Генерируем ТОЛЬКО если сертификатов нет
            if not fullchain_path.exists() or not privkey_path.exists():
                logger.info("[run_compose] Сертификаты не найдены — создаём самоподписанные на Python...")

                try:
                    from cryptography import x509
                    from cryptography.x509.oid import NameOID
                    from cryptography.hazmat.primitives import hashes, serialization
                    from cryptography.hazmat.primitives.asymmetric import rsa
                    from datetime import datetime, timedelta

                    # Определяем домен
                    domain = "mentoria.local"
                    env_path = docker_path / ".env"
                    if env_path.exists():
                        with open(env_path, 'r', encoding='utf-8') as f:
                            for line in f:
                                if line.startswith("NGINX_DOMAIN="):
                                    val = line.split("=", 1)[1].strip().strip('"\'')
                                    if val:
                                        domain = val
                                    break

                    logger.info(f"[run_compose] Домен для сертификата: {domain}")

                    # Генерация ключа
                    private_key = rsa.generate_private_key(
                        public_exponent=65537,
                        key_size=2048,
                    )

                    # Создание самоподписанного сертификата
                    subject = issuer = x509.Name([
                        x509.NameAttribute(NameOID.COUNTRY_NAME, "RU"),
                        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Moscow"),
                        x509.NameAttribute(NameOID.LOCALITY_NAME, "Moscow"),
                        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Local Development"),
                        x509.NameAttribute(NameOID.COMMON_NAME, domain),
                    ])

                    cert = x509.CertificateBuilder().subject_name(
                        subject
                    ).issuer_name(
                        issuer
                    ).public_key(
                        private_key.public_key()
                    ).serial_number(
                        x509.random_serial_number()
                    ).not_valid_before(
                        datetime.utcnow()
                    ).not_valid_after(
                        datetime.utcnow() + timedelta(days=3650)  # 10 лет
                    ).add_extension(
                        x509.SubjectAlternativeName([x509.DNSName(domain), x509.DNSName("localhost")]),
                        critical=False,
                    ).sign(private_key, hashes.SHA256())

                    # Сохранение приватного ключа
                    with open(privkey_path, "wb") as f:
                        f.write(private_key.private_bytes(
                            encoding=serialization.Encoding.PEM,
                            format=serialization.PrivateFormat.TraditionalOpenSSL,
                            encryption_algorithm=serialization.NoEncryption(),
                        ))

                    # Сохранение сертификата (fullchain = только сам сертификат, т.к. самоподписанный)
                    with open(fullchain_path, "wb") as f:
                        f.write(cert.public_bytes(serialization.Encoding.PEM))

                    logger.info("[run_compose] Самоподписанные сертификаты успешно созданы (Python)!")
                    logger.info(f"[run_compose]   → {fullchain_path}")
                    logger.info(f"[run_compose]   → {privkey_path}")

                except ImportError:
                    logger.error("[run_compose] Библиотека 'cryptography' не установлена!")
                    logger.error("[run_compose] Установи её командой: pip install cryptography")
                    logger.error("[run_compose] HTTPS работать не будет, но проект запустится на HTTP")
                except Exception as e:
                    logger.error(f"[run_compose] Ошибка при генерации сертификатов на Python: {e}")
                    logger.error("[run_compose] HTTPS будет недоступен")
            else:
                logger.info("[run_compose] Сертификаты уже существуют — используем их")
            # =========================================================================
            logger.info(f"[run_compose] Docker path: {docker_path}")
            logger.info(f"[run_compose] Absolute path: {docker_path.absolute()}")
            logger.info(f"[run_compose] Compose file exists: {compose_file.exists()}")

            # Получаем env_vars из текущего .env файла
            logger.info("[run_compose] Loading environment variables from .env...")
            env_vars = DockerModule.ensure_docker_env(docker_path, log_file_path)
            
            # Генерация compose файла
            logger.info("[run_compose] Generating docker-compose.yml from .env...")
            if not DockerModule.generate_docker_compose(env_vars, log_file_path):
                logger.error("[run_compose] Failed to generate docker-compose.yml")
                return False

            # Проверяем что compose файл создался
            if compose_file.exists():
                compose_size = compose_file.stat().st_size
                logger.info(f"[run_compose] Compose file generated: {compose_size} bytes")
                
                # Выводим первые несколько строк для отладки
                try:
                    with open(compose_file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        logger.info(f"[run_compose] First 20 lines of docker-compose.yml:")
                        for i, line in enumerate(lines[:20], 1):
                            logger.info(f"[run_compose]   {i}: {line.rstrip()}")
                except Exception as e:
                    logger.warning(f"[run_compose] Could not read compose file: {e}")
            else:
                logger.error("[run_compose] Compose file was not generated!")
                return False

            # Определяем команду docker compose
            try:
                subprocess.run(["docker", "compose", "version"], 
                            stdout=subprocess.DEVNULL, 
                            stderr=subprocess.DEVNULL, 
                            check=True)
                compose_cmd = ["docker", "compose"]
                logger.info("[run_compose] Using: docker compose")
            except Exception:
                compose_cmd = ["docker-compose"]
                logger.info("[run_compose] Using: docker-compose")

            # Проверяем доступность Docker
            logger.info("[run_compose] Checking Docker availability...")
            try:
                docker_info = subprocess.run(["docker", "info"], 
                                            capture_output=True, 
                                            text=True, 
                                            check=False)
                if docker_info.returncode != 0:
                    logger.error(f"[run_compose] Docker is not available: {docker_info.stderr}")
                    
                    # Пробуем запустить Docker
                    logger.info("[run_compose] Trying to start Docker...")
                    if platform.system() == 'Windows':
                        start_result = subprocess.run(['net', 'start', 'docker'], 
                                                    capture_output=True, 
                                                    text=True,
                                                    check=False)
                        if start_result.returncode != 0:
                            logger.error(f"[run_compose] Failed to start Docker: {start_result.stderr}")
                            return False
                        logger.info("[run_compose] Docker started successfully")
                        time.sleep(3)
                    else:
                        logger.error("[run_compose] Docker not running. Please start Docker manually.")
                        return False
                else:
                    logger.info("[run_compose] Docker is available")
            except Exception as e:
                logger.error(f"[run_compose] Error checking Docker: {e}")
                return False

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
            
            try:
                down_process = subprocess.run(
                    down_cmd, 
                    cwd=str(docker_path), 
                    capture_output=True,
                    text=True,
                    check=False
                )
                
                # Логируем результат
                logger.info(f"[run_compose] docker compose down completed with code: {down_process.returncode}")
                
                if down_process.stdout and down_process.stdout.strip():
                    for line in down_process.stdout.strip().split('\n'):
                        if line.strip():
                            logger.info(f"[compose_down] {line.strip()}")
                
                if down_process.stderr and down_process.stderr.strip():
                    for line in down_process.stderr.strip().split('\n'):
                        if line.strip():
                            logger.warning(f"[compose_down_err] {line.strip()}")
                
                # Обрабатываем возможные ошибки
                if down_process.returncode != 0:
                    error_lower = down_process.stderr.lower() if down_process.stderr else ""
                    if "network not found" in error_lower:
                        logger.warning("[run_compose] Network not found - this is normal for first run")
                    elif "no such file" in error_lower or "no resource found" in error_lower:
                        logger.warning("[run_compose] Resource not found - skipping")
                    elif "no containers to remove" in error_lower:
                        logger.info("[run_compose] No containers to remove - all good")
                    else:
                        logger.warning(f"[run_compose] docker compose down had issues (code: {down_process.returncode})")
                
            except Exception as e:
                logger.error(f"[run_compose] Error during docker compose down: {e}")

            # -------------------------------
            # 2. Получаем список образов из docker-compose
            # -------------------------------
            try:
                logger.info("[run_compose] Checking existing images...")
                images_result = subprocess.run(
                    compose_cmd + ["-f", str(compose_file), "images", "-q"],
                    cwd=str(docker_path), 
                    capture_output=True, 
                    text=True, 
                    check=False
                )
                
                if images_result.returncode == 0 and images_result.stdout:
                    image_ids = [i.strip() for i in images_result.stdout.splitlines() if i.strip()]
                    logger.info(f"[run_compose] Found {len(image_ids)} existing images")
                    for img_id in image_ids:
                        if img_id:
                            logger.info(f"[run_compose] Removing old image: {img_id[:12]}")
                            subprocess.run(
                                ["docker", "rmi", "-f", img_id], 
                                check=False,
                                capture_output=True
                            )
            except Exception as e:
                logger.warning(f"[run_compose] Failed to list/remove images: {e}")

            # -------------------------------
            # 3. Запуск docker-compose с билдом
            # -------------------------------
            logger.info("[run_compose] Building Docker images...")
            build_cmd = compose_cmd + ["-f", str(compose_file), "build", "--no-cache", "--pull"]
            logger.info(f"[run_compose] Build command: {' '.join(build_cmd)}")
            
            try:
                build_process = subprocess.Popen(
                    build_cmd,
                    cwd=str(docker_path),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    bufsize=1,
                    universal_newlines=True
                )
                
                logger.info("[run_compose] === DOCKER COMPOSE BUILD OUTPUT ===")
                for line in iter(build_process.stdout.readline, ''):
                    if line:
                        cleaned_line = line.rstrip()
                        if cleaned_line:
                            logger.info(f"[build] {cleaned_line}")

                build_return_code = build_process.wait()

                if build_return_code != 0:
                    logger.error(f"[run_compose] docker-compose build failed with code {build_return_code}")
                    return False
                else:
                    logger.info("[run_compose] Docker Compose build completed successfully")
                    
            except Exception as e:
                logger.error(f"[run_compose] Build error: {e}")
                return False

            # -------------------------------
            # 4. Запуск docker-compose в detached mode
            # -------------------------------
            logger.info("[run_compose] Starting docker-compose services...")
            up_cmd = compose_cmd + ["-f", str(compose_file), "up", "-d", "--force-recreate"]
            logger.info(f"[run_compose] Up command: {' '.join(up_cmd)}")
            
            try:
                up_process = subprocess.Popen(
                    up_cmd,
                    cwd=str(docker_path),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    bufsize=1,
                    universal_newlines=True
                )
                
                logger.info("[run_compose] === DOCKER COMPOSE UP OUTPUT ===")
                for line in iter(up_process.stdout.readline, ''):
                    if line:
                        cleaned_line = line.rstrip()
                        if cleaned_line:
                            logger.info(f"[up] {cleaned_line}")

                up_return_code = up_process.wait()

                if up_return_code != 0:
                    logger.error(f"[run_compose] docker-compose up failed with code {up_return_code}")
                    
                    # Показываем логи контейнеров при ошибке
                    try:
                        logger.info("[run_compose] Checking container logs for errors...")
                        ps_cmd = compose_cmd + ["-f", str(compose_file), "ps", "-q"]
                        ps_result = subprocess.run(
                            ps_cmd, 
                            cwd=str(docker_path), 
                            capture_output=True, 
                            text=True, 
                            check=False
                        )
                        
                        if ps_result.returncode == 0 and ps_result.stdout:
                            container_ids = ps_result.stdout.strip().split()
                            for container_id in container_ids:
                                if container_id:
                                    log_cmd = ["docker", "logs", "--tail", "20", container_id]
                                    log_result = subprocess.run(
                                        log_cmd, 
                                        capture_output=True, 
                                        text=True, 
                                        check=False
                                    )
                                    if log_result.stdout:
                                        logger.info(f"[run_compose] Logs for {container_id[:12]}:")
                                        for log_line in log_result.stdout.split('\n')[-10:]:
                                            if log_line.strip():
                                                logger.info(f"[container_log] {log_line.strip()}")
                    except Exception as log_error:
                        logger.warning(f"[run_compose] Could not get container logs: {log_error}")
                    return False
                    
            except Exception as e:
                logger.error(f"[run_compose] Up error: {e}")
                return False

            # -------------------------------
            # 5. Проверяем статус сервисов
            # -------------------------------
            logger.info("[run_compose] Checking service status...")
            time.sleep(2)
            
            try:
                ps_cmd = compose_cmd + ["-f", str(compose_file), "ps", "--all"]
                ps_result = subprocess.run(
                    ps_cmd, 
                    cwd=str(docker_path), 
                    capture_output=True, 
                    text=True, 
                    check=False
                )
                
                if ps_result.returncode == 0:
                    logger.info("[run_compose] Container status:")
                    for line in ps_result.stdout.split('\n'):
                        if line.strip():
                            logger.info(f"[status] {line.strip()}")
                else:
                    logger.warning(f"[run_compose] Could not get status: {ps_result.stderr}")
            except Exception as e:
                logger.warning(f"[run_compose] Error checking status: {e}")

            # -------------------------------
            # 6. Показываем логи запуска
            # -------------------------------
            logger.info("[run_compose] Showing startup logs (last 20 lines)...")
            try:
                logs_cmd = compose_cmd + ["-f", str(compose_file), "logs", "--tail", "20"]
                logs_process = subprocess.Popen(
                    logs_cmd,
                    cwd=str(docker_path),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    bufsize=1,
                    universal_newlines=True
                )
                
                logger.info("[run_compose] === STARTUP LOGS ===")
                for line in iter(logs_process.stdout.readline, ''):
                    if line:
                        logger.info(f"[startup_log] {line.rstrip()}")
                
                logs_process.wait()
                
            except Exception as e:
                logger.warning(f"[run_compose] Could not get startup logs: {e}")

            logger.info("[run_compose] Docker Compose started successfully!")
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
                            is_currently_executable = bool(current_mode & 0o111)
                            
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
                                    new_mode = current_mode | 0o111
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
                            return name.lstrip('/')
                        except Exception:
                            pass
        return None

    # ---------------------------
    # Проверка запуска проекта
    # ---------------------------
    @staticmethod
    def is_project_running(project_name: str) -> bool:
        from files.core.utils.loader_utils import get
        containers = get('docker', 'get_containers', all=True) or []
        project_container_name = f"php-{project_name}"
        return any(c['name'] == project_container_name and 'running' in c['status'].lower() for c in containers)

    # ---------------------------
    # Генерация docker-compose (низкоуровневая и высокоуровневая)
    # ---------------------------
    @staticmethod
    def generate_docker_compose(env_vars: Dict[str, str] = None, log_path: Optional[Path] = None) -> bool:
        try:
            docker_path = Path(get_global("docker_path"))
            docker_path.mkdir(parents=True, exist_ok=True)

            if env_vars is None:
                env_vars = DockerModule.ensure_docker_env(docker_path, log_path)

            # Получаем PULL_FROM_REGISTRY из env_vars
            pull_from_registry = env_vars.get("PULL_FROM_REGISTRY", "false").lower() == "true"

            if not DockerModule.generate_compose(docker_path, env_vars, pull_from_registry=pull_from_registry, log_path=log_path):
                return False

            return True
        except Exception as e:
            if log_path:
                with open(log_path, 'a', encoding='utf-8') as log_file:
                    log_file.write(f"[generate_docker_compose] Error: {str(e)}\n")
            logger.error(f"Error generating docker-compose: {e}")
            return False

    @staticmethod
    def generate_compose(docker_dir: Union[str, Path], env_vars: Dict[str, str], pull_from_registry: bool = False, log_path: Optional[Path] = None) -> bool:
        """
        Генерирует docker-compose.yml на основе шаблона и переменных.
        Универсальная версия для всех платформ.
        """
        try:
            docker_dir = Path(docker_dir)
            compose_example = docker_dir / "docker-compose.example"
            if not compose_example.exists():
                compose_example = docker_dir / "docker-compose.template"
            compose_output = docker_dir / "docker-compose.yml"

            if log_path:
                with open(log_path, 'a', encoding='utf-8') as log_file:
                    log_file.write(f"[generate_compose] Starting with env_vars: {list(env_vars.keys())}\n")
                    for k, v in env_vars.items():
                        if 'PASSWORD' in k or 'SECRET' in k:
                            log_file.write(f"  {k}=[HIDDEN]\n")
                        else:
                            log_file.write(f"  {k}={v}\n")

            if not compose_example.exists():
                if log_path:
                    with open(log_path, 'a', encoding='utf-8') as log_file:
                        log_file.write(f"[generate_compose] Compose template not found: {compose_example}\n")
                logger.error(f"[generate_compose] Compose template not found: {compose_example}")
                return False

            content = compose_example.read_text(encoding='utf-8')
            
            if log_path:
                with open(log_path, 'a', encoding='utf-8') as log_file:
                    log_file.write(f"[generate_compose] Read compose template ({compose_example}): {len(content)} chars\n")

            if pull_from_registry:
                content = DockerModule.remove_build_sections(content)
                if log_path:
                    with open(log_path, 'a', encoding='utf-8') as log_file:
                        log_file.write("[generate_compose] Removed build sections (pull_from_registry=True)\n")

            # Заменяем переменные окружения вне блоков
            content = DockerModule.replace_env_variables(content, env_vars)
            
            if log_path:
                with open(log_path, 'a', encoding='utf-8') as log_file:
                    log_file.write("[generate_compose] After env substitution\n")

            # Убедимся, что папка существует
            compose_output.parent.mkdir(parents=True, exist_ok=True)

            # Сохраняем файл
            compose_output.write_text(content, encoding='utf-8')
            
            if log_path:
                with open(log_path, 'a', encoding='utf-8') as log_file:
                    log_file.write(f"[generate_compose] docker-compose.yml generated at {compose_output}\n")
                    # Логируем первые несколько строк для проверки
                    lines = content.split('\n')[:10]
                    log_file.write(f"[generate_compose] First 10 lines:\n")
                    for i, line in enumerate(lines, 1):
                        log_file.write(f"  {i}: {line}\n")

            return True

        except Exception as e:
            if log_path:
                with open(log_path, 'a', encoding='utf-8') as log_file:
                    log_file.write(f"[generate_compose] Error: {str(e)}\n")
            logger.exception(f"[generate_compose] Error generating compose: {str(e)}")
            return False
    
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
                            template_lines: List[Union[str, Tuple[str, str]]],
                            log_path: Optional[Path] = None) -> str:
        """
        Генерирует содержимое .env файла на основе шаблона и переменных.
        Добавлено логирование для отслеживания изменений переменных.
        """
        result: List[str] = []
        template_keys: List[str] = []
        vars_copy = dict(vars_dict)

        # Логирование если указан путь
        if log_path:
            with open(log_path, 'a', encoding='utf-8') as log_file:
                log_file.write(f"[generate_env_content] Input variables:\n")
                for k, v in vars_dict.items():
                    log_file.write(f"  {k}={v}\n")

        for line in template_lines:
            if isinstance(line, tuple):
                key, original_line = line
                template_keys.append(key)
                if key in vars_copy:
                    value = vars_copy.pop(key)
                    result.append(f"{key}={value}")
                    
                    # Логирование подстановки
                    if log_path:
                        with open(log_path, 'a', encoding='utf-8') as log_file:
                            log_file.write(f"[generate_env_content] Substituted: {key}={value}\n")
                else:
                    result.append(original_line)
            else:
                result.append(line)

        # Добавляем оставшиеся кастомные переменные
        custom_items = [(k, v) for k, v in vars_copy.items() if k not in template_keys]
        if custom_items:
            result.append('')
            result.append('# Custom variables')
            for k, v in custom_items:
                result.append(f"{k}={v}")
                if log_path:
                    with open(log_path, 'a', encoding='utf-8') as log_file:
                        log_file.write(f"[generate_env_content] Added custom: {k}={v}\n")

        return '\n'.join(result)

    @staticmethod
    def ensure_docker_env(project_path: Path, log_path: Optional[Path] = None) -> Dict[str, str]:
        """
        Создаёт/обновляет .env в project_path на основе .env.example.
        Возвращает итоговый словарь переменных.
        Добавлено логирование для отслеживания изменений переменных.
        """
        env_example_path = project_path / '.env.example'
        env_path = project_path / '.env'

        if log_path:
            with open(log_path, 'a', encoding='utf-8') as log_file:
                log_file.write(f"[ensure_docker_env] Starting with project_path: {project_path}\n")

        if not env_example_path.exists():
            if log_path:
                with open(log_path, 'a', encoding='utf-8') as log_file:
                    log_file.write("[ensure_docker_env] .env.example not found\n")
            return {}

        example_vars, example_lines = DockerModule.parse_env_content(env_example_path.read_text(encoding='utf-8'))
        
        if log_path:
            with open(log_path, 'a', encoding='utf-8') as log_file:
                log_file.write(f"[ensure_docker_env] Example variables: {list(example_vars.keys())}\n")

        if env_path.exists():
            current_vars, _ = DockerModule.parse_env_content(env_path.read_text(encoding='utf-8'))
            if log_path:
                with open(log_path, 'a', encoding='utf-8') as log_file:
                    log_file.write(f"[ensure_docker_env] Current variables: {list(current_vars.keys())}\n")
                    for k, v in current_vars.items():
                        log_file.write(f"  {k}={v}\n")
        else:
            current_vars = {}
            if log_path:
                with open(log_path, 'a', encoding='utf-8') as log_file:
                    log_file.write("[ensure_docker_env] No existing .env found\n")

        # Объединяем переменные
        merged_vars = current_vars.copy()
        for key, value in example_vars.items():
            if key not in merged_vars:
                merged_vars[key] = value

        if log_path:
            with open(log_path, 'a', encoding='utf-8') as log_file:
                log_file.write(f"[ensure_docker_env] Merged variables: {list(merged_vars.keys())}\n")
                for k, v in merged_vars.items():
                    log_file.write(f"  {k}={v}\n")

        content = DockerModule.generate_env_content(merged_vars, example_lines, log_path)
        env_path.write_text(content, encoding='utf-8')
        
        if log_path:
            with open(log_path, 'a', encoding='utf-8') as log_file:
                log_file.write(f"[ensure_docker_env] Final .env content:\n{content}\n")

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

    # ----------------------------------------------------
    # НОВЫЕ ФУНКЦИИ ДЛЯ УПРАВЛЕНИЯ ПОДСЕТЯМИ
    # ----------------------------------------------------
    
    @staticmethod
    def get_used_subnets() -> List[str]:
        """
        Возвращает список всех используемых подсетей в формате '172.20.0.0/16'
        
        Returns:
            Список занятых подсетей, отсортированный по октету
        """
        used_subnets = set()
        
        try:
            # 1. Проверяем существующие сети Docker
            try:
                result = subprocess.run(
                    ['docker', 'network', 'ls', '-q'],
                    capture_output=True,
                    text=True,
                    check=True
                )
                
                network_ids = result.stdout.strip().split()
                for net_id in network_ids:
                    try:
                        inspect_result = subprocess.run(
                            ['docker', 'network', 'inspect', net_id],
                            capture_output=True,
                            text=True,
                            check=True
                        )
                        if inspect_result.returncode == 0:
                            networks = json.loads(inspect_result.stdout)
                            for network in networks:
                                if 'IPAM' in network and network['IPAM']['Config']:
                                    for config in network['IPAM']['Config']:
                                        if 'Subnet' in config:
                                            subnet = config['Subnet']
                                            # Фильтруем только подсети 172.x.x.x/16
                                            if subnet.startswith('172.') and subnet.endswith('/16'):
                                                used_subnets.add(subnet)
                    except Exception:
                        continue
            except Exception as e:
                logger.warning(f"Error checking Docker networks: {e}")
            
            # 2. Проверяем запущенные контейнеры
            try:
                result = subprocess.run(
                    ['docker', 'ps', '-a', '--format', '{{.ID}}'],
                    capture_output=True,
                    text=True,
                    check=True
                )
                
                container_ids = result.stdout.strip().split()
                for container_id in container_ids:
                    try:
                        inspect_result = subprocess.run(
                            ['docker', 'inspect', container_id],
                            capture_output=True,
                            text=True,
                            check=True
                        )
                        if inspect_result.returncode == 0:
                            container = json.loads(inspect_result.stdout)[0]
                            if 'NetworkSettings' in container and container['NetworkSettings']['Networks']:
                                for network in container['NetworkSettings']['Networks'].values():
                                    if 'IPAMConfig' in network and network['IPAMConfig']:
                                        if 'IPv4Address' in network['IPAMConfig']:
                                            ip = network['IPAMConfig']['IPv4Address']
                                            # Извлекаем подсеть из IP (первые два октета)
                                            parts = ip.split('.')
                                            if len(parts) >= 2 and parts[0] == '172':
                                                subnet = f"172.{parts[1]}.0.0/16"
                                                used_subnets.add(subnet)
                    except Exception:
                        continue
            except Exception as e:
                logger.warning(f"Error checking containers: {e}")
            
            # 3. Ищем в docker-compose файлах в текущей директории и родительских
            try:
                current_dir = Path.cwd()
                search_dirs = [
                    current_dir,
                    current_dir.parent,
                    current_dir.parent.parent if current_dir.parent.parent else None
                ]
                
                for search_dir in filter(None, search_dirs):
                    for compose_file in search_dir.rglob("docker-compose*.yml"):
                        try:
                            content = compose_file.read_text(encoding='utf-8', errors='ignore')
                            # Ищем подсети 172.XX.0.0/16
                            pattern = r'172\.(\d{1,3})\.0\.0/16'
                            matches = re.findall(pattern, content)
                            for octet in matches:
                                if octet.isdigit() and 0 <= int(octet) <= 255:
                                    subnet = f"172.{octet}.0.0/16"
                                    used_subnets.add(subnet)
                        except Exception:
                            continue
            except Exception as e:
                logger.warning(f"Error scanning compose files: {e}")
            
        except Exception as e:
            logger.error(f"Unexpected error in get_used_subnets: {e}")
        
        # Сортируем по второму октету
        sorted_subnets = sorted(
            list(used_subnets),
            key=lambda x: int(x.split('.')[1]) if len(x.split('.')) > 1 else 0
        )
        
        logger.debug(f"Found {len(sorted_subnets)} used subnets: {sorted_subnets}")
        return sorted_subnets
    
    @staticmethod
    def get_used_subnets_simple() -> List[str]:
        """
        Упрощенная версия - возвращает только подсети вида 172.XX.0.0/16
        
        Returns:
            Список занятых подсетей
        """
        try:
            # Получаем все подсети
            all_subnets = DockerModule.get_used_subnets()
            
            # Фильтруем только 172.XX.0.0/16
            filtered = []
            for subnet in all_subnets:
                if (subnet.startswith('172.') and 
                    subnet.endswith('/16') and 
                    subnet.count('.') == 3):
                    filtered.append(subnet)
            
            return filtered
            
        except Exception as e:
            logger.error(f"Error in get_used_subnets_simple: {e}")
            return []
    
    @staticmethod
    def get_used_octets() -> List[int]:
        """
        Возвращает список занятых вторых октетов (20, 21, 22...)
        
        Returns:
            Список занятых октетов, отсортированный по возрастанию
        """
        used_subnets = DockerModule.get_used_subnets_simple()
        octets = []
        
        for subnet in used_subnets:
            try:
                # Извлекаем второй октет из 172.XX.0.0/16
                parts = subnet.split('.')
                if len(parts) >= 2:
                    octet = int(parts[1])
                    octets.append(octet)
            except (ValueError, IndexError):
                continue
        
        # Убираем дубликаты и сортируем
        unique_octets = sorted(set(octets))
        logger.debug(f"Found {len(unique_octets)} used octets: {unique_octets}")
        return unique_octets
    
    @staticmethod
    def is_subnet_available(subnet: str) -> Tuple[bool, str]:
        """
        Проверяет, свободна ли подсеть
        
        Args:
            subnet: Подсеть в формате '172.20.0.0/16'
            
        Returns:
            Tuple[bool, str]: (доступна ли, сообщение об ошибке)
        """
        try:
            # Проверяем формат
            if not subnet.startswith('172.') or not subnet.endswith('/16'):
                return False, f"Неправильный формат подсети. Должно быть: 172.XX.0.0/16"
            
            # Извлекаем октет
            parts = subnet.split('.')
            if len(parts) != 4:
                return False, f"Неправильный формат подсети: {subnet}"
            
            octet_str = parts[1].split('/')[0]
            try:
                octet = int(octet_str)
                if octet < 20 or octet > 250:
                    return False, f"Октет должен быть в диапазоне 20-250"
            except ValueError:
                return False, f"Октет должен быть числом: {octet_str}"
            
            # Проверяем занятость
            used_octets = DockerModule.get_used_octets()
            
            if octet in used_octets:
                return False, f"Подсеть {subnet} уже используется"
            
            return True, f"Подсеть {subnet} свободна"
            
        except Exception as e:
            return False, f"Ошибка проверки подсети: {str(e)}"
    
    @staticmethod
    def find_available_subnet(start_octet: int = 20, max_attempts: int = 100) -> str:
        """
        Находит свободную подсеть, начиная с start_octet
        
        Args:
            start_octet: С какого октета начать поиск
            max_attempts: Максимальное количество попыток
            
        Returns:
            Свободная подсеть вида '172.XX.0.0/16'
            
        Raises:
            ValueError: Если не найдено свободных подсетей
        """
        used_octets = DockerModule.get_used_octets()
        
        # Ищем свободный октет
        for attempt in range(max_attempts):
            test_octet = start_octet + attempt
            if test_octet > 250:
                break
            
            if test_octet not in used_octets:
                subnet = f"172.{test_octet}.0.0/16"
                logger.info(f"Found available subnet: {subnet}")
                return subnet
        
        # Если не нашли
        used_str = ", ".join(str(o) for o in sorted(used_octets)[:10])
        raise ValueError(
            f"Не найдено свободных подсетей в диапазоне 172.{start_octet}.0.0 - 172.{start_octet + max_attempts}.0.0. "
            f"Занятые октеты: {used_str}"
        )
    
    @staticmethod
    def increment_subnet(subnet: str) -> str:
        """
        Увеличивает подсеть на 1 октет
        
        Args:
            subnet: Исходная подсеть вида '172.20.0.0/16'
            
        Returns:
            Новая подсеть вида '172.21.0.0/16'
            
        Raises:
            ValueError: Если неправильный формат или превышен лимит
        """
        try:
            # Проверяем формат
            if not subnet.startswith('172.') or not subnet.endswith('/16'):
                raise ValueError(f"Неправильный формат подсети: {subnet}. Должно быть: 172.XX.0.0/16")
            
            # Извлекаем октет
            parts = subnet.split('.')
            if len(parts) != 4:
                raise ValueError(f"Неправильный формат подсети: {subnet}")
            
            octet_part = parts[1]
            try:
                current_octet = int(octet_part)
            except ValueError:
                raise ValueError(f"Октет должен быть числом: {octet_part}")
            
            # Проверяем диапазон
            if current_octet < 20 or current_octet >= 250:
                raise ValueError(f"Октет должен быть в диапазоне 20-249. Текущий: {current_octet}")
            
            # Увеличиваем на 1
            new_octet = current_octet + 1
            new_subnet = f"172.{new_octet}.0.0/16"
            
            # Проверяем, свободна ли новая подсеть
            used_octets = DockerModule.get_used_octets()
            attempts = 0
            
            while new_octet in used_octets and attempts < 50:
                new_octet += 1
                attempts += 1
                if new_octet > 250:
                    raise ValueError(f"Достигнут предел октетов (250)")
            
            new_subnet = f"172.{new_octet}.0.0/16"
            logger.info(f"Incremented subnet: {subnet} -> {new_subnet}")
            return new_subnet
            
        except Exception as e:
            raise ValueError(f"Ошибка при увеличении подсети: {str(e)}")
    
    @staticmethod
    def get_available_subnet_or_increment(requested_subnet: str) -> Tuple[str, bool]:
        """
        Проверяет запрошенную подсеть, если занята - увеличивает
        
        Args:
            requested_subnet: Запрашиваемая подсеть вида '172.20.0.0/16'
            
        Returns:
            Tuple[подсеть, была_ли_увеличена]
            
        Пример:
            get_available_subnet_or_increment('172.20.0.0/16')
            → ('172.20.0.0/16', False)  # если свободна
            → ('172.21.0.0/16', True)   # если занята, увеличили
        """
        try:
            # Проверяем запрошенную подсеть
            available, message = DockerModule.is_subnet_available(requested_subnet)
            
            if available:
                logger.info(f"Requested subnet {requested_subnet} is available")
                return requested_subnet, False
            else:
                logger.info(f"Requested subnet {requested_subnet} is occupied: {message}")
                
                # Пробуем увеличить
                try:
                    new_subnet = DockerModule.increment_subnet(requested_subnet)
                    logger.info(f"Using incremented subnet: {new_subnet}")
                    return new_subnet, True
                except ValueError as e:
                    logger.warning(f"Could not increment {requested_subnet}: {e}")
                    
                    # Ищем любую свободную
                    try:
                        start_octet = int(requested_subnet.split('.')[1])
                        new_subnet = DockerModule.find_available_subnet(start_octet)
                        logger.info(f"Found alternative subnet: {new_subnet}")
                        return new_subnet, True
                    except ValueError as e2:
                        # Последняя попытка - найти любую свободную с начала
                        try:
                            new_subnet = DockerModule.find_available_subnet(20)
                            logger.info(f"Found free subnet from beginning: {new_subnet}")
                            return new_subnet, True
                        except ValueError:
                            raise ValueError(f"Не найдено свободных подсетей: {e2}")
                        
        except Exception as e:
            raise ValueError(f"Ошибка при поиске подсети: {str(e)}")
    
    @staticmethod
    def generate_subnet_for_project(project_name: str, 
                                    preferred_octet: int = None) -> Dict[str, any]:
        """
        Генерирует подсеть для нового проекта
        
        Args:
            project_name: Имя проекта
            preferred_octet: Предпочитаемый октет (если None - автоматически)
            
        Returns:
            Словарь с информацией о подсети
        """
        try:
            # Определяем начальный октет
            if preferred_octet is None:
                # Можно использовать хэш имени проекта для более равномерного распределения
                import hashlib
                hash_int = int(hashlib.md5(project_name.encode()).hexdigest()[:8], 16)
                start_octet = 20 + (hash_int % 50)
            else:
                start_octet = preferred_octet
            
            # Формируем запрашиваемую подсеть
            requested_subnet = f"172.{start_octet}.0.0/16"
            
            # Получаем доступную подсеть
            final_subnet, was_incremented = DockerModule.get_available_subnet_or_increment(
                requested_subnet
            )
            
            # Извлекаем октет
            final_octet = int(final_subnet.split('.')[1])
            
            result = {
                'project_name': project_name,
                'requested_subnet': requested_subnet,
                'final_subnet': final_subnet,
                'octet': final_octet,
                'was_incremented': was_incremented,
                'network_prefix': f'172.{final_octet}',
                'gateway': f'172.{final_octet}.0.1',
                'container_prefix': f'172.{final_octet}.0',
                'generated_at': datetime.now().isoformat(),
            }
            
            logger.info(f"Generated subnet for '{project_name}': {final_subnet}")
            return result
            
        except Exception as e:
            logger.error(f"Error generating subnet for {project_name}: {e}")
            raise

    # ----------------------------------------------------
    # АЛИАСЫ ДЛЯ ПРОСТОГО ИСПОЛЬЗОВАНИЯ
    # ----------------------------------------------------

    @staticmethod
    def get_used_networks() -> List[str]:
        """Алиас для DockerModule.get_used_subnets_simple()"""
        return DockerModule.get_used_subnets_simple()

    @staticmethod
    def check_and_increment_subnet(subnet: str) -> str:
        """Алиас: проверяет подсеть, если занята - увеличивает"""
        return DockerModule.get_available_subnet_or_increment(subnet)[0]

    @staticmethod
    def get_free_network() -> str:
        """Алиас: находит любую свободную подсеть"""
        return DockerModule.find_available_subnet()