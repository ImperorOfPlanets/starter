from starter_files.core.base_module import BaseModule

from typing import List

from starter_files.core.utils.globalVars_utils import get_global

class DockerModule(BaseModule):

    @staticmethod
    def return_commands_install() -> List[str]:
        """Возвращает список команд для установки Docker в macOS"""
        # Для macOS установка Docker обычно через brew или dmg
        # Возвращаем инструкции для ручной установки
        return [
            "echo 'Для установки Docker на macOS:'",
            "echo '1. Скачайте Docker Desktop с https://www.docker.com/products/docker-desktop'",
            "echo '2. Установите Docker Desktop'",
            "echo '3. Запустите Docker Desktop'",
            "echo '4. Проверьте установку: docker --version'"
        ]

    @staticmethod
    def return_commands_start() -> List[str]:
        """Возвращает команды для запуска Docker на macOS"""
        return [
            "echo 'Docker Desktop должен быть запущен через GUI'",
            "echo 'Проверьте статус: docker info'"
        ]

    @staticmethod
    def check_docker_running() -> bool:
        """Проверяет, запущен ли Docker"""
        try:
            import subprocess
            result = subprocess.run(
                ['docker', 'info'],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False