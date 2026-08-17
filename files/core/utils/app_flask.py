import logging
import os
import secrets

from datetime import timedelta
from flask import Flask, render_template, request, session
from flask_session import Session
from pathlib import Path

from files.core.utils.loader_utils import get
from files.core.utils.globalVars_utils import get_global
from files.web.routes import routes

from files.core.utils.log_utils import LogManager


# Вспомогательные функции для шаблонов
def get_current_language() -> str:
    i18n_module = get('i18n')
    if i18n_module and hasattr(i18n_module, 'get_current_language'):
        return i18n_module.get_current_language()
    return 'en'


def get_available_languages() -> dict:
    i18n_module = get('i18n')
    if i18n_module and hasattr(i18n_module, 'get_available_languages'):
        return i18n_module.get_available_languages()
    return {}


def t(key: str, _section=None, _file=None, **kwargs) -> str:
    i18n_module = get('i18n')
    if i18n_module and hasattr(i18n_module, 'translate'):
        return i18n_module.translate(key, _section, _file, **kwargs)
    return key


def configure_app() -> Flask:
    """
    Создает и настраивает экземпляр Flask приложения
    """
    # Получаем абсолютный путь к директории с шаблонами
    templates_path = str(get_global('starter_path') / 'files' / 'web' / 'templates')
    static_path = str(get_global('starter_path') / 'files' / 'web' / 'public')

    app = Flask(
        __name__,
        template_folder=templates_path,
        static_folder=static_path
    )

    LogManager.initialize(debug_mode=app.debug)
    logger = LogManager.get_logger('flask_app')

    # Получаем модуль env для работы с .env файлами
    env_module = get('env')
    if not env_module:
        logger.error("Env module not found!")
        env_vars = {}
        env_path = get_global('starter_env_path')
        if env_path and env_path.exists():
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if '=' in line and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        env_vars[key] = value
    else:
        env_path = get_global('starter_env_path')
        env_vars = env_module.read_env_file(env_path) if env_path else {}
    
    # Секретный ключ
    app.secret_key = env_vars.get('APP_SECRET_KEY', secrets.token_hex(32))
    logger.info(f"Секретный ключ установлен: {app.secret_key[:10]}...")

    # ========== БЕРЕМ ПОРТ ИЗ ГЛОБАЛЬНЫХ ПЕРЕМЕННЫХ ==========
    # Это важно! Порт мог быть изменен после выделения сети
    port = get_global('port', 2000)
    logger.info(f"Порт из глобальных переменных: {port}")

    # Настройка папки сессий
    session_dir = get_global('starter_path') / "files" / "web" / "sessions"
    logger.info(f"Папка сессий: {session_dir}")
    
    session_dir.mkdir(parents=True, exist_ok=True)
    session_dir.chmod(0o755)

    # Настройки сессии
    app.config.update({
        'SESSION_TYPE': 'filesystem',
        'SESSION_FILE_DIR': str(session_dir),
        'SESSION_PERMANENT': True,
        'SESSION_COOKIE_SECURE': True,
        'SESSION_COOKIE_SAMESITE': 'Lax',
        'PERMANENT_SESSION_LIFETIME': timedelta(days=30),
        'PREFERRED_URL_SCHEME': 'https'
    })

    Session(app)

    # Глобальные переменные для всех шаблонов
    @app.context_processor
    def inject_global_vars():
        """Добавляет глобальные переменные во все шаблоны"""
        return {
            'logged_in': session.get('logged_in', False),
            'current_language': get_current_language(),
            'languages': get_available_languages(),
            't': t
        }

    # Отключаем кеш
    app.jinja_env.cache = {}

    app.session_initialized = False
    
    @app.before_request
    def initialize_session():
        if not app.session_initialized:
            session.setdefault('initialized', True)
            session.modified = True
            app.session_initialized = True
            logger.info("Session system initialized")
            
            try:
                sid = session.sid if hasattr(session, 'sid') else 'not_set'
                logger.debug(f"Initial session ID: {sid}")
            except Exception as e:
                logger.debug(f"Could not get session ID: {e}")

    @app.after_request
    def add_header(response):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response

    # Настройка логирования Werkzeug
    werkzeug_logger = logging.getLogger('werkzeug')
    
    if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        werkzeug_logger.setLevel(logging.ERROR)
        werkzeug_logger.handlers.clear()
        for handler in logger.handlers:
            werkzeug_logger.addHandler(handler)
    else:
        werkzeug_logger.setLevel(logging.WARNING)

    @app.after_request
    def log_request(response):
        if request.path.startswith('/public/'):
            return response
            
        log_data = {
            'method': request.method,
            'path': request.path,
            'status': response.status_code,
            'ip': request.remote_addr,
            'user_agent': request.user_agent.string if request.user_agent else 'unknown',
            'response_size': len(response.get_data()),
        }
        
        if request.method == 'POST':
            try:
                form_data = {}
                sensitive_fields = ['password', 'secret', 'token', 'key']
                for key, value in request.form.items():
                    if not any(field in key.lower() for field in sensitive_fields):
                        form_data[key] = str(value)[:100] if len(str(value)) > 100 else str(value)
                if form_data:
                    log_data['form_data'] = form_data
            except Exception as e:
                logger.warning(f"Failed to log form data: {e}")
        
        logger.info(f"Request: {log_data}")
        return response

    @app.errorhandler(500)
    def internal_error(error):
        logger.exception(f"500 Internal Server Error: {error}")
        try:
            return render_template('error.html', 
                                 error_message="Internal Server Error",
                                 error_details=str(error)), 500
        except Exception as template_error:
            logger.error(f"Failed to render error.html: {template_error}")
            return f"500 Internal Server Error: {error}", 500

    app.register_blueprint(routes)
    logger.info("Flask application configured and ready")
    return app