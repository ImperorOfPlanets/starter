import json
import platform
import socket
import subprocess
import re
from typing import List, Dict, Optional, Tuple
import logging
from dataclasses import dataclass

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

def get_basic_devices_info() -> Tuple[List[BasicDeviceInfo], List[BasicDeviceInfo]]:
    """Возвращает только базовую информацию об устройствах"""
    system = platform.system().lower()
    
    if system == "windows":
        return _get_windows_basic_devices()
    elif system == "linux":
        return _get_linux_basic_devices()
    elif system == "darwin":
        return _get_mac_basic_devices()
    else:
        return [], []

def get_network_devices() -> Tuple[List[NetworkDevice], List[NetworkDevice]]:
    """Возвращает полную информацию о сетевых устройствах"""
    system = platform.system().lower()
    
    if system == "windows":
        return _get_windows_devices()
    elif system == "linux":
        return _get_linux_devices()
    elif system == "darwin":
        return _get_mac_devices()
    else:
        return [], []

def _get_windows_basic_devices() -> Tuple[List[BasicDeviceInfo], List[BasicDeviceInfo]]:
    """Получение базовой информации о устройствах Windows"""
    try:
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
            logger.error(f"PowerShell error: {result.stderr}")
            return [], []
        
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
        
    except Exception as e:
        logger.error(f"Error getting Windows devices: {str(e)}")
        return [], []

def _get_linux_basic_devices() -> Tuple[List[BasicDeviceInfo], List[BasicDeviceInfo]]:
    """Получение базовой информации о устройствах Linux"""
    try:
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
        
    except Exception as e:
        logger.error(f"Error getting Linux devices: {str(e)}")
        return [], []

def _get_windows_devices() -> Tuple[List[NetworkDevice], List[NetworkDevice]]:
    """Получение устройств Windows с разделением на физические/виртуальные"""
    try:
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
            logger.error(f"PowerShell error: {result.stderr}")
            return [], []
        
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
        
    except Exception as e:
        logger.error(f"Error getting Windows devices: {str(e)}")
        return [], []

def _get_linux_devices() -> Tuple[List[NetworkDevice], List[NetworkDevice]]:
    """Получение устройств Linux"""
    try:
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
                        gateway=_get_linux_gateway(ifname),
                        dns_servers=_get_linux_dns(),
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
        
    except Exception as e:
        logger.error(f"Error getting Linux devices: {str(e)}")
        return [], []

def _get_linux_gateway(interface: str) -> Optional[str]:
    """Получает шлюз по умолчанию для интерфейса в Linux"""
    try:
        result = subprocess.check_output(["ip", "-j", "route", "show", "default"], text=True)
        routes = json.loads(result)
        for route in routes:
            if route.get('dev') == interface:
                return route.get('gateway')
        return None
    except:
        return None

def _get_linux_dns() -> List[str]:
    """Получает DNS-серверы в Linux"""
    try:
        with open('/etc/resolv.conf', 'r') as f:
            return [
                line.split()[1] 
                for line in f 
                if line.startswith('nameserver')
            ]
    except:
        return []

def _get_mac_basic_devices() -> Tuple[List[BasicDeviceInfo], List[BasicDeviceInfo]]:
    """Получение базовой информации о устройствах macOS"""
    return [], []

def _get_mac_devices() -> Tuple[List[NetworkDevice], List[NetworkDevice]]:
    """Получение устройств macOS"""
    return [], []

# Используется для получения адреса для коннекта
def get_external_ip() -> Optional[str]:
    """Возвращает внешний IP-адрес"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except:
        try:
            import requests
            return requests.get('https://api.ipify.org').text
        except:
            return None

def get_local_ip() -> str:
    """Возвращает локальный IP адрес"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"