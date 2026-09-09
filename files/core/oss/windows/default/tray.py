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
        """Проверяет доступность модуля (только Windows)"""
        return sys.platform == 'win32'
    
    @staticmethod
    def set_globals():
        """Устанавливает глобальные переменные"""
        starter_path = get_global('starter_path')
        if starter_path:
            icons_dir = starter_path / "files" / "web" / "public"
            set_global('tray_icons_dir', icons_dir)
            logger.debug(f"Icons directory: {icons_dir}")
    
    @staticmethod
    def is_available() -> bool:
        """Проверяет доступность библиотек для трея"""
        try:
            import pystray
            from PIL import Image
            return True
        except ImportError:
            return False
    
    @staticmethod
    def check_dependencies():
        """Проверяет наличие зависимостей для трея"""
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
    def kill_starter_processes():
        """Убивает все процессы starter.py"""
        current_pid = os.getpid()
        killed = []
        
        try:
            output = subprocess.check_output(
                ['tasklist', '/FI', 'IMAGENAME eq python.exe', '/FO', 'CSV', '/NH'],
                text=True
            )
            
            import re
            for line in output.split('\n'):
                if 'starter.py' in line.lower():
                    match = re.search(r'"(\d+)"', line)
                    if match:
                        pid = int(match.group(1))
                        if pid != current_pid:
                            subprocess.run(['taskkill', '/F', '/PID', str(pid)], 
                                         capture_output=True, check=False)
                            killed.append(pid)
                            print(f"   ✅ Убит процесс starter.py PID: {pid}")
            
            return killed
        except Exception as e:
            logger.error(f"Error killing starter processes: {e}")
            return []
    
    @staticmethod
    def create_tray_icon():
        """Создает иконку в системном трее"""
        try:
            import pystray
            from PIL import Image, ImageDraw
            
            # Создаем иконку программно (64x64)
            size = 64
            img = Image.new('RGB', (size, size), color='#0d6efd')
            draw = ImageDraw.Draw(img)
            
            # Рисуем квадрат в центре
            margin = 16
            draw.rectangle([margin, margin, size - margin, size - margin], fill='white')
            
            # Рисуем внутренний квадрат
            inner_margin = 24
            draw.rectangle([inner_margin, inner_margin, size - inner_margin, size - inner_margin], 
                          fill='#0d6efd')
            
            # Рисуем стрелку "play"
            center = size // 2
            draw.polygon([
                (center - 8, center - 10),
                (center - 8, center + 10),
                (center + 10, center)
            ], fill='white')
            
            # Получаем URL сервера
            port = get_global('port', 2100)
            protocol = 'https'
            url = f"{protocol}://127.0.0.1:{port}"
            
            def on_quit(icon, item):
                """Выход из приложения"""
                print("\n🛑 Завершение работы через трей...")
                TrayModule.kill_starter_processes()
                icon.stop()
                os._exit(0)
            
            def on_restart(icon, item):
                """Перезапуск сервера"""
                print("\n🔄 Перезапуск сервера...")
                
                starter_path = get_global('starter_path')
                if starter_path:
                    script_path = starter_path / "starter.py"
                    subprocess.Popen([sys.executable, str(script_path)], 
                                   creationflags=subprocess.CREATE_NEW_CONSOLE)
                
                on_quit(icon, item)
            
            def on_open_browser(icon, item):
                """Открыть браузер"""
                import webbrowser
                webbrowser.open(url)
            
            def on_show_status(icon, item):
                """Показать статус"""
                port = get_global('port', 2100)
                protocol = 'https'
                
                ps_cmd = f'''
                Add-Type -AssemblyName System.Windows.Forms
                $notify = New-Object System.Windows.Forms.NotifyIcon
                $notify.Icon = [System.Drawing.Icon]::ExtractAssociatedIcon([System.Windows.Forms.Application]::ExecutablePath)
                $notify.Visible = $true
                $notify.ShowBalloonTip(3000, "Starter Server", "Сервер запущен на {protocol}://127.0.0.1:{port}`nPID: {os.getpid()}", [System.Windows.Forms.ToolTipIcon]::Info)
                '''
                subprocess.run(['powershell', '-Command', ps_cmd], capture_output=True)
            
            # Создаем меню
            menu = pystray.Menu(
                pystray.MenuItem(f"🌐 Открыть Starter", on_open_browser),
                pystray.MenuItem(f"📡 Порт: {port}", lambda: None, enabled=False),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("🔄 Перезапустить", on_restart),
                pystray.MenuItem("📊 Показать статус", on_show_status),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("❌ Выйти", on_quit)
            )
            
            icon = pystray.Icon("starter_server", img, "Starter Server", menu)
            return icon
            
        except ImportError as e:
            logger.warning(f"Required library not installed: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to create tray icon: {e}")
            return None
    
    @staticmethod
    def run_tray():
        """Запускает иконку в трее в отдельном потоке"""
        if TrayModule._running:
            return
        
        if not TrayModule.check_dependencies():
            return
        
        TrayModule._running = True
        
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
        """Останавливает иконку в трее"""
        TrayModule._running = False
        if TrayModule._icon:
            try:
                TrayModule._icon.stop()
            except:
                pass
        logger.info("Tray icon stopped")