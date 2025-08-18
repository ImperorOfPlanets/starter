from starter_files.utils.oss.base_module import BaseModule
from typing import List
from starter_files.utils.globalVars_utils import get_global, set_global
from starter_files.utils.oss.module_loader import get
import platform
import logging
import subprocess
import os

logger = logging.getLogger('softether_oss')

class SoftEtherModule(BaseModule):
    """Реализация для установки SoftEther VPN Client"""

    @staticmethod
    def get_architecture() -> str:
        """Определяет архитектуру процессора для выбора сборки"""
        arch_map = {
            'x86_64': 'Intel x64 / AMD64 (64bit)',
            'i386': 'Intel x86 (32bit)',
            'i686': 'Intel x86 (32bit)',
            'armv7l': 'ARM EABI (32bit)',
            'aarch64': 'ARM 64bit (64bit)',
            'mips': 'MIPS Little-Endian (32bit)',
            'powerpc': 'PowerPC (32bit)',
            'sh4': 'SH-4 (32bit)'
        }
        arch = platform.machine().lower()
        return arch_map.get(arch, 'Intel x64 / AMD64 (64bit)')

    @staticmethod
    def return_commands_install_softether() -> List[str]:
        """Возвращает команды для установки SoftEther VPN Client"""
        os_type = get_global('os_type')
        is_root = get_global('is_root')
        use_sudo = get_global('use_sudo')
        
        prefix = "sudo " if (not is_root and use_sudo) or not is_root else ""
        version = "v4.42-9798-rtm-2023.06.30"
        repo_url = "https://github.com/chipitsine/SoftEtherVPN.git"
        
        commands = []
        
        # Установка зависимостей
        if os_type == 'linux':
            if get_global('os_family') == 'debian':
                commands = [
                    f"{prefix}apt update",
                    f"{prefix}apt -y install cmake gcc g++ make pkgconf "
                    "libncurses5-dev libssl-dev libsodium-dev libreadline-dev zlib1g-dev"
                ]
            elif get_global('os_family') in ['rhel', 'centos', 'fedora']:
                commands = [
                    f"{prefix}yum -y groupinstall 'Development Tools'",
                    f"{prefix}yum -y install cmake ncurses-devel openssl-devel "
                    "libsodium-devel readline-devel zlib-devel"
                ]
        elif os_type == 'macos':
            commands = [
                "brew update",
                "brew install cmake openssl libsodium readline"
            ]
        
        # Клонирование и сборка
        build_cmd = [
            f"git clone {repo_url}",
            "cd SoftEtherVPN",
            "git submodule init && git submodule update",
            "./configure",
            "make -C build",
            f"{prefix}make -C build install"
        ]
        
        commands.extend(build_cmd)
        return commands

    @staticmethod
    def return_commands_configure_client(vpn_config: dict) -> List[str]:
        """Генерирует команды для настройки VPN-клиента"""
        commands = []
        server = vpn_config.get('server', 'vpn.example.com')
        username = vpn_config.get('username', 'user')
        password = vpn_config.get('password', 'pass')
        
        # Создание и настройка VPN-подключения
        config_cmds = [
            # Запуск VPN-клиента в фоновом режиме
            "vpnclient start",
            
            # Создание аккаунта VPN
            f"vpncmd /CLIENT localhost /CMD AccountCreate {server} "
            f"/SERVER:{server} /HUB:DEFAULT /USERNAME:{username} /NICNAME:VPN",
            
            # Установка пароля
            f"vpncmd /CLIENT localhost /CMD AccountPasswordSet {server} "
            f"/PASSWORD:{password} /TYPE:standard",
            
            # Подключение к VPN
            f"vpncmd /CLIENT localhost /CMD AccountConnect {server}"
        ]
        
        commands.extend(config_cmds)
        return commands

    @staticmethod
    def check_softether_installed() -> bool:
        """Проверяет установлен ли SoftEther VPN Client"""
        try:
            os_type = get_global('os_type')
            if os_type == 'linux' or os_type == 'macos':
                # Проверка наличия исполняемого файла
                result = subprocess.run(
                    ['which', 'vpnclient'],
                    capture_output=True,
                    text=True
                )
                return result.returncode == 0
            elif os_type == 'windows':
                # Проверка наличия в Program Files
                return os.path.exists("C:\\Program Files\\SoftEther VPN Client\\vpnclient.exe")
            return False
        except Exception:
            return False

    @staticmethod
    def return_commands_connect_vpn(profile_name: str) -> List[str]:
        """Возвращает команды для подключения к VPN"""
        return [
            f"vpnclient start",
            f"vpncmd /CLIENT localhost /CMD AccountConnect {profile_name}"
        ]

    @staticmethod
    def return_commands_disconnect_vpn(profile_name: str) -> List[str]:
        """Возвращает команды для отключения от VPN"""
        return [
            f"vpncmd /CLIENT localhost /CMD AccountDisconnect {profile_name}",
            f"vpnclient stop"
        ]

    @staticmethod
    def return_commands_list_vpn() -> List[str]:
        """Возвращает команды для списка VPN-профилей"""
        return [
            "vpncmd /CLIENT localhost /CMD AccountList"
        ]

    @staticmethod
    def return_commands_remove_vpn(profile_name: str) -> List[str]:
        """Возвращает команды для удаления VPN-профиля"""
        return [
            f"vpncmd /CLIENT localhost /CMD AccountDelete {profile_name}"
        ]
        """Устанавливает глобальные переменные для SoftEther"""
        installed = get('softether', 'check_softether_installed')
        set_global('softether_installed', installed)
        
        if installed:
            status = SoftEtherModule.get_service_status()
            set_global('softether_status', status['status_text'])
            set_global('softether_active', status['active'])
    
    @staticmethod
    def set_globals():
        """Устанавливает глобальные переменные для SoftEther"""
        installed = get('softether', 'check_softether_installed')
        set_global('softether_installed', installed)
        
        if installed:
            status = SoftEtherModule.get_service_status()
            set_global('softether_status', status['status_text'])
            set_global('softether_active', status['active'])