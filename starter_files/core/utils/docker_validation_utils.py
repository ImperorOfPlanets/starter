import os
import re
import subprocess
import json
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from starter_files.core.utils.globalVars_utils import get_global
from starter_files.core.utils.log_utils import LogManager

try:
    import yaml  # type: ignore
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    yaml = None

# Логгер будет инициализирован позже, при необходимости
logger = None

class DockerConfigValidator:
    """Валидатор конфигурации Docker"""

    @staticmethod
    def validate_docker_compose_file(file_path: Path) -> Tuple[bool, List[str]]:
        """
        Валидирует docker-compose файл
        Возвращает: (is_valid, errors_list)
        """
        errors = []

        if not file_path.exists():
            errors.append(f"Файл docker-compose не найден: {file_path}")
            return False, errors

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Проверяем базовый формат YAML
            if not YAML_AVAILABLE or yaml is None:
                errors.append("Библиотека PyYAML не установлена, пропускаю валидацию YAML")
                return True, errors

            try:
                compose_data = yaml.safe_load(content)
            except yaml.YAMLError as e:
                errors.append(f"Ошибка парсинга YAML: {str(e)}")
                return False, errors

            if not isinstance(compose_data, dict):
                errors.append("Корневой элемент должен быть словарем")
                return False, errors

            # Проверяем версию
            version = compose_data.get('version')
            if version:
                if not isinstance(version, (str, int, float)):
                    errors.append(f"Некорректная версия: {version}")
                else:
                    # Проверяем поддерживаемые версии
                    supported_versions = ['2', '2.0', '2.1', '2.2', '2.3', '2.4', '3', '3.0', '3.1', '3.2', '3.3', '3.4', '3.5', '3.6', '3.7', '3.8', '3.9']
                    if str(version) not in supported_versions:
                        errors.append(f"Неподдерживаемая версия docker-compose: {version}")

            # Проверяем секцию services
            services = compose_data.get('services', {})
            if not services:
                errors.append("Отсутствует секция 'services' или она пустая")
            elif not isinstance(services, dict):
                errors.append("Секция 'services' должна быть словарем")
            else:
                # Валидируем каждый сервис
                for service_name, service_config in services.items():
                    service_errors = DockerConfigValidator._validate_service(service_name, service_config)
                    errors.extend(service_errors)

            # Проверяем секцию volumes
            volumes = compose_data.get('volumes', {})
            if volumes and not isinstance(volumes, dict):
                errors.append("Секция 'volumes' должна быть словарем")

            # Проверяем секцию networks
            networks = compose_data.get('networks', {})
            if networks and not isinstance(networks, dict):
                errors.append("Секция 'networks' должна быть словарем")

            return len(errors) == 0, errors

        except Exception as e:
            errors.append(f"Неожиданная ошибка при валидации: {str(e)}")
            return False, errors

    @staticmethod
    def _validate_service(service_name: str, service_config: Dict) -> List[str]:
        """Валидирует конфигурацию отдельного сервиса"""
        errors = []

        if not isinstance(service_config, dict):
            errors.append(f"Сервис '{service_name}': конфигурация должна быть словарем")
            return errors

        # Проверяем наличие образа или build
        has_image = 'image' in service_config
        has_build = 'build' in service_config

        if not has_image and not has_build:
            errors.append(f"Сервис '{service_name}': должен быть указан 'image' или 'build'")

        if has_image and has_build:
            errors.append(f"Сервис '{service_name}': нельзя одновременно указывать 'image' и 'build'")

        # Валидируем image
        if has_image:
            image = service_config['image']
            if not isinstance(image, str):
                errors.append(f"Сервис '{service_name}': 'image' должен быть строкой")
            elif not image.strip():
                errors.append(f"Сервис '{service_name}': 'image' не может быть пустым")
            else:
                # Проверяем формат образа
                if ':' not in image and '@' not in image:
                    # Образ без тега - допустимо
                    pass
                elif not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9._/-]*(:[a-zA-Z0-9._-]+)?(@sha256:[a-f0-9]+)?$', image):
                    errors.append(f"Сервис '{service_name}': некорректный формат 'image': {image}")

        # Валидируем build
        if has_build:
            build = service_config['build']
            if isinstance(build, str):
                # Проверяем, что путь существует
                build_path = Path(build)
                if not build_path.exists():
                    errors.append(f"Сервис '{service_name}': путь сборки не существует: {build}")
            elif isinstance(build, dict):
                context = build.get('context')
                if context:
                    context_path = Path(context)
                    if not context_path.exists():
                        errors.append(f"Сервис '{service_name}': контекст сборки не существует: {context}")
            else:
                errors.append(f"Сервис '{service_name}': 'build' должен быть строкой или словарем")

        # Валидируем ports
        ports = service_config.get('ports', [])
        if ports:
            if not isinstance(ports, list):
                errors.append(f"Сервис '{service_name}': 'ports' должен быть списком")
            else:
                for port in ports:
                    if not isinstance(port, str):
                        errors.append(f"Сервис '{service_name}': порт должен быть строкой: {port}")
                    else:
                        # Проверяем формат host:container
                        if ':' not in port:
                            errors.append(f"Сервис '{service_name}': некорректный формат порта: {port}")

        # Валидируем volumes
        volumes = service_config.get('volumes', [])
        if volumes:
            if not isinstance(volumes, list):
                errors.append(f"Сервис '{service_name}': 'volumes' должен быть списком")
            else:
                for volume in volumes:
                    if not isinstance(volume, str):
                        errors.append(f"Сервис '{service_name}': volume должен быть строкой: {volume}")

        # Валидируем environment
        environment = service_config.get('environment', [])
        if environment:
            if not isinstance(environment, (list, dict)):
                errors.append(f"Сервис '{service_name}': 'environment' должен быть списком или словарем")

        # Валидируем depends_on
        depends_on = service_config.get('depends_on', [])
        if depends_on:
            if isinstance(depends_on, list):
                for dep in depends_on:
                    if not isinstance(dep, str):
                        errors.append(f"Сервис '{service_name}': зависимость должна быть строкой: {dep}")
            elif isinstance(depends_on, dict):
                for dep in depends_on.keys():
                    if not isinstance(dep, str):
                        errors.append(f"Сервис '{service_name}': имя зависимости должно быть строкой: {dep}")
            else:
                errors.append(f"Сервис '{service_name}': 'depends_on' должен быть списком или словарем")

        return errors

    @staticmethod
    def validate_dockerfile(file_path: Path) -> Tuple[bool, List[str]]:
        """
        Валидирует Dockerfile
        Возвращает: (is_valid, errors_list)
        """
        errors = []

        if not file_path.exists():
            errors.append(f"Dockerfile не найден: {file_path}")
            return False, errors

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # Проверяем базовые инструкции
            has_from = False
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                # Разбираем инструкцию
                parts = line.split(None, 1)
                if not parts:
                    continue

                instruction = parts[0].upper()

                # Проверяем FROM
                if instruction == 'FROM':
                    has_from = True
                    if len(parts) < 2:
                        errors.append(f"Строка {line_num}: FROM требует аргумент")
                    else:
                        image = parts[1]
                        # Базовая проверка формата образа
                        if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9._/-]*(:[a-zA-Z0-9._-]+)?$', image.split()[0]):
                            errors.append(f"Строка {line_num}: некорректный формат образа в FROM: {image}")

                # Проверяем другие инструкции
                elif instruction in ['RUN', 'CMD', 'ENTRYPOINT', 'COPY', 'ADD']:
                    if len(parts) < 2:
                        errors.append(f"Строка {line_num}: {instruction} требует аргумент")

                elif instruction in ['WORKDIR', 'ENV', 'ARG', 'LABEL']:
                    if len(parts) < 2:
                        errors.append(f"Строка {line_num}: {instruction} требует аргумент")

                elif instruction in ['EXPOSE']:
                    if len(parts) < 2:
                        errors.append(f"Строка {line_num}: EXPOSE требует порт")
                    else:
                        ports = parts[1].split()
                        for port in ports:
                            if not port.isdigit():
                                errors.append(f"Строка {line_num}: EXPOSE требует числовой порт: {port}")

            if not has_from:
                errors.append("Dockerfile должен содержать инструкцию FROM")

            return len(errors) == 0, errors

        except Exception as e:
            errors.append(f"Ошибка при чтении Dockerfile: {str(e)}")
            return False, errors

    @staticmethod
    def validate_docker_setup() -> Tuple[bool, List[str]]:
        """
        Комплексная валидация настройки Docker
        Возвращает: (is_valid, errors_list)
        """
        errors = []

        # Проверяем наличие Docker
        try:
            result = subprocess.run(['docker', '--version'], capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                errors.append("Docker не установлен или не работает")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            errors.append("Docker не найден в PATH")

        # Проверяем наличие docker-compose
        try:
            result = subprocess.run(['docker-compose', '--version'], capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                errors.append("docker-compose не установлен или не работает")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            errors.append("docker-compose не найден в PATH")

        # Ищем и валидируем docker-compose файлы
        script_path = Path(get_global('script_path'))
        docker_dir = script_path / 'docker'

        if docker_dir.exists():
            compose_files = list(docker_dir.glob('docker-compose*.yml')) + list(docker_dir.glob('docker-compose*.yaml'))

            if not compose_files:
                errors.append("Не найдены файлы docker-compose.yml в директории docker")
            else:
                for compose_file in compose_files:
                    if logger:
                        logger.info(f"Валидирую {compose_file.name}")
                    is_valid, file_errors = DockerConfigValidator.validate_docker_compose_file(compose_file)
                    if not is_valid:
                        errors.extend([f"{compose_file.name}: {err}" for err in file_errors])

            # Ищем и валидируем Dockerfiles
            dockerfiles = []
            for root, dirs, files in os.walk(docker_dir):
                for file in files:
                    if file.lower() == 'dockerfile':
                        dockerfiles.append(Path(root) / file)

            for dockerfile in dockerfiles:
                if logger:
                    logger.info(f"Валидирую {dockerfile}")
                is_valid, file_errors = DockerConfigValidator.validate_dockerfile(dockerfile)
                if not is_valid:
                    errors.extend([f"{dockerfile.name}: {err}" for err in file_errors])
        else:
            errors.append("Директория docker не найдена")

        return len(errors) == 0, errors

    @staticmethod
    def get_validation_report() -> Dict[str, Any]:
        """Возвращает полный отчет о валидации Docker конфигурации"""
        is_valid, errors = DockerConfigValidator.validate_docker_setup()

        return {
            'valid': is_valid,
            'errors': errors,
            'timestamp': datetime.datetime.now().isoformat(),
            'docker_dir': str(Path(get_global('script_path')) / 'docker')
        }