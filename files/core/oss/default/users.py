"""
Менеджер пользователей: аутентификация, роли, права доступа
"""

import hashlib
import json
import secrets
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from files.core.base_module import BaseModule
from files.core.utils.globalVars_utils import get_global, set_global
from files.core.utils.log_utils import LogManager

logger = LogManager.get_logger('users')

ROLES = {
    "admin": {
        "label": "Administrator",
        "permissions": [
            "servers.manage",
            "servers.start_stop",
            "servers.configure",
            "servers.view",
            "users.manage",
            "logs.view",
            "settings.manage",
        ]
    },
    "user": {
        "label": "User",
        "permissions": [
            "servers.start_stop",
            "servers.configure",
            "servers.view",
            "logs.view",
        ]
    },
    "viewer": {
        "label": "Viewer",
        "permissions": [
            "servers.view",
            "logs.view",
        ]
    },
}


class UsersModule(BaseModule):
    """Управление пользователями и аутентификацией"""

    _users_path: Optional[Path] = None

    @staticmethod
    def check() -> bool:
        return True

    @staticmethod
    def set_globals():
        starter_path = get_global('starter_path')
        if starter_path:
            UsersModule._users_path = starter_path / 'users.json'
            set_global('users_path', UsersModule._users_path)

    @staticmethod
    def _get_path() -> Path:
        if UsersModule._users_path is None:
            UsersModule.set_globals()
        return UsersModule._users_path

    @staticmethod
    def _hash_password(password: str) -> str:
        salt = secrets.token_hex(16)
        h = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return f"{salt}:{h.hex()}"

    @staticmethod
    def _verify_password(password: str, stored: str) -> bool:
        try:
            salt, h = stored.split(':', 1)
            check = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
            return check.hex() == h
        except Exception:
            return False

    @staticmethod
    def load() -> Dict:
        path = UsersModule._get_path()
        if not path.exists():
            return {"version": "1.0", "users": []}
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading users: {e}")
            return {"version": "1.0", "users": []}

    @staticmethod
    def save(data: Dict):
        path = UsersModule._get_path()
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @staticmethod
    def ensure_admin(login: str, password: str):
        """Создаёт admin-пользователя если нет ни одного"""
        data = UsersModule.load()
        if data["users"]:
            return

        user_id = str(secrets.token_hex(8))
        user = {
            "id": user_id,
            "login": login,
            "password_hash": UsersModule._hash_password(password),
            "role": "admin",
            "servers": ["*"],
            "created_at": datetime.utcnow().isoformat() + "Z",
            "active": True,
        }
        data["users"].append(user)
        UsersModule.save(data)
        logger.info(f"Admin user created: {login}")
        return user

    @staticmethod
    def authenticate(login: str, password: str) -> Optional[Dict]:
        """Проверяет логин/пароль, возвращает пользователя или None"""
        data = UsersModule.load()
        for user in data["users"]:
            if user["login"] == login and user.get("active", True):
                if UsersModule._verify_password(password, user["password_hash"]):
                    logger.info(f"User authenticated: {login}")
                    return {k: v for k, v in user.items() if k != "password_hash"}
        logger.warning(f"Auth failed: {login}")
        return None

    @staticmethod
    def add_user(login: str, password: str, role: str = "user",
                 servers: List[str] = None, creator_id: str = None) -> Dict:
        if role not in ROLES:
            return {"status": "error", "message": f"Invalid role: {role}"}

        data = UsersModule.load()
        for u in data["users"]:
            if u["login"] == login:
                return {"status": "error", "message": "Login already exists"}

        user_id = str(secrets.token_hex(8))
        user = {
            "id": user_id,
            "login": login,
            "password_hash": UsersModule._hash_password(password),
            "role": role,
            "servers": servers or ["*"],
            "created_at": datetime.utcnow().isoformat() + "Z",
            "created_by": creator_id,
            "active": True,
        }
        data["users"].append(user)
        UsersModule.save(data)

        logger.info(f"User added: {login} (role={role})")
        return {"status": "success", "user": {k: v for k, v in user.items() if k != "password_hash"}}

    @staticmethod
    def remove_user(user_id: str) -> Dict:
        data = UsersModule.load()
        original = len(data["users"])
        data["users"] = [u for u in data["users"] if u["id"] != user_id]

        if len(data["users"]) < original:
            UsersModule.save(data)
            return {"status": "success"}
        return {"status": "error", "message": "User not found"}

    @staticmethod
    def update_user(user_id: str, updates: Dict) -> Dict:
        data = UsersModule.load()
        for u in data["users"]:
            if u["id"] == user_id:
                if "password" in updates:
                    u["password_hash"] = UsersModule._hash_password(updates.pop("password"))
                u.update(updates)
                UsersModule.save(data)
                return {"status": "success", "user": {k: v for k, v in u.items() if k != "password_hash"}}
        return {"status": "error", "message": "User not found"}

    @staticmethod
    def get_user(user_id: str) -> Optional[Dict]:
        data = UsersModule.load()
        for u in data["users"]:
            if u["id"] == user_id:
                return {k: v for k, v in u.items() if k != "password_hash"}
        return None

    @staticmethod
    def get_all() -> List[Dict]:
        data = UsersModule.load()
        return [{k: v for k, v in u.items() if k != "password_hash"} for u in data["users"]]

    @staticmethod
    def has_permission(user: Dict, permission: str) -> bool:
        """Проверяет есть ли у пользователя право"""
        role = user.get("role", "viewer")
        role_perms = ROLES.get(role, {}).get("permissions", [])
        return permission in role_perms

    @staticmethod
    def can_access_server(user: Dict, server_id: str) -> bool:
        """Проверяет доступ пользователя к серверу"""
        if user.get("role") == "admin":
            return True
        allowed = user.get("servers", [])
        return "*" in allowed or server_id in allowed

    @staticmethod
    def get_role_permissions(role: str) -> List[str]:
        return ROLES.get(role, {}).get("permissions", [])
