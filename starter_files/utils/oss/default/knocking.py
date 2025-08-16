import logging
import subprocess
import os
import platform
import socket
import subprocess
from typing import List, Dict, Optional, Tuple

from starter_files.utils.oss.base_module import BaseModule

class KnockingModule(BaseModule):
    @staticmethod
    def is_knocking_installed() -> bool:
        """Check if port knocking is installed on the system"""
        try:
            # Check for common port knocking implementations
            if platform.system() == "Linux":
                return (
                    os.path.exists("/usr/sbin/knockd") or 
                    os.path.exists("/etc/knockd.conf")
                )
            elif platform.system() == "Windows":
                # Windows implementation checks would go here
                return False
            return False
        except Exception:
            return False

    @staticmethod
    def get_knocking_config() -> Optional[Dict]:
        """Get current knocking configuration"""
        try:
            if platform.system() == "Linux":
                # Parse knockd config file if exists
                if os.path.exists("/etc/knockd.conf"):
                    config = {}
                    with open("/etc/knockd.conf") as f:
                        for line in f:
                            if "sequence" in line:
                                ports = line.split("=")[1].strip().split(",")
                                config["ports"] = [int(p) for p in ports]
                            elif "seq_timeout" in line:
                                config["timeout"] = int(line.split("=")[1].strip())
                    return config
            return None
        except Exception:
            return None

    @staticmethod
    def is_knocking_active() -> bool:
        """Check if knocking service is running"""
        try:
            if platform.system() == "Linux":
                result = subprocess.run(
                    ["systemctl", "is-active", "knockd"],
                    capture_output=True,
                    text=True
                )
                return result.stdout.strip() == "active"
            return False
        except Exception:
            return False

    @staticmethod
    def start_knocking_service() -> bool:
        """Start the knocking service"""
        try:
            if platform.system() == "Linux":
                subprocess.run(["systemctl", "start", "knockd"], check=True)
                return True
            return False
        except Exception:
            return False

    @staticmethod
    def stop_knocking_service() -> bool:
        """Stop the knocking service"""
        try:
            if platform.system() == "Linux":
                subprocess.run(["systemctl", "stop", "knockd"], check=True)
                return True
            return False
        except Exception:
            return False

    @staticmethod
    def update_knocking_config(ports: List[int], timeout: int) -> bool:
        """Update knocking configuration"""
        try:
            if platform.system() == "Linux":
                config = f"""
    [options]
        logfile = /var/log/knockd.log

    [openSSH]
        sequence = {",".join(map(str, ports))}
        seq_timeout = {timeout}
        command = /sbin/iptables -A INPUT -s %IP% -p tcp --dport 22 -j ACCEPT
        tcpflags = syn

    [closeSSH]
        sequence = {",".join(map(str, reversed(ports)))}
        seq_timeout = {timeout}
        command = /sbin/iptables -D INPUT -s %IP% -p tcp --dport 22 -j ACCEPT
        tcpflags = syn
                """
                with open("/etc/knockd.conf", "w") as f:
                    f.write(config)
                subprocess.run(["systemctl", "restart", "knockd"], check=True)
                return True
            return False
        except Exception:
            return False

    @staticmethod
    def install_knocking() -> Tuple[bool, str]:
        """Install port knocking for the current OS"""
        try:
            if platform.system() == "Linux":
                # Для Debian/Ubuntu
                if os.path.exists("/etc/debian_version"):
                    subprocess.run(
                        ["apt-get", "update"],
                        check=True
                    )
                    subprocess.run(
                        ["apt-get", "install", "-y", "knockd"],
                        check=True
                    )
                    return True, "Knockd successfully installed"
                
                # Для CentOS/RHEL
                elif os.path.exists("/etc/redhat-release"):
                    subprocess.run(
                        ["yum", "install", "-y", "epel-release"],
                        check=True
                    )
                    subprocess.run(
                        ["yum", "install", "-y", "knock-server"],
                        check=True
                    )
                    return True, "Knock-server successfully installed"
                
                # Для других дистрибутивов
                else:
                    return False, "Unsupported Linux distribution"

            elif platform.system() == "Windows":
                # Установка для Windows (используем Chocolatey или прямой download)
                try:
                    # Проверяем наличие Chocolatey
                    subprocess.run(
                        ["choco", "--version"],
                        check=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                    
                    # Устанавливаем knockd через Chocolatey
                    subprocess.run(
                        ["choco", "install", "-y", "knockd"],
                        check=True
                    )
                    return True, "Knockd installed via Chocolatey"
                    
                except:
                    # Альтернативный метод установки для Windows
                    return False, "Windows installation requires manual steps"
            
            else:
                return False, f"Unsupported OS: {platform.system()}"
        
        except subprocess.CalledProcessError as e:
            return False, f"Installation failed: {str(e)}"
        except Exception as e:
            return False, f"Error during installation: {str(e)}"

    @staticmethod
    def _install_knocking_windows() -> Tuple[bool, str]:
        """Alternative Windows installation method"""
        try:
            # 1. Проверяем наличие Powerknock
            # 2. Если нет - скачиваем и устанавливаем
            # 3. Настраиваем службу
            
            # Это пример - нужно адаптировать под реальную реализацию
            download_url = "https://example.com/powerknock/latest.zip"
            install_path = os.path.join(os.environ["ProgramFiles"], "Powerknock")
            
            # Создаем директорию
            os.makedirs(install_path, exist_ok=True)
            
            # Скачиваем (можно использовать urllib или requests)
            # ... код для скачивания и распаковки ...
            
            # Добавляем в PATH
            subprocess.run(
                f'setx PATH "%PATH%;{install_path}"',
                shell=True,
                check=True
            )
            
            return True, "Powerknock installed successfully"
        except Exception as e:
            return False, str(e)