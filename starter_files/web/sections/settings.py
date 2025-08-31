import json
from flask import render_template, jsonify, request
from starter_files.core.utils.i18n_utils import t
from starter_files.core.utils.log_utils import LogManager
from starter_files.core.software.default.settings import SettingsModule

logger = LogManager.get_logger()

this_section_in_control_panel = True
section_icon = "bi-gear"
section_name = "Settings"
section_order = 2   # после dashboard

def index(data, session):
    """Главная страница настроек"""
    settings = SettingsModule.get_settings()
    return render_template(
        "sections/settings/index.html",
        settings=settings,
        t=t
    )

def validate_project_path(data, session):
    path = data.get("path")
    if not path:
        return jsonify({"status": "error", "message": "Path required"})
    result = SettingsModule.validate_project_path(path)
    return jsonify({"status": "success", "validation": result})

def validate_docker_path(data, session):
    path = data.get("path")
    if not path:
        return jsonify({"status": "error", "message": "Path required"})
    result = SettingsModule.validate_docker_path(path)
    return jsonify({"status": "success", "validation": result})

def save_settings(data, session):
    try:
        raw = data.get("settings")
        settings = json.loads(raw) if isinstance(raw, str) else raw
        ok = SettingsModule.save_settings(settings)
        if ok:
            return jsonify({"status": "success"})
        else:
            return jsonify({"status": "error", "message": "Save failed"})
    except Exception as e:
        logger.error(f"Error saving settings: {e}")
        return jsonify({"status": "error", "message": str(e)})

def generate_docker_compose(data, session):
    settings = SettingsModule.get_settings()
    ok = SettingsModule.generate_docker_compose(settings)
    return jsonify({"status": "success" if ok else "error"})

def run_compose(data, session):
    settings = SettingsModule.get_settings()
    ok = SettingsModule.run_compose(settings)
    return jsonify({"status": "success" if ok else "error"})
