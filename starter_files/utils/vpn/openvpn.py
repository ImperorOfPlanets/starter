import subprocess
import shutil
from .base_client import BaseVPNClient

class OpenVPNClient(BaseVPNClient):
    CLIENT_NAME = "OpenVPN"
    CLIENT_ICON = "bi-lock"
    
    def is_installed(self) -> bool:
        return bool(shutil.which('openvpn'))

    def get_version(self) -> str:
        try:
            result = subprocess.run(
                ['openvpn', '--version'],
                capture_output=True, text=True, check=True
            )
            return result.stdout.split('\n')[0].split()[1]
        except:
            return 'N/A'

    def get_status(self) -> dict:
        status = {'connected': False, 'interfaces': []}
        if self.os == 'windows':
            try:
                result = subprocess.run(
                    ['tasklist', '/FI', 'IMAGENAME eq openvpn.exe'],
                    capture_output=True, text=True, check=True
                )
                status['connected'] = 'openvpn.exe' in result.stdout
            except:
                pass
        else:
            try:
                result = subprocess.run(
                    ['ps', 'aux'], capture_output=True, text=True, check=True
                )
                status['connected'] = 'openvpn' in result.stdout
            except:
                pass
        return status