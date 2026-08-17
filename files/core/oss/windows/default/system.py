from files.core.base_module import BaseModule
import platform
import subprocess
from typing import Dict, Any
from files.core.utils.globalVars_utils import set_global

try:
    import psutil
    _psutil_available = True
except ImportError:
    _psutil_available = False

try:
    import winreg
    _winreg_available = True
except ImportError:
    _winreg_available = False


class SystemModule(BaseModule):
    """Windows-specific system info via psutil"""

    @staticmethod
    def check() -> bool:
        return platform.system() == "Windows"

    @staticmethod
    def set_globals():
        if not _psutil_available:
            return
        cpu = SystemModule.get_cpu_info()
        set_global('cpu_model', cpu.get('name', 'N/A'))
        set_global('cpu_cores', cpu.get('cores', 'N/A'))
        set_global('cpu_logical_cores', cpu.get('logical_cores', 'N/A'))
        set_global('cpu_usage', cpu.get('usage', 'N/A'))

        mem = SystemModule.get_memory_info()
        set_global('memory_total', mem.get('total', 'N/A'))
        set_global('memory_used', mem.get('used', 'N/A'))
        set_global('memory_percent', mem.get('percent', 'N/A'))
        set_global('memory_available', mem.get('available', 'N/A'))

        disk = SystemModule.get_disk_info()
        set_global('disk_total', disk.get('total', 'N/A'))
        set_global('disk_used', disk.get('used', 'N/A'))
        set_global('disk_percent', disk.get('percent', 'N/A'))
        set_global('disk_free', disk.get('free', 'N/A'))

    @staticmethod
    def get_cpu_info() -> Dict[str, Any]:
        if not _psutil_available:
            return {'name': 'N/A', 'cores': 'N/A', 'logical_cores': 'N/A', 'usage': 'N/A'}
        try:
            cpu_info = {
                'name': 'N/A',
                'cores': psutil.cpu_count(logical=False) or 'N/A',
                'logical_cores': psutil.cpu_count(logical=True) or 'N/A',
                'usage': f"{psutil.cpu_percent(interval=1):.1f}%"
            }
            if _winreg_available:
                try:
                    key = winreg.OpenKey(
                        winreg.HKEY_LOCAL_MACHINE,
                        r"Hardware\Description\System\CentralProcessor\0"
                    )
                    cpu_info['name'] = winreg.QueryValueEx(key, "ProcessorNameString")[0].strip()
                    winreg.CloseKey(key)
                except Exception:
                    cpu_info['name'] = platform.processor() or 'N/A'
            return cpu_info
        except Exception:
            return {'name': 'N/A', 'cores': 'N/A', 'logical_cores': 'N/A', 'usage': 'N/A'}

    @staticmethod
    def get_memory_info() -> Dict[str, Any]:
        if not _psutil_available:
            return {'total': 'N/A', 'used': 'N/A', 'percent': 'N/A', 'available': 'N/A'}
        try:
            mem = psutil.virtual_memory()
            return {
                'total': f"{mem.total / (1024**3):.2f} GB",
                'used': f"{mem.used / (1024**3):.2f} GB",
                'percent': f"{mem.percent:.1f}%",
                'available': f"{mem.available / (1024**3):.2f} GB"
            }
        except Exception:
            return {'total': 'N/A', 'used': 'N/A', 'percent': 'N/A', 'available': 'N/A'}

    @staticmethod
    def get_disk_info() -> Dict[str, Any]:
        if not _psutil_available:
            return {'total': 'N/A', 'used': 'N/A', 'percent': 'N/A', 'free': 'N/A'}
        try:
            disk = psutil.disk_usage('C:\\')
            return {
                'total': f"{disk.total / (1024**3):.2f} GB",
                'used': f"{disk.used / (1024**3):.2f} GB",
                'percent': f"{disk.percent:.1f}%",
                'free': f"{disk.free / (1024**3):.2f} GB"
            }
        except Exception:
            return {'total': 'N/A', 'used': 'N/A', 'percent': 'N/A', 'free': 'N/A'}
