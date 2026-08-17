# files/core/oss/default/service.py
"""
Модуль для работы с сервисами (systemd/cron fallback)
"""
import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, Any

from files.core.base_module import BaseModule
from files.core.utils.globalVars_utils import get_global, set_global
from files.core.utils.log_utils import LogManager

logger = LogManager.get_logger('service')


class ServiceModule(BaseModule):
    """Модуль для работы с сервисами (Linux systemd / cron fallback)"""
    
    SERVICE_NAME = "starter"
    SERVICE_FILE = "/etc/systemd/system/starter.service"
    
    @staticmethod
    def check() -> bool:
        """Проверяет доступность модуля"""
        return sys.platform != 'win32'
    
    @staticmethod
    def set_globals():
        """Устанавливает глобальные переменные"""
        set_global('service_name', ServiceModule.SERVICE_NAME)
    
    @staticmethod
    def has_systemd() -> bool:
        """Проверяет доступность systemd"""
        try:
            result = subprocess.run(
                ['systemctl', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
        except Exception:
            return False
    
    @staticmethod
    def is_service_installed() -> bool:
        """Проверяет, установлен ли сервис"""
        if ServiceModule.has_systemd():
            try:
                result = subprocess.run(
                    ['systemctl', 'is-enabled', ServiceModule.SERVICE_NAME],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                return result.returncode == 0
            except:
                return False
        return False
    
    @staticmethod
    def get_service_status() -> Dict[str, Any]:
        """Получает статус сервиса"""
        status = {
            'installed': False,
            'running': False,
            'enabled': False,
            'os': 'linux',
            'systemd': ServiceModule.has_systemd()
        }
        
        if not status['systemd']:
            return status
        
        try:
            # Проверка установки
            result = subprocess.run(
                ['systemctl', 'is-enabled', ServiceModule.SERVICE_NAME],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                status['installed'] = True
                status['enabled'] = True
            
            # Проверка запуска
            result = subprocess.run(
                ['systemctl', 'is-active', ServiceModule.SERVICE_NAME],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                status['running'] = True
                
        except Exception as e:
            logger.error(f"Error checking service status: {e}")
        
        return status
    
    @staticmethod
    def install_service(log_file_path: str = None) -> Dict[str, Any]:
        """Устанавливает сервис через systemd"""
        result = {'status': 'success', 'message': '', 'logs': []}
        
        print("\n" + "=" * 60)
        print("🔧 УСТАНОВКА СЕРВИСА STARTER")
        print("=" * 60)
        
        # Проверяем systemd
        if not ServiceModule.has_systemd():
            print("\n" + "!" * 60)
            print("❌ SYSTEMD НЕ ПОДДЕРЖИВАЕТСЯ В ЭТОЙ СИСТЕМЕ!")
            print("   Сервис не может быть установлен автоматически.")
            print("   Для автозапуска настройте crontab вручную:")
            print(f"   @reboot cd {get_global('starter_path')} && python starter.py")
            print("!" * 60 + "\n")
            result['status'] = 'skipped'
            result['message'] = 'systemd not available'
            return result
        
        # Проверяем права root
        if os.geteuid() != 0:
            print("\n   ⚠️ Для установки сервиса требуются права root")
            print("   💡 Запустите: sudo python starter.py --install-service")
            result['status'] = 'error'
            result['message'] = 'root required'
            return result
        
        starter_path = get_global('starter_path')
        venv_path = get_global('venv_path', starter_path / 'venv')
        venv_python = venv_path / "bin" / "python"
        script_path = starter_path / "starter.py"
        
        print(f"   Python: {venv_python}")
        print(f"   Скрипт: {script_path}")
        print(f"   Рабочая директория: {starter_path}")
        
        # Проверяем существование файлов
        if not venv_python.exists():
            print(f"   ❌ Python не найден: {venv_python}")
            result['status'] = 'error'
            result['message'] = 'Python not found in venv'
            return result
        
        if not script_path.exists():
            print(f"   ❌ starter.py не найден: {script_path}")
            result['status'] = 'error'
            result['message'] = 'starter.py not found'
            return result
        
        # Создаем systemd unit файл
        service_content = f"""[Unit]
Description=Starter Server Manager
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory={starter_path}
ExecStart={venv_python} {script_path}
Restart=on-failure
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
"""
        
        try:
            # Записываем unit файл
            with open(ServiceModule.SERVICE_FILE, 'w') as f:
                f.write(service_content)
            
            print(f"   ✅ Unit файл создан: {ServiceModule.SERVICE_FILE}")
            
            # Перезагружаем systemd
            subprocess.run(['systemctl', 'daemon-reload'], check=True)
            print("   ✅ Systemd перезагружен")
            
            # Включаем автозапуск
            subprocess.run(['systemctl', 'enable', ServiceModule.SERVICE_NAME], check=True)
            print("   ✅ Автозапуск включен")
            
            # Запускаем сервис
            subprocess.run(['systemctl', 'start', ServiceModule.SERVICE_NAME], check=True)
            print("   ✅ Сервис запущен")
            
            result['message'] = 'Service installed and started'
            
        except Exception as e:
            print(f"   ❌ Ошибка установки сервиса: {e}")
            result['status'] = 'error'
            result['message'] = str(e)
        
        return result
    
    @staticmethod
    def uninstall_service(log_file_path: str = None) -> Dict[str, Any]:
        """Удаляет сервис"""
        result = {'status': 'success', 'message': '', 'logs': []}
        
        if not ServiceModule.has_systemd():
            result['status'] = 'skipped'
            result['message'] = 'systemd not available'
            return result
        
        if os.geteuid() != 0:
            print("   ⚠️ Для удаления сервиса требуются права root")
            result['status'] = 'error'
            result['message'] = 'root required'
            return result
        
        try:
            # Останавливаем сервис
            subprocess.run(['systemctl', 'stop', ServiceModule.SERVICE_NAME], check=False)
            print("   ✅ Сервис остановлен")
            
            # Отключаем автозапуск
            subprocess.run(['systemctl', 'disable', ServiceModule.SERVICE_NAME], check=False)
            print("   ✅ Автозапуск отключен")
            
            # Удаляем unit файл
            if os.path.exists(ServiceModule.SERVICE_FILE):
                os.remove(ServiceModule.SERVICE_FILE)
                print(f"   ✅ Unit файл удален: {ServiceModule.SERVICE_FILE}")
            
            # Перезагружаем systemd
            subprocess.run(['systemctl', 'daemon-reload'], check=True)
            print("   ✅ Systemd перезагружен")
            
            result['message'] = 'Service uninstalled'
            
        except Exception as e:
            print(f"   ❌ Ошибка удаления сервиса: {e}")
            result['status'] = 'error'
            result['message'] = str(e)
        
        return result
