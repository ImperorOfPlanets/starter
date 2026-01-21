from files.core.base_module import BaseModule
import socket
import subprocess
import os

from files.core.utils.log_utils import LogManager
logger = LogManager.get_logger('portmanager')

class PortmanagerModule(BaseModule):
    @staticmethod
    def is_port_free(port: int, host: str = "127.0.0.1") -> bool:
        """Проверяет, свободен ли TCP-порт на Unix-системах"""
        print ('Сработала DEAFAULT')
        try:
            # Метод 1: Быстрая проверка через подключение
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.1)
                try:
                    s.connect((host, port))
                    logger.debug(f"[Unix] Порт {port} занят (активное соединение)")
                    return False
                except (socket.timeout, ConnectionRefusedError):
                    # Подключение отклонено - порт может быть свободен
                    pass
                except OSError:
                    return False
            
            # Метод 2: Проверка через ss или lsof (если доступны)
            try:
                # Попробуем ss (современный инструмент)
                if os.path.exists('/bin/ss') or os.path.exists('/usr/bin/ss'):
                    result = subprocess.run(
                        ['ss', '-tln'],
                        capture_output=True,
                        text=True,
                        timeout=2
                    )
                    if result.returncode == 0:
                        for line in result.stdout.split('\n'):
                            if f':{port} ' in line:
                                logger.debug(f"[Unix] Порт {port} найден в ss")
                                return False
                
                # Альтернатива: lsof
                elif os.path.exists('/usr/bin/lsof') or os.path.exists('/bin/lsof'):
                    result = subprocess.run(
                        ['lsof', '-i', f':{port}'],
                        capture_output=True,
                        text=True,
                        timeout=2
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        logger.debug(f"[Unix] Порт {port} найден в lsof")
                        return False
                        
            except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
                pass
            
            logger.debug(f"[Unix] Порт {port} свободен")
            return True
            
        except Exception as e:
            logger.warning(f"[Unix] Ошибка проверки порта {port}: {e}")
            return False