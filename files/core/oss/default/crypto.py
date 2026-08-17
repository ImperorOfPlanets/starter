"""
Модуль криптографии (ОС-независимый)
Отвечает за шифрование/дешифрование паролей
"""

import base64
import hashlib
import os
import secrets
from pathlib import Path
from typing import Optional, Tuple

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from files.core.base_module import BaseModule
from files.core.utils.globalVars_utils import get_global, set_global
from files.core.utils.log_utils import LogManager

logger = LogManager.get_logger('crypto')


class CryptoModule(BaseModule):
    """Модуль шифрования/дешифрования"""
    
    @staticmethod
    def check() -> bool:
        try:
            import cryptography
            return True
        except ImportError:
            logger.warning("cryptography library not installed")
            return False
    
    @staticmethod
    def set_globals():
        """Устанавливает глобальные переменные для криптографии"""
        starter_path = get_global('starter_path')
        if starter_path:
            crypto_dir = starter_path / "files" / "crypto"
            crypto_dir.mkdir(parents=True, exist_ok=True)
            set_global('crypto_dir', crypto_dir)
            logger.debug(f"Crypto directory: {crypto_dir}")
    
    @staticmethod
    def derive_key_from_master(master_password: str, salt: Optional[bytes] = None) -> Tuple[bytes, bytes]:
        """Генерирует ключ шифрования из мастер-пароля"""
        if salt is None:
            salt = os.urandom(16)

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(master_password.encode()))

        return key, salt
    
    @staticmethod
    def encrypt_password(password: str, master_password: str) -> str:
        """Шифрует пароль мастер-паролем"""
        key, salt = CryptoModule.derive_key_from_master(master_password)
        fernet = Fernet(key)
        
        encrypted = fernet.encrypt(password.encode())
        combined = salt + encrypted
        
        return base64.b64encode(combined).decode('utf-8')
    
    @staticmethod
    def decrypt_password(encrypted_password: str, master_password: str) -> Optional[str]:
        """Расшифровывает пароль мастер-паролем"""
        try:
            combined = base64.b64decode(encrypted_password)
            salt = combined[:16]
            encrypted = combined[16:]
            
            key, _ = CryptoModule.derive_key_from_master(master_password, salt)
            fernet = Fernet(key)
            
            decrypted = fernet.decrypt(encrypted)
            return decrypted.decode('utf-8')
        except Exception as e:
            logger.error(f"Ошибка расшифровки пароля: {e}")
            return None
    
    @staticmethod
    def generate_master_password() -> str:
        """Генерирует безопасный мастер-пароль"""
        return secrets.token_urlsafe(24)
    
    @staticmethod
    def encrypt_and_store_password(env_path: Path, password: str, master_password: str) -> bool:
        """Шифрует пароль и сохраняет в .env"""
        if not env_path.exists():
            logger.warning(f"Файл .env не найден: {env_path}")
            return False
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        encrypted = CryptoModule.encrypt_password(password, master_password)
        
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            logger.error(f"Ошибка чтения .env: {e}")
            return False
        
        new_lines = []
        has_hash = False
        has_encrypted = False
        
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('ADMIN_PASSWORD_HASH='):
                new_lines.append(f'ADMIN_PASSWORD_HASH={password_hash}\n')
                has_hash = True
            elif stripped.startswith('ADMIN_PASSWORD_ENCRYPTED='):
                new_lines.append(f'ADMIN_PASSWORD_ENCRYPTED={encrypted}\n')
                has_encrypted = True
            else:
                new_lines.append(line)
        
        if not has_hash:
            new_lines.append(f'ADMIN_PASSWORD_HASH={password_hash}\n')
        if not has_encrypted:
            new_lines.append(f'ADMIN_PASSWORD_ENCRYPTED={encrypted}\n')
        
        try:
            with open(env_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            logger.info(f"Пароль успешно зашифрован и сохранен в {env_path}")
            return True
        except Exception as e:
            logger.error(f"Ошибка записи .env: {e}")
            return False
    
    @staticmethod
    def read_encrypted_password(env_path: Path) -> Optional[str]:
        """Читает зашифрованный пароль из .env"""
        if not env_path.exists():
            logger.warning(f"Файл .env не найден: {env_path}")
            return None
        
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    stripped = line.strip()
                    if stripped.startswith('ADMIN_PASSWORD_ENCRYPTED='):
                        return stripped.split('=', 1)[1]
        except Exception as e:
            logger.error(f"Ошибка чтения зашифрованного пароля: {e}")
            return None
        
        return None
