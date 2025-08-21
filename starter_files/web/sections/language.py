import re
from pathlib import Path
from flask import redirect, url_for
from starter_files.core.utils.i18n_utils import set_language

ENV_PATH = Path('.env')

def changeLanguage(data, session):
    lang = data.get('lang')
    from starter_files.core.utils.i18n_utils import get_available_languages
    languages = get_available_languages()
    
    if lang in languages:
        if not ENV_PATH.exists():
            # Создаем .env с дефолтами
            from starter_files.web.routes import create_env_with_defaults
            create_env_with_defaults(lang)
        else:
            # Обновляем существующий .env
            current_env = ENV_PATH.read_text(encoding='utf-8')
            updated_env = re.sub(r'LANGUAGE=.*', f'LANGUAGE={lang}', current_env)
            ENV_PATH.write_text(updated_env, encoding='utf-8')
        
        set_language(lang)
        return {'status': 'success', 'message': 'Language changed successfully'}
    
    return {'status': 'error', 'message': 'Invalid language selected'}