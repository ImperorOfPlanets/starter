import json
from flask import render_template, jsonify, request
from files.core.utils.loader_utils import get
from files.core.utils.log_utils import LogManager
from files.core.utils.globalVars_utils import get_global
from files.core.software.default.settings import SettingsModule

logger = LogManager.get_logger()

def t(key: str, **kwargs) -> str:
    i18n = get('i18n')
    if i18n and hasattr(i18n, 'translate'):
        return i18n.translate(key, **kwargs)
    return key

this_section_in_control_panel = True
section_icon = "bi-gear"
section_name = "Settings"
section_order = 100

def index(data, session):
    SettingsModule.set_globals()
    env_vars = SettingsModule.read_env_file()
    docker_validation = SettingsModule.validate_docker_path()
    system_env_info = SettingsModule.get_system_env_info()
    user = session.get('user') or session.get('user_info')

    return render_template(
        "sections/settings/index.html",
        env_vars=env_vars,
        docker_validation=docker_validation,
        system_env_info=system_env_info,
        user=user,
        t=t,
    )

def validate_docker_path(data, session):
    result = SettingsModule.validate_docker_path()
    return jsonify({"status": "success", "validation": result})

def save_env(data, session):
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

def change_password(data, session):
    user = session.get('user')
    if not user:
        return jsonify({"status": "error", "message": "Unauthorized"})

    current_password = data.get('current_password', '').strip()
    new_password = data.get('new_password', '').strip()
    confirm_password = data.get('confirm_password', '').strip()

    if not current_password or not new_password:
        return jsonify({"status": "error", "message": "Заполните все поля"})

    if new_password != confirm_password:
        return jsonify({"status": "error", "message": "Пароли не совпадают"})

    if len(new_password) < 6:
        return jsonify({"status": "error", "message": "Пароль минимум 6 символов"})

    admin_module = get('admin')
    if not admin_module:
        return jsonify({"status": "error", "message": "Admin module not found"})

    if not admin_module.verify_credentials(user['login'], current_password):
        return jsonify({"status": "error", "message": "Неверный текущий пароль"})

    env_path = get_global('starter_env_path')
    if not env_path or not env_path.exists():
        return jsonify({"status": "error", "message": ".env not found"})

    import hashlib
    new_hash = hashlib.sha256(new_password.encode()).hexdigest()

    with open(env_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    new_lines = []
    for line in lines:
        if line.startswith('ADMIN_PASSWORD_HASH='):
            new_lines.append(f'ADMIN_PASSWORD_HASH={new_hash}\n')
        else:
            new_lines.append(line)
    with open(env_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

    logger.info(f"Password changed for user: {user['login']}")
    return jsonify({"status": "success", "message": "Пароль изменён"})