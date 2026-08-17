from files.core.base_module import BaseModule
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path
from files.core.utils.globalVars_utils import get_global, set_global
from files.core.utils.loader_utils import get
import subprocess
import re
import json
import logging
import time

logger = logging.getLogger('tailscale')


class TailscaleModule(BaseModule):
    """Модуль для установки и управления Tailscale VPN"""

    @staticmethod
    def check_tailscale_installed() -> bool:
        try:
            result = subprocess.run(['which', 'tailscale'], capture_output=True, text=True)
            return result.returncode == 0
        except Exception:
            return False

    @staticmethod
    def return_commands_install_tailscale() -> List[str]:
        is_root = get_global('is_root', False)
        use_sudo = get_global('use_sudo', False)
        prefix = '' if is_root or not use_sudo else 'sudo '
        return [f"{prefix}curl -fsSL https://tailscale.com/install.sh | sh"]

    @staticmethod
    def install_tailscale(log_file_path: str) -> Dict[str, str]:
        result = {'status': 'success', 'message': '', 'logs': []}
        try:
            log_dir = Path(log_file_path).parent
            log_dir.mkdir(parents=True, exist_ok=True)
            with open(log_file_path, 'w') as log_file:
                def log(message):
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    entry = f"[{timestamp}] {message}"
                    log_file.write(entry + '\n')
                    log_file.flush()
                    result['logs'].append(entry)
                    logger.info(entry)

                log("Starting Tailscale installation...")
                commands = get("tailscale", "return_commands_install_tailscale")
                for cmd in commands:
                    log(f"Executing: {cmd}")
                    proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                                           stderr=subprocess.STDOUT, text=True, bufsize=1,
                                           universal_newlines=True)
                    for line in iter(proc.stdout.readline, ''):
                        if line:
                            log(line.strip())
                    rc = proc.wait()
                    if rc != 0:
                        log(f"Command failed with exit code {rc}")
                        result['status'] = 'error'
                        result['message'] = f"Command failed: {cmd}"
                        return result

                time.sleep(2)
                if get('tailscale', 'check_tailscale_installed'):
                    log("Tailscale installed successfully!")
                    result['message'] = "Tailscale installed successfully!"
                else:
                    log("Installation completed but tailscale not detected. Try restarting your system.")
                    result['status'] = 'warning'
                    result['message'] = "Installation completed but tailscale not detected."
        except Exception as e:
            error_msg = f"Installation failed: {str(e)}"
            try:
                with open(log_file_path, 'a') as f:
                    f.write(error_msg + '\n')
            except:
                logger.exception("Failed to write error to log file")
            result['status'] = 'error'
            result['message'] = error_msg
            logger.exception("Tailscale installation error")
        return result

    @staticmethod
    def connect_tailscale(login_server: str, auth_key: str = None) -> Dict:
        cmd = f"tailscale up --login-server={login_server}"
        if auth_key:
            cmd += f" --authkey={auth_key}"
        try:
            proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, text=True)
            auth_url = None
            output_lines = []
            for line in iter(proc.stdout.readline, ''):
                if line:
                    stripped = line.strip()
                    output_lines.append(stripped)
                    match = re.search(r'(https?://\S+)', stripped)
                    if match and any(w in stripped.lower() for w in ['visit', 'auth', 'open', 'browser']):
                        auth_url = match.group(1)
            rc = proc.wait()
            if auth_url:
                return {'status': 'auth_required', 'message': '\n'.join(output_lines), 'auth_url': auth_url}
            elif rc == 0:
                return {'status': 'success', 'message': 'Connected', 'auth_url': None}
            else:
                return {'status': 'error', 'message': '\n'.join(output_lines), 'auth_url': None}
        except Exception as e:
            return {'status': 'error', 'message': str(e), 'auth_url': None}

    @staticmethod
    def disconnect_tailscale() -> Dict:
        try:
            result = subprocess.run(['tailscale', 'down'], capture_output=True, text=True, timeout=30)
            return {'status': 'success' if result.returncode == 0 else 'error',
                    'message': result.stdout + result.stderr}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    @staticmethod
    def get_tailscale_status() -> Dict:
        try:
            result = subprocess.run(['tailscale', 'status', '--json'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                data = json.loads(result.stdout)
                self_info = data.get('Self', {})
                tailscale_ips = self_info.get('TailscaleIPs', [])
                return {
                    'connected': data.get('BackendState') == 'Running',
                    'status_text': data.get('BackendState', 'Unknown'),
                    'ip': tailscale_ips[0] if tailscale_ips else None,
                    'hostname': self_info.get('HostName'),
                    'version': self_info.get('Version'),
                    'backend_state': data.get('BackendState')
                }
        except Exception:
            pass
        return {
            'connected': False, 'status_text': 'Not available', 'ip': None,
            'hostname': None, 'version': None, 'backend_state': None
        }

    @staticmethod
    def get_tailscale_ip() -> Optional[str]:
        try:
            result = subprocess.run(['tailscale', 'ip', '-4'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return None

    @staticmethod
    def get_tailscale_peers() -> List[Dict]:
        """Возвращает список всех пиров (устройств) в Tailscale-сети"""
        try:
            result = subprocess.run(['tailscale', 'status', '--json'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                data = json.loads(result.stdout)
                peers = []
                for peer_id, peer_info in data.get('Peer', {}).items():
                    ips = peer_info.get('TailscaleIPs', [])
                    peers.append({
                        'id': peer_id,
                        'hostname': peer_info.get('HostName', ''),
                        'dns_name': peer_info.get('DNSName', ''),
                        'ip': ips[0] if ips else None,
                        'online': peer_info.get('Online', False),
                        'os': peer_info.get('OS', ''),
                    })
                return peers
        except Exception:
            pass
        return []

    @staticmethod
    def set_globals():
        from files.core.software.default.env import EnvModule

        env_path = get_global('starter_env_path')
        if env_path and env_path.exists():
            env_vars = EnvModule.read_env_file(env_path)
            login_server = env_vars.get('HEADSCALE_LOGIN_SERVER', '')
            if login_server:
                set_global('headscale_login_server', login_server)

        installed = get('tailscale', 'check_tailscale_installed')
        set_global('tailscale_installed', installed)
        if installed:
            status = get('tailscale', 'get_tailscale_status')
            set_global('tailscale_status', status.get('status_text', 'Unknown'))
            set_global('tailscale_active', status.get('connected', False))
            set_global('tailscale_ip', status.get('ip'))
