# files/core/oss/windows/default/tray.py
"""
Модуль для системного трея в Windows
"""
import os
import sys
import threading
import subprocess
import time
from pathlib import Path
from typing import Dict, Any

from files.core.base_module import BaseModule
from files.core.utils.globalVars_utils import get_global, set_global
from files.core.utils.log_utils import LogManager

logger = LogManager.get_logger('tray_windows')


class TrayModule(BaseModule):
    """Модуль для управления иконкой в системном трее Windows"""
    
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
            logger.debug(f"Icons directory: {icons_dir}")
    
    @staticmethod
    def is_available() -> bool:
        try:
            import pystray
            from PIL import Image
            return True
        except ImportError:
            return False
    
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
            print(f"\n   ⚠️ Для иконки в трее требуются: {', '.join(missing)}")
            print(f"   Установите: pip install {' '.join(missing)}")
            return False
        print("   ✅ Все зависимости для трея установлены")
        return True
    
    @staticmethod
    def create_tray_icon():
        try:
            import pystray
            from PIL import Image, ImageDraw
            
            size = 64
            img = Image.new('RGB', (size, size), color='#0d6efd')
            draw = ImageDraw.Draw(img)
            margin = 16
            draw.rectangle([margin, margin, size - margin, size - margin], fill='white')
            inner_margin = 24
            draw.rectangle([inner_margin, inner_margin, size - inner_margin, size - inner_margin], fill='#0d6efd')
            center = size // 2
            draw.polygon([(center - 8, center - 10), (center - 8, center + 10), (center + 10, center)], fill='white')
            
            port = get_global('port', 2000)
            url = f"https://localhost:{port}"
            
            def on_quit(icon, item):
                print("\n🛑 Завершение работы через трей...")
                icon.stop()
                os._exit(0)

            def on_restart(icon, item):
                print("\n🔄 Перезапуск сервера...")
                starter_path = get_global('starter_path')
                if starter_path:
                    script_path = starter_path / "starter.py"
                    subprocess.Popen([sys.executable, str(script_path)], creationflags=subprocess.CREATE_NEW_CONSOLE)
                on_quit(icon, item)

            def on_open_browser(icon, item):
                import webbrowser
                webbrowser.open(url)

            def on_show_status(icon, item):
                ps_cmd = f'''
                Add-Type -AssemblyName System.Windows.Forms
                $notify = New-Object System.Windows.Forms.NotifyIcon
                $notify.Icon = [System.Drawing.Icon]::ExtractAssociatedIcon([System.Windows.Forms.Application]::ExecutablePath)
                $notify.Visible = $true
                $notify.ShowBalloonTip(3000, "Starter Server", "Сервер запущен на {protocol}://localhost:{port}`nPID: {os.getpid()}", [System.Windows.Forms.ToolTipIcon]::Info)
                '''
                subprocess.run(['powershell', '-Command', ps_cmd], capture_output=True)

            def check_server_status():
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                result = sock.connect_ex(('127.0.0.1', port))
                sock.close()
                return result == 0

            def on_start_server(icon, item):
                starter_path = get_global('starter_path')
                if starter_path:
                    script_path = starter_path / "starter.py"
                    subprocess.Popen([sys.executable, str(script_path)], creationflags=subprocess.CREATE_NEW_CONSOLE)
                    time.sleep(2)
                    update_menu(icon)

            def on_stop_server(icon, item):
                from files.core.utils.loader_utils import get
                process_module = get('process')
                if process_module:
                    process_module.cleanup_orphaned()
                    processes_file = get_global('starter_path') / 'processes.json'
                    if processes_file.exists():
                        import json
                        with open(processes_file, 'r') as f:
                            data = json.load(f)
                        for proc in data.get('processes', []):
                            if proc.get('pid') != os.getpid():
                                try:
                                    import psutil
                                    psutil.Process(proc['pid']).terminate()
                                except:
                                    pass
                    time.sleep(1)
                    update_menu(icon)

            def update_menu(icon):
                server_running = check_server_status()
                status_text = "🟢 Работает" if server_running else "🔴 Остановлен"
                start_text = "⏹️ Остановить сервер" if server_running else "▶️ Запустить сервер"

                menu = pystray.Menu(
                    pystray.MenuItem(f"🌐 Открыть Starter", on_open_browser),
                    pystray.MenuItem(f"📡 Порт: {port}", lambda: None, enabled=False),
                    pystray.MenuItem(f"{status_text}", lambda: None, enabled=False),
                    pystray.Menu.SEPARATOR,
                    pystray.MenuItem(start_text, on_stop_server if server_running else on_start_server),
                    pystray.MenuItem("🔄 Перезапустить", on_restart),
                    pystray.MenuItem("📊 Показать статус", on_show_status),
                    pystray.Menu.SEPARATOR,
                    pystray.MenuItem("❌ Выйти", on_quit)
                )
                icon.menu = menu
                icon.update_menu()

            def refresh_loop(icon):
                while True:
                    time.sleep(5)
                    try:
                        update_menu(icon)
                    except:
                        pass

            menu = pystray.Menu(
                pystray.MenuItem(f"🌐 Открыть Starter", on_open_browser),
                pystray.MenuItem(f"📡 Порт: {port}", lambda: None, enabled=False),
                pystray.MenuItem("🟢 Работает" if check_server_status() else "🔴 Остановлен", lambda: None, enabled=False),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("⏹️ Остановить сервер" if check_server_status() else "▶️ Запустить сервер",
                                 on_stop_server if check_server_status() else on_start_server),
                pystray.MenuItem("🔄 Перезапустить", on_restart),
                pystray.MenuItem("📊 Показать статус", on_show_status),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("❌ Выйти", on_quit)
            )
            icon = pystray.Icon("starter_server", img, "Starter Server", menu)

            refresh_thread = threading.Thread(target=refresh_loop, args=(icon,), daemon=True)
            refresh_thread.start()

            return icon
        except ImportError as e:
            logger.warning(f"Required library not installed: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to create tray icon: {e}")
            return None
    
    @staticmethod
    def run_tray():
        if TrayModule._running:
            return

        # Проверяем, не запущен ли уже трей (по PID в processes.json)
        processes_file = get_global('starter_path') / 'processes.json'
        if processes_file.exists():
            try:
                import json
                with open(processes_file, 'r') as f:
                    data = json.load(f)
                current_pid = os.getpid()
                for proc in data.get('processes', []):
                    if proc.get('pid') != current_pid and proc.get('status') == 'running':
                        print("   ℹ️ Трей уже запущен другим процессом — пропускаем")
                        return
            except Exception:
                pass

        if not TrayModule.check_dependencies():
            return
        TrayModule._running = True

        # Дополнительная проверка — порт не должен быть занят
        import socket
        port = get_global('port', 2000)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if sock.connect_ex(('127.0.0.1', port)) == 0:
            print(f"   ⚠️ Порт {port} занят — трей не запускается")
            sock.close()
            return
        sock.close()
        
        def tray_loop():
            try:
                TrayModule._icon = TrayModule.create_tray_icon()
                if TrayModule._icon:
                    print("   🖥️ Иконка в системном трее активна")
                    TrayModule._icon.run()
                else:
                    print("   ⚠️ Не удалось создать иконку в трее")
            except Exception as e:
                logger.error(f"Tray icon error: {e}")
        
        TrayModule._tray_thread = threading.Thread(target=tray_loop, daemon=False)
        TrayModule._tray_thread.start()
        time.sleep(1)
    
    @staticmethod
    def stop_tray():
        TrayModule._running = False
        if TrayModule._icon:
            try:
                TrayModule._icon.stop()
            except:
                pass
        logger.info("Tray icon stopped")