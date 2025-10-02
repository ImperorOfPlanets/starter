# web контроллер
import json
from flask import render_template, jsonify, request
from starter_files.core.utils.i18n_utils import t
from starter_files.core.utils.log_utils import LogManager
from starter_files.core.software.default.settings import SettingsModule

logger = LogManager.get_logger()

this_section_in_control_panel = True
section_icon = "bi-gear"
section_name = "Docker Settings"
section_order = 2

def index(data, session):
    """Главная страница - редактор .env с информацией о системных переменных"""
    # Убедимся что глобальные переменные установлены
    SettingsModule.set_globals()
    
    env_vars = SettingsModule.read_env_file()
    docker_validation = SettingsModule.validate_docker_path()
    system_env_info = SettingsModule.get_system_env_info()

    return render_template(
        "sections/settings/index.html",
        env_vars=env_vars,
        docker_validation=docker_validation,
        system_env_info=system_env_info,
        t=t,
    )

def validate_docker_path(data, session):
    """Валидация Docker пути"""
    result = SettingsModule.validate_docker_path()
    return jsonify({"status": "success", "validation": result})

def save_env(data, session):
    """Сохранение .env файла"""
    try:
        raw_vars = data.get("env_vars")
        env_vars = json.loads(raw_vars) if isinstance(raw_vars, str) else raw_vars
        
        success = SettingsModule.write_env_file(env_vars)
        if success:
            return jsonify({"status": "success", "message": "Env file saved"})
        else:
            return jsonify({"status": "error", "message": "Failed to save env file"})
    except Exception as e:
        logger.error(f"Error saving env: {e}")
        return jsonify({"status": "error", "message": str(e)})