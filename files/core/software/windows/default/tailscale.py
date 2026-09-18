import subprocess
import sys
from typing import List
from files.core.base_module import BaseModule


def _si():
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = subprocess.SW_HIDE
    return si


class TailscaleModule(BaseModule):
    """Windows Tailscale installation via winget"""

    @staticmethod
    def check_tailscale_installed() -> bool:
        """Check if Tailscale is installed on Windows"""
        try:
            result = subprocess.run(['where', 'tailscale'], capture_output=True, text=True, startupinfo=_si())
            return result.returncode == 0
        except Exception:
            return False

    @staticmethod
    def return_commands_install_tailscale() -> List[str]:
        """Returns commands to install Tailscale on Windows via winget"""
        return [
            'winget install --id Tailscale.Tailscale -e --accept-source-agreements --accept-package-agreements'
        ]
