# files/core/oss/windows/default/service.py
"""
Модуль для работы с сервисами через Startup + Watchdog (Windows)
Замена systemd — автозапуск, перезапуск при падении, фоновый режим
"""
import os
import sys
import subprocess
import time
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
            service_dir = os.path.join(str(starter_path), "files", "service")
            os.makedirs(service_dir, exist_ok=True)
            set_global('service_dir', service_dir)
        set_global('service_installed', ServiceModule.is_service_installed())
        status = ServiceModule.get_service_status()
        set_global('service_status', 'running' if status.get('running') else ('installed' if status.get('installed') else 'unknown'))

    @staticmethod
    def is_service_installed() -> bool:
        bat = os.path.join(os.environ.get('APPDATA', ''), "Microsoft", "Windows", "Start Menu", "Programs", "Startup", "StarterService.bat")
        return os.path.exists(bat)

    @staticmethod
    def get_service_status() -> Dict[str, Any]:
        installed = ServiceModule.is_service_installed()
        pythonw_running = False
        try:
            result = subprocess.run(
                ['tasklist', '/FI', 'IMAGENAME eq pythonw.exe'],
                **ServiceModule._kwargs()
            )
            pythonw_running = 'pythonw.exe' in (result.stdout or '')
        except Exception:
            pass
        return {
            'installed': installed,
            'running': pythonw_running,
            'enabled': installed,
            'os': 'windows'
        }

    @staticmethod
    def install_service(log_file_path: str = None) -> Dict[str, Any]:
        result = {'status': 'success', 'message': '', 'logs': []}

        starter_path = get_global('starter_path')
        if not starter_path:
            starter_path = os.getcwd()
            if not os.path.exists(os.path.join(starter_path, 'starter.py')):
                starter_path = os.path.dirname(starter_path)

        venv_path = get_global('venv_path') or os.path.join(starter_path, 'venv')
        venv_python = os.path.join(venv_path, 'Scripts', 'python.exe')
        script_path = os.path.join(starter_path, 'starter.py')
        pythonw = os.path.join(venv_path, 'Scripts', 'pythonw.exe')

        print("\n" + "=" * 60)
        print("🔧 УСТАНОВКА СЕРВИСА STARTER (Startup + Watchdog)")
        print("=" * 60)
        print(f"   Python: {venv_python}")
        print(f"   Скрипт: {script_path}")

        if not os.path.exists(pythonw):
            result['status'] = 'error'
            result['message'] = f'pythonw.exe not found: {pythonw}'
            return result

        startup_dir = os.path.join(os.environ.get('APPDATA', ''), "Microsoft", "Windows", "Start Menu", "Programs", "Startup")
        os.makedirs(startup_dir, exist_ok=True)

        bat_content = f'@echo off\ncd /d {starter_path}\nstart /MIN "" "{pythonw}" "{script_path}"\n'
        bat_path = os.path.join(startup_dir, "StarterService.bat")
        with open(bat_path, 'w', encoding='utf-8') as f:
            f.write(bat_content)
        print(f"   ✅ Автозапуск: {bat_path}")

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
        watchdog_path = os.path.join(startup_dir, "StarterWatchdog.bat")
        with open(watchdog_path, 'w', encoding='utf-8') as f:
            f.write(watchdog_content)
        print(f"   ✅ Watchdog: {watchdog_path}")

        subprocess.run(['start', '/B', pythonw, script_path], shell=True)
        print("   🚀 Сервис запущен")

        result['message'] = 'Сервис установлен: Startup + Watchdog'
        print(f"\n   ✅ Сервис установлен!")
        return result

    @staticmethod
    def uninstall_service(log_file_path: str = None) -> Dict[str, Any]:
        result = {'status': 'success', 'message': '', 'logs': []}

        print("\n" + "=" * 60)
        print("🔧 УДАЛЕНИЕ СЕРВИСА STARTER")
        print("=" * 60)

        startup_dir = os.path.join(os.environ.get('APPDATA', ''), "Microsoft", "Windows", "Start Menu", "Programs", "Startup")
        for f in ["StarterService.bat", "StarterWatchdog.bat"]:
            p = os.path.join(startup_dir, f)
            if os.path.exists(p):
                os.remove(p)
                print(f"   ✅ Удалён: {f}")

        result['message'] = 'Сервис удалён'
        print("   ✅ Сервис удалён")
        return result

    @staticmethod
    def _find_starter_pids() -> list:
        """Найти PID процессов pythonw.exe запускающих starter.py"""
        pids = []
        try:
            import re
            output = subprocess.check_output(
                ['tasklist', '/FI', 'IMAGENAME eq pythonw.exe', '/FO', 'CSV', '/NH'],
                text=True, **ServiceModule._kwargs()
            )
            for line in output.split('\n'):
                if not line.strip():
                    continue
                match = re.search(r'"(\d+)"', line)
                if match:
                    pid = int(match.group(1))
                    try:
                        import psutil
                        proc = psutil.Process(pid)
                        cmdline = ' '.join(proc.cmdline())
                        if 'starter.py' in cmdline:
                            pids.append(pid)
                    except Exception:
                        pass
        except Exception:
            pass
        return pids

    @staticmethod
    def service_action(action: str) -> Dict[str, Any]:
        starter_path = get_global('starter_path')
        if not starter_path:
            starter_path = os.getcwd()

        venv_path = get_global('venv_path') or os.path.join(starter_path, 'venv')
        pythonw = os.path.join(venv_path, 'Scripts', 'pythonw.exe')
        script_path = os.path.join(starter_path, 'starter.py')

        if action == 'start':
            subprocess.run(['start', '/B', pythonw, script_path], shell=True)
            return {'status': 'success', 'message': 'Сервис запущен'}
        elif action == 'stop':
            for pid in ServiceModule._find_starter_pids():
                subprocess.run(['taskkill', '/F', '/PID', str(pid)], capture_output=True)
            return {'status': 'success', 'message': 'Сервис остановлен'}
        elif action == 'restart':
            for pid in ServiceModule._find_starter_pids():
                subprocess.run(['taskkill', '/F', '/PID', str(pid)], capture_output=True)
            time.sleep(2)
            subprocess.run(['start', '/B', pythonw, script_path], shell=True)
            return {'status': 'success', 'message': 'Сервис перезапущен'}
        elif action == 'status':
            return ServiceModule.get_service_status()
        elif action == 'install':
            return ServiceModule.install_service()
        elif action == 'uninstall':
            return ServiceModule.uninstall_service()
        else:
            return {'status': 'error', 'message': f'Неизвестное действие: {action}'}
