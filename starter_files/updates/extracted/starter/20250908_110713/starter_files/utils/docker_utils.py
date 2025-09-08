import subprocess
import re
import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple

class DockerUtils:
    @staticmethod
    def check_installed() -> bool:
        """Проверяет установлен ли Docker и возвращает статус"""
        try:
            result = subprocess.run(
                ['docker', '--version'],
                capture_output=True,
                text=True,
                check=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    @staticmethod
    def check_docker_compose_installed() -> bool:
        """Проверяет установлен ли Docker Compose и возвращает статус"""
        try:
            subprocess.run(
                ['docker-compose', '--version'],
                capture_output=True,
                text=True,
                check=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    @staticmethod
    def check_dockerfiles(docker_dir: str) -> bool:
        """Проверка наличия необходимых Dockerfile"""
        required = [
            os.path.join("dockerfiles", "Dockerfile_other"),
            os.path.join("dockerfiles", "Dockerfile_php")
        ]
        for path in required:
            if not (Path(docker_dir) / path).exists():
                return False
        return True

    @staticmethod
    def replace_env_variables(content: str, env_vars: Dict[str, str]) -> str:
        """Заменяет ${PROJECTNAME} на значение из env_vars"""
        def replace_match(match):
            return env_vars.get("PROJECTNAME", match.group(0))
        
        return re.sub(
            r'\$\{PROJECTNAME\}',
            replace_match,
            content
        )

    @staticmethod
    def process_service_blocks(content: str, enabled_services: List[str], env_vars: Dict[str, str]) -> str:
        """Обрабатывает блоки сервисов, оставляя только разрешенные"""
        pattern = re.compile(
            r'### START (.*?) ###(.*?)### END \1 ###',
            re.DOTALL
        )
        
        def replace_block(match):
            service_name = match.group(1).strip().upper()
            block_content = match.group(2)
            
            if service_name in enabled_services:
                replaced_content = DockerUtils.replace_env_variables(block_content, env_vars)
                return f"### START {service_name} ###{replaced_content}### END {service_name} ###"
            return ''

        return pattern.sub(replace_block, content)

    @staticmethod
    def generate_compose(docker_dir: Path, env_vars: Dict[str, str], pull_from_registry: bool = False) -> bool:
        """Генерирует docker-compose.yml на основе примера"""
        compose_example = Path(docker_dir) / "docker-compose.example"
        compose_output = Path(docker_dir) / "docker-compose.yml"
        
        try:
            content = compose_example.read_text(encoding='utf-8')

            if pull_from_registry:
                content = re.sub(
                    r'\n\s+build:.*?dockerfile:.*?\n',
                    '\n',
                    content,
                    flags=re.DOTALL
                )

            enabled_services = [
                s.strip().upper() 
                for s in env_vars.get("ENABLED_SERVICES", "").split(",") 
                if s.strip()
            ]

            content = DockerUtils.process_service_blocks(content, enabled_services, env_vars)
            content = DockerUtils.replace_env_variables(content, env_vars)

            compose_output.write_text(content, encoding='utf-8')
            return True
        except Exception:
            return False

    @staticmethod
    def check_docker_registry_auth(registry: str) -> bool:
        """Проверяет авторизацию в Docker Registry"""
        try:
            result = subprocess.run(
                ["docker", "login", registry],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                input=b'\n',
                check=False
            )
            return result.returncode == 0
        except Exception:
            return False