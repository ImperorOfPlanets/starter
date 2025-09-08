import subprocess
import os
import shutil
from pathlib import Path
from typing import Optional

from starter_files.utils.docker_utils import DockerUtils
from starter_files.utils.env import validate_env_file
from starter_files.utils.vpn import check_vpn_config
from starter_files.utils.nginx import check_nginx_configs
from starter_files.utils.logger import logger

class DockerManager:
    def __init__(self):
        self.docker_utils = DockerUtils()

    def log_command(self, command: list, description: Optional[str] = None) -> None:
        """Логирует выполняемую команду"""
        cmd_str = ' '.join(command)
        if description:
            print(f"\n🔹 {description}:")
        print(f"Выполняю команду: {cmd_str}")

    def push_images(self) -> bool:
        """Собирает и отправляет образы в реестр"""
        registry = "gitflic.myidon.site:80"
        images = [
            ("server-other", "Dockerfile_other"),
            ("server-php", "Dockerfile_php"),
        ]
        version = "0.1"

        try:
            for image_name, dockerfile in images:
                image_tag = f"{registry}/{image_name}:{version}"
                build_cmd = [
                    "docker", "build",
                    "-t", image_tag,
                    "-f", f"./docker/dockerfiles/{dockerfile}",
                    "./docker/dockerfiles"
                ]
                self.log_command(build_cmd, "Сборка Docker-образа")
                subprocess.run(build_cmd, check=True)

                push_cmd = ["docker", "push", image_tag]
                self.log_command(push_cmd, "Отправка образа в реестр")
                subprocess.run(push_cmd, check=True)
                
                print(f"✅ Образ {image_tag} успешно отправлен")
            return True
        except subprocess.CalledProcessError as e:
            print(f"🚨 Ошибка при работе с образами: {str(e)}")
            return False

    def check_docker_login(self, registry: str) -> bool:
        """Проверяет и выполняет вход в Docker Registry"""
        if not self.docker_utils.check_docker_registry_auth(registry):
            print(f"🔒 Требуется вход в реестр {registry}")
            login_cmd = ["docker", "login", registry]
            self.log_command(login_cmd, "Аутентификация в Docker-реестре")
            try:
                subprocess.run(login_cmd, check=True)
                return True
            except Exception:
                return False
        return True

    def install_docker(self) -> bool:
        """Устанавливает Docker для Ubuntu/Debian"""
        print("\n[Установка Docker]")
        try:
            if os.geteuid() != 0:
                print("Требуются права администратора. Используйте sudo.")
                return False

            subprocess.run(['apt-get', 'update'], check=True)
            subprocess.run(['apt-get', 'install', '-y', 'docker.io'], check=True)
            subprocess.run(['systemctl', 'start', 'docker'], check=True)
            subprocess.run(['systemctl', 'enable', 'docker'], check=True)
            
            print("[Docker] Успешно установлен")
            return True
        except subprocess.CalledProcessError as e:
            print(f"[Ошибка] Не удалось установить Docker: {e}")
            return False

    def install_docker_compose(self) -> bool:
        """Устанавливает Docker Compose"""
        print("\n[Установка Docker Compose]")
        try:
            subprocess.run(
                'curl -L "https://github.com/docker/compose/releases/download/v2.35.1/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose',
                shell=True,
                check=True
            )
            subprocess.run(['chmod', '+x', '/usr/local/bin/docker-compose'], check=True)
            print("[Docker Compose] Успешно установлен")
            return True
        except subprocess.CalledProcessError as e:
            print(f"[Ошибка] Не удалось установить Docker Compose: {e}")
            return False

    def run_docker_compose(self, push_to_registry: bool = False, pull_from_registry: bool = False) -> bool:
        """Запускает docker-compose с настройками"""
        docker_dir = 'docker'
        env_path = os.path.join(docker_dir, '.env')
        env_example_path = os.path.join(docker_dir, '.env.example')
        
        # Проверка и создание .env
        if not os.path.isfile(env_path):
            if os.path.isfile(env_example_path):
                shutil.copyfile(env_example_path, env_path)
                print("\n[Внимание] .env создан из примера. Заполните его!")
                return False
            raise Exception("Отсутствуют .env и .env.example!")

        # Валидация .env
        empty_vars = validate_env_file(env_path)
        if empty_vars:
            raise Exception(f"Пустые переменные в .env: {', '.join(empty_vars)}")

        # Чтение переменных окружения
        env_vars = {}
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    key, value = line.split("=", 1)
                    env_vars[key.strip()] = value.strip().strip('"')

        # Дополнительные проверки
        check_vpn_config(env_vars, docker_dir)
        check_nginx_configs(env_vars, docker_dir)
        
        if not self.docker_utils.check_dockerfiles(docker_dir):
            raise Exception("Не найдены необходимые Dockerfile")

        if push_to_registry:
            print("\n[Этап] Сборка и отправка образов в реестр...")
            if not self.check_docker_login(registry="gitflic.myidon.site:80"):
                return False
            if not self.push_images():
                return False

        # Генерация docker-compose.yml
        print("\n[Этап] Генерация docker-compose.yml...")
        if not self.docker_utils.generate_compose(Path(docker_dir), env_vars, pull_from_registry):
            raise Exception("Ошибка генерации docker-compose.yml")

        try:
            compose_path = os.path.join(docker_dir, 'docker-compose.yml')

            if pull_from_registry:
                print("\n[Этап] Обновление образов из реестра...")
                subprocess.run(
                    ["docker-compose", "pull"],
                    cwd=docker_dir,
                    check=True
                )

            print(f"\n[Запуск] Используется compose-файл: {compose_path}")
            
            log_dir = os.path.abspath(os.path.join(docker_dir, 'logs'))
            os.makedirs(log_dir, exist_ok=True)
            
            with open(os.path.join(log_dir, 'docker-compose.log'), 'a') as log_file:
                process = subprocess.Popen(
                    ["docker-compose", "up", "-d", "--build"],
                    cwd=docker_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True
                )
                
                for line in process.stdout:
                    print(line, end='')
                    log_file.write(line)
                    
                process.wait()
                
                if process.returncode != 0:
                    raise subprocess.CalledProcessError(
                        process.returncode, 
                        process.args
                    )
                    
            print("[Успех] Контейнеры запущены")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"[Ошибка] Docker Compose exited with code {e.returncode}")
            print(f"[Ошибка] Причина: {e.stderr if e.stderr else 'См. логи'}")
            return False
        except Exception as e:
            print(f"[Критическая ошибка] {str(e)}")
            return False