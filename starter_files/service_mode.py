import os
import sys
import platform
import subprocess
import shutil

from pathlib import Path
from typing import Tuple, Optional
import getpass

from starter_files.core.utils.log_utils import logger

class ServiceManager:
    def __init__(self, script_path: str, service_name: str = "starter-service"):
        self.script_path = Path(script_path).absolute()
        self.service_name = service_name
        self.system = platform.system()
        self.username = getpass.getuser()
        
        # Определяем команду для запуска скрипта фывы
        self.exec_cmd = f'"{sys.executable}" "{self.script_path}"'
        
    def is_installed(self) -> bool:
        """Проверяет, установлена ли служба"""
        if self.system == "Windows":
            return self._check_windows_service()
        elif self.system in ["Linux", "Darwin"]:
            return self._check_unix_service()
        return False
    
    def install(self) -> bool:
        """Устанавливает службу"""
        print(f"\n{'='*40}")
        print(f"Установка службы {self.service_name} для {self.system}")
        
        if self.system == "Windows":
            return self._install_windows_service()
        elif self.system in ["Linux", "Darwin"]:
            return self._install_unix_service()
        return False
    
    def uninstall(self) -> bool:
        """Удаляет службу"""
        print(f"\n{'='*40}")
        print(f"Удаление службы {self.service_name} ({self.system})")
        
        if not self.is_installed():
            print("⚠️ Служба не установлена")
            return False
            
        if self.system == "Windows":
            return self._uninstall_windows_service()
        elif self.system in ["Linux", "Darwin"]:
            return self._uninstall_unix_service()
        return False
    
    def _check_windows_service(self) -> bool:
        """Проверяет наличие службы в Windows (более надежная версия)"""
        try:
            # Способ 1: через sc query
            result = subprocess.run(
                ['sc', 'query', self.service_name],
                capture_output=True,
                text=True,
                check=False
            )
            if "RUNNING" in result.stdout or "STOPPED" in result.stdout:
                return True
            
            # Способ 2: через PowerShell
            ps_cmd = f"Get-Service -Name {self.service_name} -ErrorAction SilentlyContinue"
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
        """Устанавливает службу в Windows с помощью NSSM"""
        try:
            nssm_path = self._get_nssm_path()
            if not nssm_path:
                if not self._install_nssm():
                    return False
                nssm_path = self._get_nssm_path()

            service_name = self.service_name
            working_dir = str(self.script_path.parent)
            log_file = str(Path(working_dir) / 'service.log')

            # Создаем UTF-8 файл с BOM маркером
            with open(log_file, 'wb') as f:
                f.write(b'\xef\xbb\xbf')  # UTF-8 BOM
                f.write(f"Service log started at {datetime.now()}\n".encode('utf-8'))

            # Установка службы с перенаправлением вывода
            subprocess.run(
                [nssm_path, 'install', service_name, sys.executable, str(self.script_path), '--service-run'],
                check=True
            )

            # Настройка параметров
            subprocess.run([nssm_path, 'set', service_name, 'AppDirectory', working_dir], check=True)
            subprocess.run([nssm_path, 'set', service_name, 'AppStdout', log_file], check=True)
            subprocess.run([nssm_path, 'set', service_name, 'AppStderr', log_file], check=True)
            subprocess.run([nssm_path, 'set', service_name, 'Start', 'SERVICE_AUTO_START'], check=True)

            # Альтернативный способ установки кодировки - через переменную окружения
            subprocess.run(
                [nssm_path, 'set', service_name, 'AppEnvironmentExtra', 'PYTHONIOENCODING=utf-8'],
                check=True
            )

            print(f"✅ Служба {service_name} успешно установлена")
            print(f"Логи будут записываться в: {log_file} (UTF-8)")
            return True

        except subprocess.CalledProcessError as e:
            print(f"❌ Ошибка установки службы: {str(e)}")
            return False
    
    def _get_nssm_path(self) -> Optional[Path]:
        """Ищет NSSM в системе"""
        paths = [
            Path("C:\\nssm\\nssm.exe"),
            Path("C:\\Program Files\\nssm\\nssm.exe"),
            Path("C:\\Program Files (x86)\\nssm\\nssm.exe"),
            Path(os.environ.get('ProgramFiles', '')) / 'nssm' / 'nssm.exe',
            Path(os.environ.get('ProgramFiles(x86)', '')) / 'nssm' / 'nssm.exe'
        ]
        
        for path in paths:
            if path.exists():
                return path
        return None
    
    def _install_nssm(self) -> bool:
        """Устанавливает NSSM (Non-Sucking Service Manager)"""
        try:
            temp_dir = Path(os.environ['TEMP'])
            nssm_url = "https://nssm.cc/release/nssm-2.24.zip"
            zip_path = temp_dir / "nssm.zip"
            
            # Скачиваем NSSM
            print("Скачивание NSSM...")
            subprocess.run(
                ['curl', '-L', nssm_url, '-o', str(zip_path)],
                check=True
            )
            
            # Распаковываем в поддиректорию
            extract_dir = temp_dir / "nssm_extracted"
            extract_dir.mkdir(exist_ok=True)
            
            print("Распаковка архива...")
            import zipfile
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            # Ищем nssm.exe в распакованных файлах
            nssm_exe = None
            for root, _, files in os.walk(extract_dir):
                if "nssm.exe" in files:
                    nssm_exe = Path(root) / "nssm.exe"
                    break
            
            if not nssm_exe or not nssm_exe.exists():
                raise FileNotFoundError("nssm.exe не найден в распакованном архиве")
            
            # Копируем в Program Files\nssm
            nssm_dir = Path(os.environ['ProgramFiles']) / 'nssm'
            nssm_dir.mkdir(exist_ok=True)
            
            dest_path = nssm_dir / "nssm.exe"
            shutil.copy(nssm_exe, dest_path)
            
            # Добавляем в PATH
            os.environ['PATH'] += os.pathsep + str(nssm_dir)
            
            # Удаляем временные файлы
            print("Очистка временных файлов...")
            zip_path.unlink(missing_ok=True)
            shutil.rmtree(extract_dir, ignore_errors=True)
            
            print("✅ NSSM успешно установлен!")
            return True
        except Exception as e:
            print(f"❌ Ошибка установки NSSM: {str(e)}")
            return False
    
    def _check_unix_service(self) -> bool:
        """Проверяет наличие службы в Unix-системах"""
        if self.system == "Linux":
            # Проверка systemd
            systemd_dir = Path("/etc/systemd/system")
            service_file = systemd_dir / f"{self.service_name}.service"
            
            if service_file.exists():
                return True
            
            # Проверка init.d
            initd_file = Path(f"/etc/init.d/{self.service_name}")
            if initd_file.exists():
                return True
        
        # Общая проверка для всех Unix-систем
        try:
            subprocess.run(
                ['service', self.service_name, 'status'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True
            )
            return True
        except subprocess.CalledProcessError:
            return False
    
    def _install_unix_service(self) -> bool:
        """Устанавливает службу в Unix-системах"""
        try:
            if self.system == "Linux":
                # Предпочтительный способ - systemd
                systemd_dir = Path("/etc/systemd/system")
                systemd_dir.mkdir(parents=True, exist_ok=True)
                
                service_content = f"""[Unit]
Description={self.service_name}
After=network.target

[Service]
Type=simple
User={self.username}
ExecStart={self.exec_cmd}
WorkingDirectory={self.script_path.parent}
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
"""
                service_file = systemd_dir / f"{self.service_name}.service"
                with open(service_file, 'w') as f:
                    f.write(service_content)
                
                # Обновляем systemd и включаем службу
                subprocess.run(['systemctl', 'daemon-reload'], check=True)
                subprocess.run(['systemctl', 'enable', self.service_name], check=True)
                
                print("✅ Служба установлена как systemd unit")
                return True
            
            # Для других Unix-систем (включая macOS)
            initd_content = f"""#!/bin/sh
### BEGIN INIT INFO
# Provides:          {self.service_name}
# Required-Start:    $remote_fs $syslog
# Required-Stop:     $remote_fs $syslog
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: {self.service_name}
# Description:       {self.service_name}
### END INIT INFO

case "$1" in
    start)
        {self.exec_cmd} &
        ;;
    stop)
        pkill -f "{self.script_path}"
        ;;
    restart)
        $0 stop
        $0 start
        ;;
    *)
        echo "Usage: $0 {{start|stop|restart}}"
        exit 1
        ;;
esac

exit 0
"""
            initd_file = Path(f"/etc/init.d/{self.service_name}")
            with open(initd_file, 'w') as f:
                f.write(initd_content)
            
            # Даем права на выполнение
            initd_file.chmod(0o755)
            
            # Добавляем в автозагрузку
            if self.system == "Linux":
                subprocess.run(['update-rc.d', self.service_name, 'defaults'], check=True)
            elif self.system == "Darwin":
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
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>WorkingDirectory</key>
    <string>{self.script_path.parent}</string>
</dict>
</plist>
"""
                plist_file = Path(f"/Library/LaunchDaemons/{self.service_name}.plist")
                with open(plist_file, 'w') as f:
                    f.write(plist_content)
                
                subprocess.run(['launchctl', 'load', str(plist_file)], check=True)
            
            print("✅ Служба установлена")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка установки службы: {str(e)}")
            return False
    
    def _uninstall_unix_service(self) -> bool:
        """Удаляет службу в Unix-системах"""
        try:
            if self.system == "Linux":
                # Удаляем systemd unit
                systemd_file = Path(f"/etc/systemd/system/{self.service_name}.service")
                if systemd_file.exists():
                    subprocess.run(['systemctl', 'stop', self.service_name], check=False)
                    subprocess.run(['systemctl', 'disable', self.service_name], check=True)
                    systemd_file.unlink()
                    subprocess.run(['systemctl', 'daemon-reload'], check=True)
                    print("✅ Systemd unit удален")
                
                # Удаляем init.d скрипт
                initd_file = Path(f"/etc/init.d/{self.service_name}")
                if initd_file.exists():
                    subprocess.run(['service', self.service_name, 'stop'], check=False)
                    subprocess.run(['update-rc.d', '-f', self.service_name, 'remove'], check=True)
                    initd_file.unlink()
                    print("✅ Init.d скрипт удален")
            
            elif self.system == "Darwin":
                plist_file = Path(f"/Library/LaunchDaemons/{self.service_name}.plist")
                if plist_file.exists():
                    subprocess.run(['launchctl', 'unload', str(plist_file)], check=True)
                    plist_file.unlink()
                    print("✅ LaunchDaemon удален")
            
            else:
                initd_file = Path(f"/etc/init.d/{self.service_name}")
                if initd_file.exists():
                    subprocess.run(['service', self.service_name, 'stop'], check=False)
                    initd_file.unlink()
                    print("✅ Init скрипт удален")
            
            return True
        except Exception as e:
            print(f"❌ Ошибка удаления службы: {str(e)}")
            return False

    def _uninstall_windows_service(self) -> bool:
        """Удаляет службу Windows с помощью NSSM"""
        try:
            # 1. Получаем путь к NSSM
            nssm_path = self._get_nssm_path()
            if not nssm_path:
                print("❌ NSSM не найден, удаление невозможно")
                return False

            # 2. Останавливаем службу
            try:
                subprocess.run(
                    ['sc', 'stop', self.service_name],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                print("✅ Служба остановлена")
            except subprocess.CalledProcessError:
                pass  # Служба уже остановлена или не существует

            # 3. Удаляем службу через NSSM
            subprocess.run(
                [nssm_path, 'remove', self.service_name, 'confirm'],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            # 4. Дополнительно удаляем через sc (на случай если NSSM не сработал)
            try:
                subprocess.run(
                    ['sc', 'delete', self.service_name],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            except subprocess.CalledProcessError:
                pass

            print(f"✅ Служба {self.service_name} успешно удалена")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка удаления службы: {str(e)}")
            return False

def manage_service(script_path: str):
    """Основная функция управления службой"""
    service_name = "starter-service"
    manager = ServiceManager(script_path, service_name)
    
    print("\n" + "="*50)
    print("⚙️ Управление службой".center(50))
    print("="*50)
    print(f"\nСкрипт: {script_path}")
    print(f"ОС: {platform.system()}")
    print(f"Имя службы: {service_name}")
    
    if manager.is_installed():
        print("Текущий статус: ✅ Служба установлена")
    else:
        print("Текущий статус: ❌ Служба не установлена")

    print("\nОпции:")
    print("1. Установить службу")
    print("2. Удалить службу (если установлена)")
    print("3. Пропустить")
    
    while True:
        choice = input("\nВаш выбор [1-3]: ").strip()
        
        if choice == '1':
            if manager.is_installed():
                print("\n⚠️ Служба уже установлена")
            else:
                if manager.install():
                    print("\n✅ Служба успешно установлена!")
                    # Запускаем службу после установки
                    try:
                        if platform.system() == "Windows":
                            subprocess.run(['sc', 'start', service_name], check=True)
                        else:
                            subprocess.run(['service', service_name, 'start'], check=True)
                        print("✅ Служба запущена")
                    except Exception as e:
                        print(f"⚠️ Не удалось запустить службу: {str(e)}")
                    return True
        elif choice == '2':
            if not manager.is_installed():
                print("\n⚠️ Служба не установлена")
            elif manager.uninstall():
                print("\n✅ Служба успешно удалена!")
                return True
        elif choice == '3':
            print("\n⏭ Пропускаем управление службой")
            return False
        else:
            print("⚠️ Неверный выбор, попробуйте снова")