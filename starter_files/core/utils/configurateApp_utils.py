import logging
import os
import secrets

from datetime import timedelta
from flask import Flask, render_template, request,session
from flask_session import Session
from pathlib import Path

from starter_files.core.utils.envStarter_utils import read_env_file
from starter_files.core.utils.globalVars_utils import get_global
from starter_files.web.routes import routes

from starter_files.core.utils.log_utils import LogManager

def configure_app() -> Flask:
    """
    Создает и настраивает экземпляр Flask приложения
    Returns:
        Flask: настроенное Flask приложение
    """
    # Получаем абсолютный путь к директории с шаблонами
    base_dir = get_global('script_path')
    templates_path = str(base_dir / 'starter_files' / 'web' / 'templates')
    static_path = str(base_dir / 'starter_files' / 'web' / 'public')

    app = Flask(
        __name__,
        template_folder=templates_path,
        static_folder=static_path
    )
    LogManager.initialize(debug_mode=app.debug)
    logger = LogManager.get_logger('flask_app')

    # Считываем секретный ключ
    env_vars = read_env_file(get_global('script_path') / '.env')
    app.secret_key = env_vars.get('APP_SECRET_KEY', secrets.token_hex(32))
    logger.info("Устанавливаемый ключ")
    logger.info(app.secret_key)

    # Настройка папки сессий
    session_dir = base_dir / "starter_files" / "web" / "sessions"
    logger.info("Пака сессий")
    logger.info(session_dir)
    
    # Создаем папку (если не существует)
    session_dir.mkdir(parents=True, exist_ok=True)
    
    # Устанавливаем правильные права (755 для папок)
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

    # Отключаем кеш
    app.jinja_env.cache = {}

    # Выводим перед загрузкой
    app.session_initialized = False
    
    @app.before_request
    def initialize_session():
        if not app.session_initialized:
            # Инициализация сессии при первом запросе
            session.setdefault('initialized', True)
            session.modified = True
            app.session_initialized = True
            logger.info("Session system initialized")
            
            # Для отладки
            try:
                sid = session.sid if hasattr(session, 'sid') else 'not_set'
                logger.debug(f"Initial session ID: {sid}")
            except Exception as e:
                logger.error(f"Error getting session ID: {str(e)}")

    # Добавляем заголовки отключения кеширования
    @app.after_request
    def add_header(response):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response

    werkzeug_logger = LogManager.get_logger('werkzeug')
    # Отключаем логирование Werkzeug (встроенного сервера Flask)
    if app.debug:
        werkzeug_logger.setLevel(logging.WARNING)

    # Настройка логирования Werkzeug
    if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        werkzeug_logger.setLevel(logging.ERROR)
        
        # Удаляем стандартные обработчики Werkzeug
        for handler in werkzeug_logger.handlers[:]:
            werkzeug_logger.removeHandler(handler)
        
        # Добавляем наши обработчики
        for handler in logger.handlers:
            werkzeug_logger.addHandler(handler)

    # Add request logging middleware
    @app.after_request
    def log_request(response):
        # Skip static files logging
        if request.path.startswith('/public/'):
            return response
            
        # Prepare log data
        log_data = {
            'method': request.method,
            'path': request.path,
            'status': response.status_code,
            'ip': request.remote_addr,
            'user_agent': request.user_agent.string,
            'response_size': len(response.get_data()),
        }
        
        # Add form data for POST requests
        if request.method == 'POST':
            try:
                # Get form data (excluding sensitive fields) фывфы
                form_data = {}
                for key, value in request.form.items():
                    if 'password' not in key.lower():
                        form_data[key] = value
                log_data['form_data'] = form_data
            except Exception as e:
                logger.warning(f"Failed to log form data: {str(e)}")
        
        logger.info(f"Request: {log_data}")
        return response

    @app.errorhandler(500)
    def internal_error(error):
        logger.exception(f"500 Internal Server Error: {str(error)}")
        try:
            return render_template('error.html', error_message="Internal Server Error",error_details=str(error)), 500
        except Exception as template_error:
            logger.error(f"Не удалось отрендерить error.html: {template_error}")
            return f"500 Internal Server Error: {str(error)}", 500

    app.register_blueprint(routes)
    logger.info("Приложение запущено")
    return app

