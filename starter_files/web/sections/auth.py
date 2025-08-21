# starter_files/web/sections/auth.py
import hashlib
import os
from flask import session, url_for
from starter_files.core.utils.i18n_utils import t, get_available_languages

from starter_files.core.utils.log_utils import LogManager
logger = LogManager.get_logger()

def hash_password(password: str) -> str:
    """Хеширование пароля"""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def login(data, session):
    """Обработчик входа"""
    # Логирование входящих данных
    logger.info(f"\n=== DEBUG AUTH ===")
    logger.info(f"Input data: {data}")
    logger.info(f"Session: {dict(session)}")
    logger.info(f"ENV: ADMIN_LOGIN={os.getenv('ADMIN_LOGIN')}")
    logger.info(f"ENV: ADMIN_PASSWORD_HASH={os.getenv('ADMIN_PASSWORD_HASH')}")

    username = data.get('username')
    password = data.get('password')
    admin_login = os.getenv('ADMIN_LOGIN')
    admin_pass_hash = os.getenv('ADMIN_PASSWORD_HASH')

    # Хэширование входящего пароля для сравнения
    input_hash = hashlib.sha256(password.encode('utf-8')).hexdigest() if password else None
    logger.info(f"Input hash: {input_hash}")
    logger.info(f"Stored hash: {admin_pass_hash}")
    
    # Проверка наличия данных
    if not all([username, password]):
        return {
            'status': 'error',
            'message': t('missing_credentials'),
            'auth_form': True
        }
    
    # Проверка конфигурации
    if not admin_login or not admin_pass_hash:
        return {
            'status': 'error',
            'message': t('auth_not_configured'),
            'auth_form': True
        }
    
    # Проверка учетных данных
    if username == admin_login and hash_password(password) == admin_pass_hash:
        session['username'] = username
        session.permanent = True  # Делаем сессию постоянной
        session.modified = True
        # Явное сохранение сессии
        if hasattr(session, 'save'):
            session.save()

        logger.info(f"Установлена сессия. ID: {session.sid if hasattr(session, 'sid') else 'not_set'}")
        logger.info(f"Данные сессии: {dict(session)}")

        return {
            'status': 'success',
            'redirect': url_for('routes.index')
        }
    
    return {
        'status': 'error',
        'message': t('invalid_credentials'),
        'auth_form': True
    }

def logout(data, session):
    """Обработчик выхода"""
    session.pop('username', None)
    return {
        'status': 'success',
        'redirect': url_for('routes.index')
    }