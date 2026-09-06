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
    """Реализация Docker утилит"""
    # ---------------------------
    # Проверки установки Docker
    # ---------------------------
    @staticmethod
    def check_docker_installed() -> bool:
        cached = get_global('docker_installed')
        if cached is not None:
            return cached
        try:
            subprocess.run(['docker', '--version'], capture_output=True, text=True, check=True)
            set_global('docker_installed', True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            set_global('docker_installed', False)
            return False

    @staticmethod
    def check_docker_compose_installed() -> bool:
        cached = get_global('docker_compose_installed')
        if cached is not None:
            return cached
        try:
            subprocess.check_output(["docker", "compose", "version"], stderr=subprocess.DEVNULL)
            set_global('docker_compose_installed', True)
            return True
        except (FileNotFoundError, subprocess.CalledProcessError):
            try:
                subprocess.check_output(["docker-compose", "--version"], stderr=subprocess.DEVNULL)
                set_global('docker_compose_installed', True)
                return True
            except (FileNotFoundError, subprocess.CalledProcessError):
                set_global('docker_compose_installed', False)
                return False

    # ---------------------------
    # РЈСЃС‚Р°РЅРѕРІРєР° Docker / Compose
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
                docker_installed = get('docker','check_docker_installed')
                set_global('docker_installed', docker_installed)
                docker_compose_installed = get('docker','check_docker_compose_installed')
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
                docker_compose_installed = get('docker','check_docker_compose_installed')
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
    # РћР±С‰РёРµ СѓС‚РёР»РёС‚С‹ РґР»СЏ РїРѕРґСЃС‚Р°РЅРѕРІРєРё РїРµСЂРµРјРµРЅРЅС‹С… Рё Р±Р»РѕРєРѕРІ
    # ---------------------------
    @staticmethod
    def replace_env_variables(content: str, env_vars: Dict[str, str]) -> str:
        """Р—Р°РјРµРЅСЏРµС‚ ${VAR} РЅР° Р·РЅР°С‡РµРЅРёРµ РёР· env_vars (РµСЃР»Рё РµСЃС‚СЊ)"""
        def repl(match):
            var = match.group(1)
            return env_vars.get(var, match.group(0))
        return re.sub(r'\$\{(\w+)\}', repl, content)

    @staticmethod
    def remove_build_sections(content: str) -> str:
        """
        РЈР±РёСЂР°РµС‚ Р±Р»РѕРєРё 'build:' Рё РІР»РѕР¶РµРЅРЅС‹Рµ РѕС‚СЃС‚СѓРїР»РµРЅРЅС‹Рµ СЃС‚СЂРѕРєРё.
        Р РµРіСѓР»СЏСЂРєР° СѓРґР°Р»СЏРµС‚ 'build:' Рё РІСЃРµ РїРѕСЃР»РµРґСѓСЋС‰РёРµ СЃС‚СЂРѕРє СЃ Р±РѕР»СЊС€РёРј РѕС‚СЃС‚СѓРїРѕРј.
        """
        # РЈРґР°Р»СЏРµРј СЃРµРєС†РёРё build: РІРјРµСЃС‚Рµ СЃ РёС… РІР»РѕР¶РµРЅРЅС‹РјРё СЃС‚СЂРѕРєР°РјРё
        content = re.sub(r'(?m)^[ \t]*build:.*(?:\n[ \t]+.*)*', '', content)
        return content

    # ---------------------------
    # РЎС‚Р°С‚СѓСЃ РєРѕРЅС‚РµР№РЅРµСЂРѕРІ Рё СѓРїСЂР°РІР»РµРЅРёРµ
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
    # РЎР±РѕСЂ РёРЅС„РѕСЂРјР°С†РёРё Рѕ Docker
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
    # РџРѕР»СѓС‡РµРЅРёРµ СЂРµСЃСѓСЂСЃРѕРІ Docker
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
            result = subprocess.run(['docker', 'images', '--format', '{{.ID}}|{{.Repository}}|{{.Tag}}|{{.CreatedSince}}|{{.CreatedAt}}|{{.Size}}'], capture_output=True, text=True)
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    parts = line.split('|')
                    if len(parts) >= 6:
                        images.append({ 'id': parts[0], 'repository': parts[1], 'tag': parts[2],'created_since': parts[3], 'created_at': parts[4], 'size': parts[5]})
        except Exception as e:
            logger.error(f"Error getting images: {str(e)}")
        return images

    @staticmethod
    def get_logs(container_id: str, tail: int = 100) -> str:
        try:
            result = subprocess.run(['docker', 'logs', '--tail', str(tail), container_id], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout
        except Exception as e:
            logger.error(f"Error getting logs: {str(e)}")
        return ""

    # ---------------------------
    # РЎРµС‚Рё Рё С‚РѕРјР°
    # ---------------------------
    @staticmethod
    def get_networks() -> List[Dict]:
        networks = []
        try:
            result = subprocess.run(['docker', 'network', 'ls', '--format', '{{.ID}}|{{.Name}}|{{.Driver}}|{{.Scope}}|{{.IPv6}}|{{.Internal}}|{{.Created}}'],capture_output=True, text=True)
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    parts = line.split('|')
                    if len(parts) >= 7:
                        networks.append({'id': parts[0], 'name': parts[1], 'driver': parts[2],'scope': parts[3], 'ipv6': parts[4], 'internal': parts[5], 'created': parts[6]})
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
    # Р”РµР№СЃС‚РІРёСЏ СЃ РєРѕРЅС‚РµР№РЅРµСЂРѕРј Рё РѕР±СЂР°Р·РѕРј
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
    # РџРµСЂРµР·Р°РїСѓСЃРє Docker
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
    # РћС‡РёСЃС‚РєР° СЃРёСЃС‚РµРјС‹ Docker
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
    # Р“Р»РѕР±Р°Р»СЊРЅС‹Рµ РїРµСЂРµРјРµРЅРЅС‹Рµ Docker
    # ---------------------------
    @staticmethod
    def set_globals():
        docker_installed = get('docker','check_docker_installed')
        docker_compose_installed = get('docker','check_docker_compose_installed')
        set_global('docker_installed', docker_installed)
        set_global('docker_compose_installed', docker_compose_installed)

    # ---------------------------
    # РџСЂРѕРІРµСЂРєР° РґРѕСЃС‚СѓРїРЅРѕСЃС‚Рё Docker daemon
    # ---------------------------
    @staticmethod
    def is_docker_available() -> bool:
        try:
            subprocess.run(["docker", "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            return True
        except Exception:
            return False

    # ---------------------------
    # Р—Р°РїСѓСЃРє docker-compose (РІРєР»СЋС‡Р°СЏ РїРѕРґРіРѕС‚РѕРІРєСѓ .env Рё compose)
    # ---------------------------
    @staticmethod
    def run_compose(log_path: Path = None) -> bool:
        """
        Р—Р°РїСѓСЃРєР°РµС‚ docker-compose СЃ Р»РѕРіРёСЂРѕРІР°РЅРёРµРј РІСЃРµС… СЌС‚Р°РїРѕРІ.
        """
        file_handler = None
        orig_handlers = []
        orig_level = logger.level
        try:
            starts_log_dir = get_global('starter_path') / 'files' / 'logs' / 'starts'
            starts_log_dir.mkdir(parents=True, exist_ok=True)

            # РµСЃР»Рё РїРµСЂРµРґР°РЅ log_path вЂ“ РёСЃРїРѕР»СЊР·СѓРµРј РµРіРѕ, РёРЅР°С‡Рµ СЃРѕР·РґР°С‘Рј РЅРѕРІС‹Р№ РїРѕ РґР°С‚Рµ
            if log_path:
                log_file_path = Path(log_path)
            else:
                log_file_path = starts_log_dir / f"start_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

            # СЃРѕС…СЂР°РЅСЏРµРј С…СЌРЅРґР»РµСЂС‹
            orig_handlers = logger.handlers[:]
            orig_level = logger.level
            for h in orig_handlers:
                logger.removeHandler(h)

            # РЅРѕРІС‹Р№ С„Р°Р№Р»РѕРІС‹Р№ С…СЌРЅРґР»РµСЂ
            file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
            file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            logger.addHandler(file_handler)
            logger.setLevel(logging.DEBUG)
            logger.propagate = False

            logger.info(f"[run_compose] Logging output to {log_file_path}")
            
            logger.info(f"[run_compose] ===== START DOCKER COMPOSE =====")
            # ==================== РђР’РўРћР“Р•РќР•Р РђР¦РРЇ SSL РЎР•Р РўРР¤РРљРђРўРћР’ (Р§РРЎРўР«Р™ PYTHON) ====================
            logger.info("[run_compose] РџСЂРѕРІРµСЂРєР° Рё Р°РІС‚РѕРіРµРЅРµСЂР°С†РёСЏ SSL СЃРµСЂС‚РёС„РёРєР°С‚РѕРІ (РЅР° Python)...")
            certs_dir = get_global('docker_path') / "configs" / "nginx" / "certs"
            fullchain_path = certs_dir / "fullchain.pem"
            privkey_path = certs_dir / "privkey.pem"

            certs_dir.mkdir(parents=True, exist_ok=True)

            # Р“РµРЅРµСЂРёСЂСѓРµРј РўРћР›Р¬РљРћ РµСЃР»Рё СЃРµСЂС‚РёС„РёРєР°С‚РѕРІ РЅРµС‚
            if not fullchain_path.exists() or not privkey_path.exists():
                logger.info("[run_compose] РЎРµСЂС‚РёС„РёРєР°С‚С‹ РЅРµ РЅР°Р№РґРµРЅС‹ вЂ” СЃРѕР·РґР°С‘Рј СЃР°РјРѕРїРѕРґРїРёСЃР°РЅРЅС‹Рµ РЅР° Python...")

                try:
                    from cryptography import x509
                    from cryptography.x509.oid import NameOID
                    from cryptography.hazmat.primitives import hashes, serialization
                    from cryptography.hazmat.primitives.asymmetric import rsa
                    from datetime import datetime, timedelta

                    # РћРїСЂРµРґРµР»СЏРµРј РґРѕРјРµРЅ
                    domain = "client.local"
                    if get_global('docker_env_path').exists():
                        with open(get_global('docker_env_path'), 'r', encoding='utf-8') as f:
                            for line in f:
                                if line.startswith("NGINX_DOMAIN="):
                                    val = line.split("=", 1)[1].strip().strip('"\'')
                                    if val:
                                        domain = val
                                    break

                    logger.info(f"[run_compose] Р”РѕРјРµРЅ РґР»СЏ СЃРµСЂС‚РёС„РёРєР°С‚Р°: {domain}")

                    # Р“РµРЅРµСЂР°С†РёСЏ РєР»СЋС‡Р°
                    private_key = rsa.generate_private_key(
                        public_exponent=65537,
                        key_size=2048,
                    )

                    # РЎРѕР·РґР°РЅРёРµ СЃР°РјРѕРїРѕРґРїРёСЃР°РЅРЅРѕРіРѕ СЃРµСЂС‚РёС„РёРєР°С‚Р°
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
                        datetime.utcnow() + timedelta(days=3650)  # 10 Р»РµС‚
                    ).add_extension(
                        x509.SubjectAlternativeName([x509.DNSName(domain), x509.DNSName("localhost")]),
                        critical=False,
                    ).sign(private_key, hashes.SHA256())

                    # РЎРѕС…СЂР°РЅРµРЅРёРµ РїСЂРёРІР°С‚РЅРѕРіРѕ РєР»СЋС‡Р°
                    with open(privkey_path, "wb") as f:
                        f.write(private_key.private_bytes(
                            encoding=serialization.Encoding.PEM,
                            format=serialization.PrivateFormat.TraditionalOpenSSL,
                            encryption_algorithm=serialization.NoEncryption(),
                        ))

                    # РЎРѕС…СЂР°РЅРµРЅРёРµ СЃРµСЂС‚РёС„РёРєР°С‚Р° (fullchain = С‚РѕР»СЊРєРѕ СЃР°Рј СЃРµСЂС‚РёС„РёРєР°С‚, С‚.Рє. СЃР°РјРѕРїРѕРґРїРёСЃР°РЅРЅС‹Р№)
                    with open(fullchain_path, "wb") as f:
                        f.write(cert.public_bytes(serialization.Encoding.PEM))

                    logger.info("[run_compose] РЎР°РјРѕРїРѕРґРїРёСЃР°РЅРЅС‹Рµ СЃРµСЂС‚РёС„РёРєР°С‚С‹ СѓСЃРїРµС€РЅРѕ СЃРѕР·РґР°РЅС‹ (Python)!")
                    logger.info(f"[run_compose]   в†’ {fullchain_path}")
                    logger.info(f"[run_compose]   в†’ {privkey_path}")

                except ImportError:
                    logger.error("[run_compose] Р‘РёР±Р»РёРѕС‚РµРєР° 'cryptography' РЅРµ СѓСЃС‚Р°РЅРѕРІР»РµРЅР°!")
                    logger.error("[run_compose] РЈСЃС‚Р°РЅРѕРІРё РµС‘ РєРѕРјР°РЅРґРѕР№: pip install cryptography")
                    logger.error("[run_compose] HTTPS СЂР°Р±РѕС‚Р°С‚СЊ РЅРµ Р±СѓРґРµС‚, РЅРѕ РїСЂРѕРµРєС‚ Р·Р°РїСѓСЃС‚РёС‚СЃСЏ РЅР° HTTP")
                except Exception as e:
                    logger.error(f"[run_compose] РћС€РёР±РєР° РїСЂРё РіРµРЅРµСЂР°С†РёРё СЃРµСЂС‚РёС„РёРєР°С‚РѕРІ РЅР° Python: {e}")
                    logger.error("[run_compose] HTTPS Р±СѓРґРµС‚ РЅРµРґРѕСЃС‚СѓРїРµРЅ")
            else:
                logger.info("[run_compose] РЎРµСЂС‚РёС„РёРєР°С‚С‹ СѓР¶Рµ СЃСѓС‰РµСЃС‚РІСѓСЋС‚ вЂ” РёСЃРїРѕР»СЊР·СѓРµРј РёС…")
            # =========================================================================
            logger.info(f"[run_compose] Docker path: {get_global('docker_path')}")
            logger.info(f"[run_compose] Absolute path: {get_global('docker_path').absolute()}")
            logger.info(f"[run_compose] Compose file exists: {get_global('docker_compose_path').exists()}")

            # РџРѕР»СѓС‡Р°РµРј env_vars РёР· С‚РµРєСѓС‰РµРіРѕ .env С„Р°Р№Р»Р°
            logger.info("[run_compose] Loading environment variables from .env...")
            env_vars = get('docker','ensure_docker_env', log_file_path)
            
            # Р“РµРЅРµСЂР°С†РёСЏ compose С„Р°Р№Р»Р°
            logger.info("[run_compose] Generating docker-compose.yml from .env...")
            if not get('docker','generate_docker_compose',env_vars, log_file_path):
                logger.error("[run_compose] Failed to generate docker-compose.yml")
                return False

            # РџСЂРѕРІРµСЂСЏРµРј С‡С‚Рѕ compose С„Р°Р№Р» СЃРѕР·РґР°Р»СЃСЏ
            if get_global('docker_compose_path').exists():
                compose_size = get_global('docker_compose_path').stat().st_size
                logger.info(f"[run_compose] Compose file generated: {compose_size} bytes")
                
                # Р’С‹РІРѕРґРёРј РїРµСЂРІС‹Рµ РЅРµСЃРєРѕР»СЊРєРѕ СЃС‚СЂРѕРє РґР»СЏ РѕС‚Р»Р°РґРєРё
                try:
                    with open(get_global('docker_compose_path'), 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        logger.info(f"[run_compose] First 20 lines of docker-compose.yml:")
                        for i, line in enumerate(lines[:20], 1):
                            logger.info(f"[run_compose]   {i}: {line.rstrip()}")
                except Exception as e:
                    logger.warning(f"[run_compose] Could not read compose file: {e}")
            else:
                logger.error("[run_compose] Compose file was not generated!")
                return False

            # РћРїСЂРµРґРµР»СЏРµРј РєРѕРјР°РЅРґСѓ docker compose
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

            # РџСЂРѕРІРµСЂСЏРµРј РґРѕСЃС‚СѓРїРЅРѕСЃС‚СЊ Docker
            logger.info("[run_compose] Checking Docker availability...")
            try:
                docker_info = subprocess.run(["docker", "info"], capture_output=True, text=True, check=False)
                if docker_info.returncode != 0:
                    logger.error(f"[run_compose] Docker is not available: {docker_info.stderr}")
                    
                    # РџСЂРѕР±СѓРµРј Р·Р°РїСѓСЃС‚РёС‚СЊ Docker
                    logger.info("[run_compose] Trying to start Docker...")
                    if platform.system() == 'Windows':
                        start_result = subprocess.run(['net', 'start', 'docker'], capture_output=True, text=True,check=False)
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

            # РСЃРїРѕР»СЊР·СѓРµРј sudo, РµСЃР»Рё РЅСѓР¶РЅРѕ
            use_sudo = get_global("use_sudo")
            if use_sudo and not Path("/.dockerenv").exists():
                compose_cmd.insert(0, "sudo")
                logger.info("[run_compose] Using sudo for docker commands")

            # -------------------------------
            # 1. РћС‡РёС‰Р°РµРј СЃС‚Р°СЂС‹Рµ РєРѕРЅС‚РµР№РЅРµСЂС‹ Рё СЃРµС‚Рё
            # -------------------------------
            logger.info("[run_compose] Cleaning up old containers...")
            down_cmd = compose_cmd + ["-f", str(get_global('docker_compose_path')), "down", "--remove-orphans"]
            logger.info(f"[run_compose] Running: {' '.join(down_cmd)}")
            logger.info(f"[run_compose] Working directory: {get_global('docker_path')}")
            
            try:
                down_process = subprocess.run(
                    down_cmd, 
                    cwd=str(get_global('docker_path')), 
                    capture_output=True,
                    text=True,
                    check=False
                )
                
                # Р›РѕРіРёСЂСѓРµРј СЂРµР·СѓР»СЊС‚Р°С‚
                logger.info(f"[run_compose] docker compose down completed with code: {down_process.returncode}")
                
                if down_process.stdout and down_process.stdout.strip():
                    for line in down_process.stdout.strip().split('\n'):
                        if line.strip():
                            logger.info(f"[compose_down] {line.strip()}")
                
                if down_process.stderr and down_process.stderr.strip():
                    for line in down_process.stderr.strip().split('\n'):
                        if line.strip():
                            logger.warning(f"[compose_down_err] {line.strip()}")
                
                # РћР±СЂР°Р±Р°С‚С‹РІР°РµРј РІРѕР·РјРѕР¶РЅС‹Рµ РѕС€РёР±РєРё
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
            # 2. РџРѕР»СѓС‡Р°РµРј СЃРїРёСЃРѕРє РѕР±СЂР°Р·РѕРІ РёР· docker-compose
            # -------------------------------
            try:
                logger.info("[run_compose] Checking existing images...")
                images_result = subprocess.run(
                    compose_cmd + ["-f", str(get_global('docker_compose_path')), "images", "-q"],
                    cwd=str(get_global('docker_path')), 
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
            # 3. Р—Р°РїСѓСЃРє docker-compose СЃ Р±РёР»РґРѕРј
            # -------------------------------
            logger.info("[run_compose] Building Docker images...")
            #build_cmd = compose_cmd + ["-f", str(get_global('docker_compose_path')), "build", "--no-cache", "--pull"]
            build_cmd = compose_cmd + ["-f", str(get_global('docker_compose_path')), "build"]
            logger.info(f"[run_compose] Build command: {' '.join(build_cmd)}")
            
            try:
                build_process = subprocess.Popen(
                    build_cmd,
                    cwd=str(get_global('docker_path')),
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
            # 4. Р—Р°РїСѓСЃРє docker-compose РІ detached mode
            # -------------------------------
            logger.info("[run_compose] Starting docker-compose services...")
            up_cmd = compose_cmd + ["-f", str(get_global('docker_compose_path')), "up", "-d", "--force-recreate"]
            logger.info(f"[run_compose] Up command: {' '.join(up_cmd)}")
            
            try:
                up_process = subprocess.Popen(
                    up_cmd,
                    cwd=str(get_global('docker_path')),
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
                    
                    # РџРѕРєР°Р·С‹РІР°РµРј Р»РѕРіРё РєРѕРЅС‚РµР№РЅРµСЂРѕРІ РїСЂРё РѕС€РёР±РєРµ
                    try:
                        logger.info("[run_compose] Checking container logs for errors...")
                        ps_cmd = compose_cmd + ["-f", str(get_global('docker_compose_path')), "ps", "-q"]
                        ps_result = subprocess.run(
                            ps_cmd, 
                            cwd=str(get_global('docker_path')), 
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
            # 5. РџСЂРѕРІРµСЂСЏРµРј СЃС‚Р°С‚СѓСЃ СЃРµСЂРІРёСЃРѕРІ
            # -------------------------------
            logger.info("[run_compose] Checking service status...")
            time.sleep(2)
            
            try:
                ps_cmd = compose_cmd + ["-f", str(get_global('docker_compose_path')), "ps", "--all"]
                ps_result = subprocess.run(
                    ps_cmd, 
                    cwd=str(get_global('docker_path')), 
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
            # 6. РџРѕРєР°Р·С‹РІР°РµРј Р»РѕРіРё Р·Р°РїСѓСЃРєР°
            # -------------------------------
            logger.info("[run_compose] Showing startup logs (last 20 lines)...")
            try:
                logs_cmd = compose_cmd + ["-f", str(get_global('docker_compose_path')), "logs", "--tail", "20"]
                logs_process = subprocess.Popen(
                    logs_cmd,
                    cwd=str(get_global('docker_path')),
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
        Р’РѕСЃСЃС‚Р°РЅР°РІР»РёРІР°РµС‚ РїСЂР°РІР° РЅР° РІС‹РїРѕР»РЅРµРЅРёРµ РґР»СЏ РІСЃРµС… СЃРєСЂРёРїС‚РѕРІ Рё РёСЃРїРѕР»РЅСЏРµРјС‹С… С„Р°Р№Р»РѕРІ
        """
        result = {'status': 'success', 'fixed_files': [], 'errors': []}
        
        # РџРѕР»СѓС‡Р°РµРј РЅР°СЃС‚СЂРѕР№РєСѓ use_sudo РёР· РіР»РѕР±Р°Р»СЊРЅС‹С… РїРµСЂРµРјРµРЅРЅС‹С…
        use_sudo = get_global("use_sudo", False)
        
        # РџСЂРѕРІРµСЂСЏРµРј, СѓСЃС‚Р°РЅРѕРІР»РµРЅ Р»Рё sudo РµСЃР»Рё РѕРЅ РЅСѓР¶РµРЅ
        if use_sudo:
            try:
                # РџСЂРѕРІРµСЂСЏРµРј РґРѕСЃС‚СѓРїРЅРѕСЃС‚СЊ sudo
                subprocess.run(['sudo', '--version'], capture_output=True, check=True)
                sudo_available = True
            except (subprocess.CalledProcessError, FileNotFoundError):
                sudo_available = False
                logger.warning("sudo requested but not available, continuing without sudo")
                use_sudo = False
        else:
            sudo_available = False

        # РџР°С‚С‚РµСЂРЅС‹ РґР»СЏ РѕРїСЂРµРґРµР»РµРЅРёСЏ РёСЃРїРѕР»РЅСЏРµРјС‹С… С„Р°Р№Р»РѕРІ
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
            logger.info(f"Р’РѕСЃСЃС‚Р°РЅРѕРІР»РµРЅРёРµ РїСЂР°РІ РЅР° РёСЃРїРѕР»РЅСЏРµРјС‹Рµ С„Р°Р№Р»С‹ (use_sudo={use_sudo})...")
            
            fixed_count = 0
            for root, dirs, files in os.walk(project_path):
                for file in files:
                    file_path = Path(root) / file
                    rel_path = file_path.relative_to(project_path)
                    rel_path_str = str(rel_path).replace('\\', '/')
                    file_lower = file.lower()
                    
                    # РџСЂРѕРІРµСЂСЏРµРј РєСЂРёС‚РµСЂРёРё РґР»СЏ РёСЃРїРѕР»РЅСЏРµРјРѕРіРѕ С„Р°Р№Р»Р°
                    is_executable = (
                        file_path.suffix.lower() in executable_extensions or
                        any(name in file_lower for name in executable_names) or
                        any(script_dir in rel_path_str for script_dir in script_directories)
                    )
                    
                    if is_executable:
                        try:
                            # РџСЂРѕРІРµСЂСЏРµРј С‚РµРєСѓС‰РёРµ РїСЂР°РІР°
                            current_mode = file_path.stat().st_mode
                            is_currently_executable = bool(current_mode & 0o111)
                            
                            if not is_currently_executable:
                                # РЈСЃС‚Р°РЅР°РІР»РёРІР°РµРј РїСЂР°РІР° РЅР° РІС‹РїРѕР»РЅРµРЅРёРµ
                                if use_sudo and sudo_available:
                                    # РСЃРїРѕР»СЊР·СѓРµРј sudo РµСЃР»Рё РЅСѓР¶РЅРѕ Рё РґРѕСЃС‚СѓРїРµРЅ
                                    subprocess.run(
                                        ['sudo', 'chmod', '+x', str(file_path)], 
                                        check=True, 
                                        capture_output=True
                                    )
                                else:
                                    # Р‘РµР· sudo РёР»Рё РµСЃР»Рё sudo РЅРµРґРѕСЃС‚СѓРїРµРЅ
                                    new_mode = current_mode | 0o111
                                    file_path.chmod(new_mode)
                                
                                result['fixed_files'].append(rel_path_str)
                                fixed_count += 1
                                logger.debug(f"РЈСЃС‚Р°РЅРѕРІР»РµРЅС‹ РїСЂР°РІР° РЅР° РІС‹РїРѕР»РЅРµРЅРёРµ: {rel_path_str}")
                                
                        except Exception as e:
                            error_msg = f"РќРµ СѓРґР°Р»РѕСЃСЊ СѓСЃС‚Р°РЅРѕРІРёС‚СЊ РїСЂР°РІР° РґР»СЏ {rel_path_str}: {e}"
                            result['errors'].append(error_msg)
                            logger.warning(error_msg)
            
            logger.info(f"Р’РѕСЃСЃС‚Р°РЅРѕРІР»РµРЅС‹ РїСЂР°РІР° РґР»СЏ {fixed_count} С„Р°Р№Р»РѕРІ")
            if result['errors']:
                result['status'] = 'warning'
                result['message'] = f"Р’РѕСЃСЃС‚Р°РЅРѕРІР»РµРЅС‹ РїСЂР°РІР° РґР»СЏ {fixed_count} С„Р°Р№Р»РѕРІ, РЅРѕ Р±С‹Р»Рё РѕС€РёР±РєРё"
            else:
                result['message'] = f"Р’РѕСЃСЃС‚Р°РЅРѕРІР»РµРЅС‹ РїСЂР°РІР° РґР»СЏ {fixed_count} С„Р°Р№Р»РѕРІ"
                
        except Exception as e:
            error_msg = f"РћС€РёР±РєР° РїСЂРё РІРѕСЃСЃС‚Р°РЅРѕРІР»РµРЅРёРё РїСЂР°РІ: {e}"
            result['status'] = 'error'
            result['message'] = error_msg
            result['errors'].append(error_msg)
            logger.error(error_msg)
        
        return result

    @staticmethod
    def get_container_mounts(container_name: str) -> dict:
        """
        Р’РѕР·РІСЂР°С‰Р°РµС‚ СЃР»РѕРІР°СЂСЊ РјРѕРЅС‚РёСЂРѕРІР°РЅРёР№ РєРѕРЅС‚РµР№РЅРµСЂР°:
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
        Р’РѕР·РІСЂР°С‰Р°РµС‚ РёРјСЏ РєРѕРЅС‚РµР№РЅРµСЂР° СЃР°РјРѕРіРѕ Р¶Рµ СЃРµР±СЏ РіРґРµ Р·Р°РїСѓС‰РµРЅ
        """
        cgroup_path = "/proc/self/cgroup"
        if os.path.exists(cgroup_path):
            with open(cgroup_path) as f:
                for line in f:
                    # РёС‰РµРј docker/<container_id> (РѕР±С‹С‡РЅРѕ)
                    parts = line.strip().split('/')
                    if 'docker' in parts:
                        container_id = parts[-1]
                        # docker inspect РґР»СЏ РёРјРµРЅРё
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
    # РџСЂРѕРІРµСЂРєР° Р·Р°РїСѓСЃРєР° РїСЂРѕРµРєС‚Р°
    # ---------------------------
    @staticmethod
    def is_project_running(project_name: str) -> bool:
        from files.core.utils.loader_utils import get
        containers = get('docker', 'get_containers', all=True) or []
        project_container_name = f"php-{project_name}"
        return any(c['name'] == project_container_name and 'running' in c['status'].lower() for c in containers)

    # ---------------------------
    # Р“РµРЅРµСЂР°С†РёСЏ docker-compose (РЅРёР·РєРѕСѓСЂРѕРІРЅРµРІР°СЏ Рё РІС‹СЃРѕРєРѕСѓСЂРѕРІРЅРµРІР°СЏ)
    # ---------------------------
    @staticmethod
    def generate_docker_compose(env_vars: Dict[str, str] = None, log_path: Optional[Path] = None) -> bool:
        try:
            docker_path = Path(get_global("docker_path"))
            docker_path.mkdir(parents=True, exist_ok=True)

            if env_vars is None:
                env_vars = get('docker','ensure_docker_env', log_path)

            # РџРѕР»СѓС‡Р°РµРј PULL_FROM_REGISTRY РёР· env_vars
            pull_from_registry = env_vars.get("PULL_FROM_REGISTRY", "false").lower() == "true"

            if not get('docker','generate_compose',env_vars, pull_from_registry=pull_from_registry, log_path=log_path):
                return False

            return True
        except Exception as e:
            if log_path:
                with open(log_path, 'a', encoding='utf-8') as log_file:
                    log_file.write(f"[generate_docker_compose] Error: {str(e)}\n")
            logger.error(f"Error generating docker-compose: {e}")
            return False

    @staticmethod
    def generate_compose(env_vars: Dict[str, str], pull_from_registry: bool = False, log_path: Optional[Path] = None) -> bool:
        """
        Р“РµРЅРµСЂРёСЂСѓРµС‚ docker-compose.yml РЅР° РѕСЃРЅРѕРІРµ С€Р°Р±Р»РѕРЅР° Рё РїРµСЂРµРјРµРЅРЅС‹С….
        РЈРЅРёРІРµСЂСЃР°Р»СЊРЅР°СЏ РІРµСЂСЃРёСЏ РґР»СЏ РІСЃРµС… РїР»Р°С‚С„РѕСЂРј.
        """
        try:
            if log_path:
                with open(log_path, 'a', encoding='utf-8') as log_file:
                    log_file.write(f"[generate_compose] Starting with env_vars: {list(env_vars.keys())}\n")
                    for k, v in env_vars.items():
                        if 'PASSWORD' in k or 'SECRET' in k:
                            log_file.write(f"  {k}=[HIDDEN]\n")
                        else:
                            log_file.write(f"  {k}={v}\n")

            if not get_global('docker_compose_example_path').exists():
                if log_path:
                    with open(log_path, 'a', encoding='utf-8') as log_file:
                        log_file.write(f"[generate_compose] Compose template not found: {get_global('docker_compose_example_path')}\n")
                logger.error(f"[generate_compose] Compose template not found: {get_global('docker_compose_example_path')}")
                return False

            content = get_global('docker_compose_example_path').read_text(encoding='utf-8')
            
            if log_path:
                with open(log_path, 'a', encoding='utf-8') as log_file:
                    log_file.write(f"[generate_compose] Read compose template ({get_global('docker_compose_example_path')}): {len(content)} chars\n")

            if pull_from_registry:
                content = get('docker','remove_build_sections',content)
                if log_path:
                    with open(log_path, 'a', encoding='utf-8') as log_file:
                        log_file.write("[generate_compose] Removed build sections (pull_from_registry=True)\n")

            # Р—Р°РјРµРЅСЏРµРј РїРµСЂРµРјРµРЅРЅС‹Рµ РѕРєСЂСѓР¶РµРЅРёСЏ РІРЅРµ Р±Р»РѕРєРѕРІ
            content = get('docker','replace_env_variables',content, env_vars)
            
            if log_path:
                with open(log_path, 'a', encoding='utf-8') as log_file:
                    log_file.write("[generate_compose] After env substitution\n")

            # РЈР±РµРґРёРјСЃСЏ, С‡С‚Рѕ РїР°РїРєР° СЃСѓС‰РµСЃС‚РІСѓРµС‚
            get_global('docker_compose_path').parent.mkdir(parents=True, exist_ok=True)

            # РЎРѕС…СЂР°РЅСЏРµРј С„Р°Р№Р»
            get_global('docker_compose_path').write_text(content, encoding='utf-8')
            
            if log_path:
                with open(log_path, 'a', encoding='utf-8') as log_file:
                    log_file.write(f"[generate_compose] docker-compose.yml generated at {get_global('docker_compose_path')}\n")
                    # Р›РѕРіРёСЂСѓРµРј РїРµСЂРІС‹Рµ РЅРµСЃРєРѕР»СЊРєРѕ СЃС‚СЂРѕРє РґР»СЏ РїСЂРѕРІРµСЂРєРё
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
    # ENV: РїР°СЂСЃРёРЅРі, РіРµРЅРµСЂР°С†РёСЏ Рё СЂР°Р±РѕС‚Р° СЃ .env
    # ---------------------------

    @staticmethod
    def parse_env_content(content: str) -> Tuple[Dict[str, str], List[Union[str, Tuple[str, str]]]]:
        """
        РџР°СЂСЃРёС‚ .env (РёР»Рё .env.example) Рё РІРѕР·РІСЂР°С‰Р°РµС‚ (variables_dict, template_lines)
        template_lines вЂ” СЃРїРёСЃРѕРє СЃС‚СЂРѕРє Рё (key, original_line) РґР»СЏ СЃРѕС…СЂР°РЅРµРЅРёСЏ СЃС‚СЂСѓРєС‚СѓСЂС‹.
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
    def generate_env_content(vars_dict: Dict[str, str], template_lines: List[Union[str, Tuple[str, str]]],log_path: Optional[Path] = None) -> str:
        """
        Р“РµРЅРµСЂРёСЂСѓРµС‚ СЃРѕРґРµСЂР¶РёРјРѕРµ .env С„Р°Р№Р»Р° РЅР° РѕСЃРЅРѕРІРµ С€Р°Р±Р»РѕРЅР° Рё РїРµСЂРµРјРµРЅРЅС‹С….
        Р”РѕР±Р°РІР»РµРЅРѕ Р»РѕРіРёСЂРѕРІР°РЅРёРµ РґР»СЏ РѕС‚СЃР»РµР¶РёРІР°РЅРёСЏ РёР·РјРµРЅРµРЅРёР№ РїРµСЂРµРјРµРЅРЅС‹С….
        """
        result: List[str] = []
        template_keys: List[str] = []
        vars_copy = dict(vars_dict)

        # Р›РѕРіРёСЂРѕРІР°РЅРёРµ РµСЃР»Рё СѓРєР°Р·Р°РЅ РїСѓС‚СЊ
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
                    
                    # Р›РѕРіРёСЂРѕРІР°РЅРёРµ РїРѕРґСЃС‚Р°РЅРѕРІРєРё
                    if log_path:
                        with open(log_path, 'a', encoding='utf-8') as log_file:
                            log_file.write(f"[generate_env_content] Substituted: {key}={value}\n")
                else:
                    result.append(original_line)
            else:
                result.append(line)

        # Р”РѕР±Р°РІР»СЏРµРј РѕСЃС‚Р°РІС€РёРµСЃСЏ РєР°СЃС‚РѕРјРЅС‹Рµ РїРµСЂРµРјРµРЅРЅС‹Рµ
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
    def ensure_docker_env(log_path: Optional[Path] = None) -> Dict[str, str]:
        """
        РЎРѕР·РґР°С‘С‚/РѕР±РЅРѕРІР»СЏРµС‚ .env РІ project_path РЅР° РѕСЃРЅРѕРІРµ .env.example.
        """
        def log(msg: str):
            print(msg)
            logger.info(msg)

        # РРЎРџР РђР’Р›Р•РќРћ: РёСЃРїРѕР»СЊР·СѓРµРј docker_path РёР· РіР»РѕР±Р°Р»СЊРЅС‹С… РїРµСЂРµРјРµРЅРЅС‹С…
        docker_path = get_global('docker_path')
        if not docker_path:
            log("   вќЊ docker_path РЅРµ СѓСЃС‚Р°РЅРѕРІР»РµРЅ РІ РіР»РѕР±Р°Р»СЊРЅС‹С… РїРµСЂРµРјРµРЅРЅС‹С…!")
            if log_path:
                with open(log_path, 'a', encoding='utf-8') as log_file:
                    log_file.write("[ensure_docker_env] ERROR: docker_path not set in globals\n")
            return {}
        
        docker_env_example_path = docker_path / ".env.example"
        docker_env_path = docker_path / ".env"

        log("")
        log(f"   рџ“‚ ensure_docker_env()")
        log(f"      рџ“„ docker_env_example_path: {docker_env_example_path}")
        log(f"      рџ“„ docker_env_path: {docker_env_path}")

        if log_path:
            with open(log_path, 'a', encoding='utf-8') as log_file:
                log_file.write(f"[ensure_docker_env] Starting...\n")
                log_file.write(f"  docker_path: {docker_path}\n")
                log_file.write(f"  docker_env_example_path: {docker_env_example_path}\n")
                log_file.write(f"  docker_env_path: {docker_env_path}\n")

        if not docker_env_example_path.exists():
            log(f"      вљ пёЏ  .env.example РќР• РќРђР™Р”Р•Рќ: {docker_env_example_path}")
            if log_path:
                with open(log_path, 'a', encoding='utf-8') as log_file:
                    log_file.write("[ensure_docker_env] ERROR: .env.example not found\n")
            return {}
        else:
            log(f"      вњ… .env.example РЅР°Р№РґРµРЅ")

        # РџР°СЂСЃРёРј .env.example
        try:
            example_content = docker_env_example_path.read_text(encoding='utf-8')
            example_vars, example_lines = get('docker','parse_env_content', example_content)
            log(f"      рџ“‹ РџРµСЂРµРјРµРЅРЅС‹С… РІ .env.example: {len(example_vars)}")
            
            if log_path:
                with open(log_path, 'a', encoding='utf-8') as log_file:
                    log_file.write(f"[ensure_docker_env] Example variables: {list(example_vars.keys())}\n")
                    for k, v in example_vars.items():
                        log_file.write(f"  {k}={v}\n")
        except Exception as e:
            log(f"      вќЊ РћС€РёР±РєР° РїР°СЂСЃРёРЅРіР° .env.example: {e}")
            if log_path:
                with open(log_path, 'a', encoding='utf-8') as log_file:
                    log_file.write(f"[ensure_docker_env] Error parsing .env.example: {e}\n")
            return {}

        # Р§РёС‚Р°РµРј С‚РµРєСѓС‰РёР№ .env РµСЃР»Рё РµСЃС‚СЊ
        current_vars = {}
        if docker_env_path.exists():
            log(f"      вњ… .env РЅР°Р№РґРµРЅ, С‡РёС‚Р°РµРј С‚РµРєСѓС‰РёРµ РїРµСЂРµРјРµРЅРЅС‹Рµ...")
            if log_path:
                with open(log_path, 'a', encoding='utf-8') as log_file:
                    log_file.write("[ensure_docker_env] Existing .env found, reading...\n")
            
            try:
                current_content = docker_env_path.read_text(encoding='utf-8')
                current_vars, _ = get('docker','parse_env_content', current_content)
                log(f"      рџ“‹ РўРµРєСѓС‰РёС… РїРµСЂРµРјРµРЅРЅС‹С… РІ .env: {len(current_vars)}")
                
                if log_path:
                    with open(log_path, 'a', encoding='utf-8') as log_file:
                        log_file.write(f"[ensure_docker_env] Current variables: {list(current_vars.keys())}\n")
                        for k, v in current_vars.items():
                            log_file.write(f"  {k}={v}\n")
            except Exception as e:
                log(f"      вќЊ РћС€РёР±РєР° С‡С‚РµРЅРёСЏ .env: {e}")
                if log_path:
                    with open(log_path, 'a', encoding='utf-8') as log_file:
                        log_file.write(f"[ensure_docker_env] Error reading .env: {e}\n")
                current_vars = {}
        else:
            log(f"      вљ пёЏ  .env РЅРµ РЅР°Р№РґРµРЅ, Р±СѓРґРµС‚ СЃРѕР·РґР°РЅ РЅРѕРІС‹Р№")
            if log_path:
                with open(log_path, 'a', encoding='utf-8') as log_file:
                    log_file.write("[ensure_docker_env] No existing .env found, will create new\n")

        # РћР±СЉРµРґРёРЅСЏРµРј РїРµСЂРµРјРµРЅРЅС‹Рµ (С‚РµРєСѓС‰РёРµ РёРјРµСЋС‚ РїСЂРёРѕСЂРёС‚РµС‚)
        merged_vars = current_vars.copy()
        for key, value in example_vars.items():
            if key not in merged_vars:
                merged_vars[key] = value

        if log_path:
            with open(log_path, 'a', encoding='utf-8') as log_file:
                log_file.write(f"[ensure_docker_env] Merged variables: {list(merged_vars.keys())}\n")
                for k, v in merged_vars.items():
                    log_file.write(f"  {k}={v}\n")

        # Р“РµРЅРµСЂРёСЂСѓРµРј Рё СЃРѕС…СЂР°РЅСЏРµРј
        try:
            content = get('docker','generate_env_content', merged_vars, example_lines, log_path)
            log(f"      рџ’ѕ Р—Р°РїРёСЃСЊ РІ: {docker_env_path}")
            
            if log_path:
                with open(log_path, 'a', encoding='utf-8') as log_file:
                    log_file.write(f"[ensure_docker_env] Generated content:\n{content}\n")
            
            docker_env_path.write_text(content, encoding='utf-8')
            log(f"      вњ… .env Р·Р°РїРёСЃР°РЅ ({len(content)} СЃРёРјРІРѕР»РѕРІ)")
            
            if log_path:
                with open(log_path, 'a', encoding='utf-8') as log_file:
                    log_file.write(f"[ensure_docker_env] Successfully wrote .env ({len(content)} bytes)\n")
                    log_file.write("[ensure_docker_env] Final .env content:\n")
                    for line in content.split('\n'):
                        if line and '=' in line:
                            k = line.split('=', 1)[0]
                            if 'PASSWORD' in k or 'SECRET' in k or 'KEY' in k:
                                log_file.write(f"  {k}=[HIDDEN]\n")
                            else:
                                log_file.write(f"  {line}\n")
                        else:
                            log_file.write(f"  {line}\n")
        except Exception as e:
            log(f"      вќЊ РћС€РёР±РєР° Р·Р°РїРёСЃРё .env: {e}")
            if log_path:
                with open(log_path, 'a', encoding='utf-8') as log_file:
                    log_file.write(f"[ensure_docker_env] Error writing .env: {e}\n")
            return {}

        return merged_vars

    @staticmethod
    def read_docker_env() -> Dict[str, str]:
        """
        Р§РёС‚Р°РµС‚ docker/.env Рё РІРѕР·РІСЂР°С‰Р°РµС‚ СЃР»РѕРІР°СЂСЊ РїРµСЂРµРјРµРЅРЅС‹С….
        """
        # РРЎРџР РђР’Р›Р•РќРћ: РёСЃРїРѕР»СЊР·СѓРµРј docker_path РёР· РіР»РѕР±Р°Р»СЊРЅС‹С… РїРµСЂРµРјРµРЅРЅС‹С…
        docker_path = get_global('docker_path')
        if not docker_path:
            return {}
        
        docker_env_path = docker_path / ".env"

        def log(msg: str):
            print(msg)
            logger.info(msg)

        if not docker_env_path.exists():
            log(f"      вљ пёЏ  Р¤Р°Р№Р» РќР• РќРђР™Р”Р•Рќ: {docker_env_path}")
            return {}

        log(f"      рџ“– Р§С‚РµРЅРёРµ: {docker_env_path}")
        try:
            with open(docker_env_path, 'r', encoding='utf-8') as f:
                content = f.read()
            vars_dict, _ = DockerModule.parse_env_content(content)
            log(f"      рџ“‹ РџСЂРѕС‡РёС‚Р°РЅРѕ РїРµСЂРµРјРµРЅРЅС‹С…: {len(vars_dict)}")
            return vars_dict
        except Exception as e:
            log(f"      вќЊ РћС€РёР±РєР° С‡С‚РµРЅРёСЏ: {e}")
            return {}

    @staticmethod
    def process_port_plus_variables(base_port: int):
        """
        РћРїС†РёРѕРЅР°Р»СЊРЅРѕ РѕР±СЂР°Р±Р°С‚С‹РІР°РµС‚ PORT_*_PLUS РїРµСЂРµРјРµРЅРЅС‹Рµ РёР· ./docker/.env.example
        Р•СЃР»Рё РїРµСЂРµРјРµРЅРЅС‹С… РЅРµС‚ - РїСЂРѕСЃС‚Рѕ РїСЂРѕРїСѓСЃРєР°РµС‚
        """
        docker_path = get_global('docker_path')
        if not docker_path:
            print("   вќЊ docker_path РЅРµ СѓСЃС‚Р°РЅРѕРІР»РµРЅ РІ РіР»РѕР±Р°Р»СЊРЅС‹С… РїРµСЂРµРјРµРЅРЅС‹С…!")
            return
        
        env_example_path = docker_path / ".env.example"
        env_output_path = docker_path / ".env"
        
        if not env_example_path.exists():
            print(f"   в„№пёЏ Р¤Р°Р№Р» .env.example РЅРµ РЅР°Р№РґРµРЅ, РїСЂРѕРїСѓСЃРєР°РµРј РѕР±СЂР°Р±РѕС‚РєСѓ PORT_*_PLUS")
            return
        
        # Р§РёС‚Р°РµРј .env.example
        with open(env_example_path, 'r', encoding='utf-8') as f:
            example_lines = f.readlines()
        
        # РС‰РµРј PORT_*_PLUS РїРµСЂРµРјРµРЅРЅС‹Рµ
        new_port_vars = {}
        plus_count = 0
        
        for line in example_lines:
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue
            if '=' in stripped:
                key, raw_val = stripped.split('=', 1)
                key = key.strip()
                if key.endswith('_PLUS'):
                    try:
                        plus_value = int(raw_val.strip())
                        base_name = key[:-5]  # СѓРґР°Р»СЏРµРј '_PLUS'
                        computed_port = base_port + plus_value
                        new_port_vars[base_name] = str(computed_port)
                        plus_count += 1
                        print(f"         рџ“Љ {key}={plus_value} в†’ {base_name}={computed_port}")
                    except ValueError:
                        print(f"         вљ пёЏ {key}={raw_val} вЂ” РЅРµРєРѕСЂСЂРµРєС‚РЅРѕРµ Р·РЅР°С‡РµРЅРёРµ, РїСЂРѕРїСѓСЃРєР°РµРј")
                        continue
        
        # Р•СЃР»Рё РµСЃС‚СЊ PORT_*_PLUS - РѕР±РЅРѕРІР»СЏРµРј .env
        if plus_count > 0:
            # Р§РёС‚Р°РµРј С‚РµРєСѓС‰РёР№ .env
            current_vars = {}
            if env_output_path.exists():
                with open(env_output_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        stripped = line.strip()
                        if '=' in stripped and not stripped.startswith('#'):
                            k, v = stripped.split('=', 1)
                            current_vars[k.strip()] = v.strip()
            
            # РћР±РЅРѕРІР»СЏРµРј РїРѕСЂС‚С‹
            current_vars.update(new_port_vars)
            
            # Р—Р°РїРёСЃС‹РІР°РµРј
            with open(env_output_path, 'w', encoding='utf-8') as f:
                for k, v in current_vars.items():
                    f.write(f"{k}={v}\n")
            
            print(f"      вњ… Р”РѕР±Р°РІР»РµРЅРѕ {plus_count} PORT_* РїРµСЂРµРјРµРЅРЅС‹С… (Р±Р°Р·РѕРІС‹Р№ РїРѕСЂС‚ {base_port})")
        else:
            print(f"      в„№пёЏ РќРµС‚ PORT_*_PLUS РїРµСЂРµРјРµРЅРЅС‹С… РІ .env.example, РїСЂРѕРїСѓСЃРєР°РµРј")

    @staticmethod
    def allocate_network_and_ports() -> Dict[str, Any]:
        """
        РџРѕР»РЅРѕСЃС‚СЊСЋ Р°РІС‚РѕРЅРѕРјРЅР°СЏ С„СѓРЅРєС†РёСЏ РґР»СЏ РІС‹РґРµР»РµРЅРёСЏ СЃРµС‚Рё Рё РїРѕСЂС‚РѕРІ.
        """
        import traceback
        
        def log(msg: str, level: str = "INFO"):
            """Р’С‹РІРѕРґРёС‚ СЃРѕРѕР±С‰РµРЅРёРµ СЃ СѓСЂРѕРІРЅРµРј"""
            prefix = {
                "INFO": "в„№пёЏ",
                "SUCCESS": "вњ…",
                "WARNING": "вљ пёЏ",
                "ERROR": "вќЊ",
                "DEBUG": "рџ”Ќ"
            }.get(level, "рџ“Њ")
            print(f"{prefix} {msg}")
            if level == "ERROR":
                logger.error(msg)
            elif level == "WARNING":
                logger.warning(msg)
            else:
                logger.info(msg)

        log("=" * 80)
        log("рџЊђ РќРђР§РђР›Рћ Р’Р«Р”Р•Р›Р•РќРРЇ РЎР•РўР Р РџРћР РўРћР’", "INFO")
        log("=" * 80)

        # ========== Р”РРђР“РќРћРЎРўРРљРђ: С‡С‚Рѕ Сѓ РЅР°СЃ РµСЃС‚СЊ ==========
        log("", "INFO")
        log("рџ“‹ Р”РРђР“РќРћРЎРўРРљРђ РРЎРҐРћР”РќР«РҐ Р”РђРќРќР«РҐ", "INFO")
        log("-" * 60, "INFO")
        
        # РџСЂРѕРІРµСЂСЏРµРј РіР»РѕР±Р°Р»СЊРЅС‹Рµ РїРµСЂРµРјРµРЅРЅС‹Рµ
        starter_path = get_global('starter_path')
        project_path = get_global('project_path')
        docker_path = get_global('docker_path')
        
        log(f"starter_path: {starter_path}", "DEBUG")
        log(f"project_path: {project_path}", "DEBUG")
        log(f"docker_path: {docker_path}", "DEBUG")
        
        # РџСЂРѕРІРµСЂСЏРµРј РЅР°Р»РёС‡РёРµ С„Р°Р№Р»РѕРІ
        env_example = docker_path / ".env.example" if docker_path else None
        env_file = docker_path / ".env" if docker_path else None
        
        log(f".env.example СЃСѓС‰РµСЃС‚РІСѓРµС‚: {env_example.exists() if env_example else 'N/A'}", "DEBUG")
        log(f".env СЃСѓС‰РµСЃС‚РІСѓРµС‚: {env_file.exists() if env_file else 'N/A'}", "DEBUG")
        
        # ========== РЁРђР“ 1: Р РµРµСЃС‚СЂ РїСЂРѕРµРєС‚РѕРІ ==========
        log("", "INFO")
        log("рџ“‹ РЁРђР“ 1: РџРћР›РЈР§Р•РќРР• Р—РђРќРЇРўР«РҐ РћРљРўР•РўРћР’ РР— Р Р•Р•РЎРўР Рђ", "INFO")
        log("-" * 60, "INFO")
        
        used_octets_registry = set()
        registry_module = get('registry')
        
        if registry_module is None:
            log("RegistryModule РЅРµ РЅР°Р№РґРµРЅ С‡РµСЂРµР· get('registry')!", "WARNING")
        else:
            log(f"RegistryModule РЅР°Р№РґРµРЅ: {registry_module}", "SUCCESS")
            try:
                exclude_path = str(project_path) if project_path else ""
                log(f"Р’С‹Р·РѕРІ get_used_octets(exclude_path='{exclude_path}')", "DEBUG")
                used_octets_registry = set(registry_module.get_used_octets(exclude_path))
                log(f"Р—Р°РЅСЏС‚С‹Рµ РѕРєС‚РµС‚С‹ РёР· СЂРµРµСЃС‚СЂР°: {sorted(used_octets_registry)}", "INFO")
            except Exception as e:
                log(f"РћС€РёР±РєР° РїСЂРё РїРѕР»СѓС‡РµРЅРёРё РѕРєС‚РµС‚РѕРІ РёР· СЂРµРµСЃС‚СЂР°: {e}", "ERROR")
                log(traceback.format_exc(), "DEBUG")
                used_octets_registry = set()
        
        # ========== РЁРђР“ 2: Docker СЃРµС‚Рё ==========
        log("", "INFO")
        log("рџ“‹ РЁРђР“ 2: РџРћР›РЈР§Р•РќРР• Р—РђРќРЇРўР«РҐ РџРћР”РЎР•РўР•Р™ РР— DOCKER", "INFO")
        log("-" * 60, "INFO")
        
        used_octets_docker = set()
        
        # РџСЂРѕРІРµСЂСЏРµРј РґРѕСЃС‚СѓРїРЅРѕСЃС‚СЊ Docker
        try:
            docker_version = subprocess.run(['docker', '--version'], capture_output=True, text=True, timeout=5)
            if docker_version.returncode == 0:
                log(f"Docker РґРѕСЃС‚СѓРїРµРЅ: {docker_version.stdout.strip()}", "SUCCESS")
            else:
                log("Docker РЅРµ РѕС‚РІРµС‡Р°РµС‚!", "WARNING")
        except Exception as e:
            log(f"РќРµ СѓРґР°Р»РѕСЃСЊ РїСЂРѕРІРµСЂРёС‚СЊ Docker: {e}", "WARNING")
        
        try:
            used_subnets = DockerModule.get_used_subnets()
            log(f"РќР°Р№РґРµРЅРѕ РїРѕРґСЃРµС‚РµР№ Docker: {len(used_subnets)}", "INFO")
            
            for subnet in used_subnets:
                log(f"  - {subnet}", "DEBUG")
                try:
                    # РР·РІР»РµРєР°РµРј РІС‚РѕСЂРѕР№ РѕРєС‚РµС‚ РёР· 172.XX.0.0/16
                    parts = subnet.split('.')
                    if len(parts) >= 2:
                        octet_val = int(parts[1])
                        used_octets_docker.add(octet_val)
                        log(f"    в†’ РѕРєС‚РµС‚ {octet_val}", "DEBUG")
                except (IndexError, ValueError) as e:
                    log(f"    в†’ РѕС€РёР±РєР° РёР·РІР»РµС‡РµРЅРёСЏ РѕРєС‚РµС‚Р°: {e}", "WARNING")
                    
            log(f"Р—Р°РЅСЏС‚С‹Рµ РѕРєС‚РµС‚С‹ РІ Docker: {sorted(used_octets_docker)}", "INFO")
        except Exception as e:
            log(f"РћС€РёР±РєР° РїСЂРё РїРѕР»СѓС‡РµРЅРёРё РїРѕРґСЃРµС‚РµР№ Docker: {e}", "ERROR")
            log(traceback.format_exc(), "DEBUG")
        
        # ========== РЁРђР“ 3: РџРѕРёСЃРє СЃРІРѕР±РѕРґРЅРѕРіРѕ РѕРєС‚РµС‚Р° ==========
        log("", "INFO")
        log("рџ“‹ РЁРђР“ 3: РџРћРРЎРљ РЎР’РћР‘РћР”РќРћР“Рћ РћРљРўР•РўРђ", "INFO")
        log("-" * 60, "INFO")
        
        preferred_octet = 20
        max_octet = 65
        
        log(f"Р”РёР°РїР°Р·РѕРЅ РїРѕРёСЃРєР°: {preferred_octet} - {max_octet}", "INFO")
        log(f"РСЃРєР»СЋС‡Р°РµРј РѕРєС‚РµС‚С‹ РёР· СЂРµРµСЃС‚СЂР°: {sorted(used_octets_registry)}", "DEBUG")
        log(f"РСЃРєР»СЋС‡Р°РµРј РѕРєС‚РµС‚С‹ РёР· Docker: {sorted(used_octets_docker)}", "DEBUG")
        
        final_octet = None
        final_base_port = None
        final_ports = []
        attempts = 0
        skipped_reasons = {}

        for octet in range(preferred_octet, max_octet + 1):
            attempts += 1
            log("", "DEBUG")
            log(f"рџ”„ РџР РћР’Р•Р РљРђ РћРљРўР•РўРђ {octet} (РїРѕРїС‹С‚РєР° {attempts})", "INFO")
            log(f"   {'в”Ђ' * 50}", "DEBUG")
            
            reason = None
            
            # РџСЂРѕРІРµСЂРєР° РІ СЂРµРµСЃС‚СЂРµ
            if octet in used_octets_registry:
                reason = f"РѕРєС‚РµС‚ {octet} Р·Р°РЅСЏС‚ РІ СЂРµРµСЃС‚СЂРµ"
                log(f"   вќЊ {reason}", "WARNING")
                skipped_reasons[octet] = reason
                continue
            else:
                log(f"   вњ… РѕРєС‚РµС‚ {octet} СЃРІРѕР±РѕРґРµРЅ РІ СЂРµРµСЃС‚СЂРµ", "DEBUG")
            
            # РџСЂРѕРІРµСЂРєР° РІ Docker
            if octet in used_octets_docker:
                reason = f"РїРѕРґСЃРµС‚СЊ 172.{octet}.0.0/16 Р·Р°РЅСЏС‚Р° РІ Docker"
                log(f"   вќЊ {reason}", "WARNING")
                skipped_reasons[octet] = reason
                continue
            else:
                log(f"   вњ… РїРѕРґСЃРµС‚СЊ 172.{octet}.0.0/16 СЃРІРѕР±РѕРґРЅР° РІ Docker", "DEBUG")
            
            # Р’С‹С‡РёСЃР»СЏРµРј Р±Р°Р·РѕРІС‹Р№ РїРѕСЂС‚
            base_port = octet * 100
            log(f"   рџ“ђ Р±Р°Р·РѕРІС‹Р№ РїРѕСЂС‚ = {octet} Г— 100 = {base_port}", "DEBUG")
            
            # РџСЂРѕРІРµСЂРєР° Р±Р°Р·РѕРІРѕРіРѕ РїРѕСЂС‚Р°
            port_manager = get('portmanager')
            if port_manager is None:
                log(f"   вќЊ PortmanagerModule РЅРµ РЅР°Р№РґРµРЅ!", "ERROR")
                reason = "PortmanagerModule РЅРµ РЅР°Р№РґРµРЅ"
                skipped_reasons[octet] = reason
                continue
            
            try:
                is_free = port_manager.is_port_free(base_port)
                if not is_free:
                    reason = f"Р±Р°Р·РѕРІС‹Р№ РїРѕСЂС‚ {base_port} Р·Р°РЅСЏС‚"
                    log(f"   вќЊ {reason}", "WARNING")
                    skipped_reasons[octet] = reason
                    continue
                else:
                    log(f"   вњ… Р±Р°Р·РѕРІС‹Р№ РїРѕСЂС‚ {base_port} СЃРІРѕР±РѕРґРµРЅ", "DEBUG")
            except Exception as e:
                log(f"   вќЊ РѕС€РёР±РєР° РїСЂРѕРІРµСЂРєРё РїРѕСЂС‚Р° {base_port}: {e}", "ERROR")
                reason = f"РѕС€РёР±РєР° РїСЂРѕРІРµСЂРєРё РїРѕСЂС‚Р°: {e}"
                skipped_reasons[octet] = reason
                continue
            
            # Р“РµРЅРµСЂР°С†РёСЏ docker/.env
            log(f"   рџ“ќ РіРµРЅРµСЂР°С†РёСЏ РІСЂРµРјРµРЅРЅРѕРіРѕ docker/.env...", "DEBUG")
            try:
                get('docker', 'ensure_docker_env')
                get('docker', 'process_port_plus_variables', base_port)
                log(f"   вњ… РІСЂРµРјРµРЅРЅС‹Р№ .env СЃРіРµРЅРµСЂРёСЂРѕРІР°РЅ", "DEBUG")
            except Exception as e:
                log(f"   вќЊ РѕС€РёР±РєР° РіРµРЅРµСЂР°С†РёРё .env: {e}", "ERROR")
                reason = f"РѕС€РёР±РєР° РіРµРЅРµСЂР°С†РёРё .env: {e}"
                skipped_reasons[octet] = reason
                continue
            
            # Р§С‚РµРЅРёРµ РїРѕСЂС‚РѕРІ РёР· docker/.env
            log(f"   рџ“– С‡С‚РµРЅРёРµ PORT_* РїРµСЂРµРјРµРЅРЅС‹С… РёР· docker/.env...", "DEBUG")
            try:
                docker_vars = get('docker', 'read_docker_env')
                
                if docker_vars is None:
                    docker_vars = {}
                
                if not docker_vars:
                    log(f"   вљ пёЏ docker_vars РїСѓСЃС‚, РЅРѕ СЌС‚Рѕ РЅРµ РєСЂРёС‚РёС‡РЅРѕ", "WARNING")
                
                # РЎРѕР±РёСЂР°РµРј PORT_* РїРµСЂРµРјРµРЅРЅС‹Рµ (РµСЃР»Рё РѕРЅРё РµСЃС‚СЊ)
                ports_to_check = []
                has_port_vars = False
                
                for key, val in docker_vars.items():
                    if key.startswith('PORT_'):
                        has_port_vars = True
                        try:
                            port_num = int(val)
                            ports_to_check.append(port_num)
                            log(f"     рџ“Љ {key} = {val} в†’ РїРѕСЂС‚ {port_num}", "DEBUG")
                        except ValueError:
                            log(f"     вљ пёЏ {key} = {val} вЂ” РЅРµ С‡РёСЃР»Рѕ, РїСЂРѕРїСѓСЃРєР°РµРј", "WARNING")
                
                # Р•СЃР»Рё РЅРµС‚ PORT_* РїРµСЂРµРјРµРЅРЅС‹С…, РїСЂРѕРІРµСЂСЏРµРј С‚РѕР»СЊРєРѕ Р±Р°Р·РѕРІС‹Р№ РїРѕСЂС‚
                if not has_port_vars:
                    log(f"   в„№пёЏ РќРµС‚ PORT_* РїРµСЂРµРјРµРЅРЅС‹С… РІ docker/.env, РїСЂРѕРІРµСЂСЏРµРј С‚РѕР»СЊРєРѕ Р±Р°Р·РѕРІС‹Р№ РїРѕСЂС‚ {base_port}", "INFO")
                    ports_to_check = [base_port]
                    log(f"   рџ“‹ РїРѕСЂС‚РѕРІ РґР»СЏ РїСЂРѕРІРµСЂРєРё: {ports_to_check}", "INFO")
                else:
                    log(f"   рџ“‹ РЅР°Р№РґРµРЅРѕ PORT_* РїРµСЂРµРјРµРЅРЅС‹С…: {len(ports_to_check)}", "INFO")
                    log(f"   рџ“‹ СЃРїРёСЃРѕРє РїРѕСЂС‚РѕРІ: {ports_to_check}", "DEBUG")
                
                # РџСЂРѕРІРµСЂРєР° РєР°Р¶РґРѕРіРѕ РїРѕСЂС‚Р°
                log(f"   рџ”Ќ РїСЂРѕРІРµСЂРєР° РїРѕСЂС‚РѕРІ РЅР° Р·Р°РЅСЏС‚РѕСЃС‚СЊ...", "DEBUG")
                all_free = True
                busy_ports = []
                
                for idx, p in enumerate(ports_to_check, 1):
                    try:
                        is_free = port_manager.is_port_free(p)
                        if not is_free:
                            log(f"     [{idx}/{len(ports_to_check)}] РїРѕСЂС‚ {p} вќЊ Р—РђРќРЇРў", "WARNING")
                            all_free = False
                            busy_ports.append(p)
                        else:
                            log(f"     [{idx}/{len(ports_to_check)}] РїРѕСЂС‚ {p} вњ… РЎР’РћР‘РћР”Р•Рќ", "DEBUG")
                    except Exception as e:
                        log(f"     [{idx}/{len(ports_to_check)}] РїРѕСЂС‚ {p} вќЊ РћРЁРР‘РљРђ: {e}", "ERROR")
                        all_free = False
                        busy_ports.append(p)
                
                if not all_free:
                    reason = f"РїРѕСЂС‚С‹ Р·Р°РЅСЏС‚С‹: {busy_ports}"
                    log(f"   вќЊ {reason}", "WARNING")
                    skipped_reasons[octet] = reason
                    continue
                
                # Р’РЎР• РџР РћР’Р•Р РљР РџР РћР™Р”Р•РќР«!
                log(f"   рџЋ‰ Р’РЎР• РџР РћР’Р•Р РљР РџР РћР™Р”Р•РќР«!", "SUCCESS")
                final_octet = octet
                final_base_port = base_port
                final_ports = ports_to_check
                break
                
            except Exception as e:
                log(f"   вќЊ РѕС€РёР±РєР° РїСЂРё РѕР±СЂР°Р±РѕС‚РєРµ РѕРєС‚РµС‚Р° {octet}: {e}", "ERROR")
                log(traceback.format_exc(), "DEBUG")
                reason = f"РѕС€РёР±РєР°: {e}"
                skipped_reasons[octet] = reason
                continue
        
        # ========== РРўРћР“Р ==========
        log("", "INFO")
        log("=" * 80, "INFO")
        
        if final_octet is None:
            log("вќЊ РќР• РЈР”РђР›РћРЎР¬ РќРђР™РўР РЎР’РћР‘РћР”РќРЈР® РљРћРњР‘РРќРђР¦РР®!", "ERROR")
            log(f"", "INFO")
            log(f"рџ“Љ РЎРўРђРўРРЎРўРРљРђ:", "INFO")
            log(f"   рџ”„ Р’СЃРµРіРѕ РїРѕРїС‹С‚РѕРє: {attempts}", "INFO")
            log(f"   рџ“‹ Р—Р°РЅСЏС‚С‹Рµ РѕРєС‚РµС‚С‹ (СЂРµРµСЃС‚СЂ): {sorted(used_octets_registry)}", "INFO")
            log(f"   рџђі Р—Р°РЅСЏС‚С‹Рµ РѕРєС‚РµС‚С‹ (Docker): {sorted(used_octets_docker)}", "INFO")
            log(f"", "INFO")
            log(f"рџ“‹ РџР РР§РРќР« РџР РћРџРЈРЎРљРђ РћРљРўР•РўРћР’:", "INFO")
            for octet, reason in list(skipped_reasons.items())[:20]:
                log(f"   {octet}: {reason}", "DEBUG")
            
            raise RuntimeError(f"РќРµ РЅР°Р№РґРµРЅРѕ СЃРІРѕР±РѕРґРЅРѕРіРѕ РѕРєС‚РµС‚Р° РІ РґРёР°РїР°Р·РѕРЅРµ {preferred_octet}вЂ“{max_octet}. "
                            f"Р РµРµСЃС‚СЂ: {sorted(used_octets_registry)}, Docker: {sorted(used_octets_docker)}")
        
        # ========== РЎРћРҐР РђРќР•РќРР• Р Р•Р—РЈР›Р¬РўРђРўРћР’ ==========
        log("рџЋ‰ Р’Р«Р”Р•Р›Р•РќРР• РЎР•РўР Р РџРћР РўРћР’ Р—РђР’Р•Р РЁР•РќРћ РЈРЎРџР•РЁРќРћ!", "SUCCESS")
        log(f"   рџ“Њ РћРєС‚РµС‚: {final_octet}", "SUCCESS")
        log(f"   рџ“Њ Р‘Р°Р·РѕРІС‹Р№ РїРѕСЂС‚: {final_base_port}", "SUCCESS")
        log(f"   рџ“Њ РџРѕРґСЃРµС‚СЊ: 172.{final_octet}.0.0/16", "SUCCESS")
        log(f"   рџ“Њ РџРѕСЂС‚С‹: {final_ports}", "SUCCESS")
        log("=" * 80, "INFO")
        
        network_prefix = f"172.{final_octet}"
        subnet = f"{network_prefix}.0.0/16"
        
        # РћР±РЅРѕРІР»СЏРµРј РіР»РѕР±Р°Р»СЊРЅС‹Рµ РїРµСЂРµРјРµРЅРЅС‹Рµ
        set_global('subnet_octet', final_octet)
        set_global('port', final_base_port)
        set_global('docker_network_prefix', network_prefix)
        set_global('docker_subnet', subnet)
        
        os.environ["PORT"] = str(final_base_port)
        os.environ["SUBNET_OCTET"] = str(final_octet)
        os.environ["DOCKER_NETWORK_PREFIX"] = network_prefix
        os.environ["DOCKER_SUBNET"] = subnet
        
        # Р¤РёРЅР°Р»СЊРЅР°СЏ Р·Р°РїРёСЃСЊ
        get('docker', 'ensure_docker_env')
        get('docker', 'process_port_plus_variables', final_base_port)
        
        return {
            'octet': final_octet,
            'base_port': final_base_port,
            'network_prefix': network_prefix,
            'subnet': subnet,
            'used_ports': final_ports,
            'attempts': attempts,
            'skipped_reasons': skipped_reasons
        }

    @staticmethod
    def get_used_subnets() -> List[str]:
        """
        Р’РѕР·РІСЂР°С‰Р°РµС‚ СЃРїРёСЃРѕРє РІСЃРµС… РёСЃРїРѕР»СЊР·СѓРµРјС‹С… РїРѕРґСЃРµС‚РµР№ РІ С„РѕСЂРјР°С‚Рµ '172.20.0.0/16'
        
        Returns:
            РЎРїРёСЃРѕРє Р·Р°РЅСЏС‚С‹С… РїРѕРґСЃРµС‚РµР№, РѕС‚СЃРѕСЂС‚РёСЂРѕРІР°РЅРЅС‹Р№ РїРѕ РѕРєС‚РµС‚Сѓ
        """
        used_subnets = set()
        
        try:
            # 1. РџСЂРѕРІРµСЂСЏРµРј СЃСѓС‰РµСЃС‚РІСѓСЋС‰РёРµ СЃРµС‚Рё Docker
            try:
                result = subprocess.run(['docker', 'network', 'ls', '-q'],capture_output=True,text=True,check=True)
                
                network_ids = result.stdout.strip().split()
                for net_id in network_ids:
                    try:
                        inspect_result = subprocess.run(['docker', 'network', 'inspect', net_id],capture_output=True,text=True,check=True)
                        if inspect_result.returncode == 0:
                            networks = json.loads(inspect_result.stdout)
                            for network in networks:
                                if 'IPAM' in network and network['IPAM']['Config']:
                                    for config in network['IPAM']['Config']:
                                        if 'Subnet' in config:
                                            subnet = config['Subnet']
                                            # Р¤РёР»СЊС‚СЂСѓРµРј С‚РѕР»СЊРєРѕ РїРѕРґСЃРµС‚Рё 172.x.x.x/16
                                            if subnet.startswith('172.') and subnet.endswith('/16'):
                                                used_subnets.add(subnet)
                    except Exception:
                        continue
            except Exception as e:
                logger.warning(f"Error checking Docker networks: {e}")
            
            # 2. РџСЂРѕРІРµСЂСЏРµРј Р·Р°РїСѓС‰РµРЅРЅС‹Рµ РєРѕРЅС‚РµР№РЅРµСЂС‹
            try:
                result = subprocess.run(['docker', 'ps', '-a', '--format', '{{.ID}}'],capture_output=True,text=True,check=True)
                
                container_ids = result.stdout.strip().split()
                for container_id in container_ids:
                    try:
                        inspect_result = subprocess.run(['docker', 'inspect', container_id],capture_output=True,text=True,check=True)
                        if inspect_result.returncode == 0:
                            container = json.loads(inspect_result.stdout)[0]
                            if 'NetworkSettings' in container and container['NetworkSettings']['Networks']:
                                for network in container['NetworkSettings']['Networks'].values():
                                    if 'IPAMConfig' in network and network['IPAMConfig']:
                                        if 'IPv4Address' in network['IPAMConfig']:
                                            ip = network['IPAMConfig']['IPv4Address']
                                            # РР·РІР»РµРєР°РµРј РїРѕРґСЃРµС‚СЊ РёР· IP (РїРµСЂРІС‹Рµ РґРІР° РѕРєС‚РµС‚Р°)
                                            parts = ip.split('.')
                                            if len(parts) >= 2 and parts[0] == '172':
                                                subnet = f"172.{parts[1]}.0.0/16"
                                                used_subnets.add(subnet)
                    except Exception:
                        continue
            except Exception as e:
                logger.warning(f"Error checking containers: {e}")
            

            content = get_global('docker_compose_path').read_text(encoding='utf-8', errors='ignore')
            # РС‰РµРј РїРѕРґСЃРµС‚Рё 172.XX.0.0/16
            pattern = r'172\.(\d{1,3})\.0\.0/16'
            matches = re.findall(pattern, content)
            for octet in matches:
                if octet.isdigit() and 0 <= int(octet) <= 255:
                    subnet = f"172.{octet}.0.0/16"
                    used_subnets.add(subnet)
            
        except Exception as e:
            logger.error(f"Unexpected error in get_used_subnets: {e}")
        
        # РЎРѕСЂС‚РёСЂСѓРµРј РїРѕ РІС‚РѕСЂРѕРјСѓ РѕРєС‚РµС‚Сѓ
        sorted_subnets = sorted(list(used_subnets),key=lambda x: int(x.split('.')[1]) if len(x.split('.')) > 1 else 0)
        
        logger.debug(f"Found {len(sorted_subnets)} used subnets: {sorted_subnets}")
        return sorted_subnets
    
    @staticmethod
    def get_used_subnets_simple() -> List[str]:
        """
        РЈРїСЂРѕС‰РµРЅРЅР°СЏ РІРµСЂСЃРёСЏ - РІРѕР·РІСЂР°С‰Р°РµС‚ С‚РѕР»СЊРєРѕ РїРѕРґСЃРµС‚Рё РІРёРґР° 172.XX.0.0/16
        
        Returns:
            РЎРїРёСЃРѕРє Р·Р°РЅСЏС‚С‹С… РїРѕРґСЃРµС‚РµР№
        """
        try:
            # РџРѕР»СѓС‡Р°РµРј РІСЃРµ РїРѕРґСЃРµС‚Рё
            all_subnets = get('docker','get_used_subnets')
            
            # Р¤РёР»СЊС‚СЂСѓРµРј С‚РѕР»СЊРєРѕ 172.XX.0.0/16
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
        Р’РѕР·РІСЂР°С‰Р°РµС‚ СЃРїРёСЃРѕРє Р·Р°РЅСЏС‚С‹С… РІС‚РѕСЂС‹С… РѕРєС‚РµС‚РѕРІ (20, 21, 22...)
        
        Returns:
            РЎРїРёСЃРѕРє Р·Р°РЅСЏС‚С‹С… РѕРєС‚РµС‚РѕРІ, РѕС‚СЃРѕСЂС‚РёСЂРѕРІР°РЅРЅС‹Р№ РїРѕ РІРѕР·СЂР°СЃС‚Р°РЅРёСЋ
        """
        used_subnets = get('docker','get_used_subnets_simple')
        octets = []
        
        for subnet in used_subnets:
            try:
                # РР·РІР»РµРєР°РµРј РІС‚РѕСЂРѕР№ РѕРєС‚РµС‚ РёР· 172.XX.0.0/16
                parts = subnet.split('.')
                if len(parts) >= 2:
                    octet = int(parts[1])
                    octets.append(octet)
            except (ValueError, IndexError):
                continue
        
        # РЈР±РёСЂР°РµРј РґСѓР±Р»РёРєР°С‚С‹ Рё СЃРѕСЂС‚РёСЂСѓРµРј
        unique_octets = sorted(set(octets))
        logger.debug(f"Found {len(unique_octets)} used octets: {unique_octets}")
        return unique_octets
    
    @staticmethod
    def is_subnet_available(subnet: str) -> Tuple[bool, str]:
        """
        РџСЂРѕРІРµСЂСЏРµС‚, СЃРІРѕР±РѕРґРЅР° Р»Рё РїРѕРґСЃРµС‚СЊ
        
        Args:
            subnet: РџРѕРґСЃРµС‚СЊ РІ С„РѕСЂРјР°С‚Рµ '172.20.0.0/16'
            
        Returns:
            Tuple[bool, str]: (РґРѕСЃС‚СѓРїРЅР° Р»Рё, СЃРѕРѕР±С‰РµРЅРёРµ РѕР± РѕС€РёР±РєРµ)
        """
        try:
            # РџСЂРѕРІРµСЂСЏРµРј С„РѕСЂРјР°С‚
            if not subnet.startswith('172.') or not subnet.endswith('/16'):
                return False, f"РќРµРїСЂР°РІРёР»СЊРЅС‹Р№ С„РѕСЂРјР°С‚ РїРѕРґСЃРµС‚Рё. Р”РѕР»Р¶РЅРѕ Р±С‹С‚СЊ: 172.XX.0.0/16"
            
            # РР·РІР»РµРєР°РµРј РѕРєС‚РµС‚
            parts = subnet.split('.')
            if len(parts) != 4:
                return False, f"РќРµРїСЂР°РІРёР»СЊРЅС‹Р№ С„РѕСЂРјР°С‚ РїРѕРґСЃРµС‚Рё: {subnet}"
            
            octet_str = parts[1].split('/')[0]
            try:
                octet = int(octet_str)
                if octet < 20 or octet > 250:
                    return False, f"РћРєС‚РµС‚ РґРѕР»Р¶РµРЅ Р±С‹С‚СЊ РІ РґРёР°РїР°Р·РѕРЅРµ 20-250"
            except ValueError:
                return False, f"РћРєС‚РµС‚ РґРѕР»Р¶РµРЅ Р±С‹С‚СЊ С‡РёСЃР»РѕРј: {octet_str}"
            
            # РџСЂРѕРІРµСЂСЏРµРј Р·Р°РЅСЏС‚РѕСЃС‚СЊ
            used_octets = get('docker','get_used_octets')
            
            if octet in used_octets:
                return False, f"РџРѕРґСЃРµС‚СЊ {subnet} СѓР¶Рµ РёСЃРїРѕР»СЊР·СѓРµС‚СЃСЏ"
            
            return True, f"РџРѕРґСЃРµС‚СЊ {subnet} СЃРІРѕР±РѕРґРЅР°"
            
        except Exception as e:
            return False, f"РћС€РёР±РєР° РїСЂРѕРІРµСЂРєРё РїРѕРґСЃРµС‚Рё: {str(e)}"
    
    @staticmethod
    def find_available_subnet(start_octet: int = 20, max_attempts: int = 100) -> str:
        """
        РќР°С…РѕРґРёС‚ СЃРІРѕР±РѕРґРЅСѓСЋ РїРѕРґСЃРµС‚СЊ, РЅР°С‡РёРЅР°СЏ СЃ start_octet
        
        Args:
            start_octet: РЎ РєР°РєРѕРіРѕ РѕРєС‚РµС‚Р° РЅР°С‡Р°С‚СЊ РїРѕРёСЃРє
            max_attempts: РњР°РєСЃРёРјР°Р»СЊРЅРѕРµ РєРѕР»РёС‡РµСЃС‚РІРѕ РїРѕРїС‹С‚РѕРє
            
        Returns:
            РЎРІРѕР±РѕРґРЅР°СЏ РїРѕРґСЃРµС‚СЊ РІРёРґР° '172.XX.0.0/16'
            
        Raises:
            ValueError: Р•СЃР»Рё РЅРµ РЅР°Р№РґРµРЅРѕ СЃРІРѕР±РѕРґРЅС‹С… РїРѕРґСЃРµС‚РµР№
        """
        used_octets = get('docker','get_used_octets')
        
        # РС‰РµРј СЃРІРѕР±РѕРґРЅС‹Р№ РѕРєС‚РµС‚
        for attempt in range(max_attempts):
            test_octet = start_octet + attempt
            if test_octet > 250:
                break
            
            if test_octet not in used_octets:
                subnet = f"172.{test_octet}.0.0/16"
                logger.info(f"Found available subnet: {subnet}")
                return subnet
        
        # Р•СЃР»Рё РЅРµ РЅР°С€Р»Рё
        used_str = ", ".join(str(o) for o in sorted(used_octets)[:10])
        raise ValueError(
            f"РќРµ РЅР°Р№РґРµРЅРѕ СЃРІРѕР±РѕРґРЅС‹С… РїРѕРґСЃРµС‚РµР№ РІ РґРёР°РїР°Р·РѕРЅРµ 172.{start_octet}.0.0 - 172.{start_octet + max_attempts}.0.0. "
            f"Р—Р°РЅСЏС‚С‹Рµ РѕРєС‚РµС‚С‹: {used_str}"
        )
    
    @staticmethod
    def increment_subnet(subnet: str) -> str:
        """
        РЈРІРµР»РёС‡РёРІР°РµС‚ РїРѕРґСЃРµС‚СЊ РЅР° 1 РѕРєС‚РµС‚
        
        Args:
            subnet: РСЃС…РѕРґРЅР°СЏ РїРѕРґСЃРµС‚СЊ РІРёРґР° '172.20.0.0/16'
            
        Returns:
            РќРѕРІР°СЏ РїРѕРґСЃРµС‚СЊ РІРёРґР° '172.21.0.0/16'
            
        Raises:
            ValueError: Р•СЃР»Рё РЅРµРїСЂР°РІРёР»СЊРЅС‹Р№ С„РѕСЂРјР°С‚ РёР»Рё РїСЂРµРІС‹С€РµРЅ Р»РёРјРёС‚
        """
        try:
            # РџСЂРѕРІРµСЂСЏРµРј С„РѕСЂРјР°С‚
            if not subnet.startswith('172.') or not subnet.endswith('/16'):
                raise ValueError(f"РќРµРїСЂР°РІРёР»СЊРЅС‹Р№ С„РѕСЂРјР°С‚ РїРѕРґСЃРµС‚Рё: {subnet}. Р”РѕР»Р¶РЅРѕ Р±С‹С‚СЊ: 172.XX.0.0/16")
            
            # РР·РІР»РµРєР°РµРј РѕРєС‚РµС‚
            parts = subnet.split('.')
            if len(parts) != 4:
                raise ValueError(f"РќРµРїСЂР°РІРёР»СЊРЅС‹Р№ С„РѕСЂРјР°С‚ РїРѕРґСЃРµС‚Рё: {subnet}")
            
            octet_part = parts[1]
            try:
                current_octet = int(octet_part)
            except ValueError:
                raise ValueError(f"РћРєС‚РµС‚ РґРѕР»Р¶РµРЅ Р±С‹С‚СЊ С‡РёСЃР»РѕРј: {octet_part}")
            
            # РџСЂРѕРІРµСЂСЏРµРј РґРёР°РїР°Р·РѕРЅ
            if current_octet < 20 or current_octet >= 250:
                raise ValueError(f"РћРєС‚РµС‚ РґРѕР»Р¶РµРЅ Р±С‹С‚СЊ РІ РґРёР°РїР°Р·РѕРЅРµ 20-249. РўРµРєСѓС‰РёР№: {current_octet}")
            
            # РЈРІРµР»РёС‡РёРІР°РµРј РЅР° 1
            new_octet = current_octet + 1
            new_subnet = f"172.{new_octet}.0.0/16"
            
            # РџСЂРѕРІРµСЂСЏРµРј, СЃРІРѕР±РѕРґРЅР° Р»Рё РЅРѕРІР°СЏ РїРѕРґСЃРµС‚СЊ
            used_octets = get('docker','get_used_octets')
            attempts = 0
            
            while new_octet in used_octets and attempts < 50:
                new_octet += 1
                attempts += 1
                if new_octet > 250:
                    raise ValueError(f"Р”РѕСЃС‚РёРіРЅСѓС‚ РїСЂРµРґРµР» РѕРєС‚РµС‚РѕРІ (250)")
            
            new_subnet = f"172.{new_octet}.0.0/16"
            logger.info(f"Incremented subnet: {subnet} -> {new_subnet}")
            return new_subnet
            
        except Exception as e:
            raise ValueError(f"РћС€РёР±РєР° РїСЂРё СѓРІРµР»РёС‡РµРЅРёРё РїРѕРґСЃРµС‚Рё: {str(e)}")
    
    @staticmethod
    def get_available_subnet_or_increment(requested_subnet: str) -> Tuple[str, bool]:
        """
        РџСЂРѕРІРµСЂСЏРµС‚ Р·Р°РїСЂРѕС€РµРЅРЅСѓСЋ РїРѕРґСЃРµС‚СЊ, РµСЃР»Рё Р·Р°РЅСЏС‚Р° - СѓРІРµР»РёС‡РёРІР°РµС‚
        
        Args:
            requested_subnet: Р—Р°РїСЂР°С€РёРІР°РµРјР°СЏ РїРѕРґСЃРµС‚СЊ РІРёРґР° '172.20.0.0/16'
            
        Returns:
            Tuple[РїРѕРґСЃРµС‚СЊ, Р±С‹Р»Р°_Р»Рё_СѓРІРµР»РёС‡РµРЅР°]
            
        РџСЂРёРјРµСЂ:
            get_available_subnet_or_increment('172.20.0.0/16')
            в†’ ('172.20.0.0/16', False)  # РµСЃР»Рё СЃРІРѕР±РѕРґРЅР°
            в†’ ('172.21.0.0/16', True)   # РµСЃР»Рё Р·Р°РЅСЏС‚Р°, СѓРІРµР»РёС‡РёР»Рё
        """
        try:
            # РџСЂРѕРІРµСЂСЏРµРј Р·Р°РїСЂРѕС€РµРЅРЅСѓСЋ РїРѕРґСЃРµС‚СЊ
            available, message = get('docker','is_subnet_available',requested_subnet)
            
            if available:
                logger.info(f"Requested subnet {requested_subnet} is available")
                return requested_subnet, False
            else:
                logger.info(f"Requested subnet {requested_subnet} is occupied: {message}")
                
                # РџСЂРѕР±СѓРµРј СѓРІРµР»РёС‡РёС‚СЊ
                try:
                    new_subnet = get('docker','increment_subnet',requested_subnet)
                    logger.info(f"Using incremented subnet: {new_subnet}")
                    return new_subnet, True
                except ValueError as e:
                    logger.warning(f"Could not increment {requested_subnet}: {e}")
                    
                    # РС‰РµРј Р»СЋР±СѓСЋ СЃРІРѕР±РѕРґРЅСѓСЋ
                    try:
                        start_octet = int(requested_subnet.split('.')[1])
                        new_subnet = get('docker','find_available_subnet',start_octet)
                        logger.info(f"Found alternative subnet: {new_subnet}")
                        return new_subnet, True
                    except ValueError as e2:
                        # РџРѕСЃР»РµРґРЅСЏСЏ РїРѕРїС‹С‚РєР° - РЅР°Р№С‚Рё Р»СЋР±СѓСЋ СЃРІРѕР±РѕРґРЅСѓСЋ СЃ РЅР°С‡Р°Р»Р°
                        try:
                            new_subnet = get('docker','find_available_subnet',20)
                            logger.info(f"Found free subnet from beginning: {new_subnet}")
                            return new_subnet, True
                        except ValueError:
                            raise ValueError(f"РќРµ РЅР°Р№РґРµРЅРѕ СЃРІРѕР±РѕРґРЅС‹С… РїРѕРґСЃРµС‚РµР№: {e2}")
                        
        except Exception as e:
            raise ValueError(f"РћС€РёР±РєР° РїСЂРё РїРѕРёСЃРєРµ РїРѕРґСЃРµС‚Рё: {str(e)}")
    
    @staticmethod
    def generate_subnet_for_project(project_name: str, 
                                    preferred_octet: int = None) -> Dict[str, any]:
        """
        Р“РµРЅРµСЂРёСЂСѓРµС‚ РїРѕРґСЃРµС‚СЊ РґР»СЏ РЅРѕРІРѕРіРѕ РїСЂРѕРµРєС‚Р°
        
        Args:
            project_name: РРјСЏ РїСЂРѕРµРєС‚Р°
            preferred_octet: РџСЂРµРґРїРѕС‡РёС‚Р°РµРјС‹Р№ РѕРєС‚РµС‚ (РµСЃР»Рё None - Р°РІС‚РѕРјР°С‚РёС‡РµСЃРєРё)
            
        Returns:
            РЎР»РѕРІР°СЂСЊ СЃ РёРЅС„РѕСЂРјР°С†РёРµР№ Рѕ РїРѕРґСЃРµС‚Рё
        """
        try:
            # РћРїСЂРµРґРµР»СЏРµРј РЅР°С‡Р°Р»СЊРЅС‹Р№ РѕРєС‚РµС‚
            if preferred_octet is None:
                # РњРѕР¶РЅРѕ РёСЃРїРѕР»СЊР·РѕРІР°С‚СЊ С…СЌС€ РёРјРµРЅРё РїСЂРѕРµРєС‚Р° РґР»СЏ Р±РѕР»РµРµ СЂР°РІРЅРѕРјРµСЂРЅРѕРіРѕ СЂР°СЃРїСЂРµРґРµР»РµРЅРёСЏ
                import hashlib
                hash_int = int(hashlib.md5(project_name.encode()).hexdigest()[:8], 16)
                start_octet = 20 + (hash_int % 50)
            else:
                start_octet = preferred_octet
            
            # Р¤РѕСЂРјРёСЂСѓРµРј Р·Р°РїСЂР°С€РёРІР°РµРјСѓСЋ РїРѕРґСЃРµС‚СЊ
            requested_subnet = f"172.{start_octet}.0.0/16"
            
            # РџРѕР»СѓС‡Р°РµРј РґРѕСЃС‚СѓРїРЅСѓСЋ РїРѕРґСЃРµС‚СЊ
            final_subnet, was_incremented = get('docker','get_available_subnet_or_increment',requested_subnet)
            
            # РР·РІР»РµРєР°РµРј РѕРєС‚РµС‚
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

    # ========== Р’РђР›РР”РђР¦РРЇ DOCKER РљРћРќР¤РР“РЈР РђР¦РР ==========
    
    @staticmethod
    def validate_docker_compose_file(file_path: Path) -> Tuple[bool, List[str]]:
        """Р’Р°Р»РёРґРёСЂСѓРµС‚ docker-compose С„Р°Р№Р»"""
        errors = []

        if not file_path.exists():
            errors.append(f"Р¤Р°Р№Р» docker-compose РЅРµ РЅР°Р№РґРµРЅ: {file_path}")
            return False, errors

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            try:
                import yaml
                compose_data = yaml.safe_load(content)
            except ImportError:
                errors.append("Р‘РёР±Р»РёРѕС‚РµРєР° PyYAML РЅРµ СѓСЃС‚Р°РЅРѕРІР»РµРЅР°, РїСЂРѕРїСѓСЃРєР°СЋ РІР°Р»РёРґР°С†РёСЋ YAML")
                return True, errors
            except yaml.YAMLError as e:
                errors.append(f"РћС€РёР±РєР° РїР°СЂСЃРёРЅРіР° YAML: {str(e)}")
                return False, errors

            # РџСЂРѕРІРµСЂРєР° СЃС‚СЂСѓРєС‚СѓСЂС‹
            if not isinstance(compose_data, dict):
                errors.append("РљРѕСЂРЅРµРІРѕР№ СЌР»РµРјРµРЅС‚ РґРѕР»Р¶РµРЅ Р±С‹С‚СЊ СЃР»РѕРІР°СЂРµРј")
                return False, errors

            # РџСЂРѕРІРµСЂСЏРµРј СЃРµРєС†РёСЋ services
            services = compose_data.get('services', {})
            if not services:
                errors.append("РћС‚СЃСѓС‚СЃС‚РІСѓРµС‚ СЃРµРєС†РёСЏ 'services' РёР»Рё РѕРЅР° РїСѓСЃС‚Р°СЏ")

            return len(errors) == 0, errors

        except Exception as e:
            errors.append(f"РќРµРѕР¶РёРґР°РЅРЅР°СЏ РѕС€РёР±РєР° РїСЂРё РІР°Р»РёРґР°С†РёРё: {str(e)}")
            return False, errors

    @staticmethod
    def validate_docker_setup() -> Tuple[bool, List[str]]:
        """РљРѕРјРїР»РµРєСЃРЅР°СЏ РІР°Р»РёРґР°С†РёСЏ РЅР°СЃС‚СЂРѕР№РєРё Docker"""
        errors = []

        # РџСЂРѕРІРµСЂСЏРµРј РЅР°Р»РёС‡РёРµ Docker
        try:
            result = subprocess.run(['docker', '--version'], capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                errors.append("Docker РЅРµ СѓСЃС‚Р°РЅРѕРІР»РµРЅ РёР»Рё РЅРµ СЂР°Р±РѕС‚Р°РµС‚")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            errors.append("Docker РЅРµ РЅР°Р№РґРµРЅ РІ PATH")

        # РџСЂРѕРІРµСЂСЏРµРј docker-compose С„Р°Р№Р»С‹
        docker_path = get_global('docker_path')
        if docker_path and docker_path.exists():
            compose_files = list(docker_path.glob('docker-compose*.yml'))
            if not compose_files:
                errors.append("РќРµ РЅР°Р№РґРµРЅС‹ С„Р°Р№Р»С‹ docker-compose.yml РІ РґРёСЂРµРєС‚РѕСЂРёРё docker")

        return len(errors) == 0, errors
