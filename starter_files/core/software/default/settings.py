# starter_files\core\software\default\settings.py
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional

from starter_files.core.base_module import BaseModule
from starter_files.core.utils.globalVars_utils import get_global, set_global
from starter_files.core.utils.log_utils import LogManager

logger = LogManager.get_logger('settings')

class SettingsModule(BaseModule):

    DEFAULT_SETTINGS = {
        "project_path": "/app/laravel",
        "docker_files": "/app/docker/", #  Это путь до папки где лежат файлы для докера и скрипты запуска контейнеров
        "project_type": "client",
        "environment": "production"
    }

    """Модуль для управления настройками проекта"""
    
    # Путь к файлу настроек по умолчанию
    DEFAULT_SETTINGS_PATH = "/app/config/settings.json"
    
    @staticmethod
    def get_settings() -> Dict[str, Any]:
        """Получает текущие настройки проекта"""
        settings_path = SettingsModule._get_settings_path()
        
        # Если файл настроек существует, загружаем его
        if os.path.exists(settings_path):
            try:
                with open(settings_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading settings: {str(e)}")
                return SettingsModule.DEFAULT_SETTINGS.copy()
        
        # Если файла нет, возвращаем настройки по умолчанию
        return SettingsModule.DEFAULT_SETTINGS.copy()
    
    @staticmethod
    def save_settings(settings: Dict[str, Any]) -> bool:
        """Сохраняет настройки проекта"""
        try:
            settings_path = SettingsModule._get_settings_path()
            
            # Создаем директорию, если её нет
            os.makedirs(os.path.dirname(settings_path), exist_ok=True)
            
            # Сохраняем настройки
            with open(settings_path, 'w') as f:
                json.dump(settings, f, indent=4)
            
            logger.info("Settings saved successfully")
            return True
        except Exception as e:
            logger.error(f"Error saving settings: {str(e)}")
            return False
    
    @staticmethod
    def validate_project_path(path: str) -> Dict[str, Any]:
        """Проверяет путь к проекту на валидность"""
        result = {
            "valid": False,
            "exists": False,
            "is_dir": False,
            "message": ""
        }
        
        try:
            path_obj = Path(path)
            result["exists"] = path_obj.exists()
            result["is_dir"] = path_obj.is_dir()
            
            if not result["exists"]:
                result["message"] = "Path does not exist"
            elif not result["is_dir"]:
                result["message"] = "Path is not a directory"
            else:
                # Проверяем, содержит ли путь файлы проекта
                project_files = list(path_obj.glob('*'))
                result["valid"] = len(project_files) > 0
                result["message"] = "Valid project path" if result["valid"] else "Directory is empty"
                
        except Exception as e:
            result["message"] = f"Validation error: {str(e)}"
        
        return result
    
    @staticmethod
    def validate_docker_path(path: str) -> Dict[str, Any]:
        """Проверяет путь к Docker на валидность"""
        result = {
            "valid": False,
            "exists": False,
            "is_dir": False,
            "has_compose": False,
            "message": ""
        }
        
        try:
            path_obj = Path(path)
            result["exists"] = path_obj.exists()
            result["is_dir"] = path_obj.is_dir()
            
            if not result["exists"]:
                result["message"] = "Path does not exist"
            elif not result["is_dir"]:
                result["message"] = "Path is not a directory"
            else:
                # Проверяем наличие docker-compose.yml
                compose_path = path_obj / "docker-compose.yml"
                result["has_compose"] = compose_path.exists()
                result["valid"] = result["has_compose"]
                result["message"] = "Valid Docker path" if result["valid"] else "Missing docker-compose.yml"
                
        except Exception as e:
            result["message"] = f"Validation error: {str(e)}"
        
        return result
    
    @staticmethod
    def generate_docker_compose(settings: Dict[str, Any]) -> bool:
        pass
    
    @staticmethod
    def _generate_compose_content(settings: Dict[str, Any]) -> str:
        pass
    
    @staticmethod
    def _get_settings_path() -> str:
        """Возвращает путь к файлу настроек"""
        # Можно добавить логику для определения пути к файлу настроек
        # Например, из переменных окружения или глобальных настроек
        return os.environ.get('APP_SETTINGS_PATH', SettingsModule.DEFAULT_SETTINGS_PATH)
    
    @staticmethod
    def set_globals():
        """Устанавливает глобальные переменные для настроек"""
        settings = SettingsModule.get_settings()
        set_global('project_settings', settings)
        set_global('project_path', settings.get('project_path', '/app/laravel'))
        set_global('docker_path', settings.get('docker_path', '/app/docker'))