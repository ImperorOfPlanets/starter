from starter_files.core.base_module import BaseModule

import socket
import json
import platform
import subprocess
import sys

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from starter_files.core.utils.globalVars_utils import get_global, set_global

@dataclass
class NetworkConnection:
    ip: str
    netmask: str
    gateway: Optional[str] = None
    dns_servers: List[str] = None
    status: str = "Unknown"

@dataclass
class NetworkDevice:
    name: str
    mac: str
    is_physical: bool
    is_up: bool
    connections: List[NetworkConnection]
    speed: Optional[str] = None
    interface_id: Optional[str] = None

    def __post_init__(self):
        self.is_virtual = not self.is_physical

@dataclass
class BasicDeviceInfo:
    name: str
    is_up: bool
    is_physical: bool

class NetworkModule(BaseModule):

    @staticmethod
    def check() -> bool:
        """Всегда возвращает False, так как модуль не реализован"""
        return True
    
    @staticmethod
    def get_ips() -> list:
        """Базовый способ получения IP-адресов (default реализация)"""
        hostname = socket.gethostname()
        ip_address = socket.gethostbyname(hostname)
        return [ip_address] if ip_address else []

    @staticmethod
    def get_local_ip_fallback() -> str:
        """Простейший способ получить один локальный IP"""
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]

    @staticmethod
    def get_public_ip() -> str:
        """Получение публичного IP-адреса (default реализация)"""
        import requests
        return requests.get('https://api.ipify.org').text

    @staticmethod
    def get_basic_devices_info() -> Tuple[List[BasicDeviceInfo], List[BasicDeviceInfo]]:
        """Базовая реализация для неподдерживаемых ОС"""
        return [], []

    @staticmethod
    def get_all_local_ips() -> list:
        """Возвращает список локальных IP, учитывая Docker и хост"""
        cached_ips = get_global('local_ips')
        if cached_ips:
            return cached_ips

        ips = set()
        running_in_docker = get_global('running_in_docker')
        try:
            if running_in_docker:
                print("В ДОКЕРЕ")
                # В Docker fallback на localhost или eth0
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                    s.connect(("8.8.8.8", 80))
                    ips.add(s.getsockname()[0])
            else:
                system = platform.system()
                if system == "Windows":
                    hostname = socket.gethostname()
                    ip = socket.gethostbyname(hostname)
                    if ip:
                        ips.add(ip)
                else:
                    # POSIX
                    try:
                        output = subprocess.check_output("ip -4 addr", shell=True, text=True, stderr=subprocess.DEVNULL)
                        for line in output.splitlines():
                            line = line.strip()
                            if line.startswith("inet "):
                                ip = line.split()[1].split("/")[0]
                                if not ip.startswith("127."):
                                    ips.add(ip)
                    except Exception:
                        # fallback через сокет
                        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                            s.connect(("8.8.8.8", 80))
                            ips.add(s.getsockname()[0])
        except Exception as e:
            logger.info(f"[WARN] Не удалось получить локальные IP: {e}")

        ips_list = list(ips) if ips else ["0.0.0.0" if sys.platform != "win32" else "127.0.0.1"]
        set_global('local_ips', ips_list)
        return ips_list

    @staticmethod
    def get_network_devices() -> Tuple[List[NetworkDevice], List[NetworkDevice]]:
        """Базовая реализация для неподдерживаемых ОС"""
        return [], []

    @staticmethod
    def get_external_ip() -> Optional[str]:
        """Default реализация получения внешнего IP"""
        import requests
        return requests.get('https://api.ipify.org').text

    @staticmethod
    def get_local_ip() -> str:
        """Default реализация получения локального IP"""
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]