import subprocess
from typing import Optional
from starter_files.utils.docker_utils import DockerUtils

class DockerService:
    def __init__(self):
        self.docker_utils = DockerUtils()

    def check_environment(self) -> bool:
        """Проверяет готовность Docker окружения"""
        if not self.docker_utils.check_docker_installed():
            return False
        if not self.docker_utils.check_docker_compose_installed():
            return False
        return True

    def validate_compose_file(self, docker_dir: str) -> bool:
        """Проверяет валидность docker-compose файла"""
        try:
            result = subprocess.run(
                ["docker-compose", "config"],
                cwd=docker_dir,
                capture_output=True,
                text=True,
                check=True
            )
            return "valid" in result.stdout.lower()
        except subprocess.CalledProcessError:
            return False