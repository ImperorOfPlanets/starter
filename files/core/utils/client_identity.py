"""
Идентичность клиента (установленного сервера/модуля).

Fingerprint клиента = <hardware fingerprint стартера>-<уникальная комбинация>.

- hardware fingerprint (CPU/board/disk/BIOS -> SHA-256) берётся из
  files/core/utils/hardware_id.py; при отказе пользователя от аппаратного
  консенса используется мягкий fingerprint (часы/MAC/имя хоста).
- уникальная комбинация (salt) генерируется ОДИН раз при первой установке
  и хранится в <host>/docker/.client_id вместе с activation key,
  выданным myidon.site. Благодаря этому:
    * два клиента на одном ПК - разные fingerprint;
    * смена ПК/железа - fingerprint клиента сохраняется (salt переживает),
      а myidon.site при новом check видит смену hardware fingerprint
      и может перепривязать клиента по activation key.
"""

import json
import secrets
from datetime import datetime
from pathlib import Path
from typing import Optional

from files.core.utils.log_utils import LogManager

logger = LogManager.get_logger('client_identity')

_ID_FILE = '.client_id'


def _id_path(host_path) -> Path:
    return Path(host_path) / 'docker' / _ID_FILE


def _hardware_fingerprint() -> str:
    """Аппаратный fingerprint этой машины (с мягким fallback)."""
    try:
        from files.core.utils.hardware_id import get_device_fingerprint
        return get_device_fingerprint()
    except Exception as e:
        logger.warning('hardware fingerprint failed: %s', e)
        import hashlib, platform, time
        raw = f'{platform.node()}-{time.time()}-{secrets.token_hex(4)}'
        return hashlib.sha256(raw.encode()).hexdigest()[:32]


def get_client_fingerprint(host_path, create: bool = True) -> Optional[str]:
    """Fingerprint клиента в host_path (создаёт при отсутствии).

    Возвращает None, если хост не создан и create=False.
    """
    host_path = Path(host_path)
    id_file = _id_path(host_path)

    if id_file.exists():
        try:
            data = json.loads(id_file.read_text(encoding='utf-8'))
            fp = data.get('client_fingerprint')
            if fp:
                return fp
        except Exception as e:
            logger.warning('client id unreadable (%s), regenerating', e)

    if not create:
        return None

    hw = _hardware_fingerprint()
    salt = secrets.token_hex(6)               # уникальная комбинация клиента
    fingerprint = f'{hw}-{salt}'

    id_file.parent.mkdir(parents=True, exist_ok=True)
    id_file.write_text(json.dumps({
        'client_fingerprint': fingerprint,
        'hardware_fingerprint': hw,
        'hostname': _hostname(),
        'created': datetime.utcnow().isoformat() + 'Z',
        'activation_key': None,
    }, indent=2, ensure_ascii=False), encoding='utf-8')
    logger.info('client identity created: %s (%s)', fingerprint, host_path)
    return fingerprint


def get_activation_key(host_path) -> Optional[str]:
    try:
        data = json.loads(_id_path(host_path).read_text(encoding='utf-8'))
        return data.get('activation_key')
    except Exception:
        return None


def set_activation_key(host_path, key: str) -> None:
    """Сохраняет activation key, выданный myidon.site, для этого клиента."""
    id_file = _id_path(host_path)
    try:
        data = json.loads(id_file.read_text(encoding='utf-8'))
    except Exception:
        data = {'client_fingerprint': get_client_fingerprint(host_path)}
    data['activation_key'] = key
    data['activated_at'] = datetime.utcnow().isoformat() + 'Z'
    id_file.parent.mkdir(parents=True, exist_ok=True)
    id_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')


def _hostname() -> str:
    import socket
    try:
        return socket.gethostname()
    except Exception:
        return ''
