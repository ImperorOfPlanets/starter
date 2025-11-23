import re
from pathlib import Path
from flask import redirect, url_for
from starter_files.core.utils.i18n_utils import set_language

def changeLanguage(data, session):
    lang = data.get('lang')
    from starter_files.core.utils.i18n_utils import get_available_languages
    languages = get_available_languages()

    if lang in languages:
        # Используем правильный путь к .env файлу относительно корня проекта
        from starter_files.core.utils.globalVars_utils import get_global
        script_path = Path(get_global('script_path'))
        env_path = script_path / '.env'

        if not env_path.exists():
            # Создаем .env с базовыми настройками
            default_env_content = f"""# Конфигурация приложения
LANGUAGE={lang}
APP_SECRET_KEY=your-secret-key-here
ADMIN_LOGIN=admin
ADMIN_PASSWORD_HASH=your-password-hash-here
PROJECT_ID=your-project-id
PORT=8000

# SMTP настройки
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_USE_TLS=true
SMTP_FROM_EMAIL=

# Docker пути
PATH_APP_DOCKER=/app/docker
PATH_APP_DOCKER_LOGS=/app/docker/logs

# Core сервер
CORE_SERVER_URL=https://core.myidon.site
"""
            env_path.write_text(default_env_content, encoding='utf-8')
        else:
            # Обновляем существующий .env
            try:
                current_env = env_path.read_text(encoding='utf-8')
                # Используем более надежную замену с учетом возможных пробелов и комментариев
                pattern = r'^(\s*LANGUAGE\s*=\s*).*$'
                replacement = f'\\1{lang}'
                updated_env = re.sub(pattern, replacement, current_env, flags=re.MULTILINE)

                # Если замена не произошла, добавляем строку
                if updated_env == current_env:
                    updated_env = current_env.rstrip() + f'\nLANGUAGE={lang}\n'

                env_path.write_text(updated_env, encoding='utf-8')
            except Exception as e:
                return {'status': 'error', 'message': f'Failed to update .env file: {str(e)}'}

        # Устанавливаем язык в текущей сессии
        set_language(lang)

        # Возвращаем локализованное сообщение
        from starter_files.core.utils.i18n_utils import t
        success_message = t('language_changed', _section='changeLanguage', _file='main')
        return {'status': 'success', 'message': success_message}

    # Возвращаем локализованное сообщение об ошибке
    from starter_files.core.utils.i18n_utils import t
    error_message = t('invalid_language', _section='changeLanguage', _file='main')
    return {'status': 'error', 'message': error_message}