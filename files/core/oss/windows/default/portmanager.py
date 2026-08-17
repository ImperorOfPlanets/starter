from files.core.base_module import BaseModule
import socket
import subprocess
import re

from files.core.utils.log_utils import LogManager

logger = LogManager.get_logger('portmanager')

class PortmanagerModule(BaseModule):
    @staticmethod
    def is_port_free(port: int, host: str = "127.0.0.1") -> bool:
        """Проверяет, свободен ли TCP-порт на Windows"""
        print ('Сработала WINDOWS')
        try:
            # Метод 1: Быстрая проверка через подключение
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.1)
                try:
                    s.connect((host, port))
                    logger.debug(f"[Windows] Порт {port} занят (активное соединение)")
                    return False
                except (socket.timeout, ConnectionRefusedError):
                    # Подключение отклонено - порт может быть свободен
                    pass
                except OSError:
                    return False
            
            # Метод 2: Проверка через netstat (точная проверка)
            try:
                result = subprocess.run(
                    ['netstat', '-ano'],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if f':{port}' in line and 'LISTENING' in line:
                            logger.debug(f"[Windows] Порт {port} найден в netstat как LISTENING")
                            return False
            except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
                pass
            
            logger.debug(f"[Windows] Порт {port} свободен")
            return True
            
        except Exception as e:
            logger.warning(f"[Windows] Ошибка проверки порта {port}: {e}")
            return False