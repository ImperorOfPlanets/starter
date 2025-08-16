import os
import platform
import subprocess
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional
from starter_files.utils.oss.base_module import BaseModule

class VpnModule(BaseModule): 
    pass
class BaseVPNClient(BaseModule):
    """Абстрактный базовый класс для VPN клиентов"""
    
    CLIENT_NAME = "Base VPN Client"
    CLIENT_ICON = "bi-shield"
    
    def __init__(self):
        self.os = platform.system().lower()
    
    @classmethod
    def check(cls) -> bool:
        """Проверяет доступность клиента в системе"""
        return True
    
    @abstractmethod
    def is_installed(self) -> bool:
        """Проверяет, установлен ли клиент"""
        pass
    
    @abstractmethod
    def get_version(self) -> str:
        """Возвращает версию клиента"""
        pass
    
    @abstractmethod
    def get_status(self) -> dict:
        """Возвращает статус подключения"""
        pass
    
    def get_client_info(self) -> dict:
        """Возвращает полную информацию о клиенте"""
        return {
            'name': self.CLIENT_NAME,
            'icon': self.CLIENT_ICON,
            'installed': self.is_installed(),
            'version': self.get_version() if self.is_installed() else 'N/A',
            'os': self.os,
            'status': self.get_status() if self.is_installed() else {'connected': False},
            'interfaces': self._get_interfaces() if self.is_installed() else []
        }
    
    def _get_interfaces(self) -> List[str]:
        """Возвращает список VPN интерфейсов (может быть переопределен)"""
        return []

class OpenVPNClient(BaseVPNClient):
    """Реализация для OpenVPN клиента"""
    
    CLIENT_NAME = "OpenVPN"
    CLIENT_ICON = "bi-lock"
    
    def is_installed(self) -> bool:
        return bool(shutil.which('openvpn'))

    def get_version(self) -> str:
        try:
            result = subprocess.run(
                ['openvpn', '--version'],
                capture_output=True, 
                text=True, 
                check=True
            )
            return result.stdout.split('\n')[0].split()[1]
        except Exception:
            return 'N/A'

    def get_status(self) -> dict:
        status = {'connected': False}
        if self.os == 'windows':
            try:
                result = subprocess.run(
                    ['tasklist', '/FI', 'IMAGENAME eq openvpn.exe'],
                    capture_output=True, 
                    text=True, 
                    check=True
                )
                status['connected'] = 'openvpn.exe' in result.stdout
            except Exception:
                pass
        else:
            try:
                result = subprocess.run(
                    ['ps', 'aux'], 
                    capture_output=True, 
                    text=True, 
                    check=True
                )
                status['connected'] = 'openvpn' in result.stdout
            except Exception:
                pass
        
        status['interfaces'] = self._get_interfaces()
        return status
    
    def _get_interfaces(self) -> List[str]:
        """Получает список VPN интерфейсов для OpenVPN"""
        interfaces = []
        if self.os == 'linux':
            try:
                result = subprocess.run(
                    ['ip', 'a'],
                    capture_output=True,
                    text=True,
                    check=True
                )
                interfaces = [
                    line.split()[1].rstrip(':') 
                    for line in result.stdout.splitlines() 
                    if 'tun' in line or 'tap' in line
                ]
            except Exception:
                pass
        return interfaces

class SoftEtherVPNClient(BaseVPNClient):
    """Реализация для SoftEther VPN клиента"""
    
    CLIENT_NAME = "SoftEther VPN"
    CLIENT_ICON = "bi-shield-lock"
    
    def is_installed(self) -> bool:
        if self.os == 'windows':
            paths = [
                Path(os.environ.get('ProgramFiles', '')) / 'SoftEther VPN Client' / 'vpnclient.exe',
                Path(os.environ.get('ProgramFiles(x86)', '')) / 'SoftEther VPN Client' / 'vpnclient.exe'
            ]
            return any(p.exists() for p in paths)
        return bool(shutil.which('vpnclient'))

    def get_version(self) -> str:
        if self.os == 'windows':
            try:
                exe_path = next(
                    p for p in [
                        Path(os.environ.get('ProgramFiles', '')) / 'SoftEther VPN Client' / 'vpnclient.exe',
                        Path(os.environ.get('ProgramFiles(x86)', '')) / 'SoftEther VPN Client' / 'vpnclient.exe'
                    ] if p.exists()
                )
                result = subprocess.run(
                    ['wmic', 'datafile', 'where', f'name="{exe_path}"', 'get', 'version'],
                    capture_output=True, 
                    text=True, 
                    check=True
                )
                return result.stdout.split('\n')[1].strip()
            except Exception:
                pass
        else:
            try:
                result = subprocess.run(
                    ['vpnclient', 'version'],
                    capture_output=True, 
                    text=True, 
                    check=True
                )
                return result.stdout.split('\n')[0].strip()
            except Exception:
                pass
        return 'N/A'

    def get_status(self) -> dict:
        status = {'connected': False}
        if self.os == 'windows':
            try:
                result = subprocess.run(
                    ['tasklist', '/FI', 'IMAGENAME eq vpnclient.exe'],
                    capture_output=True, 
                    text=True, 
                    check=True
                )
                status['connected'] = 'vpnclient.exe' in result.stdout
            except Exception:
                pass
        else:
            try:
                result = subprocess.run(
                    ['ps', 'aux'], 
                    capture_output=True, 
                    text=True, 
                    check=True
                )
                status['connected'] = 'vpnclient' in result.stdout
            except Exception:
                pass
        
        status['interfaces'] = self._get_interfaces()
        return status
    
    def _get_interfaces(self) -> List[str]:
        """Получает список VPN интерфейсов для SoftEther"""
        interfaces = []
        if self.os == 'windows':
            try:
                result = subprocess.run(
                    ['netsh', 'interface', 'show', 'interface'],
                    capture_output=True,
                    text=True,
                    check=True
                )
                interfaces = [
                    line.split('  ')[-1].strip()
                    for line in result.stdout.splitlines()
                    if 'VPN' in line or 'SoftEther' in line
                ]
            except Exception:
                pass
        return interfaces

class VPNManager:
    """Менеджер VPN клиентов для default реализации"""
    
    def __init__(self):
        self.clients = {
            'openvpn': OpenVPNClient(),
            'softether': SoftEtherVPNClient()
        }
    
    def get_available_clients(self) -> Dict[str, dict]:
        """Возвращает информацию о доступных клиентах"""
        return {
            name: client.get_client_info()
            for name, client in self.clients.items()
        }
    
    def get_client_status(self, client_name: Optional[str] = None) -> dict:
        """Возвращает статус указанного или первого доступного клиента"""
        if client_name and client_name in self.clients:
            return self.clients[client_name].get_client_info()
        
        for client in self.clients.values():
            if client.is_installed():
                return client.get_client_info()
        
        return {
            'installed': False,
            'connected': False,
            'version': 'N/A',
            'os': platform.system().lower(),
            'interfaces': []
        }

# Глобальный экземпляр менеджера фывыф
vpn_manager = VPNManager()

def get_available_clients() -> Dict[str, dict]:
    """Возвращает список доступных VPN клиентов"""
    return vpn_manager.get_available_clients()

def get_vpn_status(client_name: Optional[str] = None) -> dict:
    """Возвращает статус VPN подключения"""
    return vpn_manager.get_client_status(client_name)