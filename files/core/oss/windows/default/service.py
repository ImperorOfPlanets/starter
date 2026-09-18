# files/core/oss/windows/default/service.py
"""
Модуль для работы с сервисами через VBScript + Startup (Windows)
VBScript запускает процессы БЕЗ окон CMD —完全 невидимо
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
    SERVICE_VBS = "StarterService.vbs"
    WEB_VBS = "StarterWeb.vbs"

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
    def _get_paths() -> Dict[str, str]:
        starter_path = get_global('starter_path')
        if not starter_path:
            starter_path = os.getcwd()
            if not os.path.exists(os.path.join(starter_path, 'starter.py')):
                starter_path = os.path.dirname(starter_path)

        venv_path = get_global('venv_path') or os.path.join(starter_path, 'venv')
        return {
            'starter_path': str(starter_path),
            'venv_python': os.path.join(venv_path, 'Scripts', 'python.exe'),
            'pythonw': os.path.join(venv_path, 'Scripts', 'pythonw.exe'),
            'script': os.path.join(starter_path, 'starter.py'),
        }

    @staticmethod
    def _get_startup_dir() -> str:
        return os.path.join(
            os.environ.get('APPDATA', ''),
            "Microsoft", "Windows", "Start Menu", "Programs", "Startup"
        )

    @staticmethod
    def _make_vbs(pythonw: str, script: str, args: str = '') -> str:
        arg_part = f' {args}' if args else ''
        return (
            f'Set WshShell = CreateObject("WScript.Shell")\r\n'
            f'WshShell.CurrentDirectory = "{os.path.dirname(script)}"\r\n'
            f'WshShell.Run """{pythonw}"" ""{script}""{arg_part}", 0, False\r\n'
        )

    @staticmethod
    def is_service_installed() -> bool:
        startup = ServiceModule._get_startup_dir()
        return os.path.exists(os.path.join(startup, ServiceModule.SERVICE_VBS))

    @staticmethod
    def get_service_status() -> Dict[str, Any]:
        installed = ServiceModule.is_service_installed()

        service_running = False
        web_running = False
        try:
            import re
            result = subprocess.run(
                ['tasklist', '/FI', 'IMAGENAME eq pythonw.exe', '/FO', 'CSV', '/NH'],
                capture_output=True, text=True, timeout=10
            )
            for line in (result.stdout or '').strip().split('\n'):
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
                            if '--service' in cmdline:
                                service_running = True
                            else:
                                web_running = True
                    except Exception:
                        pass
        except Exception:
            pass

        return {
            'installed': installed,
            'running': service_running or web_running,
            'service_running': service_running,
            'web_running': web_running,
            'enabled': installed,
            'os': 'windows'
        }

    @staticmethod
    def install_service(log_file_path: str = None) -> Dict[str, Any]:
        result = {'status': 'success', 'message': '', 'logs': []}
        paths = ServiceModule._get_paths()

        print("\n" + "=" * 60)
        print("🔧 УСТАНОВКА СЕРВИСА STARTER (VBScript + Startup)")
        print("=" * 60)
        print(f"   Python: {paths['venv_python']}")
        print(f"   Скрипт: {paths['script']}")

        if not os.path.exists(paths['pythonw']):
            result['status'] = 'error'
            result['message'] = f'pythonw.exe not found: {paths["pythonw"]}'
            print(f"   ❌ {result['message']}")
            return result

        ServiceModule._remove_old_bat_files()

        startup = ServiceModule._get_startup_dir()
        os.makedirs(startup, exist_ok=True)

        service_vbs = os.path.join(startup, ServiceModule.SERVICE_VBS)
        with open(service_vbs, 'w', encoding='ascii', newline='\r\n') as f:
            f.write(ServiceModule._make_vbs(paths['pythonw'], paths['script'], '--service'))
        print(f"   ✅ Сервис (фон): {service_vbs}")

        print("\n   🚀 Запуск сервиса...")
        ServiceModule.service_action('start')

        result['message'] = 'Сервис установлен: VBScript + Startup'
        print(f"\n   ✅ Сервис установлен!")
        return result

    @staticmethod
    def uninstall_service(log_file_path: str = None) -> Dict[str, Any]:
        result = {'status': 'success', 'message': '', 'logs': []}

        print("\n" + "=" * 60)
        print("🔧 УДАЛЕНИЕ СЕРВИСА STARTER")
        print("=" * 60)

        ServiceModule._remove_old_bat_files()

        startup = ServiceModule._get_startup_dir()
        for f in [ServiceModule.SERVICE_VBS, ServiceModule.WEB_VBS]:
            p = os.path.join(startup, f)
            if os.path.exists(p):
                os.remove(p)
                print(f"   ✅ Удалён: {f}")

        result['message'] = 'Сервис удалён'
        print("   ✅ Сервис удалён")
        return result

    @staticmethod
    def _remove_old_bat_files():
        startup = ServiceModule._get_startup_dir()
        for f in ["StarterService.bat", "StarterWatchdog.bat"]:
            p = os.path.join(startup, f)
            if os.path.exists(p):
                os.remove(p)
                print(f"   🧹 Удалён старый .bat: {f}")

    @staticmethod
    def _find_starter_pids() -> list:
        pids = []
        try:
            import re
            output = subprocess.check_output(
                ['tasklist', '/FI', 'IMAGENAME eq pythonw.exe', '/FO', 'CSV', '/NH'],
                text=True, timeout=10
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
        paths = ServiceModule._get_paths()

        if action == 'start':
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = subprocess.SW_HIDE
            subprocess.Popen(
                [paths['pythonw'], paths['script']],
                cwd=paths['starter_path'],
                startupinfo=si,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            return {'status': 'success', 'message': 'Сервис запущен'}

        elif action == 'stop':
            for pid in ServiceModule._find_starter_pids():
                subprocess.run(['taskkill', '/F', '/PID', str(pid)], capture_output=True, timeout=10)
            return {'status': 'success', 'message': 'Сервис остановлен'}

        elif action == 'restart':
            for pid in ServiceModule._find_starter_pids():
                subprocess.run(['taskkill', '/F', '/PID', str(pid)], capture_output=True, timeout=10)
            time.sleep(2)
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = subprocess.SW_HIDE
            subprocess.Popen(
                [paths['pythonw'], paths['script']],
                cwd=paths['starter_path'],
                startupinfo=si,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            return {'status': 'success', 'message': 'Сервис перезапущен'}

        elif action == 'status':
            return ServiceModule.get_service_status()

        elif action == 'install':
            return ServiceModule.install_service()

        elif action == 'uninstall':
            return ServiceModule.uninstall_service()

        elif action == 'start-web':
            return ServiceModule._start_web()

        elif action == 'stop-web':
            return ServiceModule._stop_web()

        else:
            return {'status': 'error', 'message': f'Неизвестное действие: {action}'}

    @staticmethod
    def _start_web() -> Dict[str, Any]:
        paths = ServiceModule._get_paths()

        for pid in ServiceModule._find_starter_pids():
            try:
                import psutil
                proc = psutil.Process(pid)
                cmdline = ' '.join(proc.cmdline())
                if 'starter.py' in cmdline and '--service' not in cmdline:
                    return {'status': 'success', 'message': 'Веб-интерфейс уже запущен'}
            except Exception:
                pass

        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = subprocess.SW_HIDE
        subprocess.Popen(
            [paths['pythonw'], paths['script']],
            cwd=paths['starter_path'],
            startupinfo=si,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        return {'status': 'success', 'message': 'Веб-интерфейс запущен'}

    @staticmethod
    def _stop_web() -> Dict[str, Any]:
        stopped = 0
        for pid in ServiceModule._find_starter_pids():
            try:
                import psutil
                proc = psutil.Process(pid)
                cmdline = ' '.join(proc.cmdline())
                if 'starter.py' in cmdline and '--service' not in cmdline:
                    subprocess.run(['taskkill', '/F', '/PID', str(pid)], capture_output=True, timeout=10)
                    stopped += 1
            except Exception:
                pass
        return {'status': 'success', 'message': f'Остановлено web-процессов: {stopped}'}
