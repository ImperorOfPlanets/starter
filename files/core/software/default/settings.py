# files\core\software\default\settings.py
import os
from pathlib import Path
from typing import Dict, Any

from files.core.base_module import BaseModule
from files.core.utils.globalVars_utils import get_global, set_global
from files.core.utils.log_utils import LogManager

logger = LogManager.get_logger("settings")

class SettingsModule(BaseModule):
    """
    Модуль для работы с .env Docker с поддержкой системных переменных
    """

    @staticmethod
    def set_globals():
        """Устанавливаем глобальные переменные с приоритетом: .env > системные переменные > дефолтные"""
        from pathlib import Path
        
        # Получаем путь к скрипту
        script_path = get_global('script_path')
        if not script_path:
            script_path = Path(__file__).parent.parent.parent.parent.parent.absolute()
            set_global('script_path', script_path)
        
        script_path = Path(script_path)
        
        # 1. Сначала пытаемся прочитать .env файл в папке docker
        possible_docker_paths = [
            script_path.parent / "docker",  # C:\control\mentoria\docker
            script_path / "docker"         # C:\control\mentoria\starter\docker
        ]
        
        docker_path = None
        docker_logs_path = None
        
        # Ищем .env файл и читаем пути из него
        for test_path in possible_docker_paths:
            env_file = test_path / ".env"
            if env_file.exists():
                try:
                    with open(env_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if line.startswith('PATH_APP_DOCKER='):
                                docker_path = line.split('=', 1)[1].strip()
                                # Убираем кавычки если есть
                                docker_path = docker_path.strip('"\'')
                            elif line.startswith('PATH_APP_DOCKER_LOGS='):
                                docker_logs_path = line.split('=', 1)[1].strip()
                                docker_logs_path = docker_logs_path.strip('"\'')
                except Exception as e:
                    logger.error(f"Error reading .env file {env_file}: {e}")
        
        # 2. Если не нашли в .env, проверяем системные переменные
        if not docker_path:
            docker_path = os.environ.get("PATH_APP_DOCKER")
        
        if not docker_logs_path:
            docker_logs_path = os.environ.get("PATH_APP_DOCKER_LOGS")
        
        # 3. Если все еще нет, используем дефолтный путь (предполагаемая структура)
        if not docker_path:
            docker_path = str(script_path.parent / "docker")
        
        if not docker_logs_path:
            docker_logs_path = str(Path(docker_path) / "logs")
        
        # Преобразуем пути в абсолютные
        docker_path = Path(docker_path)
        if not docker_path.is_absolute():
            docker_path = script_path.parent / docker_path
        
        docker_logs_path = Path(docker_logs_path)
        if not docker_logs_path.is_absolute():
            docker_logs_path = script_path.parent / docker_logs_path
        
        # Создаем директории если их нет
        docker_path.mkdir(parents=True, exist_ok=True)
        docker_logs_path.mkdir(parents=True, exist_ok=True)
        
        set_global("docker_path", str(docker_path))
        set_global("docker_logs_path", str(docker_logs_path))
        
        logger.info(f"Set docker_path: {docker_path}")
        logger.info(f"Set docker_logs_path: {docker_logs_path}")
        
        # Также сохраняем в переменные окружения для дочерних процессов
        os.environ["PATH_APP_DOCKER"] = str(docker_path)
        os.environ["PATH_APP_DOCKER_LOGS"] = str(docker_logs_path)

    @staticmethod
    def get_docker_env_path() -> Path:
        """Получаем путь к .env файлу Docker"""
        docker_path = Path(get_global("docker_path", "/app/docker"))
        return docker_path / ".env"

    @staticmethod
    def get_docker_env_example_path() -> Path:
        """Получаем путь к .env.example файлу"""
        docker_path = Path(get_global("docker_path", "/app/docker"))
        return docker_path / ".env.example"

    @staticmethod
    def validate_docker_path() -> Dict[str, Any]:
        """Валидация Docker пути"""
        docker_path = Path(get_global("docker_path", "/app/docker"))
        
        result = {
            "valid": False,
            "exists": False,
            "is_dir": False,
            "has_compose": False,
            "has_env": False,
            "has_env_example": False,
            "path": str(docker_path),
            "message": "",
        }

        try:
            result["exists"] = docker_path.exists()
            result["is_dir"] = docker_path.is_dir()

            if not result["exists"]:
                result["message"] = "Docker path does not exist"
            elif not result["is_dir"]:
                result["message"] = "Docker path is not a directory"
            else:
                # Проверяем docker-compose.yml
                compose_path = docker_path / "docker-compose.yml"
                result["has_compose"] = compose_path.exists()
                
                # Проверяем .env
                env_path = docker_path / ".env"
                result["has_env"] = env_path.exists()
                
                # Проверяем .env.example
                env_example_path = docker_path / ".env.example"
                result["has_env_example"] = env_example_path.exists()
                
                result["valid"] = result["has_compose"]
                result["message"] = (
                    "Valid Docker path" if result["valid"] else "Missing docker-compose.yml"
                )
        except Exception as e:
            result["message"] = f"Validation error: {str(e)}"

        return result

    @staticmethod
    def read_env_file() -> Dict[str, str]:
        """Читаем .env файл Docker, используем .env.example как шаблон если нужно"""
        env_path = SettingsModule.get_docker_env_path()
        env_example_path = SettingsModule.get_docker_env_example_path()
        
        # Если .env не существует, но есть .env.example, создаем из шаблона
        if not env_path.exists() and env_example_path.exists():
            logger.info("Creating .env from .env.example template")
            with open(env_example_path, "r", encoding="utf-8") as f:
                template_content = f.read()
            
            # Парсим шаблон и создаем базовые переменные
            template_vars = {}
            for line in template_content.splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                if "=" in stripped:
                    key, value = stripped.split("=", 1)
                    template_vars[key.strip()] = value.strip()
            
            SettingsModule.write_env_file(template_vars)
            return template_vars
        
        if not env_path.exists():
            return {}

        try:
            with open(env_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            variables = {}
            for line in content.splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                if "=" in stripped:
                    key, value = stripped.split("=", 1)
                    variables[key.strip()] = value.strip()
            
            return variables
        except Exception as e:
            logger.error(f"Error reading env file: {str(e)}")
            return {}

    @staticmethod
    def write_env_file(vars_dict: Dict[str, str]):
        """Записываем .env файл Docker, используя .env.example как шаблон для структуры"""
        env_path = SettingsModule.get_docker_env_path()
        env_example_path = SettingsModule.get_docker_env_example_path()
        
        try:
            # Создаем директорию если нужно
            env_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Если есть .env.example, используем его как шаблон для сохранения структуры
            if env_example_path.exists():
                with open(env_example_path, "r", encoding="utf-8") as f:
                    template_content = f.read()
                
                # Парсим шаблон
                result_lines = []
                template_vars = {}
                
                for line in template_content.splitlines():
                    stripped = line.strip()
                    if not stripped or stripped.startswith("#"):
                        result_lines.append(line)
                        continue
                    
                    if "=" in stripped:
                        key, original_value = stripped.split("=", 1)
                        key = key.strip()
                        template_vars[key] = original_value.strip()
                        
                        # Если эта переменная есть в новых данных, используем новое значение
                        if key in vars_dict:
                            result_lines.append(f"{key}={vars_dict[key]}")
                        else:
                            result_lines.append(line)
                
                # Добавляем кастомные переменные которых нет в шаблоне
                custom_vars = {k: v for k, v in vars_dict.items() if k not in template_vars}
                if custom_vars:
                    result_lines.append("\n# Custom variables")
                    for key, value in custom_vars.items():
                        result_lines.append(f"{key}={value}")
                
                content = "\n".join(result_lines)
            else:
                # Если шаблона нет, просто формируем содержимое
                content = ""
                for key, value in vars_dict.items():
                    content += f"{key}={value}\n"
            
            with open(env_path, "w", encoding="utf-8") as f:
                f.write(content)
            
            logger.info("Env file saved successfully")
            return True
        except Exception as e:
            logger.error(f"Error writing env file: {str(e)}")
            return False

    @staticmethod
    def get_system_env_info() -> Dict[str, str]:
        """Получаем информацию о системных переменных"""
        return {
            "PATH_APP_DOCKER": os.environ.get("PATH_APP_DOCKER", "Not set"),
            "PATH_APP_DOCKER_LOGS": os.environ.get("PATH_APP_DOCKER_LOGS", "Not set"),
        }