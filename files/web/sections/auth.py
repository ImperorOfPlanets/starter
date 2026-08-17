# files/web/sections/auth.py
import hashlib
import os
import time
from flask import session, url_for, render_template, request
from files.core.utils.loader_utils import get
from files.core.utils.log_utils import LogManager

logger = LogManager.get_logger('auth')

LOGIN_LOCKOUT_SECONDS = 5
_failed_attempts = {}


def _check_lockout(ip):
    if ip in _failed_attempts:
        elapsed = time.time() - _failed_attempts[ip]
        if elapsed < LOGIN_LOCKOUT_SECONDS:
            remaining = int(LOGIN_LOCKOUT_SECONDS - elapsed)
            return True, remaining
        else:
            del _failed_attempts[ip]
    return False, 0


def _record_failure(ip):
    _failed_attempts[ip] = time.time()


def _clear_failures(ip):
    _failed_attempts.pop(ip, None)


def t(key: str, **kwargs) -> str:
    i18n_module = get('i18n')
    if i18n_module and hasattr(i18n_module, 'translate'):
        return i18n_module.translate(key, **kwargs)
    return key


def login_page(data, session_obj):
    """Показать страницу входа"""
    return render_template('login.html')


def login(data, session_obj):
    """Обработчик входа — .env admin credentials"""
    ip = request.remote_addr or 'unknown'

    locked, remaining = _check_lockout(ip)
    if locked:
        return {'status': 'error', 'message': f'Слишком много попыток. Подождите {remaining} сек.', 'auth_form': True}

    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username or not password:
        return {'status': 'error', 'message': t('missing_credentials'), 'auth_form': True}

    admin_module = get('admin')
    if not admin_module:
        return {'status': 'error', 'message': t('auth_not_configured'), 'auth_form': True}

    if not admin_module.verify_credentials(username, password):
        _record_failure(ip)
        logger.warning(f"Failed login for {username} from {ip}")
        return {'status': 'error', 'message': t('invalid_credentials'), 'auth_form': True}

    _clear_failures(ip)
    session_obj['logged_in'] = True
    session_obj['username'] = username
    session_obj['is_admin'] = True
    session_obj['user'] = {
        'id': 'admin',
        'login': username,
        'role': 'admin',
        'servers': ['*']
    }
    session_obj.permanent = True
    logger.info(f"User {username} logged in via .env")
    return {'status': 'success', 'redirect': url_for('routes.index')}


def logout(data, session_obj):
    """Обработчик выхода"""
    username = session_obj.get('username', 'unknown')
    session_obj.clear()
    logger.info(f"User logged out: {username}")
    return {'status': 'success', 'redirect': url_for('routes.index')}


def login_with_myidon(data, session_obj):
    """Обработчик входа через MyIDon — сразу перенаправляем на MyIDon для OAuth"""
    logger.info("=== LOGIN WITH MYIDON INITIATED ===")

    oauth_module = get('oauth')

    if oauth_module is None:
        logger.error("OAuth module not found!")
        return {
            'status': 'error',
            'message': 'OAuth module not available'
        }

    # Принудительно ставим CLIENT_ID/SECRET из .env если ещё не установлены
    if not oauth_module.is_configured():
        env_path = get_global('starter_env_path')
        if env_path and env_path.exists():
            from files.core.software.default.env import EnvModule
            env_vars = EnvModule.read_env_file(env_path)
            client_id = env_vars.get('OAUTH_CLIENT_ID') or env_vars.get('OAUTH_STARTER_ID')
            client_secret = env_vars.get('OAUTH_CLIENT_SECRET') or env_vars.get('OAUTH_STARTER_SECRET')
            if client_id and client_secret:
                oauth_module.CLIENT_ID = client_id
                oauth_module.CLIENT_SECRET = client_secret
                logger.info(f"OAuth credentials loaded from .env: client_id={client_id}")

        # Определяем redirect_uri
        port = get_global('port', 2000)
        host = 'localhost'
        oauth_module.REDIRECT_URI = f"https://{host}:{port}/oauth/callback"

    # Генерируем URL для авторизации — сразу редиректим на MyIDon
    try:
        auth_url = oauth_module.get_authorization_url()
        logger.info(f"Auth URL generated: {auth_url}")

        if not auth_url:
            return {
                'status': 'error',
                'message': 'Failed to generate authorization URL'
            }

        return {
            'status': 'redirect',
            'redirect_url': auth_url
        }
    except Exception as e:
        logger.error(f"Error generating auth URL: {e}", exc_info=True)
        return {
            'status': 'error',
            'message': str(e)
        }


def oauth_callback(data, session_obj):
    """
    Обработчик callback после OAuth авторизации на MyIDon
    Принимает code и state, обменивает на токен и авторизует пользователя
    """
    logger.info("=== OAUTH CALLBACK ===")
    logger.info(f"Data: {data}")
    
    oauth_module = get('oauth')
    
    if oauth_module is None:
        logger.error("OAuth module not found!")
        return {
            'status': 'error',
            'message': 'OAuth module not available'
        }
    
    # Проверяем, есть ли функция oauth_callback в модуле oauth
    if not hasattr(oauth_module, 'oauth_callback'):
        logger.error("oauth_callback not found in oauth module")
        return {
            'status': 'error',
            'message': 'OAuth callback not available'
        }
    
    # Вызываем обработчик OAuth модуля
    try:
        result = oauth_module.oauth_callback(data, session_obj)
        logger.info(f"OAuth callback result: {result}")
        return result
    except Exception as e:
        logger.error(f"Error in OAuth callback: {e}", exc_info=True)
        return {
            'status': 'error',
            'message': f'OAuth callback failed: {str(e)}'
        }


def login_with_social(data, session_obj):
    """Обработчик входа через соцсеть (Telegram, VK и др.)"""
    oauth_module = get('oauth')
    if not oauth_module:
        return {
            'status': 'error',
            'message': 'OAuth module not available'
        }
    
    return oauth_module.login_with_social(data, session_obj)


def link_social_account(data, session_obj):
    """Подключение соцсети к существующему аккаунту"""
    oauth_module = get('oauth')
    if not oauth_module:
        return {
            'status': 'error',
            'message': 'OAuth module not available'
        }
    
    return oauth_module.link_social_account(data, session_obj)


def get_social_connections(data, session_obj):
    """Получение списка подключенных соцсетей"""
    oauth_module = get('oauth')
    if not oauth_module or not session_obj.get('oauth_token'):
        return {
            'status': 'success',
            'connections': []
        }
    
    connections = oauth_module.get_user_social_connections(session_obj.get('oauth_token'))
    return {
        'status': 'success',
        'connections': connections or []
    }


def get_available_social_providers(data, session_obj):
    """Получает список доступных соцсетей для авторизации"""
    try:
        oauth_module = get('oauth')
        myidon_url = oauth_module.MYIDON_URL if oauth_module else 'https://myidon.site'
        
        import requests
        response = requests.get(
            f"{myidon_url}/api/social-providers",
            timeout=5
        )
        
        if response.status_code == 200:
            providers = response.json()
            return {
                'status': 'success',
                'providers': providers
            }
        else:
            return {
                'status': 'success',
                'providers': [
                    {'name': 'telegram', 'display_name': 'Telegram', 'color': '#0088cc'},
                    {'name': 'vkontakte', 'display_name': 'VKontakte', 'color': '#4a76a8'},
                ]
            }
    except Exception as e:
        logger.error(f"Error getting social providers: {e}")
        return {
            'status': 'success',
            'providers': []
        }