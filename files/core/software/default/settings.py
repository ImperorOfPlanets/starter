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