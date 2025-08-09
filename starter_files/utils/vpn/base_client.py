from abc import ABC, abstractmethod
import platform

class BaseVPNClient(ABC):
    """Абстрактный базовый класс для VPN клиентов"""
    
    CLIENT_NAME = "Base VPN Client"
    CLIENT_ICON = "bi-shield"
    
    def __init__(self):
        self.os = platform.system().lower()
    
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
        """Возвращает информацию о клиенте"""
        return {
            'name': self.CLIENT_NAME,
            'icon': self.CLIENT_ICON,
            'installed': self.is_installed(),
            'version': self.get_version() if self.is_installed() else 'N/A',
            'status': self.get_status() if self.is_installed() else {'connected': False}
        }