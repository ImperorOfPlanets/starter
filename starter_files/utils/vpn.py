import importlib
import platform
import pkgutil
from pathlib import Path
from typing import Dict, Optional

# Путь к папке с клиентами
VPN_CLIENTS_DIR = Path(__file__).parent / 'vpn'

class VPNManager:
    """Менеджер VPN клиентов"""
    
    def __init__(self):
        self.clients = self._load_clients()
    
    def _load_clients(self) -> Dict[str, object]:
        """Динамически загружает все доступные клиенты"""
        clients = {}
        
        for module_info in pkgutil.iter_modules([str(VPN_CLIENTS_DIR)]):
            if module_info.name.startswith('_'):
                continue
                
            try:
                module = importlib.import_module(
                    f'starter_files.utils.vpn.{module_info.name}'
                )
                for attr in dir(module):
                    cls = getattr(module, attr)
                    if (
                        isinstance(cls, type) and 
                        issubclass(cls, BaseVPNClient) and 
                        cls != BaseVPNClient
                    ):
                        clients[module_info.name] = cls()
            except ImportError as e:
                continue
                
        return clients
    
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

# Создаем глобальный экземпляр менеджера
vpn_manager = VPNManager()

# Функции для удобного импорта
def get_available_clients():
    return vpn_manager.get_available_clients()

def get_vpn_status(client_name=None):
    return vpn_manager.get_client_status(client_name)