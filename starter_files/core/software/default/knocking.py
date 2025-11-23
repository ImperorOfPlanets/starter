import subprocess
import os
import platform
import logging
import time
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from pathlib import Path
from starter_files.core.utils.globalVars_utils import get_global, set_global
from starter_files.core.utils.loader_utils import get

from starter_files.core.base_module import BaseModule

logger = logging.getLogger('knocking')

class KnockingModule(BaseModule):

    @staticmethod
    def is_knocking_installed() -> bool:
        """Установлен ли порт Port Knocking"""
        try:
            return (
                os.path.exists("/usr/sbin/knockd") or
                os.path.exists("/etc/knockd.conf")
            )
        except Exception:
            return False

    @staticmethod
    def install_knocking(log_file_path: str) -> Dict[str, str]:
        """Устанавливает Port Knocking и записывает логи в указанный файл"""
        result = {'status': 'success', 'message': '', 'logs': []}

        try:
            log_dir = Path(log_file_path).parent
            log_dir.mkdir(parents=True, exist_ok=True)

            with open(log_file_path, 'w') as log_file:
                def log(message):
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    log_entry = f"[{timestamp}] {message}"
                    log_file.write(log_entry + '\n')
                    log_file.flush()
                    result['logs'].append(log_entry)
                    logger.info(log_entry)

                log("Starting Port Knocking installation...")

                commands = get("knocking", "return_commands_install_knocking")

                if commands is None:
                    log("Failed to retrieve installation commands")
                    result['status'] = 'error'
                    result['message'] = "Failed to retrieve installation commands"
                    return result

                for cmd in commands:
                    log(f"Executing: {cmd}")
                    process = subprocess.Popen(
                        cmd,
                        shell=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        bufsize=1,
                        universal_newlines=True
                    )

                    if process.stdout is not None:
                        for line in iter(process.stdout.readline, ''):
                            if line:
                                log(line.strip())

                    return_code = process.wait()
                    if return_code != 0:
                        log(f"Command failed with exit code {return_code}")
                        result['status'] = 'error'
                        result['message'] = f"Command failed: {cmd}"
                        return result

                time.sleep(2)
                if KnockingModule.is_knocking_installed():
                    log("Port Knocking installed successfully!")
                    result['message'] = "Port Knocking installed successfully!"
                else:
                    log("Installation completed but Port Knocking not detected.")
                    result['status'] = 'warning'
                    result['message'] = "Installation completed but Port Knocking not detected."

        except Exception as e:
            error_msg = f"Installation failed: {str(e)}"
            try:
                with open(log_file_path, 'a') as f:
                    f.write(error_msg + '\n')
                    f.write("INSTALL FINISH!\n")
            except:
                logger.exception("Failed to write error to log file")

            result['status'] = 'error'
            result['message'] = error_msg
            logger.exception("Port Knocking installation error")

        return result

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
    def set_globals():
        """Устанавливает глобальные для Port Knocking"""
        knocking_installed = get('knocking',"is_knocking_installed")
        
        # Устанавливаем глобальные переменные
        set_global('knocking_installed', knocking_installed)