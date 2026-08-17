# files/core/oss/default/admin.py
"""
Модуль административных функций
Восстановление доступа, управление учетными записями
"""

import hashlib
import secrets
from pathlib import Path
from typing import Dict, Optional

from files.core.base_module import BaseModule
from files.core.software.default.env import EnvModule
from files.core.oss.default.crypto import CryptoModule
from files.core.utils.globalVars_utils import get_global, set_global
from files.core.utils.log_utils import LogManager

logger = LogManager.get_logger('admin')


class AdminModule(BaseModule):
    """Модуль административных функций"""
    
    @staticmethod
    def check() -> bool:
        return True
    
    @staticmethod
    def set_globals():
        """Устанавливает глобальные переменные"""
        pass
    
    @staticmethod
    def show_current_credentials(env_path: Path = None) -> Dict[str, str]:
        """
        Показывает текущие учетные данные (без пароля, только логин)
        
        Returns:
            Dict с текущими настройками
        """
        if env_path is None:
            env_path = get_global('starter_env_path')
        
        if not env_path.exists():
            logger.error(f"Файл .env не найден: {env_path}")
            return {}
        
        env_vars = EnvModule.read_env_file(env_path)

        print("\n" + "="*60)
        print("🔍 ТЕКУЩИЕ УЧЕТНЫЕ ДАННЫЕ")
        print("="*60)

        login = env_vars.get('ADMIN_LOGIN', 'НЕ УСТАНОВЛЕН')
        password_hash = env_vars.get('ADMIN_PASSWORD_HASH', 'НЕ УСТАНОВЛЕН')
        app_secret = env_vars.get('APP_SECRET_KEY', 'НЕ УСТАНОВЛЕН')

        print(f"👤 Логин администратора: {login}")
        print(f"🔐 Хеш пароля: {password_hash[:32] if password_hash != 'НЕ УСТАНОВЛЕН' else 'НЕ УСТАНОВЛЕН'}...")
        print(f"🔑 APP_SECRET_KEY: {app_secret[:32] if app_secret != 'НЕ УСТАНОВЛЕН' else 'НЕ УСТАНОВЛЕН'}...")

        if login == 'НЕ УСТАНОВЛЕН' or password_hash == 'НЕ УСТАНОВЛЕН':
            print("\n⚠️  ВНИМАНИЕ: Учетные данные не настроены!")
            print("   Требуется первоначальная настройка")
        else:
            print("\n✅ Учетные данные найдены в конфигурации")

        print("="*60 + "\n")

        return {
            'login': login,
            'password_hash': password_hash,
            'app_secret_key': app_secret
        }
    
    @staticmethod
    def reset_admin_password(env_path: Path = None, new_password: Optional[str] = None) -> Dict[str, str]:
        """
        Сбрасывает пароль администратора
        
        Args:
            env_path: Путь к .env файлу
            new_password: Новый пароль (если None, генерируется автоматически)
            
        Returns:
            Dict с новыми учетными данными
        """
        if env_path is None:
            env_path = get_global('starter_env_path')
        
        if not env_path.exists():
            logger.error(f"Файл .env не найден: {env_path}")
            return {}
        
        # Читаем текущий .env
        with open(env_path, 'r', encoding='utf-8') as f:
            env_content = f.read()

        env_vars, env_lines = EnvModule.parse_env_content(env_content)

        # Генерируем или используем предоставленный пароль
        if new_password:
            password = new_password
        else:
            password = secrets.token_urlsafe(12)

        # Создаем новый хеш
        password_hash = hashlib.sha256(password.encode()).hexdigest()

        # Обновляем переменные
        env_vars['ADMIN_PASSWORD_HASH'] = password_hash

        # Если логина нет, тоже создадим
        if 'ADMIN_LOGIN' not in env_vars or not env_vars['ADMIN_LOGIN']:
            login = 'admin_' + secrets.token_hex(2)
            env_vars['ADMIN_LOGIN'] = login
        else:
            login = env_vars['ADMIN_LOGIN']

        # Записываем обновленный .env
        new_content = EnvModule.generate_env_content(env_vars, env_lines)

        with open(env_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        print("\n" + "="*60)
        print("✅ ПАРОЛЬ АДМИНИСТРАТОРА СБРОШЕН")
        print("="*60)
        print(f"👤 Логин: {login}")
        print(f"🔑 Новый пароль: {password}")
        print(f"🔐 Хеш: {password_hash}")
        print("\n⚠️  ВАЖНО: Сохраните эти данные!")
        print("="*60 + "\n")

        logger.info(f"Пароль администратора сброшен. Логин: {login}")

        return {
            'login': login,
            'password': password,
            'password_hash': password_hash
        }
    
    @staticmethod
    def regenerate_all_credentials(env_path: Path = None) -> Dict[str, str]:
        """
        Полная перегенерация всех учетных данных (логин + пароль + secret key)
        
        Returns:
            Dict с новыми учетными данными
        """
        if env_path is None:
            env_path = get_global('starter_env_path')
        
        if not env_path.exists():
            logger.error(f"Файл .env не найден: {env_path}")
            return {}
        
        # Генерируем новые данные
        password = secrets.token_urlsafe(12)
        login = 'admin_' + secrets.token_hex(2)
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        app_secret_key = secrets.token_hex(32)

        # Читаем текущий .env
        with open(env_path, 'r', encoding='utf-8') as f:
            env_content = f.read()

        env_vars, env_lines = EnvModule.parse_env_content(env_content)

        # Обновляем все учетные данные
        env_vars['ADMIN_LOGIN'] = login
        env_vars['ADMIN_PASSWORD_HASH'] = password_hash
        env_vars['APP_SECRET_KEY'] = app_secret_key

        # Записываем обновленный .env
        new_content = EnvModule.generate_env_content(env_vars, env_lines)

        with open(env_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        print("\n" + "="*60)
        print("🔄 ВСЕ УЧЕТНЫЕ ДАННЫЕ ПЕРЕГЕНЕРИРОВАНЫ")
        print("="*60)
        print(f"👤 Новый логин: {login}")
        print(f"🔑 Новый пароль: {password}")
        print(f"🔐 Хеш пароля: {password_hash}")
        print(f"🔑 APP_SECRET_KEY: {app_secret_key}")
        print("\n⚠️  ВАЖНО: Сохраните эти данные в безопасном месте!")
        print("="*60 + "\n")

        logger.info(f"Все учетные данные перегенерированы. Логин: {login}")

        return {
            'login': login,
            'password': password,
            'password_hash': password_hash,
            'app_secret_key': app_secret_key
        }
    
    @staticmethod
    def verify_credentials(login: str, password: str, env_path: Path = None) -> bool:
        """
        Проверяет правильность учетных данных
        
        Args:
            login: Логин для проверки
            password: Пароль для проверки
            env_path: Путь к .env файлу
            
        Returns:
            True если учетные данные верны
        """
        if env_path is None:
            env_path = get_global('starter_env_path')
        
        if not env_path.exists():
            logger.error("Файл .env не найден")
            return False
        
        env_vars = EnvModule.read_env_file(env_path)

        stored_login = env_vars.get('ADMIN_LOGIN', '')
        stored_hash = env_vars.get('ADMIN_PASSWORD_HASH', '')

        if not stored_login or not stored_hash:
            logger.error("Учетные данные не настроены")
            return False

        password_hash = hashlib.sha256(password.encode()).hexdigest()

        is_valid = (login == stored_login) and (password_hash == stored_hash)

        if is_valid:
            logger.info("Учетные данные верны")
        else:
            logger.warning("Неверные учетные данные")

        return is_valid
    
    @staticmethod
    def decrypt_password(master_password: str, env_path: Path = None) -> Optional[Dict[str, str]]:
        """
        Расшифровывает пароль из .env через мастер-пароль сканера
        
        Args:
            master_password: Мастер-пароль сканера проектов
            env_path: Путь к .env файлу
            
        Returns:
            Dict с расшифрованными данными или None
        """
        if env_path is None:
            env_path = get_global('starter_env_path')
        
        if not env_path.exists():
            logger.error(f"Файл .env не найден: {env_path}")
            return None
        
        # Читаем зашифрованный пароль
        encrypted = CryptoModule.read_encrypted_password(env_path)
        if not encrypted:
            print("\n❌ Зашифрованный пароль не найден в .env!")
            return None

        # Расшифровываем
        decrypted = CryptoModule.decrypt_password(encrypted, master_password)
        if not decrypted:
            print("\n❌ Не удалось расшифровать пароль!")
            return None

        # Читаем остальные данные из .env
        env_vars = EnvModule.read_env_file(env_path)

        print("\n" + "="*60)
        print("✅ ПАРОЛЬ УСПЕШНО РАСШИФРОВАН")
        print("="*60)
        print(f"👤 Логин: {env_vars.get('ADMIN_LOGIN', 'НЕ НАЙДЕН')}")
        print(f"🔑 Пароль: {decrypted}")
        print(f"🌐 Домен: {env_vars.get('DOMAIN', 'НЕ УСТАНОВЛЕН')}")
        print(f"📡 Порт: {env_vars.get('PORT', 'НЕ УСТАНОВЛЕН')}")
        print("="*60 + "\n")

        logger.info("Пароль успешно расшифрован")

        return {
            'login': env_vars.get('ADMIN_LOGIN', ''),
            'password': decrypted,
            'domain': env_vars.get('DOMAIN', ''),
            'port': env_vars.get('PORT', ''),
        }