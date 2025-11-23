from starter_files.core.base_module import BaseModule
from typing import List, Dict
from datetime import datetime
from pathlib import Path
from starter_files.core.utils.globalVars_utils import get_global, set_global
from starter_files.core.utils.loader_utils import get
import platform
import logging
import subprocess
import os
import time

logger = logging.getLogger('softether_oss')

class SoftetherModule(BaseModule):
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
    def install_softether(log_file_path: str) -> Dict[str, str]:
        """Устанавливает SoftEtherVPN и записывает логи в указанный файл"""
        result = {'status': 'success', 'message': '', 'logs': []}
        
        try:
            # Создаем директорию для логов, если нужно
            log_dir = Path(log_file_path).parent
            log_dir.mkdir(parents=True, exist_ok=True)
            
            # Открываем файл для записи логов один раз на весь процесс установки
            with open(log_file_path, 'w') as log_file:
                def log(message):
                    """Вспомогательная функция для записи в лог и в результат"""
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    log_entry = f"[{timestamp}] {message}"
                    log_file.write(log_entry + '\n')
                    log_file.flush()  # Обеспечиваем немедленную запись
                    result['logs'].append(log_entry)
                    logger.info(log_entry)
                
                log("Starting SoftEtherVPN installation...")

                commands = get("softether","return_commands_install_softether")

                # Выполняем команды установки
                for cmd in commands:
                    log(f"Executing: {cmd}")
                    process = subprocess.Popen(
                        cmd,
                        shell=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,  # Объединяем stdout и stderr
                        text=True,
                        bufsize=1,  # Построчный буфер
                        universal_newlines=True
                    )
                    
                    # Читаем вывод в реальном времени
                    for line in iter(process.stdout.readline, ''):
                        if line:
                            log(line.strip())
                    
                    # Проверяем статус завершения
                    return_code = process.wait()
                    if return_code != 0:
                        log(f"Command failed with exit code {return_code}")
                        result['status'] = 'error'
                        result['message'] = f"Command failed: {cmd}"
                        return result
                
                # Проверяем успешность установки
                time.sleep(2)
                if get('softether','check_softether_installed'):
                    log("SoftEtherVPN installed successfully! Please restart your session.")
                    result['message'] = "Docker installed successfully! Please restart your session."
                else:
                    log("Installation completed but Docker not detected. Try restarting your system.")
                    result['status'] = 'warning'
                    result['message'] = "Installation completed but Docker not detected. Try restarting your system."
        
        except Exception as e:
            # Записываем ошибку в лог
            error_msg = f"Installation failed: {str(e)}"
            try:
                with open(log_file_path, 'a') as f:
                    f.write(error_msg + '\n')
            except:
                logger.exception("Failed to write error to log file")
            
            result['status'] = 'error'
            result['message'] = error_msg
            logger.exception("SoftEtherVPN installation error")
        
        return result

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
            status = SoftetherModule.get_service_status()
            set_global('softether_status', status['status_text'])
            set_global('softether_active', status['active'])