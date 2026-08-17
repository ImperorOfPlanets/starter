import os
import sys
import platform
import subprocess
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Tuple, Optional
import getpass
from datetime import datetime

from files.core.utils.globalVars_utils import get_global, set_global
from files.core.utils.log_utils import logger

class ServiceManager:
    def __init__(self, service_name: str = "starter-service"):
        # Используем глобальные переменные
        self.script_path = get_global('script_path') or Path(sys.argv[0]).absolute()
        self.starter_path = get_global('starter_path') or self.script_path.parent
        self.service_name = service_name
        self.system = platform.system().lower()
        self.username = getpass.getuser()
        
        # Определяем команду для запуска
        self.exec_cmd = f'"{sys.executable}" "{self.script_path}"'
        
    def is_installed(self) -> bool:
        """Проверяет, установлена ли служба"""
        if self.system == "windows":
            return self._check_windows_service()
        elif self.system in ["linux", "darwin"]:
            return self._check_unix_service()
        return False
    
    def install(self) -> bool:
        """Устанавливает службу"""
        print(f"\n{'='*40}")
        print(f"📦 Установка службы {self.service_name}")
        
        if self.system == "windows":
            return self._install_windows_service()
        elif self.system in ["linux", "darwin"]:
            return self._install_unix_service()
        
        print(f"❌ Неподдерживаемая ОС: {self.system}")
        return False
    
    def uninstall(self) -> bool:
        """Удаляет службу"""
        print(f"\n{'='*40}")
        print(f"🗑️  Удаление службы {self.service_name}")
        
        if not self.is_installed():
            print("⚠️ Служба не установлена")
            return False
            
        if self.system == "windows":
            return self._uninstall_windows_service()
        elif self.system in ["linux", "darwin"]:
            return self._uninstall_unix_service()
        
        return False
    
    def start(self) -> bool:
        """Запускает службу"""
        try:
            if self.system == "windows":
                subprocess.run(['sc', 'start', self.service_name], check=True, 
                             capture_output=True, text=True)
            elif self.system == "linux":
                subprocess.run(['systemctl', 'start', self.service_name], check=True)
            elif self.system == "darwin":
                subprocess.run(['launchctl', 'start', self.service_name], check=True)
            
            print(f"✅ Служба {self.service_name} запущена")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Ошибка запуска службы: {e}")
            return False
    
    def stop(self) -> bool:
        """Останавливает службу"""
        try:
            if self.system == "windows":
                subprocess.run(['sc', 'stop', self.service_name], check=True,
                             capture_output=True, text=True)
            elif self.system == "linux":
                subprocess.run(['systemctl', 'stop', self.service_name], check=True)
            elif self.system == "darwin":
                subprocess.run(['launchctl', 'stop', self.service_name], check=True)
            
            print(f"✅ Служба {self.service_name} остановлена")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Ошибка остановки службы: {e}")
            return False

    def _check_windows_service(self) -> bool:
        """Проверяет наличие службы в Windows"""
        try:
            # Проверяем через sc query
            result = subprocess.run(
                ['sc', 'query', self.service_name],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode == 0 and "SERVICE_NAME" in result.stdout:
                return True
            
            # Дополнительная проверка через PowerShell
            ps_cmd = f"Get-Service '{self.service_name}' -ErrorAction SilentlyContinue"
            result = subprocess.run(
                ['powershell', '-Command', ps_cmd],
                capture_output=True,
                text=True,
                check=False
            )
            
            return result.returncode == 0
            
        except Exception:
            return False

    def _install_windows_service(self) -> bool:
        """Устанавливает службу в Windows с автоматической установкой NSSM"""
        try:
            # 1. Проверяем или устанавливаем NSSM
            nssm_path = self._get_nssm_path()
            if not nssm_path:
                print("🔄 NSSM не найден, начинаем автоматическую установку...")
                nssm_path = self._install_nssm_auto()
                if not nssm_path:
                    return False
            
            # 2. Подготавливаем директории для логов
            log_dir = get_global('path_log_install') or self.starter_path / "logs" / "service"
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / "service.log"
            
            # 3. Создаем файл лога
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(f"=== Service Log Started at {datetime.now()} ===\n")
                f.write(f"Service: {self.service_name}\n")
                f.write(f"Python: {sys.executable}\n")
                f.write(f"Script: {self.script_path}\n")
                f.write(f"Working Dir: {self.starter_path}\n")
                f.write("="*50 + "\n\n")
            
            print(f"📁 Рабочая директория: {self.starter_path}")
            print(f"📄 Лог файл: {log_file}")
            print(f"🔧 NSSM: {nssm_path}")
            
            # 4. Останавливаем службу если она уже существует
            if self.is_installed():
                print("⚠️  Служба уже существует, останавливаем...")
                self.stop()
                time.sleep(2)
            
            # 5. Устанавливаем службу через NSSM
            print("🔄 Установка службы через NSSM...")
            
            # Команда для установки
            install_cmd = [
                str(nssm_path), 'install', self.service_name,
                str(sys.executable), str(self.script_path), '--service'
            ]
            
            result = subprocess.run(
                install_cmd,
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode != 0:
                print(f"❌ Ошибка при установке: {result.stderr}")
                return False
            
            # 6. Настраиваем параметры службы
            print("⚙️ Настройка параметров службы...")
            
            # Рабочая директория
            subprocess.run([str(nssm_path), 'set', self.service_name, 
                          'AppDirectory', str(self.starter_path)], 
                         check=True, capture_output=True)
            
            # Перенаправление вывода
            subprocess.run([str(nssm_path), 'set', self.service_name, 
                          'AppStdout', str(log_file)], 
                         check=True, capture_output=True)
            
            subprocess.run([str(nssm_path), 'set', self.service_name, 
                          'AppStderr', str(log_file)], 
                         check=True, capture_output=True)
            
            # Автозапуск
            subprocess.run([str(nssm_path), 'set', self.service_name, 
                          'Start', 'SERVICE_AUTO_START'], 
                         check=True, capture_output=True)
            
            # Тип службы
            subprocess.run([str(nssm_path), 'set', self.service_name, 
                          'Type', 'SERVICE_WIN32_OWN_PROCESS'], 
                         check=True, capture_output=True)
            
            # Восстановление после сбоев
            subprocess.run([str(nssm_path), 'set', self.service_name, 
                          'AppRestartDelay', '5000'], 
                         check=True, capture_output=True)
            
            # Устанавливаем кодировку UTF-8
            subprocess.run([str(nssm_path), 'set', self.service_name,
                          'AppEnvironmentExtra', 'PYTHONIOENCODING=utf-8'],
                         check=True, capture_output=True)
            
            print(f"✅ Служба {self.service_name} успешно установлена!")
            print("\n📋 КОМАНДЫ ДЛЯ УПРАВЛЕНИЯ:")
            print(f"  Запуск:    sc start {self.service_name}")
            print(f"  Остановка: sc stop {self.service_name}")
            print(f"  Статус:    sc query {self.service_name}")
            print(f"  Логи:      {log_file}")
            print(f"  Удаление:  nssm remove {self.service_name} confirm")
            
            # 7. Запускаем службу
            print("\n🔄 Запуск службы...")
            if self.start():
                print("✅ Служба успешно запущена!")
            else:
                print("⚠️  Служба установлена, но не запущена автоматически")
                print("💡 Запустите вручную: sc start {self.service_name}")
            
            return True

        except subprocess.CalledProcessError as e:
            print(f"❌ Ошибка установки службы: {e}")
            if hasattr(e, 'stderr') and e.stderr:
                print(f"Детали: {e.stderr[:200]}")
            return False
        except Exception as e:
            print(f"❌ Критическая ошибка: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _get_nssm_path(self) -> Optional[Path]:
        """Ищет NSSM в системе"""
        possible_paths = []
        
        # Стандартные пути
        possible_paths.append(Path("C:\\nssm\\nssm.exe"))
        possible_paths.append(Path("C:\\Program Files\\nssm\\nssm.exe"))
        possible_paths.append(Path("C:\\Program Files (x86)\\nssm\\nssm.exe"))
        
        # Из переменных окружения
        for env_var in ['ProgramFiles', 'ProgramFiles(x86)', 'SystemDrive']:
            if env_var in os.environ:
                possible_paths.append(Path(os.environ[env_var]) / 'nssm' / 'nssm.exe')
        
        # Из PATH
        path_dirs = os.environ.get('PATH', '').split(os.pathsep)
        for dir_path in path_dirs:
            if dir_path:
                possible_paths.append(Path(dir_path) / 'nssm.exe')
        
        # Проверяем все пути
        for path in possible_paths:
            if path.exists():
                return path.resolve()
        
        return None
    
    def _install_nssm_auto(self) -> Optional[Path]:
        """Автоматическая установка NSSM"""
        try:
            print("\n" + "="*50)
            print("🔄 АВТОМАТИЧЕСКАЯ УСТАНОВКА NSSM")
            print("="*50)
            
            # URL для скачивания (используем последнюю версию)
            nssm_url = "https://nssm.cc/release/nssm-2.24.zip"
            print(f"📥 Скачивание NSSM с: {nssm_url}")
            
            # Создаем временную директорию
            temp_dir = Path(tempfile.gettempdir()) / "nssm_install"
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            zip_path = temp_dir / "nssm.zip"
            
            # Скачиваем архив
            try:
                urllib.request.urlretrieve(nssm_url, zip_path)
                print(f"✅ Скачано: {zip_path}")
            except Exception as e:
                print(f"❌ Ошибка скачивания: {e}")
                print("💡 Альтернатива: скачайте NSSM вручную с https://nssm.cc/download")
                return None
            
            # Распаковываем архив
            extract_dir = temp_dir / "extracted"
            extract_dir.mkdir(parents=True, exist_ok=True)
            
            print(f"📦 Распаковка архива в: {extract_dir}")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            # Ищем nssm.exe в распакованных файлах
            nssm_exe = None
            for root, dirs, files in os.walk(extract_dir):
                for file in files:
                    if file.lower() == "nssm.exe":
                        nssm_exe = Path(root) / file
                        break
                if nssm_exe:
                    break
            
            if not nssm_exe or not nssm_exe.exists():
                print("❌ nssm.exe не найден в архиве")
                return None
            
            print(f"✅ Найден NSSM: {nssm_exe}")
            
            # Определяем куда установить (обычно Program Files)
            if 'ProgramFiles' in os.environ:
                install_dir = Path(os.environ['ProgramFiles']) / 'nssm'
            else:
                install_dir = Path("C:\\Program Files\\nssm")
            
            install_dir.mkdir(parents=True, exist_ok=True)
            dest_path = install_dir / "nssm.exe"
            
            # Копируем файл
            print(f"📝 Копирование в: {dest_path}")
            shutil.copy2(nssm_exe, dest_path)
            
            # Добавляем в PATH если нужно
            current_path = os.environ.get('PATH', '')
            if str(install_dir) not in current_path:
                # Для текущей сессии
                os.environ['PATH'] = f"{install_dir}{os.pathsep}{current_path}"
                
                # Пытаемся добавить в системный PATH (требует прав администратора)
                try:
                    import winreg
                    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                      "SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Environment",
                                      0, winreg.KEY_ALL_ACCESS) as key:
                        path_value, _ = winreg.QueryValueEx(key, "Path")
                        if str(install_dir) not in path_value:
                            new_path = f"{path_value}{os.pathsep}{install_dir}"
                            winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new_path)
                            print("✅ Добавлено в системный PATH")
                except Exception:
                    print("⚠️  Не удалось добавить в системный PATH (требуются права администратора)")
            
            # Очищаем временные файлы
            try:
                shutil.rmtree(temp_dir)
            except:
                pass
            
            print("✅ NSSM успешно установлен!")
            return dest_path
            
        except Exception as e:
            print(f"❌ Ошибка установки NSSM: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _check_unix_service(self) -> bool:
        """Проверяет наличие службы в Unix-системах"""
        try:
            if self.system == "linux":
                # Проверка systemd
                service_file = Path(f"/etc/systemd/system/{self.service_name}.service")
                if service_file.exists():
                    return True
                
                # Проверка через systemctl
                result = subprocess.run(
                    ['systemctl', 'status', self.service_name],
                    capture_output=True,
                    text=True,
                    check=False
                )
                return result.returncode == 0
            elif self.system == "darwin":
                # Проверка launchd
                plist_file = Path(f"/Library/LaunchDaemons/{self.service_name}.plist")
                if plist_file.exists():
                    return True
            
            # Общая проверка
            result = subprocess.run(
                ['service', self.service_name, 'status'],
                capture_output=True,
                text=True,
                check=False
            )
            return result.returncode == 0
            
        except Exception:
            return False
    
    def _install_unix_service(self) -> bool:
        """Устанавливает службу в Unix-системах"""
        try:
            if self.system == "linux":
                return self._install_linux_systemd()
            elif self.system == "darwin":
                return self._install_macos_launchd()
            else:
                return self._install_generic_unix()
                
        except Exception as e:
            print(f"❌ Ошибка установки службы: {e}")
            return False
    
    def _install_linux_systemd(self) -> bool:
        """Устанавливает службу как systemd unit для Linux"""
        try:
            # Проверяем права
            if os.geteuid() != 0:
                print("❌ Для установки systemd службы требуются права root")
                print("💡 Запустите с sudo:")
                print(f"   sudo {sys.executable} {self.script_path} --setup-service")
                return False
            
            # Подготавливаем директории для логов
            log_dir = self.starter_path / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            
            service_content = f"""[Unit]
Description={self.service_name} - Starter Service
After=network.target
Wants=network.target

[Service]
Type=simple
User={self.username}
ExecStart={sys.executable} {self.script_path} --service
WorkingDirectory={self.starter_path}
Restart=always
RestartSec=5
StandardOutput=append:{log_dir}/service.log
StandardError=append:{log_dir}/service-error.log
Environment=PYTHONUNBUFFERED=1

# Безопасность
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
"""
            service_file = Path(f"/etc/systemd/system/{self.service_name}.service")
            
            print(f"📝 Создание файла службы: {service_file}")
            service_file.write_text(service_content)
            
            # Перезагружаем systemd и включаем службу
            print("🔄 Обновление systemd...")
            subprocess.run(['systemctl', 'daemon-reload'], check=True)
            subprocess.run(['systemctl', 'enable', self.service_name], check=True)
            
            print("✅ Служба установлена как systemd unit")
            print("\n📋 КОМАНДЫ ДЛЯ УПРАВЛЕНИЯ:")
            print(f"  Запуск:    sudo systemctl start {self.service_name}")
            print(f"  Остановка: sudo systemctl stop {self.service_name}")
            print(f"  Статус:    systemctl status {self.service_name}")
            print(f"  Логи:      journalctl -u {self.service_name} -f")
            print(f"  Удаление:  sudo systemctl disable {self.service_name} && sudo rm {service_file}")
            
            # Запускаем службу
            print("\n🔄 Запуск службы...")
            subprocess.run(['systemctl', 'start', self.service_name], check=True)
            print("✅ Служба запущена!")
            
            return True
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return False
    
    def _install_macos_launchd(self) -> bool:
        """Устанавливает службу как launchd для macOS"""
        try:
            # Проверяем права
            if os.geteuid() != 0:
                print("❌ Для установки launchd службы требуются права root")
                print("💡 Запустите с sudo:")
                print(f"   sudo {sys.executable} {self.script_path} --setup-service")
                return False
            
            # Подготавливаем директории для логов
            log_dir = self.starter_path / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            
            plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{self.service_name}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{sys.executable}</string>
        <string>{self.script_path}</string>
        <string>--service</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>WorkingDirectory</key>
    <string>{self.starter_path}</string>
    <key>StandardOutPath</key>
    <string>{log_dir}/service.log</string>
    <key>StandardErrorPath</key>
    <string>{log_dir}/service-error.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PYTHONUNBUFFERED</key>
        <string>1</string>
    </dict>
</dict>
</plist>
"""
            plist_file = Path(f"/Library/LaunchDaemons/{self.service_name}.plist")
            
            print(f"📝 Создание файла службы: {plist_file}")
            plist_file.write_text(plist_content)
            
            # Загружаем службу
            print("🔄 Загрузка службы...")
            subprocess.run(['launchctl', 'load', str(plist_file)], check=True)
            
            print("✅ Служба установлена как launchd")
            print("\n📋 КОМАНДЫ ДЛЯ УПРАВЛЕНИЯ:")
            print(f"  Запуск:    sudo launchctl start {self.service_name}")
            print(f"  Остановка: sudo launchctl stop {self.service_name}")
            print(f"  Статус:    launchctl list | grep {self.service_name}")
            print(f"  Логи:      tail -f {log_dir}/service.log")
            print(f"  Удаление:  sudo launchctl unload {plist_file} && sudo rm {plist_file}")
            
            # Запускаем службу
            print("\n🔄 Запуск службы...")
            subprocess.run(['launchctl', 'start', self.service_name], check=True)
            print("✅ Служба запущена!")
            
            return True
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return False
    
    def _install_generic_unix(self) -> bool:
        """Устанавливает службу для других Unix-систем"""
        try:
            # Проверяем права
            if os.geteuid() != 0:
                print("❌ Для установки службы требуются права root")
                return False
            
            # Подготавливаем директории
            log_dir = self.starter_path / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            
            initd_content = f"""#!/bin/bash
### BEGIN INIT INFO
# Provides:          {self.service_name}
# Required-Start:    $network $local_fs $remote_fs
# Required-Stop:     $network $local_fs $remote_fs
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: {self.service_name}
# Description:       Starter Service
### END INIT INFO

NAME="{self.service_name}"
SCRIPT="{self.script_path}"
WORKDIR="{self.starter_path}"
LOGFILE="{log_dir}/service.log"
PIDFILE="/var/run/${{NAME}}.pid"
PYTHON="{sys.executable}"

start() {{
    echo -n "Starting $NAME: "
    cd "$WORKDIR"
    $PYTHON "$SCRIPT" --service >> "$LOGFILE" 2>&1 &
    echo $! > "$PIDFILE"
    echo "OK"
}}

stop() {{
    echo -n "Stopping $NAME: "
    if [ -f "$PIDFILE" ]; then
        kill -9 $(cat "$PIDFILE") 2>/dev/null
        rm -f "$PIDFILE"
    fi
    echo "OK"
}}

status() {{
    if [ -f "$PIDFILE" ]; then
        PID=$(cat "$PIDFILE")
        if ps -p $PID > /dev/null 2>&1; then
            echo "$NAME is running (pid: $PID)"
            return 0
        fi
    fi
    echo "$NAME is not running"
    return 3
}}

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        stop
        sleep 2
        start
        ;;
    status)
        status
        ;;
    *)
        echo "Usage: $0 {{start|stop|restart|status}}"
        exit 1
        ;;
