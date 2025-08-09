import os
import subprocess
from pathlib import Path
from .base_client import BaseVPNClient

class SoftEtherVPNClient(BaseVPNClient):
    CLIENT_NAME = "SoftEther VPN"
    CLIENT_ICON = "bi-shield-lock"
    
    def is_installed(self) -> bool:
        if self.os == 'windows':
            paths = [
                Path(os.environ.get('ProgramFiles', '')) / 'SoftEther VPN Client' / 'vpnclient.exe',
                Path(os.environ.get('ProgramFiles(x86)', '')) / 'SoftEther VPN Client' / 'vpnclient.exe'
            ]
            return any(p.exists() for p in paths)
        
        return bool(shutil.which('vpnclient'))

    def get_version(self) -> str:
        if self.os == 'windows':
            try:
                exe_path = next(
                    p for p in [
                        Path(os.environ.get('ProgramFiles', '')) / 'SoftEther VPN Client' / 'vpnclient.exe',
                        Path(os.environ.get('ProgramFiles(x86)', '')) / 'SoftEther VPN Client' / 'vpnclient.exe'
                    ] if p.exists()
                )
                result = subprocess.run(
                    ['wmic', 'datafile', 'where', f'name="{exe_path}"', 'get', 'version'],
                    capture_output=True, text=True, check=True
                )
                return result.stdout.split('\n')[1].strip()
            except:
                pass
        else:
            try:
                result = subprocess.run(
                    ['vpnclient', 'version'],
                    capture_output=True, text=True, check=True
                )
                return result.stdout.split('\n')[0].strip()
            except:
                pass
        return 'N/A'

    def get_status(self) -> dict:
        status = {'connected': False, 'interfaces': []}
        if self.os == 'windows':
            try:
                result = subprocess.run(
                    ['tasklist', '/FI', 'IMAGENAME eq vpnclient.exe'],
                    capture_output=True, text=True, check=True
                )
                status['connected'] = 'vpnclient.exe' in result.stdout
            except:
                pass
        else:
            try:
                result = subprocess.run(
                    ['ps', 'aux'], capture_output=True, text=True, check=True
                )
                status['connected'] = 'vpnclient' in result.stdout
            except:
                pass
        return status