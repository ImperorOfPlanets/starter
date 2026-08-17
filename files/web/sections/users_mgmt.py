# files/web/sections/users_mgmt.py
"""
Секция управления пользователями
"""

from flask import render_template, jsonify, session

from files.core.utils.globalVars_utils import get_global
from files.core.utils.loader_utils import get
from files.core.utils.log_utils import LogManager

logger = LogManager.get_logger('web-users')

this_section_in_control_panel = True
section_icon = "bi-people"
section_name = "Users"
section_order = 3


def t(key: str, **kwargs) -> str:
    i18n = get('i18n')
    if i18n and hasattr(i18n, 'translate'):
        return i18n.translate(key, **kwargs)
    return key


def _check_admin():
    user = session.get('user')
    if not user:
        return None
    users_mod = get('users')
    if users_mod and not users_mod.has_permission(user, 'users.manage'):
        return None
    return user


def index(data, session_obj):
    user = _check_admin()
    if not user:
        return jsonify({'status': 'error', 'message': 'Admin access required'}), 403

    users_mod = get('users')
    users = users_mod.get_all() if users_mod else []

    from files.core.oss.default.users import ROLES
    servers_mod = get('servers')
    servers = servers_mod.get_all() if servers_mod else []

    return render_template('sections/users/index.html',
                           users=users, roles=ROLES, servers=servers,
                           current_user=user, t=t)


def list_users(data, session_obj):
    user = _check_admin()
    if not user:
        return jsonify({'status': 'error', 'message': 'Admin access required'}), 403

    users_mod = get('users')
    if not users_mod:
        return jsonify({'status': 'error', 'message': 'Users module not found'})

    return jsonify({'status': 'success', 'users': users_mod.get_all()})


def add_user(data, session_obj):
    user = _check_admin()
    if not user:
        return jsonify({'status': 'error', 'message': 'Admin access required'}), 403

    login = data.get('login', '').strip()
    password = data.get('password', '').strip()
    role = data.get('role', 'user').strip()
    server_ids = data.get('servers', '*')

    if not login or not password:
        return jsonify({'status': 'error', 'message': 'Login and password required'})

    if len(password) < 6:
        return jsonify({'status': 'error', 'message': 'Password must be at least 6 characters'})

    users_mod = get('users')
    if not users_mod:
        return jsonify({'status': 'error', 'message': 'Users module not found'})

    if server_ids != '*' and isinstance(server_ids, str):
        server_ids = [s.strip() for s in server_ids.split(',') if s.strip()]
    elif not isinstance(server_ids, list):
        server_ids = ['*']

    result = users_mod.add_user(
        login=login,
        password=password,
        role=role,
        servers=server_ids,
        creator_id=user.get('id')
    )
    return jsonify(result)


def remove_user(data, session_obj):
    user = _check_admin()
    if not user:
        return jsonify({'status': 'error', 'message': 'Admin access required'}), 403

    user_id = data.get('user_id')
    if not user_id:
        return jsonify({'status': 'error', 'message': 'User ID required'})

    users_mod = get('users')
    if not users_mod:
        return jsonify({'status': 'error', 'message': 'Users module not found'})

    if user_id == user.get('id'):
        return jsonify({'status': 'error', 'message': 'Cannot delete yourself'})

    result = users_mod.remove_user(user_id)
    return jsonify(result)


def update_user(data, session_obj):
    user = _check_admin()
    if not user:
        return jsonify({'status': 'error', 'message': 'Admin access required'}), 403

    user_id = data.get('user_id')
    if not user_id:
        return jsonify({'status': 'error', 'message': 'User ID required'})

    users_mod = get('users')
    if not users_mod:
        return jsonify({'status': 'error', 'message': 'Users module not found'})

    updates = {}
    if 'role' in data:
        updates['role'] = data['role']
    if 'password' in data and data['password']:
        updates['password'] = data['password']
    if 'servers' in data:
        updates['servers'] = data['servers']
    if 'active' in data:
        updates['active'] = data['active']

    result = users_mod.update_user(user_id, updates)
    return jsonify(result)
