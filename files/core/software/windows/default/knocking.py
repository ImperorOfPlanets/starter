import socket
import json
import time
import subprocess
from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime
from files.core.base_module import BaseModule
from files.core.utils.globalVars_utils import get_global, set_global
from files.core.utils.log_utils import LogManager

logger = LogManager.get_logger('knocking_windows')

CONFIG_FILE = "knocking_config.json"
RULE_PREFIX = "StarterKnock"


class KnockingModule(BaseModule):
    """Windows Port Knocking via Windows Firewall rules"""

    @staticmethod
    def is_knocking_installed() -> bool:
        """Always available on Windows (uses built-in firewall)"""
        return True

    @staticmethod
    def is_knocking_active() -> bool:
        """Check if any starter knocking rules exist in firewall"""
        try:
            result = subprocess.run(
                ['powershell', '-Command',
                 f'Get-NetFirewallRule -DisplayName "{RULE_PREFIX}*" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty DisplayName'],
                capture_output=True, text=True, timeout=10
            )
            return bool(result.stdout.strip())
        except Exception:
            return False

    @staticmethod
    def get_knocking_config() -> Optional[Dict]:
        """Get current knocking configuration"""
        config_path = get_global('starter_path') / 'files' / 'data' / CONFIG_FILE
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        # Default config
        return {
            'ports': [7000, 8000, 9000],
            'timeout': 5,
            'target_port': 22,
            'knock_action': 'open',
            'auto_close_seconds': 30
        }

    @staticmethod
    def save_knocking_config(config: Dict) -> bool:
        """Save knocking configuration"""
        try:
            config_path = get_global('starter_path') / 'files' / 'data' / CONFIG_FILE
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            return False

    @staticmethod
    def send_knock(host: str, ports: List[int], interval: float = 0.5) -> bool:
        """Send knocking sequence to host"""
        try:
            for port in ports:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                try:
                    sock.connect_ex((host, port))
                except Exception:
                    pass
                finally:
                    sock.close()
                time.sleep(interval)
            return True
        except Exception as e:
            logger.error(f"Knock send failed: {e}")
            return False

    @staticmethod
    def _ps_run(command: str) -> Dict:
        """Run PowerShell command and return result"""
        try:
            result = subprocess.run(
                ['powershell', '-NoProfile', '-Command', command],
                capture_output=True, text=True, timeout=30
            )
            return {
                'success': result.returncode == 0,
                'stdout': result.stdout.strip(),
                'stderr': result.stderr.strip()
            }
        except Exception as e:
            return {'success': False, 'stdout': '', 'stderr': str(e)}

    @staticmethod
    def open_firewall_rule(port: int, rule_name: str = None, description: str = "") -> bool:
        """Open a port in Windows Firewall"""
        name = rule_name or f"{RULE_PREFIX}_Open_{port}"
        cmd = f'''
        $existing = Get-NetFirewallRule -DisplayName "{name}" -ErrorAction SilentlyContinue
        if ($existing) {{
            Remove-NetFirewallRule -DisplayName "{name}"
        }}
        New-NetFirewallRule -DisplayName "{name}" `
            -Direction Inbound `
            -Protocol TCP `
            -LocalPort {port} `
            -Action Allow `
            -Profile Any `
            -Description "{description or f'Starter auto-open port {port}'}"
        '''
        result = KnockingModule._ps_run(cmd)
        if result['success']:
            logger.info(f"Firewall rule created: {name} for port {port}")
        else:
            logger.error(f"Failed to create rule: {result['stderr']}")
        return result['success']

    @staticmethod
    def close_firewall_rule(port: int) -> bool:
        """Remove firewall rule for a port"""
        name = f"{RULE_PREFIX}_Open_{port}"
        cmd = f'Remove-NetFirewallRule -DisplayName "{name}" -ErrorAction SilentlyContinue'
        result = KnockingModule._ps_run(cmd)
        return result['success']

    @staticmethod
    def close_all_knock_rules() -> bool:
        """Remove all starter knocking rules"""
        cmd = f'Get-NetFirewallRule -DisplayName "{RULE_PREFIX}*" | Remove-NetFirewallRule'
        result = KnockingModule._ps_run(cmd)
        return result['success']

    @staticmethod
    def get_open_knock_ports() -> List[Dict]:
        """Get all currently open knock ports"""
        cmd = f'''
        Get-NetFirewallRule -DisplayName "{RULE_PREFIX}*" -ErrorAction SilentlyContinue |
        ForEach-Object {{
            $port = ($_ | Get-NetFirewallPortFilter).LocalPort
            [PSCustomObject]@{{
                Name = $_.DisplayName
                Port = $port
                Enabled = $_.Enabled
                Direction = $_.Direction
            }}
        }} | ConvertTo-Json -Compress
        '''
        result = KnockingModule._ps_run(cmd)
        if result['success'] and result['stdout']:
            try:
                data = json.loads(result['stdout'])
                if isinstance(data, dict):
                    data = [data]
                return data
            except json.JSONDecodeError:
                pass
        return []

    @staticmethod
    def knock_and_open(host: str, config: Dict = None) -> Dict:
        """Perform knocking sequence and open target port"""
        if config is None:
            config = KnockingModule.get_knocking_config()

        ports = config.get('ports', [7000, 8000, 9000])
        target_port = config.get('target_port', 22)
        timeout = config.get('timeout', 5)
        auto_close = config.get('auto_close_seconds', 30)

        # Send knock sequence
        logger.info(f"Sending knock to {host}: {ports}")
        knock_ok = KnockingModule.send_knock(host, ports, interval=0.5)

        if not knock_ok:
            return {'status': 'error', 'message': 'Failed to send knock sequence'}

        # Open target port
        rule_ok = KnockingModule.open_firewall_rule(
            target_port,
            description=f"Opened by knock sequence from {host}"
        )

        if not rule_ok:
            return {'status': 'error', 'message': 'Failed to open firewall rule'}

        # Auto-close after timeout
        if auto_close > 0:
            def auto_close_timer():
                time.sleep(auto_close)
                KnockingModule.close_firewall_rule(target_port)
                logger.info(f"Auto-closed port {target_port} after {auto_close}s")

            import threading
            timer = threading.Thread(target=auto_close_timer, daemon=True)
            timer.start()

        return {
            'status': 'success',
            'message': f'Port {target_port} opened. Auto-close in {auto_close}s.',
            'port': target_port,
            'auto_close': auto_close
        }

    @staticmethod
    def set_globals():
        """Set global variables for knocking"""
        is_windows = get_global('os_type', '') == 'windows'
        if is_windows:
            set_global('knocking_installed', True)
            active = KnockingModule.is_knocking_active()
            set_global('knocking_active', active)
        else:
            knocking_installed = get('knocking', 'is_knocking_installed')
            set_global('knocking_installed', knocking_installed)
