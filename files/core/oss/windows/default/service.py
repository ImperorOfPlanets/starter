# files/core/oss/windows/default/service.py
"""
Модуль для работы с сервисами через Task Scheduler (Windows)
Замена systemd — автозапуск, перезапуск при падении, фоновый режим
"""
import os
import sys
import subprocess
import time
from pathlib import Path
from typing import Dict, Any

from files.core.base_module import BaseModule
from files.core.utils.globalVars_utils import get_global, set_global
from files.core.utils.log_utils import LogManager

logger = LogManager.get_logger('service_windows')


class ServiceModule(BaseModule):
    SERVICE_NAME = "StarterService"
    TASK_NAME = "StarterService"

    @staticmethod
    def _kwargs(**extra):
        """kwargs для subprocess со startupinfo на Windows"""
        kwargs = {'capture_output': True}
        kwargs.update(extra)
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = subprocess.SW_HIDE
        kwargs['startupinfo'] = si
        return kwargs

    @staticmethod
    def check() -> bool:
        return sys.platform == 'win32'

    @staticmethod
    def has_systemd() -> bool:
        return False

    @staticmethod
    def set_globals():
        starter_path = get_global('starter_path')
        if starter_path:
            service_dir = starter_path / "files" / "service"
            service_dir.mkdir(parents=True, exist_ok=True)
            set_global('service_dir', service_dir)

    @staticmethod
    def is_service_installed() -> bool:
        try:
            result = subprocess.run(
                ['schtasks', '/Query', '/TN', ServiceModule.TASK_NAME],
                **ServiceModule._kwargs()
            )
            return result.returncode == 0
        except:
            return False

    @staticmethod
    def get_service_status() -> Dict[str, Any]:
        status = {'installed': False, 'running': False, 'enabled': False, 'os': 'windows'}
        try:
            result = subprocess.run(
                ['schtasks', '/Query', '/TN', ServiceModule.TASK_NAME, '/FO', 'LIST'],
                **ServiceModule._kwargs()
            )
            if result.returncode == 0:
                status['installed'] = True
                if 'Status: Running' in result.stdout:
                    status['running'] = True
                if 'Scheduled Task Status:' in result.stdout:
                    status['enabled'] = True
        except Exception as e:
            logger.error(f"Error checking service status: {e}")
        return status

    @staticmethod
    def install_service(log_file_path: str = None) -> Dict[str, Any]:
        result = {'status': 'success', 'message': '', 'logs': []}
        starter_path = get_global('starter_path') or Path.cwd()
        venv_path = get_global('venv_path') or starter_path / 'venv'
        venv_python = venv_path / "Scripts" / "python.exe"
        script_path = starter_path / "starter.py"
        pythonw = venv_path / "Scripts" / "pythonw.exe"

        print("\n" + "=" * 60)
        print("🔧 УСТАНОВКА СЕРВИСА STARTER (Startup + Watchdog)")
        print("=" * 60)
        print(f"   Python: {venv_python}")
        print(f"   Скрипт: {script_path}")

        if not pythonw.exists():
            result['status'] = 'error'
            result['message'] = f'pythonw.exe not found: {pythonw}'
            return result

        # Startup папка
        startup_dir = Path(os.environ['APPDATA']) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        startup_dir.mkdir(parents=True, exist_ok=True)

        # Создаём bat для запуска
        bat_content = f'@echo off\ncd /d {starter_path}\nstart /MIN "" "{pythonw}" "{script_path}"\n'
        bat_path = startup_dir / "StarterService.bat"
        bat_path.write_text(bat_content, encoding='utf-8')
        print(f"   ✅ Автозапуск: {bat_path}")

        # Создаём watchdog
        watchdog_content = f"""@echo off
cd /d {starter_path}
:loop
tasklist /FI "IMAGENAME eq pythonw.exe" 2>nul | find /I "pythonw" >nul
if %errorlevel% neq 0 (
    start /MIN "" "{pythonw}" "{script_path}"
)
timeout /t 30 /nobreak >nul
goto loop
"""
        watchdog_path = startup_dir / "StarterWatchdog.bat"
        watchdog_path.write_text(watchdog_content, encoding='utf-8')
        print(f"   ✅ Watchdog: {watchdog_path}")

        # Запускаем сейчас
        subprocess.run(['start', '/B', str(pythonw), str(script_path)], shell=True)
        print("   🚀 Сервис запущен")

        result['message'] = 'Сервис установлен: Startup + Watchdog (перезапуск каждые 30 сек)'
        print(f"\n   ✅ Сервис установлен!")
        return result

    @staticmethod
    def uninstall_service(log_file_path: str = None) -> Dict[str, Any]:
        result = {'status': 'success', 'message': '', 'logs': []}

        print("\n" + "=" * 60)
        print("🔧 УДАЛЕНИЕ СЕРВИСА STARTER")
        print("=" * 60)

        # Удаляем из Startup
        startup_dir = Path(os.environ['APPDATA']) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        for f in ["StarterService.bat", "StarterWatchdog.bat"]:
            p = startup_dir / f
            if p.exists():
                p.unlink()
                print(f"   ✅ Удалён: {p.name}")

        result['message'] = 'Сервис удалён (autostart + watchdog)'
        print("   ✅ Сервис удалён")
        return result

    @staticmethod
    def service_action(action: str) -> Dict[str, Any]:
        starter_path = get_global('starter_path') or Path.cwd()
        venv_path = get_global('venv_path') or starter_path / 'venv'
        pythonw = venv_path / "Scripts" / "pythonw.exe"
        script_path = starter_path / "starter.py"

        if action == 'start':
            subprocess.run(['start', '/B', str(pythonw), str(script_path)], shell=True)
            return {'status': 'success', 'message': 'Сервис запущен'}
        elif action == 'stop':
            subprocess.run(['taskkill', '/F', '/IM', 'pythonw.exe'], capture_output=True)
            return {'status': 'success', 'message': 'Сервис остановлен'}
        elif action == 'restart':
            subprocess.run(['taskkill', '/F', '/IM', 'pythonw.exe'], capture_output=True)
            time.sleep(2)
            subprocess.run(['start', '/B', str(pythonw), str(script_path)], shell=True)
            return {'status': 'success', 'message': 'Сервис перезапущен'}
        elif action == 'status':
            return ServiceModule.get_service_status()
        elif action == 'install':
            return ServiceModule.install_service()
        elif action == 'uninstall':
            return ServiceModule.uninstall_service()
        else:
            return {'status': 'error', 'message': f'Неизвестное действие: {action}'}
