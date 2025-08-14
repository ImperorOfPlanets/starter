from starter_files.utils.oss.base_module import BaseModule
import socket
import logging
import json
import platform
import subprocess
import re

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from starter_files.utils.globalVars_utils import get_global, set_global

logger = logging.getLogger(__name__)

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
    @classmethod
    def check(cls) -> bool:
        """Проверка доступности модуля"""
        return True  # Всегда доступен
    
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
        """Получаем все локальные IP и кешируем их"""
        cached_ips = get_global('local_ips')
        if cached_ips:
            return cached_ips

        # Получаем устройства
        network_mod = get_network_module()
        physical, virtual = network_mod.get_network_devices()

        ips = []
        for dev in physical + virtual:
            for conn in dev.connections:
                if conn.status.lower() == 'up' and conn.ip:
                    ips.append(conn.ip)

        # Если ничего не нашли — хотя бы один способ по-умолчанию
        if not ips:
            ips.append(NetworkModule.get_local_ip_fallback())

        set_global('local_ips', ips)

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


class WindowsNetworkModule(NetworkModule):
    """Специализированная реализация для Windows"""
    
    @staticmethod
    def get_basic_devices_info() -> Tuple[List[BasicDeviceInfo], List[BasicDeviceInfo]]:
        ps_script = """
        $adapters = Get-NetAdapter -IncludeHidden | Where-Object {
            $_.InterfaceDescription -notmatch 'TAP|NDIS|WFP|Loopback|Microsoft'
        }
        
        $result = @()
        foreach ($adapter in $adapters) {
            $result += [PSCustomObject]@{
                Name = $adapter.InterfaceDescription
                IsPhysical = $adapter.InterfaceDescription -notmatch 'Virtual|VPN|Tunnel'
                IsUp = $adapter.Status -eq 'Up'
            }
        }
        
        $result | ConvertTo-Json -Depth 2
        """
        
        result = subprocess.run(
            ['powershell', '-Command', ps_script],
            capture_output=True,
            text=True,
            encoding='utf-8',
            check=True
        )
        
        if result.returncode != 0:
            logger.warning("Windows implementation failed, falling back to default")
            return NetworkModule.get_basic_devices_info()
        
        devices = [
            BasicDeviceInfo(
                name=item['Name'],
                is_up=item['IsUp'],
                is_physical=item['IsPhysical']
            ) for item in json.loads(result.stdout)
        ]
        
        physical = [d for d in devices if d.is_physical]
        virtual = [d for d in devices if not d.is_physical]
        
        return physical, virtual

    @staticmethod
    def get_network_devices() -> Tuple[List[NetworkDevice], List[NetworkDevice]]:
        ps_script = """
        function Get-InterfaceDetails {
            param($adapter)
            
            $details = @{
                IPs = @()
                Gateways = @()
                DnsServers = @()
            }
            
            $ipConfigs = Get-NetIPAddress -InterfaceIndex $adapter.ifIndex -AddressFamily IPv4 -ErrorAction SilentlyContinue
            foreach ($ipConfig in $ipConfigs) {
                $details.IPs += @{
                    Address = $ipConfig.IPAddress
                    Netmask = $ipConfig.PrefixLength
                }
                
                $route = Get-NetRoute -InterfaceIndex $adapter.ifIndex -DestinationPrefix '0.0.0.0/0' -ErrorAction SilentlyContinue
                if ($route) {
                    $details.Gateways += $route.NextHop
                }
                
                $dns = Get-DnsClientServerAddress -InterfaceIndex $adapter.ifIndex -AddressFamily IPv4 -ErrorAction SilentlyContinue
                if ($dns) {
                    $details.DnsServers += $dns.ServerAddresses
                }
            }
            
            return $details
        }

        $adapters = Get-NetAdapter -IncludeHidden | Where-Object {
            $_.InterfaceDescription -notmatch 'TAP|NDIS|WFP|Loopback|Microsoft'
        }
        
        $result = @()
        foreach ($adapter in $adapters) {
            $details = Get-InterfaceDetails $adapter
            $connections = @()
            
            for ($i = 0; $i -lt $details.IPs.Count; $i++) {
                $connections += @{
                    IP = $details.IPs[$i].Address
                    Netmask = $details.IPs[$i].Netmask
                    Gateway = if ($i -lt $details.Gateways.Count) { $details.Gateways[$i] } else { $null }
                    DnsServers = $details.DnsServers
                    Status = if ($adapter.Status -eq 'Up') { 'Up' } else { 'Down' }
                }
            }
            
            $result += [PSCustomObject]@{
                Name = $adapter.InterfaceDescription
                Mac = $adapter.MacAddress
                IsPhysical = $adapter.InterfaceDescription -notmatch 'Virtual|VPN|Tunnel'
                IsUp = $adapter.Status -eq 'Up'
                Speed = if ($adapter.LinkSpeed) { "$($adapter.LinkSpeed) Mbps" } else { $null }
                Connections = $connections
                InterfaceId = $adapter.InterfaceGuid
            }
        }
        
        $result | ConvertTo-Json -Depth 5
        """
        
        result = subprocess.run(
            ['powershell', '-Command', ps_script],
            capture_output=True,
            text=True,
            encoding='utf-8',
            check=True
        )
        
        if result.returncode != 0:
            logger.warning("Windows implementation failed, falling back to default")
            return NetworkModule.get_network_devices()
        
        devices = [
            NetworkDevice(
                name=item['Name'],
                mac=item['Mac'],
                is_physical=item['IsPhysical'],
                is_up=item['IsUp'],
                speed=item['Speed'],
                connections=[
                    NetworkConnection(
                        ip=conn['IP'],
                        netmask=str(conn['Netmask']),
                        gateway=conn['Gateway'],
                        dns_servers=conn['DnsServers'],
                        status=conn['Status']
                    ) for conn in item['Connections']
                ],
                interface_id=item['InterfaceId']
            ) for item in json.loads(result.stdout)
        ]
        
        physical = [d for d in devices if d.is_physical]
        virtual = [d for d in devices if not d.is_physical]
        
        return physical, virtual


