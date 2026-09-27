"""
Фиксация установки серверов/клиентов после одобрения заявки.
При первой установке сохраняет данные для сравнения.
При переустановке проверяет что данные совпадают.
"""

import json
import hashlib
import socket
import uuid
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

from files.core.utils.log_utils import LogManager
from files.core.utils.globalVars_utils import get_global

logger = LogManager.get_logger('installation_lock')

# Путь к файлу с записями установок
LOCKS_FILE = 'installation_locks.json'


def _get_locks_path() -> Path:
    """Путь к файлу блокировок установок"""
    starter_path = get_global('starter_path')
    if starter_path:
        return Path(starter_path) / 'files' / LOCKS_FILE
    return Path(LOCKS_FILE)


def _load_locks() -> Dict:
    """Загрузить все записи установок"""
    locks_path = _get_locks_path()
    if locks_path.exists():
        try:
            with open(locks_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load locks: {e}")
    return {}


def _save_locks(locks: Dict):
    """Сохранить записи установок"""
    locks_path = _get_locks_path()
    try:
        locks_path.parent.mkdir(parents=True, exist_ok=True)
        with open(locks_path, 'w', encoding='utf-8') as f:
            json.dump(locks, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to save locks: {e}")


def get_device_fingerprint() -> str:
    """Получить отпечаток устройства"""
    hostname = socket.gethostname()
    
    mac_address = "unknown"
    try:
        mac_address = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) 
                               for elements in range(0, 2*6, 2)][::-1])
    except:
        pass
    
    starter_path = str(get_global('starter_path', ''))
    
    fingerprint_data = f"{hostname}:{mac_address}:{starter_path}"
    return hashlib.sha256(fingerprint_data.encode()).hexdigest()[:32]


def _generate_lock_key(server_type: str, server_path: str) -> str:
    """Генерирует уникальный ключ для записи установки"""
    return f"{server_type}:{server_path}"


def check_installation_allowed(
    server_type: str,
    server_path: str,
    user_id: int,
    application_id: int
) -> Dict:
    """
    Проверяет можно ли устанавливать/переустанавливать сервер.
    
    Returns:
        {
            'allowed': bool,
            'reason': str,
            'existing_lock': dict or None
        }
    """
    locks = _load_locks()
    lock_key = _generate_lock_key(server_type, server_path)
    
    if lock_key not in locks:
        # Первая установка — разрешаем
        return {
            'allowed': True,
            'reason': 'first_installation',
            'existing_lock': None
        }
    
    existing = locks[lock_key]
    device_fingerprint = get_device_fingerprint()
    
    # Проверяем совпадение данных
    checks = {
        'user_id': existing.get('user_id') == user_id,
        'application_id': existing.get('application_id') == application_id,
        'device_fingerprint': existing.get('device_fingerprint') == device_fingerprint,
    }
    
    all_match = all(checks.values())
    
    if all_match:
        # Все совпадает — разрешаем переустановку
        return {
            'allowed': True,
            'reason': 'same_user_same_device',
            'existing_lock': existing
        }
    
    # Есть расхождения — блокируем
    mismatched = [k for k, v in checks.items() if not v]
    return {
        'allowed': False,
        'reason': f'mismatch: {", ".join(mismatched)}',
        'existing_lock': existing,
        'checks': checks
    }


def record_installation(
    server_type: str,
    server_path: str,
    user_id: int,
    user_email: str,
    application_id: int,
    oauth_token: str = None,
    additional_data: Dict = None
) -> bool:
    """
    Фиксирует установку сервера/клиента.
    Вызывается ПОСЛЕ успешной установки.
    """
    locks = _load_locks()
    lock_key = _generate_lock_key(server_type, server_path)
    
    record = {
        'server_type': server_type,
        'server_path': server_path,
        'user_id': user_id,
        'user_email': user_email,
        'application_id': application_id,
        'device_fingerprint': get_device_fingerprint(),
        'hostname': socket.gethostname(),
        'installed_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat(),
    }
    
    if additional_data:
        record['additional_data'] = additional_data
    
    locks[lock_key] = record
    _save_locks(locks)
    
    logger.info(f"Installation recorded: {lock_key} for user {user_email}")
    return True


def update_installation(
    server_type: str,
    server_path: str,
    additional_data: Dict = None
) -> bool:
    """Обновляет запись установки (например, после обновления)"""
    locks = _load_locks()
    lock_key = _generate_lock_key(server_type, server_path)
    
    if lock_key in locks:
        locks[lock_key]['updated_at'] = datetime.now().isoformat()
        if additional_data:
            locks[lock_key]['additional_data'] = additional_data
        _save_locks(locks)
        logger.info(f"Installation updated: {lock_key}")
        return True
    
    return False


def get_installation_info(server_type: str, server_path: str) -> Optional[Dict]:
    """Получить информацию об установке"""
    locks = _load_locks()
    lock_key = _generate_lock_key(server_type, server_path)
    return locks.get(lock_key)


def get_all_installations() -> Dict:
    """Получить все записи установок"""
    return _load_locks()


def remove_installation(server_type: str, server_path: str) -> bool:
    """Удалить запись установки (при удалении сервера)"""
    locks = _load_locks()
    lock_key = _generate_lock_key(server_type, server_path)
    
    if lock_key in locks:
        del locks[lock_key]
        _save_locks(locks)
        logger.info(f"Installation record removed: {lock_key}")
        return True
    
    return False
