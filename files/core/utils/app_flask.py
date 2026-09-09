import logging
import os

from datetime import timedelta
from flask import Flask, render_template, request, session
from pathlib import Path

from files.core.utils.loader_utils import get
from files.core.utils.globalVars_utils import get_global, set_global
from files.web.routes import routes

from files.core.utils.log_utils import LogManager


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
    templates_path = str(get_global('starter_path') / 'files' / 'web' / 'templates')
    static_path = str(get_global('starter_path') / 'files' / 'web' / 'public')

    app = Flask(
        __name__,
        template_folder=templates_path,
        static_folder=static_path
    )

    LogManager.initialize(debug_mode=app.debug)
    logger = LogManager.get_logger('flask_app')

    env_module = get('env')
    if not env_module:
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

    app_secret = os.environ.get('APP_SECRET_KEY')
    if not app_secret:
        env_path = get_global('starter_env_path')
        if env_path and env_path.exists():
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip().startswith('APP_SECRET_KEY='):
                        app_secret = line.strip().split('=', 1)[1]
                        break
    if not app_secret:
        app_secret = 'fallback-key-change-me'

    app.secret_key = app_secret

    sessions_dir = get_global('starter_path') / "files" / "web" / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)

    from cachelib.file import FileSystemCache
    from flask_session import Session

    session_cache = FileSystemCache(
        cache_dir=str(sessions_dir),
        threshold=0,
        mode=0o600
    )

    app.config.update({
        'SECRET_KEY': app_secret,
        'SESSION_TYPE': 'cachelib',
        'SESSION_CACHELIB': session_cache,
        'SESSION_PERMANENT': True,
        'SESSION_USE_SIGNER': True,
        'SESSION_COOKIE_SECURE': False,
        'SESSION_COOKIE_HTTPONLY': True,
        'SESSION_COOKIE_SAMESITE': 'Lax',
        'SESSION_COOKIE_NAME': 'starter_session',
        'SESSION_COOKIE_DOMAIN': None,
        'PERMANENT_SESSION_LIFETIME': timedelta(days=30),
        'PREFERRED_URL_SCHEME': 'https',
        'SESSION_REFRESH_EACH_REQUEST': False,
    })

    Session(app)

    @app.context_processor
    def inject_global_vars():
        return {
            'logged_in': session.get('logged_in', False),
            'current_language': get_current_language(),
            'languages': get_available_languages(),
            't': t
        }

    app.jinja_env.cache = {}

    @app.before_request
    def ensure_starter_path():
        if not get_global('starter_path'):
            starter = Path(__file__).resolve().parent.parent.parent.parent
            set_global('starter_path', starter)
            set_global('venv_path', starter / 'venv')

    werkzeug_logger = logging.getLogger('werkzeug')
    if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        werkzeug_logger.setLevel(logging.ERROR)
        werkzeug_logger.handlers.clear()
        for handler in logger.handlers:
            werkzeug_logger.addHandler(handler)
    else:
        werkzeug_logger.setLevel(logging.WARNING)

    @app.after_request
    def add_header(response):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
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

    try:
        from files.web.api import api as api_blueprint
        app.register_blueprint(api_blueprint)
    except Exception as e:
        logger.error(f"Failed to register API blueprint: {e}")

    return app
