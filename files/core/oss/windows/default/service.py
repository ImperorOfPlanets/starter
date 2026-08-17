# files/core/oss/windows/default/service.py
"""
Модуль для работы с сервисами в Windows (через NSSM)
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
    
    @staticmethod
    def check() -> bool:
        return sys.platform == 'win32'
    
    @staticmethod
    def set_globals():
        starter_path = get_global('starter_path')
        if starter_path:
            service_dir = starter_path / "files" / "service"
            service_dir.mkdir(parents=True, exist_ok=True)
            set_global('service_dir', service_dir)
            logger.debug(f"Service directory: {service_dir}")
    
    @staticmethod
    def is_service_installed() -> bool:
        try:
            result = subprocess.run(['sc', 'query', ServiceModule.SERVICE_NAME], capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False
    
    @staticmethod
    def get_service_status() -> Dict[str, Any]:
        status = {'installed': False, 'running': False, 'enabled': False, 'os': 'windows'}
        try:
            result = subprocess.run(['sc', 'query', ServiceModule.SERVICE_NAME], capture_output=True, text=True)
            if result.returncode == 0:
                status['installed'] = True
                if 'RUNNING' in result.stdout:
                    status['running'] = True
                if 'AUTO_START' in result.stdout:
                    status['enabled'] = True
        except Exception as e:
            logger.error(f"Error checking service status: {e}")
        return status
    
    @staticmethod
    def _get_nssm_path() -> Path:
        possible_paths = [
            Path("C:/nssm/nssm.exe"),
            Path("C:/Program Files/nssm/nssm.exe"),
            Path("C:/Program Files (x86)/nssm/nssm.exe"),
        ]
        program_files = os.environ.get('ProgramFiles', 'C:/Program Files')
        possible_paths.append(Path(program_files) / "nssm" / "nssm.exe")
        program_files_x86 = os.environ.get('ProgramFiles(x86)', 'C:/Program Files (x86)')
        possible_paths.append(Path(program_files_x86) / "nssm" / "nssm.exe")
        for p in os.environ.get('PATH', '').split(';'):
            if p:
                possible_paths.append(Path(p) / "nssm.exe")
        for path in possible_paths:
            if path.exists():
                return path
        return None
    
    @staticmethod
    def install_service(log_file_path: str = None) -> Dict[str, Any]:
        result = {'status': 'success', 'message': '', 'logs': []}
        print("\n" + "=" * 60)
        print("🔧 УСТАНОВКА СЕРВИСА STARTER")
        print("=" * 60)
        starter_path = get_global('starter_path')
        venv_path = get_global('venv_path', starter_path / 'venv')
        venv_python = venv_path / "Scripts" / "python.exe"
        script_path = starter_path / "starter.py"
        print(f"   Python: {venv_python}")
        print(f"   Скрипт: {script_path}")
        print(f"   Рабочая директория: {starter_path}")
        nssm_path = ServiceModule._get_nssm_path()
        if not nssm_path:
            print("\n   ❌ NSSM не найден!")
            print("   💡 Скачайте NSSM с https://nssm.cc/download")
            print("   📁 Распакуйте и поместите nssm.exe в C:\\nssm\\ или добавьте в PATH")
            result['status'] = 'error'
            result['message'] = 'NSSM not found'
            return result
        print(f"   ✅ NSSM найден: {nssm_path}")
        if not venv_python.exists():
            print(f"   ❌ Python не найден: {venv_python}")
            result['status'] = 'error'
            result['message'] = 'Python not found in venv'
            return result
        if not script_path.exists():
            print(f"   ❌ starter.py не найден: {script_path}")
            result['status'] = 'error'
            result['message'] = 'starter.py not found'
            return result
        if ServiceModule.is_service_installed():
            print("   ⏸️ Останавливаем существующий сервис...")
            subprocess.run(['sc', 'stop', ServiceModule.SERVICE_NAME], capture=True, check=False)
            time.sleep(2)
            subprocess.run(['sc', 'delete', ServiceModule.SERVICE_NAME], capture=True, check=False)
            time.sleep(1)
        try:
            print("\n   📦 Установка сервиса...")
            cmd = [str(nssm_path), 'install', ServiceModule.SERVICE_NAME, str(venv_python), str(script_path), '--service']
            subprocess.run(cmd, check=True, capture=True)
            print("   ⚙️ Настройка параметров...")
            subprocess.run([str(nssm_path), 'set', ServiceModule.SERVICE_NAME, 'AppDirectory', str(starter_path)], check=True, capture=True)
            subprocess.run([str(nssm_path), 'set', ServiceModule.SERVICE_NAME, 'Start', 'SERVICE_AUTO_START'], check=True, capture=True)
            log_dir = starter_path / "files" / "logs" / "service"
            log_dir.mkdir(parents=True, exist_ok=True)
            subprocess.run([str(nssm_path), 'set', ServiceModule.SERVICE_NAME, 'AppStdout', str(log_dir / "stdout.log")], check=True, capture=True)
            subprocess.run([str(nssm_path), 'set', ServiceModule.SERVICE_NAME, 'AppStderr', str(log_dir / "stderr.log")], check=True, capture=True)
            print("   🚀 Запуск сервиса...")
            subprocess.run(['sc', 'start', ServiceModule.SERVICE_NAME], check=True, capture=True)
            time.sleep(2)
            status = ServiceModule.get_service_status()
            if status['running']:
                print("\n   ✅ Сервис успешно установлен и запущен!")
                result['message'] = "Service installed and started successfully"
            else:
                print("\n   ⚠️ Сервис установлен, но не запущен")
                result['status'] = 'warning'
                result['message'] = "Service installed but not running"
        except subprocess.CalledProcessError as e:
            print(f"\n   ❌ Ошибка установки: {e}")
            result['status'] = 'error'
            result['message'] = str(e)
        except Exception as e:
            print(f"\n   ❌ Ошибка: {e}")
            result['status'] = 'error'
            result['message'] = str(e)
        return result
    
    @staticmethod
    def uninstall_service(log_file_path: str = None) -> Dict[str, Any]:
        result = {'status': 'success', 'message': '', 'logs': []}
        print("\n" + "=" * 60)
        print("🔧 УДАЛЕНИЕ СЕРВИСА STARTER")
        print("=" * 60)
        if not ServiceModule.is_service_installed():
            print("   ℹ️ Сервис не установлен")
            result['message'] = "Service not installed"
            return result
        try:
            print("   ⏸️ Остановка сервиса...")
            subprocess.run(['sc', 'stop', ServiceModule.SERVICE_NAME], capture=True, check=False)
            time.sleep(2)
            print("   🗑️ Удаление сервиса...")
            subprocess.run(['sc', 'delete', ServiceModule.SERVICE_NAME], capture=True, check=True)
            print("\n   ✅ Сервис успешно удален")
            result['message'] = "Service uninstalled successfully"
        except Exception as e:
            print(f"\n   ❌ Ошибка: {e}")
            result['status'] = 'error'
            result['message'] = str(e)
        return result
    
    @staticmethod
    def service_action(data: Dict[str, Any]) -> Dict[str, Any]:
        action = data.get('action')
        if not ServiceModule.is_service_installed():
            return {'status': 'error', 'message': 'Service not installed'}
        try:
            if action == 'start':
                subprocess.run(['sc', 'start', ServiceModule.SERVICE_NAME], check=True, capture=True)
                return {'status': 'success', 'message': 'Service started'}
            elif action == 'stop':
                subprocess.run(['sc', 'stop', ServiceModule.SERVICE_NAME], check=True, capture=True)
                return {'status': 'success', 'message': 'Service stopped'}
            elif action == 'restart':
                subprocess.run(['sc', 'stop', ServiceModule.SERVICE_NAME], capture=True, check=False)
                time.sleep(2)
                subprocess.run(['sc', 'start', ServiceModule.SERVICE_NAME], check=True, capture=True)
                return {'status': 'success', 'message': 'Service restarted'}
            elif action == 'enable':
                subprocess.run(['sc', 'config', ServiceModule.SERVICE_NAME, 'start=', 'auto'], check=True, capture=True)
                return {'status': 'success', 'message': 'Service autostart enabled'}
            elif action == 'disable':
                subprocess.run(['sc', 'config', ServiceModule.SERVICE_NAME, 'start=', 'demand'], check=True, capture=True)
                return {'status': 'success', 'message': 'Service autostart disabled'}
            else:
                return {'status': 'error', 'message': f'Unknown action: {action}'}
        except subprocess.CalledProcessError as e:
            return {'status': 'error', 'message': f'Failed to {action} service: {e}'}
    
    @staticmethod
    def restart_service() -> Dict[str, Any]:
        return ServiceModule.service_action({'action': 'restart'})
    
    @staticmethod
    def diagnose_service() -> Dict[str, Any]:
        result = {'status': 'success', 'problems': []}
        status = ServiceModule.get_service_status()
        result['status_info'] = status
        if not status['installed']:
            result['problems'].append('Service not installed')
            return result
        nssm_path = ServiceModule._get_nssm_path()
        if not nssm_path:
            result['problems'].append('NSSM not found')
        else:
            result['nssm_path'] = str(nssm_path)
        starter_path = get_global('starter_path')
        venv_path = get_global('venv_path', starter_path / 'venv')
        venv_python = venv_path / "Scripts" / "python.exe"
        script_path = starter_path / "starter.py"
        result['paths'] = {
            'starter_path': str(starter_path),
            'venv_python': str(venv_python),
            'python_exists': venv_python.exists(),
            'script_exists': script_path.exists()
        }
        if not result['paths']['python_exists']:
            result['problems'].append('Python executable not found in venv')
        if not result['paths']['script_exists']:
            result['problems'].append('starter.py not found')
        log_dir = starter_path / "files" / "logs" / "service"
        if log_dir.exists():
            stdout_log = log_dir / "stdout.log"
            stderr_log = log_dir / "stderr.log"
            if stdout_log.exists():
                result['stdout_log_size'] = stdout_log.stat().st_size
            if stderr_log.exists():
                result['stderr_log_size'] = stderr_log.stat().st_size
        return result