class LinuxNetworkModule(NetworkModule):
    """Специализированная реализация для Linux"""
    
    @staticmethod
    def get_basic_devices_info() -> Tuple[List[BasicDeviceInfo], List[BasicDeviceInfo]]:
        interfaces = subprocess.check_output(["ip", "-j", "link"], text=True)
        interfaces = json.loads(interfaces)
        
        devices = []
        
        for iface in interfaces:
            ifname = iface['ifname']
            
            if ifname.startswith('lo') or ifname.startswith('docker') or ifname.startswith('veth'):
                continue
                
            is_physical = not (ifname.startswith('virbr') or ifname.startswith('vnet') or ifname.startswith('tun'))
            
            devices.append(BasicDeviceInfo(
                name=ifname,
                is_up=iface['operstate'] == 'UP',
                is_physical=is_physical
            ))
        
        physical = [d for d in devices if d.is_physical]
        virtual = [d for d in devices if not d.is_physical]
        
        return physical, virtual

    @staticmethod
    def get_network_devices() -> Tuple[List[NetworkDevice], List[NetworkDevice]]:
        interfaces = subprocess.check_output(["ip", "-j", "link"], text=True)
        interfaces = json.loads(interfaces)
        
        devices = []
        
        for iface in interfaces:
            ifname = iface['ifname']
            
            if ifname.startswith('lo') or ifname.startswith('docker') or ifname.startswith('veth'):
                continue
                
            is_physical = not (ifname.startswith('virbr') or ifname.startswith('vnet') or ifname.startswith('tun'))
            
            ips = subprocess.check_output(["ip", "-j", "addr", "show", "dev", ifname], text=True)
            ips = json.loads(ips)
            
            connections = []
            for addr_info in ips[0]['addr_info']:
                if addr_info['family'] == 'inet':
                    connections.append(NetworkConnection(
                        ip=addr_info['local'],
                        netmask=str(addr_info['prefixlen']),
                        gateway=LinuxNetworkModule._get_linux_gateway(ifname),
                        dns_servers=LinuxNetworkModule._get_linux_dns(),
                        status='Up' if iface['operstate'] == 'UP' else 'Down'
                    ))
            
            speed = None
            try:
                with open(f"/sys/class/net/{ifname}/speed", 'r') as f:
                    speed = f"{f.read().strip()} Mbps"
            except:
                pass
            
            devices.append(NetworkDevice(
                name=ifname,
                mac=iface['address'],
                is_physical=is_physical,
                is_up=iface['operstate'] == 'UP',
                connections=connections,
                speed=speed
            ))
        
        physical = [d for d in devices if d.is_physical]
        virtual = [d for d in devices if not d.is_physical]
        
        return physical, virtual

    @staticmethod
    def _get_linux_gateway(interface: str) -> Optional[str]:
        result = subprocess.check_output(["ip", "-j", "route", "show", "default"], text=True)
        routes = json.loads(result)
        for route in routes:
            if route.get('dev') == interface:
                return route.get('gateway')
        return None

    @staticmethod
    def _get_linux_dns() -> List[str]:
        with open('/etc/resolv.conf', 'r') as f:
            return [
                line.split()[1] 
                for line in f 
                if line.startswith('nameserver')
            ]


class MacNetworkModule(NetworkModule):
    """Специализированная реализация для macOS"""
    # Реализация будет добавлена по мере необходимости
    pass


def get_network_module() -> NetworkModule:
    """Фабрика для получения правильной реализации модуля"""
    system = platform.system().lower()
    
    if system == "windows":
        return WindowsNetworkModule()
    elif system == "linux":
        return LinuxNetworkModule()
    elif system == "darwin":
        return MacNetworkModule()
    else:
        return NetworkModule()  # Default реализация