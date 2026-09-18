# files/core/oss/windows/default/tray.py
"""
Модуль системного трея Windows
Управление стартером: статус, запуск, остановка, открытие веб-интерфейса
"""
import os
import sys
import socket
import threading
import subprocess
import time
from pathlib import Path
from typing import Dict, Any

from files.core.base_module import BaseModule
from files.core.utils.globalVars_utils import get_global, set_global
from files.core.utils.log_utils import LogManager

logger = LogManager.get_logger('tray_windows')


def _si():
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = subprocess.SW_HIDE
    return si


def _find_starter_pids() -> list:
    """Найти PID всех процессов starter.py"""
    pids = []
    try:
        import re
        output = subprocess.check_output(
            ['tasklist', '/FI', 'IMAGENAME eq pythonw.exe', '/FO', 'CSV', '/NH'],
            text=True, startupinfo=_si()
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


def _is_web_running() -> bool:
    """Проверяет, работает ли веб-сервер стартера"""
    port = get_global('port', 2000)
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex(('127.0.0.1', port))
            return result == 0
    except Exception:
        return False


def _is_service_running() -> bool:
    """Проверяет, работает ли сервисный режим"""
    for pid in _find_starter_pids():
        try:
            import psutil
            proc = psutil.Process(pid)
            cmdline = ' '.join(proc.cmdline())
            if '--service' in cmdline:
                return True
        except Exception:
            pass
    return False


class TrayModule(BaseModule):
    """Модуль системного трея Windows — управление стартером"""

    _tray_thread = None
    _running = False
    _icon = None

    @staticmethod
    def check() -> bool:
        return sys.platform == 'win32'

    @staticmethod
    def set_globals():
        starter_path = get_global('starter_path')
        if starter_path:
            icons_dir = starter_path / "files" / "web" / "public"
            set_global('tray_icons_dir', icons_dir)

    @staticmethod
    def has_desktop() -> bool:
        """Проверяет, есть ли рабочий стол (не Docker, не Server Core, не WSL)"""
        if sys.platform != 'win32':
            return False
        try:
            import ctypes
            user32 = ctypes.windll.user32
            session_id = ctypes.windll.kernel32.WTSGetActiveConsoleSessionId()
            if session_id == 0:
                return False
            desktop = user32.OpenDesktopW('Default', 0, False, 0x0100)
            if desktop:
                user32.CloseDesktop(desktop)
                return True
        except Exception:
            pass
        return False

    @staticmethod
    def is_available() -> bool:
        """Проверяет и библиотеки, и наличие рабочего стола"""
        if not TrayModule.has_desktop():
            return False
        try:
            import pystray
            from PIL import Image
            return True
        except ImportError:
            return False

    @staticmethod
    def tray_dependencies_needed() -> bool:
        """Нужно ли устанавливать зависимости для трея"""
        if not TrayModule.has_desktop():
            return False
        try:
            import pystray
            from PIL import Image
            return False
        except ImportError:
            return True

    @staticmethod
    def check_dependencies():
        missing = []
        try:
            import pystray
        except ImportError:
            missing.append('pystray')
        try:
            from PIL import Image
        except ImportError:
            missing.append('Pillow')
        if missing:
            print(f"\n   ⚠️ Для трея требуются: {', '.join(missing)}")
            print(f"   💡 pip install {' '.join(missing)}")
            return False
        print("   ✅ Зависимости трея установлены")
        return True

    @staticmethod
    def _start_web_server():
        """Запуск веб-сервера стартера (без окон)"""
        starter_path = get_global('starter_path')
        venv_python = str(Path(starter_path) / "venv" / "Scripts" / "pythonw.exe")
        script = str(Path(starter_path) / "starter.py")

        if not os.path.exists(venv_python):
            return False

        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = subprocess.SW_HIDE
        subprocess.Popen(
            [venv_python, script],
            cwd=starter_path,
            startupinfo=si,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        return True

    @staticmethod
    def _stop_web_server():
        """Остановка веб-сервера стартера (убивает только интерактивные процессы)"""
        current_pid = os.getpid()
        stopped = 0
        for pid in _find_starter_pids():
            if pid == current_pid:
                continue
            try:
                import psutil
                proc = psutil.Process(pid)
                cmdline = ' '.join(proc.cmdline())
                if 'starter.py' in cmdline and '--service' not in cmdline:
                    subprocess.run(['taskkill', '/F', '/PID', str(pid)],
                                   capture_output=True, startupinfo=_si())
                    stopped += 1
            except Exception:
                pass
        return stopped

    @staticmethod
    def _kill_all():
        """Убить все процессы стартера"""
        for pid in _find_starter_pids():
            subprocess.run(['taskkill', '/F', '/PID', str(pid)],
                           capture_output=True, startupinfo=_si())

    @staticmethod
    def create_tray_icon():
        try:
            import pystray
            from PIL import Image, ImageDraw

            port = get_global('port', 2000)
            url = f"https://127.0.0.1:{port}"

            def make_icon(color='#0d6efd'):
                size = 64
                img = Image.new('RGB', (size, size), color=color)
                draw = ImageDraw.Draw(img)
                margin = 16
                draw.rectangle([margin, margin, size - margin, size - margin], fill='white')
                inner = 24
                draw.rectangle([inner, inner, size - inner, size - inner], fill=color)
                center = size // 2
                draw.polygon([
                    (center - 8, center - 10),
                    (center - 8, center + 10),
                    (center + 10, center)
                ], fill='white')
                return img

            def update_icon():
                """Обновить иконку в зависимости от статуса"""
                if not TrayModule._icon:
                    return
                try:
                    if _is_web_running():
                        TrayModule._icon.icon = make_icon('#198754')
                    else:
                        TrayModule._icon.icon = make_icon('#dc3545')
                except Exception:
                    pass

            def on_show(icon, item):
                """Открыть веб-интерфейс, запустить если нужно"""
                if not _is_web_running():
                    TrayModule._start_web_server()
                    time.sleep(3)
                import webbrowser
                webbrowser.open(url)

            def on_start(icon, item):
                """Запустить веб-сервер"""
                if _is_web_running():
                    return
                TrayModule._start_web_server()
                time.sleep(2)
                update_icon()

            def on_stop(icon, item):
                """Остановить веб-сервер"""
                TrayModule._stop_web_server()
                time.sleep(1)
                update_icon()

            def on_status(icon, item):
                """Показать статус через балloon"""
                service = _is_service_running()
                web = _is_web_running()
                lines = [
                    f"Сервис: {'ON' if service else 'OFF'}",
                    f"Веб-сервер: {'ON' if web else 'OFF'}",
                    f"Порт: {port}",
                    f"PID: {os.getpid()}"
                ]
                TrayModule._balloon("Starter Status", "\n".join(lines))

            def on_restart(icon, item):
                """Перезапуск — убить всё и запустить заново"""
                TrayModule._kill_all()
                time.sleep(2)
                TrayModule._start_web_server()
                time.sleep(3)
                update_icon()

            def on_quit(icon, item):
                """Выход"""
                TrayModule._kill_all()
                icon.stop()
                os._exit(0)

            menu = pystray.Menu(
                pystray.MenuItem("🌐 Показать Starter", on_show, default=True),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("▶️ Запустить веб-сервер", on_start),
                pystray.MenuItem("⏹ Остановить веб-сервер", on_stop),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("🔄 Перезапустить", on_restart),
                pystray.MenuItem("📊 Статус", on_status),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("❌ Выйти", on_quit)
            )

            icon = pystray.Icon(
                "starter_server",
                make_icon('#0d6efd'),
                "Starter Server",
                menu
            )

            icon.run_detached()

            def monitor_loop():
                while TrayModule._running:
                    time.sleep(5)
                    update_icon()

            threading.Thread(target=monitor_loop, daemon=True).start()

            return icon

        except ImportError as e:
            logger.warning(f"pystray not installed: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to create tray: {e}")
            return None

    @staticmethod
    def _balloon(title: str, message: str):
        """Показать balloon-уведомление через PowerShell"""
        ps_cmd = f'''
        Add-Type -AssemblyName System.Windows.Forms
        $notify = New-Object System.Windows.Forms.NotifyIcon
        $notify.Icon = [System.Drawing.Icon]::ExtractAssociatedIcon([System.Windows.Forms.Application]::ExecutablePath)
        $notify.Visible = $true
        $notify.ShowBalloonTip(3000, "{title}", "{message}", [System.Windows.Forms.ToolTipIcon]::Info)
        '''
        try:
            subprocess.run(['powershell', '-Command', ps_cmd],
                           capture_output=True, startupinfo=_si(), timeout=10)
        except Exception:
            pass

    @staticmethod
    def run_tray():
        if TrayModule._running:
            return
        if not TrayModule.check_dependencies():
            return

        if 'pythonw' in sys.executable.lower():
            import multiprocessing
            p = multiprocessing.Process(target=TrayModule._tray_main, daemon=True)
            p.start()
            return

        TrayModule._running = True
        TrayModule._tray_main()

    @staticmethod
    def stop_tray():
        TrayModule._running = False
        if TrayModule._icon:
            try:
                TrayModule._icon.stop()
            except Exception:
                pass
        logger.info("Tray stopped")
