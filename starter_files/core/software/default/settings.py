# starter_files\core\software\default\settings.py
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Tuple, Union

from starter_files.core.base_module import BaseModule
from starter_files.core.utils.globalVars_utils import get_global, set_global
from starter_files.core.utils.log_utils import LogManager

logger = LogManager.get_logger("settings")


class SettingsModule(BaseModule):
    """
    Модуль управления настройками, env и docker-compose
    """

    DEFAULT_SETTINGS = {
        "project_path": "/app/laravel",
        "docker_files": "/app/docker/",
        "project_type": "client",
        "environment": "production",
    }

    DEFAULT_SETTINGS_PATH = "/app/config/settings.json"

    # -------------------------------------------------------------------------
    # БАЗОВЫЕ НАСТРОЙКИ
    # -------------------------------------------------------------------------

    @staticmethod
    def get_settings() -> Dict[str, Any]:
        settings_path = SettingsModule._get_settings_path()

        if os.path.exists(settings_path):
            try:
                with open(settings_path, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading settings: {str(e)}")
                return SettingsModule.DEFAULT_SETTINGS.copy()

        return SettingsModule.DEFAULT_SETTINGS.copy()

    @staticmethod
    def save_settings(settings: Dict[str, Any]) -> bool:
        try:
            settings_path = SettingsModule._get_settings_path()
            os.makedirs(os.path.dirname(settings_path), exist_ok=True)

            with open(settings_path, "w") as f:
                json.dump(settings, f, indent=4)

            logger.info("Settings saved successfully")
            return True
        except Exception as e:
            logger.error(f"Error saving settings: {str(e)}")
            return False

    @staticmethod
    def _get_settings_path() -> str:
        return os.environ.get("APP_SETTINGS_PATH", SettingsModule.DEFAULT_SETTINGS_PATH)

    @staticmethod
    def set_globals():
        settings = SettingsModule.get_settings()
        set_global("project_settings", settings)
        set_global("project_path", settings.get("project_path", "/app/laravel"))
        set_global("docker_path", settings.get("docker_files", "/app/docker"))

    # -------------------------------------------------------------------------
    # ВАЛИДАЦИЯ ПУТЕЙ
    # -------------------------------------------------------------------------

    @staticmethod
    def validate_project_path(path: str) -> Dict[str, Any]:
        result = {"valid": False, "exists": False, "is_dir": False, "message": ""}
        try:
            path_obj = Path(path)
            result["exists"] = path_obj.exists()
            result["is_dir"] = path_obj.is_dir()

            if not result["exists"]:
                result["message"] = "Path does not exist"
            elif not result["is_dir"]:
                result["message"] = "Path is not a directory"
            else:
                project_files = list(path_obj.glob("*"))
                result["valid"] = len(project_files) > 0
                result["message"] = (
                    "Valid project path" if result["valid"] else "Directory is empty"
                )
        except Exception as e:
            result["message"] = f"Validation error: {str(e)}"

        return result

    @staticmethod
    def validate_docker_path(path: str) -> Dict[str, Any]:
        result = {
            "valid": False,
            "exists": False,
            "is_dir": False,
            "has_compose": False,
            "message": "",
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
                compose_path = path_obj / "docker-compose.yml"
                result["has_compose"] = compose_path.exists()
                result["valid"] = result["has_compose"]
                result["message"] = (
                    "Valid Docker path" if result["valid"] else "Missing docker-compose.yml"
                )
        except Exception as e:
            result["message"] = f"Validation error: {str(e)}"

        return result

    # -------------------------------------------------------------------------
    # ENV: ЧТЕНИЕ, ЗАПИСЬ, ГЕНЕРАЦИЯ
    # -------------------------------------------------------------------------

    @staticmethod
    def parse_env_content(
        content: str,
    ) -> Tuple[Dict[str, str], List[Union[str, Tuple[str, str]]]]:
        variables = {}
        lines = []
        for line in content.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                lines.append(line)
                continue

            if "=" in stripped:
                key, value = stripped.split("=", 1)
                key = key.strip()
                variables[key] = value.strip()
                lines.append((key, line))
            else:
                lines.append(line)

        return variables, lines

    @staticmethod
    def generate_env_content(
        vars_dict: Dict[str, str],
        template_lines: List[Union[str, Tuple[str, str]]],
        preserve_custom: bool = True,
    ) -> str:
        result = []
        vars_to_add = vars_dict.copy()

        for line in template_lines:
            if isinstance(line, tuple):
                key, original_line = line
                if key in vars_to_add:
                    if "=" in original_line:
                        prefix = original_line.split("=", 1)[0]
                        new_line = f"{prefix}={vars_to_add.pop(key)}"
                    else:
                        new_line = f"{key}={vars_to_add.pop(key)}"
                    result.append(new_line)
                else:
                    result.append(original_line)
            else:
                result.append(line)

        if preserve_custom:
            custom_vars = {
                k: v
                for k, v in vars_dict.items()
                if k not in [l[0] for l in template_lines if isinstance(l, tuple)]
            }
            if custom_vars:
                result.append("\n# Custom variables")
                for key, value in custom_vars.items():
                    result.append(f"{key}={value}")

        return "\n".join(result)

    @staticmethod
    def read_env_file(env_path: Path) -> Dict[str, str]:
        if not env_path.exists():
            return {}

        with open(env_path, "r", encoding="utf-8") as f:
            content = f.read()
        variables, _ = SettingsModule.parse_env_content(content)
        return variables

    @staticmethod
    def write_env_file(env_path: Path, vars_dict: Dict[str, str], template_path: Path = None):
        if template_path and template_path.exists():
            with open(template_path, "r", encoding="utf-8") as f:
                template_content = f.read()
            _, template_lines = SettingsModule.parse_env_content(template_content)
            content = SettingsModule.generate_env_content(vars_dict, template_lines)
        else:
            content = SettingsModule.generate_env_content(vars_dict, [])

        with open(env_path, "w", encoding="utf-8") as f:
            f.write(content)

    @staticmethod
    def ensure_env_variables():
        script_path = Path(get_global("script_path"))
        env_path = script_path / ".env"
        env_example_path = script_path / ".env.example"

        if not env_example_path.exists():
            return

        current_vars = SettingsModule.read_env_file(env_path)
        with open(env_example_path, "r", encoding="utf-8") as f:
            example_content = f.read()
        example_vars, example_lines = SettingsModule.parse_env_content(example_content)

        merged_vars = {**example_vars, **current_vars}
        content = SettingsModule.generate_env_content(merged_vars, example_lines)

        with open(env_path, "w", encoding="utf-8") as f:
            f.write(content)