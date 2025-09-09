from starter_files.core.base_module import BaseModule

import socket
import platform
import os
import fcntl
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
    def check() -> bool:
        return True
    
    @staticmethod
    def get_local_ip_fallback() -> str:
        """Простейший способ получить локальный IP"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except:
            return "127.0.0.1"

    @staticmethod
    def get_public_ip() -> str:
        """Получение публичного IP-адреса"""
        try:
            import requests
            return requests.get('https://api.ipify.org').text
        except:
            return "N/A"

    @staticmethod
    def get_all_local_ips() -> list:
        """Возвращает список локальных IP адресов"""
        ips = set()
        
        try:
            # Пробуем разные методы получения IP
            ips.update(NetworkModule._get_ips_from_socket())
            ips.update(NetworkModule._get_ips_from_hostname())
            
            # Фильтруем невалидные адреса
            valid_ips = []
            for ip in ips:
                if ip and ip not in ['0.0.0.0', '127.0.0.1']:
                    valid_ips.append(ip)
            
            return valid_ips if valid_ips else ['127.0.0.1']
            
        except Exception as e:
            logger.error(f"Error getting local IPs: {str(e)}")
            return ['127.0.0.1']

    @staticmethod
    def _get_ips_from_socket() -> set:
        """Получает IP через socket"""
        ips = set()
        try:
            # Через подключение к внешнему серверу
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                if local_ip and local_ip != '0.0.0.0':
                    ips.add(local_ip)
        except:
            pass
        return ips

    @staticmethod
    def _get_ips_from_hostname() -> set:
        """Получает IP через hostname"""
        ips = set()
        try:
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
            if ip and ip != '0.0.0.0':
                ips.add(ip)
        except:
            pass
        return ips

    @staticmethod
    def get_network_devices() -> Tuple[List[NetworkDevice], List[NetworkDevice]]:
        """Основной метод получения сетевых устройств"""
        system = platform.system().lower()
        
        if system == "linux":
            return NetworkModule._get_linux_network_info()
        
        return [], []

    @staticmethod
    def _get_linux_network_info() -> Tuple[List[NetworkDevice], List[NetworkDevice]]:
        """Получает сетевую информацию для Linux"""
        physical_devices = []
        virtual_devices = []
        
        try:
            # Пробуем получить информацию через /sys
            devices = NetworkModule._get_from_sys_class()
            if devices:
                return devices
            
            # Fallback: минимальная информация
            return NetworkModule._get_linux_minimal()
            
        except Exception as e:
            logger.error(f"Error getting Linux network info: {str(e)}")
            return [], []

    @staticmethod
    def _get_from_sys_class() -> Tuple[List[NetworkDevice], List[NetworkDevice]]:
        """Читает информацию из /sys/class/net"""
        physical_devices = []
        virtual_devices = []
        
        try:
            net_path = Path('/sys/class/net')
            if net_path.exists():
                for iface_dir in net_path.iterdir():
                    if iface_dir.is_dir():
                        ifname = iface_dir.name
                        if ifname == 'lo':  # Пропускаем loopback
                            continue
                            
                        is_physical = not any(x in ifname for x in 
                                            ['docker', 'virbr', 'veth', 'br-', 'tun', 'wg'])
                        
                        # Проверяем статус
                        is_up = NetworkModule._check_interface_status(ifname)
                        
                        # Получаем MAC адрес
                        mac = NetworkModule._get_mac_address(ifname)
                        
                        # Получаем IP адреса
                        ips = NetworkModule._get_ip_addresses(ifname)
                        
                        connections = []
                        for ip_info in ips:
                            connection = NetworkConnection(
                                ip=ip_info['ip'],
                                netmask=str(ip_info['netmask']),
                                status="Up" if is_up else "Down"
                            )
                            connections.append(connection)
                        
                        device = NetworkDevice(
                            name=ifname,
                            mac=mac,
                            is_physical=is_physical,
                            is_up=is_up,
                            connections=connections
                        )
                        
                        if is_physical:
                            physical_devices.append(device)
                        else:
                            virtual_devices.append(device)
        
        except Exception as e:
            logger.error(f"Error reading from /sys: {str(e)}")
        
        return physical_devices, virtual_devices

    @staticmethod
    def _get_linux_minimal() -> Tuple[List[NetworkDevice], List[NetworkDevice]]:
        """Минимальная реализация для Linux"""
        physical_devices = []
        virtual_devices = []
        
        try:
            # Базовые интерфейсы, которые обычно есть
            common_interfaces = ['eth0', 'wlan0', 'docker0']
            
            for ifname in common_interfaces:
                # Проверяем существование интерфейса через /sys
                iface_path = Path(f'/sys/class/net/{ifname}')
                if iface_path.exists():
                    is_physical = ifname in ['eth0', 'wlan0']
                    is_up = NetworkModule._check_interface_status(ifname)
                    mac = NetworkModule._get_mac_address(ifname)
                    
                    device = NetworkDevice(
                        name=ifname,
                        mac=mac,
                        is_physical=is_physical,
                        is_up=is_up,
                        connections=[]
                    )
                    
                    if is_physical:
                        physical_devices.append(device)
                    else:
                        virtual_devices.append(device)
        
        except Exception as e:
            logger.error(f"Error in minimal Linux method: {str(e)}")
        
        return physical_devices, virtual_devices

    @staticmethod
    def _check_interface_status(ifname: str) -> bool:
        """Проверяет статус интерфейса"""
        try:
            operstate_path = Path(f'/sys/class/net/{ifname}/operstate')
            if operstate_path.exists():
                return operstate_path.read_text().strip() == 'up'
        except:
            pass
        return False

    @staticmethod
    def _get_mac_address(ifname: str) -> str:
        """Получает MAC адрес интерфейса"""
        try:
            mac_path = Path(f'/sys/class/net/{ifname}/address')
            if mac_path.exists():
                return mac_path.read_text().strip()
        except:
            pass
        return "N/A"

    @staticmethod
    def _get_ip_addresses(ifname: str) -> List[Dict[str, Any]]:
        """Получает IP адреса интерфейса"""
        ips = []
        
        try:
            # Пробуем получить через socket
            local_ip = NetworkModule.get_local_ip_fallback()
            if local_ip and local_ip != "127.0.0.1":
                ips.append({'ip': local_ip, 'netmask': 24})
        
        except Exception as e:
            logger.error(f"Error getting IP addresses for {ifname}: {str(e)}")
        
        return ips

    @staticmethod
    def detect_available_network_tools() -> Dict[str, bool]:
        """Определяет доступные сетевые утилиты"""
        return {
            'ip': False,
            'ifconfig': False,
            'ping': False,
            'netstat': False
        }

    @staticmethod
    def get_network_devices_with_tools() -> Tuple[List[NetworkDevice], List[NetworkDevice]]:
        """Алиас для совместимости"""
        return NetworkModule.get_network_devices()