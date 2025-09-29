from starter_files.core.base_module import BaseModule

import socket
import platform
import os
import struct
import struct
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass

from starter_files.core.utils.globalVars_utils import get_global
from starter_files.core.utils.log_utils import LogManager

logger = LogManager.get_logger('network')

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

class NetworkModule(BaseModule):

    @staticmethod
    def get_all_local_ips() -> list:
        """Возвращает список локальных IP адресов для Windows"""
        ips = set()
        
        try:
            # Для Windows используем socket.gethostbyname_ex
            hostname = socket.gethostname()
            _, _, ip_list = socket.gethostbyname_ex(hostname)
            ips.update(ip_list)
            
            # Добавляем localhost
            ips.add('127.0.0.1')
            ips.add('localhost')
            
            # Фильтруем невалидные адреса
            valid_ips = [ip for ip in ips if ip and ip != '0.0.0.0']
            
            return valid_ips if valid_ips else ['127.0.0.1']
            
        except Exception as e:
            logger.error(f"Error getting local IPs: {str(e)}")
            return ['127.0.0.1', 'localhost']