esac
exit $?
"""
            initd_file = Path(f"/etc/init.d/{self.service_name}")
            
            print(f"📝 Создание init скрипта: {initd_file}")
            initd_file.write_text(initd_content)
            initd_file.chmod(0o755)
            
            # Создаем симлинки для автозапуска
            print("🔗 Создание ссылок для автозапуска...")
            for runlevel in [2, 3, 4, 5]:
                link_path = Path(f"/etc/rc{runlevel}.d/S90{self.service_name}")
                if not link_path.exists():
                    link_path.symlink_to(initd_file)
            
            print("✅ Служба установлена (init.d)")
            print("\n📋 КОМАНДЫ ДЛЯ УПРАВЛЕНИЯ:")
            print(f"  Запуск:    service {self.service_name} start")
            print(f"  Остановка: service {self.service_name} stop")
            print(f"  Статус:    service {self.service_name} status")
            print(f"  Логи:      tail -f {log_dir}/service.log")
            print(f"  Удаление:  rm {initd_file}")
            
            # Запускаем службу
            print("\n🔄 Запуск службы...")
            subprocess.run(['service', self.service_name, 'start'], check=True)
            print("✅ Служба запущена!")
            
            return True
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return False
    
    def _uninstall_unix_service(self) -> bool:
        """Удаляет службу в Unix-системах"""
        try:
            if self.system == "linux":
                # Останавливаем и отключаем systemd
                subprocess.run(['systemctl', 'stop', self.service_name], check=False)
                subprocess.run(['systemctl', 'disable', self.service_name], check=False)
                
                service_file = Path(f"/etc/systemd/system/{self.service_name}.service")
                if service_file.exists():
                    service_file.unlink()
                    subprocess.run(['systemctl', 'daemon-reload'], check=True)
                    print("✅ Systemd unit удален")
            
            elif self.system == "darwin":
                # Останавливаем и выгружаем launchd
                subprocess.run(['launchctl', 'stop', self.service_name], check=False)
                subprocess.run(['launchctl', 'unload', self.service_name], check=False)
                
                plist_file = Path(f"/Library/LaunchDaemons/{self.service_name}.plist")
                if plist_file.exists():
                    plist_file.unlink()
                    print("✅ LaunchDaemon удален")
            
            # Удаляем init.d скрипт
            initd_file = Path(f"/etc/init.d/{self.service_name}")
            if initd_file.exists():
                subprocess.run(['service', self.service_name, 'stop'], check=False)
                initd_file.unlink()
                print("✅ Init.d скрипт удален")
            
            # Удаляем pid файл
            pid_file = Path(f"/var/run/{self.service_name}.pid")
            if pid_file.exists():
                pid_file.unlink()
            
            print(f"✅ Служба {self.service_name} полностью удалена")
            return True
        except Exception as e:
            print(f"❌ Ошибка удаления: {e}")
            return False

    def _uninstall_windows_service(self) -> bool:
        """Удаляет службу Windows"""
        try:
            # 1. Останавливаем службу
            try:
                subprocess.run(['sc', 'stop', self.service_name], 
                             capture_output=True, text=True, check=False)
            except:
                pass
            
            # 2. Пробуем удалить через NSSM если он есть
            nssm_path = self._get_nssm_path()
            if nssm_path and nssm_path.exists():
                try:
                    subprocess.run([str(nssm_path), 'remove', self.service_name, 'confirm'],
                                 capture_output=True, text=True, check=False)
                    print("✅ Удалено через NSSM")
                except:
                    pass
            
            # 3. Удаляем через sc
            for _ in range(3):  # Пробуем несколько раз
                try:
                    result = subprocess.run(['sc', 'delete', self.service_name],
                                          capture_output=True, text=True, check=False)
                    if result.returncode == 0:
                        break
                except:
                    pass
            
            print(f"✅ Служба {self.service_name} удалена")
            return True
        except Exception as e:
            print(f"❌ Ошибка удаления: {e}")
            return False

def manage_service():
    """Основная функция управления службой"""
    # Создаем менеджер с использованием глобальных переменных
    manager = ServiceManager("starter-service")
    
    print("\n" + "="*60)
    print("⚙️  УПРАВЛЕНИЕ СИСТЕМНОЙ СЛУЖБОЙ".center(60))
    print("="*60)
    
    print(f"📁 Директория: {manager.starter_path}")
    print(f"📄 Скрипт: {manager.script_path.name}")
    print(f"🖥️  ОС: {platform.system()}")
    print(f"🔧 Имя службы: {manager.service_name}")
    
    # Проверяем статус
    if manager.is_installed():
        status = "✅ Установлена и запущена"
    else:
        status = "❌ Не установлена"
    print(f"📊 Статус: {status}")
    
    print("\n📋 ОПЦИИ:")
    print("1. 📥 Установить службу (автоматическая настройка)")
    print("2. 🚀 Запустить службу (если установлена)")
    print("3. ⏸️  Остановить службу (если установлена)")
    print("4. 🗑️  Удалить службу (если установлена)")
    print("5. ℹ️  Показать команды управления")
    print("6. ⏭️  Пропустить и выйти")
    
    while True:
        try:
            choice = input("\nВаш выбор [1-6]: ").strip()
            
            if choice == '1':
                if manager.is_installed():
                    print("\n⚠️ Служба уже установлена")
                    overwrite = input("Переустановить? (y/N): ").strip().lower()
                    if overwrite != 'y':
                        continue
                    manager.uninstall()
                
                if manager.install():
                    print("\n🎉 Служба успешно установлена и запущена!")
                return True
                    
            elif choice == '2':
                if not manager.is_installed():
                    print("\n⚠️ Служба не установлена")
                    print("💡 Сначала установите службу (опция 1)")
                else:
                    if manager.start():
                        print("\n✅ Служба запущена!")
                    return True
                    
            elif choice == '3':
                if not manager.is_installed():
                    print("\n⚠️ Служба не установлена")
                else:
                    if manager.stop():
                        print("\n✅ Служба остановлена!")
                    return True
                    
            elif choice == '4':
                if not manager.is_installed():
                    print("\n⚠️ Служба не установлена")
                else:
                    confirm = input(f"Удалить службу '{manager.service_name}'? (y/N): ").strip().lower()
                    if confirm == 'y':
                        if manager.uninstall():
                            print("\n✅ Служба удалена!")
                        return True
                    
            elif choice == '5':
                print("\n" + "="*60)
                print("📋 КОМАНДЫ ДЛЯ УПРАВЛЕНИЯ СЛУЖБОЙ")
                print("="*60)
                
                if manager.system == "windows":
                    print(f"  Статус:    sc query {manager.service_name}")
                    print(f"  Запуск:    sc start {manager.service_name}")
                    print(f"  Остановка: sc stop {manager.service_name}")
                    print(f"  Удаление:  sc delete {manager.service_name}")
                    print(f"  Через NSSM: nssm remove {manager.service_name} confirm")
                elif manager.system == "linux":
                    print(f"  Статус:    systemctl status {manager.service_name}")
                    print(f"  Запуск:    sudo systemctl start {manager.service_name}")
                    print(f"  Остановка: sudo systemctl stop {manager.service_name}")
                    print(f"  Логи:      journalctl -u {manager.service_name} -f")
                elif manager.system == "darwin":
                    print(f"  Статус:    launchctl list | grep {manager.service_name}")
                    print(f"  Запуск:    sudo launchctl start {manager.service_name}")
                    print(f"  Остановка: sudo launchctl stop {manager.service_name}")
                
                print(f"\n📁 Логи службы находятся в: {manager.starter_path}/logs/")
                print("="*60)
                continue
                    
            elif choice == '6':
                print("\n⏭️ Выход из управления службой")
                return False
            else:
                print("⚠️ Неверный выбор. Введите цифру от 1 до 6")
                
        except KeyboardInterrupt:
            print("\n\n⏹️ Прервано пользователем")
            return False
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return False