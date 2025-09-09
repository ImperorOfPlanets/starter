from starter_files.core.base_module import BaseModule

import socket
import json
import platform
import subprocess
import sys
import re
import os
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from starter_files.core.utils.globalVars_utils import get_global, set_global
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

@dataclass
class BasicDeviceInfo:
    name: str
    is_up: bool
    is_physical: bool

class NetworkModule(BaseModule):

    @staticmethod
    def check() -> bool:
        """Всегда возвращает True, так как модуль реализован"""
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
        try:
            import requests
            return requests.get('https://api.ipify.org').text
        except:
            return "N/A"

    @staticmethod
    def get_basic_devices_info() -> Tuple[List[BasicDeviceInfo], List[BasicDeviceInfo]]:
        """Получение базовой информации об устройствах"""
        physical_devices = []
        virtual_devices = []
        
        try:
            system = platform.system().lower()
            
            if system == "linux":
                # Для Linux используем ip link
                result = subprocess.run(['ip', 'link', 'show'], 
                                      capture_output=True, text=True, check=False)
                if result.returncode == 0:
                    lines = result.stdout.splitlines()
                    current_device = None
                    
                    for line in lines:
                        if ':' in line and not line.startswith(' '):
                            # Новая сетевая карта
                            parts = line.split(':')
                            if len(parts) >= 3:
                                device_name = parts[1].strip()
                                flags = parts[2]
                                is_up = 'UP' in flags
                                is_physical = not any(x in device_name for x in ['docker', 'virbr', 'veth', 'br-', 'lo'])
                                
                                device_info = BasicDeviceInfo(
                                    name=device_name,
                                    is_up=is_up,
                                    is_physical=is_physical
                                )
                                
                                if is_physical:
                                    physical_devices.append(device_info)
                                else:
                                    virtual_devices.append(device_info)
            
            elif system == "windows":
                # Для Windows используем ipconfig
                result = subprocess.run(['ipconfig', '/all'], 
                                      capture_output=True, text=True, check=False)
                if result.returncode == 0:
                    lines = result.stdout.split('\n')
                    current_adapter = None
                    
                    for line in lines:
                        line = line.strip()
                        if line.endswith(':'):
                            # Название адаптера
                            current_adapter = line[:-1].strip()
                        elif 'Media disconnected' not in line and current_adapter:
                            # Активный адаптер
                            is_physical = not any(x in current_adapter.lower() for x in ['virtual', 'docker', 'vpn', 'bluetooth'])
                            
                            device_info = BasicDeviceInfo(
                                name=current_adapter,
                                is_up=True,
                                is_physical=is_physical
                            )
                            
                            if is_physical:
                                physical_devices.append(device_info)
                            else:
                                virtual_devices.append(device_info)
                            current_adapter = None
            
            elif system == "darwin":
                # Для macOS используем networksetup
                result = subprocess.run(['networksetup', '-listallhardwareports'], 
                                      capture_output=True, text=True, check=False)
                if result.returncode == 0:
                    lines = result.stdout.splitlines()
                    current_device = None
                    
                    for line in lines:
                        if 'Hardware Port:' in line:
                            device_name = line.split(':', 1)[1].strip()
                            is_physical = not any(x in device_name.lower() for x in ['virtual', 'docker', 'vpn'])
                            
                            # Проверяем статус
                            status_result = subprocess.run(['ifconfig', device_name], 
                                                         capture_output=True, text=True, check=False)
                            is_up = 'status: active' in status_result.stdout.lower()
                            
                            device_info = BasicDeviceInfo(
                                name=device_name,
                                is_up=is_up,
                                is_physical=is_physical
                            )
                            
                            if is_physical:
                                physical_devices.append(device_info)
                            else:
                                virtual_devices.append(device_info)
        
        except Exception as e:
            logger.error(f"Error getting basic devices info: {str(e)}")
        
        return physical_devices, virtual_devices

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
        """Получение полной информации о сетевых устройствах"""
        physical_devices = []
        virtual_devices = []
        
        try:
            system = platform.system().lower()
            
            if system == "linux":
                # Получаем информацию об интерфейсах
                link_result = subprocess.run(['ip', 'link', 'show'], 
                                           capture_output=True, text=True, check=False)
                addr_result = subprocess.run(['ip', 'addr', 'show'], 
                                           capture_output=True, text=True, check=False)
                
                if link_result.returncode == 0 and addr_result.returncode == 0:
                    interfaces = {}
                    
                    # Парсим информацию о линках
                    for line in link_result.stdout.splitlines():
                        if ':' in line and not line.startswith(' '):
                            parts = line.split(':')
                            if len(parts) >= 3:
                                ifname = parts[1].strip()
                                flags = parts[2]
                                is_up = 'UP' in flags
                                
                                # Получаем MAC адрес
                                mac_match = re.search(r'link/(?:ether|loopback)\s+([0-9a-f:]+)', line, re.I)
                                mac = mac_match.group(1) if mac_match else "N/A"
                                
                                interfaces[ifname] = {
                                    'name': ifname,
                                    'mac': mac,
                                    'is_up': is_up,
                                    'is_physical': not any(x in ifname for x in ['docker', 'virbr', 'veth', 'br-', 'lo']),
                                    'connections': []
                                }
                    
                    # Парсим IP адреса
                    current_interface = None
                    for line in addr_result.stdout.splitlines():
                        if line.strip().startswith('inet '):
                            if current_interface and current_interface in interfaces:
                                parts = line.strip().split()
                                if len(parts) >= 2:
                                    ip_with_mask = parts[1]
                                    ip = ip_with_mask.split('/')[0]
                                    netmask = ip_with_mask.split('/')[1] if '/' in ip_with_mask else "24"
                                    
                                    connection = NetworkConnection(
                                        ip=ip,
                                        netmask=netmask,
                                        status="Up" if interfaces[current_interface]['is_up'] else "Down"
                                    )
                                    interfaces[current_interface]['connections'].append(connection)
                        
                        elif ':' in line and not line.startswith(' '):
                            parts = line.split(':')
                            if len(parts) >= 2:
                                current_interface = parts[1].strip()
                    
                    # Создаем объекты NetworkDevice
                    for ifname, info in interfaces.items():
                        device = NetworkDevice(
                            name=info['name'],
                            mac=info['mac'],
                            is_physical=info['is_physical'],
                            is_up=info['is_up'],
                            connections=info['connections']
                        )
                        
                        if info['is_physical']:
                            physical_devices.append(device)
                        else:
                            virtual_devices.append(device)
            
            elif system == "windows":
                # Базовая реализация для Windows
                result = subprocess.run(['ipconfig', '/all'], 
                                      capture_output=True, text=True, check=False)
                if result.returncode == 0:
                    lines = result.stdout.split('\n')
                    current_adapter = None
                    current_mac = "N/A"
                    connections = []
                    
                    for line in lines:
                        line = line.strip()
                        if 'adapter' in line.lower() and line.endswith(':'):
                            # Сохраняем предыдущий адаптер
                            if current_adapter:
                                is_physical = not any(x in current_adapter.lower() for x in ['virtual', 'docker', 'vpn'])
                                
                                device = NetworkDevice(
                                    name=current_adapter,
                                    mac=current_mac,
                                    is_physical=is_physical,
                                    is_up=len(connections) > 0,
                                    connections=connections
                                )
                                
                                if is_physical:
                                    physical_devices.append(device)
                                else:
                                    virtual_devices.append(device)
                            
                            # Новый адаптер
                            current_adapter = line[:-1].strip()
                            current_mac = "N/A"
                            connections = []
                        
                        elif 'physical address' in line.lower():
                            parts = line.split(':')
                            if len(parts) > 1:
                                current_mac = parts[1].strip()
                        
                        elif 'ipv4 address' in line.lower():
                            parts = line.split(':')
                            if len(parts) > 1:
                                ip = parts[1].strip()
                                connection = NetworkConnection(
                                    ip=ip,
                                    netmask="24",  # По умолчанию для Windows
                                    status="Up"
                                )
                                connections.append(connection)
                    
                    # Добавляем последний адаптер
                    if current_adapter:
                        is_physical = not any(x in current_adapter.lower() for x in ['virtual', 'docker', 'vpn'])
                        
                        device = NetworkDevice(
                            name=current_adapter,
                            mac=current_mac,
                            is_physical=is_physical,
                            is_up=len(connections) > 0,
                            connections=connections
                        )
                        
                        if is_physical:
                            physical_devices.append(device)
                        else:
                            virtual_devices.append(device)
            
            elif system == "darwin":
                # Базовая реализация для macOS
                result = subprocess.run(['ifconfig'], 
                                      capture_output=True, text=True, check=False)
                if result.returncode == 0:
                    interfaces = {}
                    current_interface = None
                    
                    for line in result.stdout.splitlines():
                        if not line.startswith(' '):
                            # Новая сетевая карта
                            current_interface = line.split(':')[0]
                            interfaces[current_interface] = {
                                'mac': 'N/A',
                                'is_up': False,
                                'connections': []
                            }
                        
                        elif 'ether' in line:
                            parts = line.split()
                            if len(parts) >= 2:
                                interfaces[current_interface]['mac'] = parts[1]
                        
                        elif 'status: active' in line:
                            interfaces[current_interface]['is_up'] = True
                        
                        elif 'inet ' in line and not 'inet6' in line:
                            parts = line.split()
                            if len(parts) >= 2:
                                ip = parts[1]
                                connection = NetworkConnection(
                                    ip=ip,
                                    netmask="24",  # По умолчанию для macOS
                                    status="Up" if interfaces[current_interface]['is_up'] else "Down"
                                )
                                interfaces[current_interface]['connections'].append(connection)
                    
                    for ifname, info in interfaces.items():
                        is_physical = not any(x in ifname for x in ['docker', 'veth', 'bridge', 'lo'])
                        
                        device = NetworkDevice(
                            name=ifname,
                            mac=info['mac'],
                            is_physical=is_physical,
                            is_up=info['is_up'],
                            connections=info['connections']
                        )
                        
                        if is_physical:
                            physical_devices.append(device)
                        else:
                            virtual_devices.append(device)
        
        except Exception as e:
            logger.error(f"Error getting network devices: {str(e)}")
        
        return physical_devices, virtual_devices

    @staticmethod
    def get_external_ip() -> Optional[str]:
        """Default реализация получения внешнего IP"""
        try:
            import requests
            return requests.get('https://api.ipify.org').text
        except:
            return None

    @staticmethod
    def get_local_ip() -> str:
        """Default реализация получения локального IP"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except:
            return "127.0.0.1"

@staticmethod
def detect_available_network_tools() -> Dict[str, bool]:
    """Определяет доступные сетевые утилиты для сбора информации"""
    system = platform.system().lower()
    tools = {}
    
    # Общие утилиты для всех ОС
    common_tools = ['ping', 'netstat', 'route', 'arp']
    
    # Специфичные утилиты
    if system == "linux":
        linux_tools = ['ip', 'ifconfig', 'ss', 'nmcli', 'iwconfig', 'ethtool', 'tcpdump']
        tools_to_check = common_tools + linux_tools
    elif system == "windows":
        windows_tools = ['ipconfig', 'netsh', 'tracert', 'getmac']
        tools_to_check = common_tools + windows_tools
    elif system == "darwin":
        darwin_tools = ['ifconfig', 'networksetup', 'traceroute']
        tools_to_check = common_tools + darwin_tools
    else:
        tools_to_check = common_tools
    
    for tool in tools_to_check:
        try:
            if system == "windows":
                result = subprocess.run(['where', tool], 
                                      capture_output=True, text=True, check=False)
                tools[tool] = result.returncode == 0
            else:
                result = subprocess.run(['which', tool], 
                                      capture_output=True, text=True, check=False)
                tools[tool] = result.returncode == 0
        except:
            tools[tool] = False
    
    return tools

@staticmethod
def get_network_devices_with_tools() -> Tuple[List[NetworkDevice], List[NetworkDevice]]:
    """Получает сетевые устройства используя доступные утилиты"""
    system = platform.system().lower()
    tools = NetworkModule.detect_available_network_tools()
    
    logger.info(f"Available network tools: {tools}")
    
    # Пробуем разные методы в порядке приоритета
    if system == "linux":
        if tools.get('ip', False):
            devices = NetworkModule._get_linux_with_ip()
            if devices: return devices
        
        if tools.get('ifconfig', False):
            devices = NetworkModule._get_linux_with_ifconfig()
            if devices: return devices
        
        # Fallback: читаем из /sys/class/net
        devices = NetworkModule._get_linux_from_sys()
        if devices: return devices
    
    elif system == "windows":
        if tools.get('ipconfig', False):
            devices = NetworkModule._get_windows_with_ipconfig()
            if devices: return devices
        
        if tools.get('netsh', False):
            devices = NetworkModule._get_windows_with_netsh()
            if devices: return devices
    
    elif system == "darwin":
        if tools.get('ifconfig', False):
            devices = NetworkModule._get_darwin_with_ifconfig()
            if devices: return devices
        
        if tools.get('networksetup', False):
            devices = NetworkModule._get_darwin_with_networksetup()
            if devices: return devices
    
    # Если ничего не сработало, возвращаем пустые списки
    return [], []

@staticmethod
def _get_linux_with_ip() -> Tuple[List[NetworkDevice], List[NetworkDevice]]:
    """Использует modern ip utility для Linux"""
    physical_devices = []
    virtual_devices = []
    
    try:
        # Получаем информацию об интерфейсах в JSON формате
        result = subprocess.run(['ip', '-j', 'link', 'show'], 
                              capture_output=True, text=True, check=False)
        if result.returncode == 0:
            interfaces = json.loads(result.stdout)
            
            for iface in interfaces:
                ifname = iface.get('ifname', '')
                is_physical = not any(x in ifname for x in 
                                    ['docker', 'virbr', 'veth', 'br-', 'lo', 'tun', 'wg'])
                
                # Получаем IP адреса для этого интерфейса
                ip_result = subprocess.run(['ip', '-j', 'addr', 'show', 'dev', ifname], 
                                         capture_output=True, text=True, check=False)
                connections = []
                
                if ip_result.returncode == 0:
                    ip_info = json.loads(ip_result.stdout)
                    for addr in ip_info[0].get('addr_info', []):
                        if addr.get('family') == 'inet':
                            connection = NetworkConnection(
                                ip=addr.get('local', 'N/A'),
                                netmask=str(addr.get('prefixlen', '24')),
                                status="Up" if iface.get('operstate') == 'UP' else "Down"
                            )
                            connections.append(connection)
                
                device = NetworkDevice(
                    name=ifname,
                    mac=iface.get('address', 'N/A'),
                    is_physical=is_physical,
                    is_up=iface.get('operstate') == 'UP',
                    connections=connections
                )
                
                if is_physical:
                    physical_devices.append(device)
                else:
                    virtual_devices.append(device)
    
    except Exception as e:
        logger.error(f"Error with ip utility: {str(e)}")
    
    return physical_devices, virtual_devices

@staticmethod
def _get_linux_with_ifconfig() -> Tuple[List[NetworkDevice], List[NetworkDevice]]:
    """Использует традиционный ifconfig для Linux"""
    physical_devices = []
    virtual_devices = []
    
    try:
        result = subprocess.run(['ifconfig', '-a'], 
                              capture_output=True, text=True, check=False)
        if result.returncode == 0:
            lines = result.stdout.splitlines()
            current_iface = None
            current_mac = "N/A"
            current_status = "Down"
            connections = []
            
            for line in lines:
                if not line.startswith(' '):
                    # Сохраняем предыдущий интерфейс
                    if current_iface:
                        is_physical = not any(x in current_iface for x in 
                                            ['docker', 'virbr', 'veth', 'br-', 'lo', 'tun'])
                        
                        device = NetworkDevice(
                            name=current_iface,
                            mac=current_mac,
                            is_physical=is_physical,
                            is_up=current_status == "Up",
                            connections=connections.copy()
                        )
                        
                        if is_physical:
                            physical_devices.append(device)
                        else:
                            virtual_devices.append(device)
                    
                    # Новый интерфейс
                    current_iface = line.split(':')[0]
                    current_mac = "N/A"
                    current_status = "Down"
                    connections = []
                    
                    if 'UP' in line:
                        current_status = "Up"
                
                elif 'ether' in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        current_mac = parts[1]
                
                elif 'inet ' in line and 'inet6' not in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        ip = parts[1]
                        netmask = "24"
                        
                        # Пытаемся определить netmask
                        netmask_index = -1
                        for i, part in enumerate(parts):
                            if 'netmask' in part.lower():
                                netmask_index = i + 1
                                break
                        
                        if netmask_index < len(parts):
                            netmask_hex = parts[netmask_index]
                            if netmask_hex.startswith('0x'):
                                # Конвертируем hex в CIDR
                                netmask_int = int(netmask_hex, 16)
                                netmask = bin(netmask_int).count('1')
                        
                        connection = NetworkConnection(
                            ip=ip,
                            netmask=str(netmask),
                            status=current_status
                        )
                        connections.append(connection)
            
            # Добавляем последний интерфейс
            if current_iface:
                is_physical = not any(x in current_iface for x in 
                                    ['docker', 'virbr', 'veth', 'br-', 'lo', 'tun'])
                
                device = NetworkDevice(
                    name=current_iface,
                    mac=current_mac,
                    is_physical=is_physical,
                    is_up=current_status == "Up",
                    connections=connections
                )
                
                if is_physical:
                    physical_devices.append(device)
                else:
                    virtual_devices.append(device)
    
    except Exception as e:
        logger.error(f"Error with ifconfig: {str(e)}")
    
    return physical_devices, virtual_devices

@staticmethod
def _get_linux_from_sys() -> Tuple[List[NetworkDevice], List[NetworkDevice]]:
    """Читает информацию из /sys/class/net (fallback)"""
    physical_devices = []
    virtual_devices = []
    
    try:
        net_path = Path('/sys/class/net')
        if net_path.exists():
            for iface_dir in net_path.iterdir():
                if iface_dir.is_dir():
                    ifname = iface_dir.name
                    is_physical = not any(x in ifname for x in 
                                        ['docker', 'virbr', 'veth', 'br-', 'lo', 'tun'])
                    
                    # Читаем MAC адрес
                    mac_file = iface_dir / 'address'
                    mac = mac_file.read_text().strip() if mac_file.exists() else "N/A"
                    
                    # Проверяем статус
                    operstate_file = iface_dir / 'operstate'
                    is_up = operstate_file.read_text().strip() == 'up' if operstate_file.exists() else False
                    
                    device = NetworkDevice(
                        name=ifname,
                        mac=mac,
                        is_physical=is_physical,
                        is_up=is_up,
                        connections=[]  # IP адреса через sys не получим
                    )
                    
                    if is_physical:
                        physical_devices.append(device)
                    else:
                        virtual_devices.append(device)
    
    except Exception as e:
        logger.error(f"Error reading from /sys: {str(e)}")
    
    return physical_devices, virtual_devices

@staticmethod
def _get_windows_with_ipconfig() -> Tuple[List[NetworkDevice], List[NetworkDevice]]:
    """Использует ipconfig для Windows"""
    physical_devices = []
    virtual_devices = []
    
    try:
        result = subprocess.run(['ipconfig', '/all'], 
                              capture_output=True, text=True, check=False)
        if result.returncode == 0:
            lines = result.stdout.splitlines()
            current_adapter = None
            current_mac = "N/A"
            connections = []
            
            for line in lines:
                line = line.strip()
                if line.endswith(':') and 'adapter' in line.lower():
                    # Сохраняем предыдущий адаптер
                    if current_adapter:
                        is_physical = not any(x in current_adapter.lower() for x in 
                                            ['virtual', 'docker', 'vpn', 'bluetooth', 'loopback'])
                        
                        device = NetworkDevice(
                            name=current_adapter,
                            mac=current_mac,
                            is_physical=is_physical,
                            is_up=len(connections) > 0,
                            connections=connections.copy()
                        )
                        
                        if is_physical:
                            physical_devices.append(device)
                        else:
                            virtual_devices.append(device)
                    
                    # Новый адаптер
                    current_adapter = line[:-1].strip()
                    current_mac = "N/A"
                    connections = []
                
                elif 'physical address' in line.lower():
                    parts = line.split(':')
                    if len(parts) > 1:
                        current_mac = parts[1].strip()
                
                elif 'ipv4 address' in line.lower():
                    parts = line.split(':')
                    if len(parts) > 1:
                        ip = parts[1].strip()
                        connection = NetworkConnection(
                            ip=ip,
                            netmask="24",  # Windows не показывает netmask в ipconfig
                            status="Up"
                        )
                        connections.append(connection)
            
            # Добавляем последний адаптер
            if current_adapter:
                is_physical = not any(x in current_adapter.lower() for x in 
                                    ['virtual', 'docker', 'vpn', 'bluetooth', 'loopback'])
                
                device = NetworkDevice(
                    name=current_adapter,
                    mac=current_mac,
                    is_physical=is_physical,
                    is_up=len(connections) > 0,
                    connections=connections
                )
                
                if is_physical:
                    physical_devices.append(device)
                else:
                    virtual_devices.append(device)
    
    except Exception as e:
        logger.error(f"Error with ipconfig: {str(e)}")
    
    return physical_devices, virtual_devices