# starter_files\core\software\default\settings.py
import os
from pathlib import Path
from typing import Dict, Any

from starter_files.core.base_module import BaseModule
from starter_files.core.utils.globalVars_utils import get_global, set_global
from starter_files.core.utils.log_utils import LogManager

logger = LogManager.get_logger("settings")

class SettingsModule(BaseModule):
    """
    Модуль для работы с .env Docker с поддержкой системных переменных
    """

    @staticmethod
    def set_globals():
        """Устанавливаем глобальные переменные из системных переменных или .env.example"""
        # Получаем пути из системных переменных или используем значения по умолчанию
        docker_path = os.environ.get("PATH_APP_DOCKER", "/app/docker")
        docker_logs_path = os.environ.get("PATH_APP_DOCKER_LOGS", "/app/docker/logs")
        
        set_global("docker_path", docker_path)
        set_global("docker_logs_path", docker_logs_path)
        
        logger.info(f"Set docker_path: {docker_path}")
        logger.info(f"Set docker_logs_path: {docker_logs_path}")

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