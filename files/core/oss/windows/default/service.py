# files/core/oss/windows/default/service.py
"""
Модуль для работы с сервисами через Task Scheduler (Windows)
Замена systemd — автозапуск, перезапуск при падении, фоновый режим
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
    TASK_NAME = "StarterService"

    @staticmethod
    def _kwargs(**extra):
        """kwargs для subprocess со startupinfo на Windows"""
        kwargs = {'capture_output': True, 'text': True}
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
            service_dir = starter_path / "files" / "service"
            service_dir.mkdir(parents=True, exist_ok=True)
            set_global('service_dir', service_dir)

    @staticmethod
    def is_service_installed() -> bool:
        try:
            result = subprocess.run(
                ['schtasks', '/Query', '/TN', ServiceModule.TASK_NAME],
                **ServiceModule._kwargs()
            )
            return result.returncode == 0
        except:
            return False

    @staticmethod
    def get_service_status() -> Dict[str, Any]:
        status = {'installed': False, 'running': False, 'enabled': False, 'os': 'windows'}
        try:
            result = subprocess.run(
                ['schtasks', '/Query', '/TN', ServiceModule.TASK_NAME, '/FO', 'LIST'],
                **ServiceModule._kwargs()
            )
            if result.returncode == 0:
                status['installed'] = True
                if 'Status: Running' in result.stdout:
                    status['running'] = True
                if 'Scheduled Task Status:' in result.stdout:
                    status['enabled'] = True
        except Exception as e:
            logger.error(f"Error checking service status: {e}")
        return status

    @staticmethod
    def install_service(log_file_path: str = None) -> Dict[str, Any]:
        result = {'status': 'success', 'message': '', 'logs': []}
        starter_path = get_global('starter_path')
        venv_path = get_global('venv_path', starter_path / 'venv')
        venv_python = venv_path / "Scripts" / "python.exe"
        script_path = starter_path / "starter.py"
        task_name = ServiceModule.TASK_NAME
        si = ServiceModule._kwargs().get('startupinfo')

        print("\n" + "=" * 60)
        print("🔧 УСТАНОВКА СЕРВИСА STARTER (Task Scheduler)")
        print("=" * 60)
        print(f"   Python: {venv_python}")
        print(f"   Скрипт: {script_path}")

        if not venv_python.exists():
            result['status'] = 'error'
            result['message'] = f'Python not found: {venv_python}'
            return result

        if not script_path.exists():
            result['status'] = 'error'
            result['message'] = f'starter.py not found: {script_path}'
            return result

        # Удаляем старую задачу
        subprocess.run(['schtasks', '/Delete', '/TN', task_name, '/F'], capture_output=True, startupinfo=si)

        # Создаём XML
        log_dir = starter_path / "files" / "logs" / "service"
        log_dir.mkdir(parents=True, exist_ok=True)

        xml = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Starter Server - AI Server Manager</Description>
  </RegistrationInfo>
  <Triggers>
    <LogonTrigger><Enabled>true</Enabled></LogonTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <RestartOnFailure><Interval>PT1M</Interval><Count>999</Count></RestartOnFailure>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{venv_python}</Command>
      <Arguments>{script_path}</Arguments>
      <WorkingDirectory>{starter_path}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>"""

        xml_path = log_dir / "task.xml"
        xml_path.write_text(xml, encoding='utf-16')

        proc = subprocess.run(
            ['schtasks', '/Create', '/TN', task_name, '/XML', str(xml_path), '/F'],
            **ServiceModule._kwargs()
        )

        if proc.returncode != 0:
            result['status'] = 'error'
            result['message'] = f'Ошибка: {proc.stderr}'
            return result

        # Запускаем
        subprocess.run(['schtasks', '/Run', '/TN', task_name], capture_output=True, startupinfo=si)

        result['message'] = f'Сервис установлен: {task_name} (автозапуск + перезапуск)'
        print(f"\n   ✅ Сервис установлен: {task_name}")
        return result

    @staticmethod
    def uninstall_service(log_file_path: str = None) -> Dict[str, Any]:
        result = {'status': 'success', 'message': '', 'logs': []}
        task_name = ServiceModule.TASK_NAME

        print("\n" + "=" * 60)
        print("🔧 УДАЛЕНИЕ СЕРВИСА STARTER")
        print("=" * 60)

        if not ServiceModule.is_service_installed():
            result['message'] = "Сервис не установлен"
            return result

        subprocess.run(['schtasks', '/End', '/TN', task_name], capture_output=True,
                       startupinfo=ServiceModule._kwargs().get('startupinfo'))
        time.sleep(1)
        subprocess.run(['schtasks', '/Delete', '/TN', task_name, '/F'], capture_output=True,
                       startupinfo=ServiceModule._kwargs().get('startupinfo'))

        result['message'] = 'Сервис удалён'
        print("   ✅ Сервис удалён")
        return result

    @staticmethod
    def service_action(action: str) -> Dict[str, Any]:
        task_name = ServiceModule.TASK_NAME
        si = ServiceModule._kwargs().get('startupinfo')

        if action == 'start':
            subprocess.run(['schtasks', '/Run', '/TN', task_name], capture_output=True, startupinfo=si)
            return {'status': 'success', 'message': 'Сервис запущен'}
        elif action == 'stop':
            subprocess.run(['schtasks', '/End', '/TN', task_name], capture_output=True, startupinfo=si)
            return {'status': 'success', 'message': 'Сервис остановлен'}
        elif action == 'restart':
            subprocess.run(['schtasks', '/End', '/TN', task_name], capture_output=True, startupinfo=si)
            time.sleep(2)
            subprocess.run(['schtasks', '/Run', '/TN', task_name], capture_output=True, startupinfo=si)
            return {'status': 'success', 'message': 'Сервис перезапущен'}
        elif action == 'status':
            return ServiceModule.get_service_status()
        elif action == 'install':
            return ServiceModule.install_service()
        elif action == 'uninstall':
            return ServiceModule.uninstall_service()
        else:
            return {'status': 'error', 'message': f'Неизвестное действие: {action}'}
