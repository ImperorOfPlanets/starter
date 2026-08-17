import subprocess
from typing import List
from files.core.base_module import BaseModule


class TailscaleModule(BaseModule):
    """Windows Tailscale installation via winget"""

    @staticmethod
    def check_tailscale_installed() -> bool:
        """Check if Tailscale is installed on Windows"""
        try:
            result = subprocess.run(['where', 'tailscale'], capture_output=True, text=True)
            return result.returncode == 0
        except Exception:
            return False

    @staticmethod
    def return_commands_install_tailscale() -> List[str]:
        """Returns commands to install Tailscale on Windows via winget"""
        return [
            'winget install --id Tailscale.Tailscale -e --accept-source-agreements --accept-package-agreements'
        ]
