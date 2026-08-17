import re
from pathlib import Path
from flask import redirect, url_for
from files.core.utils.loader_utils import get

def set_language(lang_code):
    """Устанавливает язык через i18n модуль"""
    i18n = get('i18n')
    if i18n and hasattr(i18n, 'set_language'):
        i18n.set_language(lang_code)

def get_available_languages():
    """Получает доступные языки через i18n модуль"""
    i18n = get('i18n')
    if i18n and hasattr(i18n, 'get_available_languages'):
        return i18n.get_available_languages()
    return {}

ENV_PATH = Path('.env')

def changeLanguage(data, session):
    lang = data.get('lang')
    languages = get_available_languages()
    
    if lang in languages:
        if not ENV_PATH.exists():
            from files.web.routes import create_env_with_defaults
            create_env_with_defaults(lang)
        else:
            current_env = ENV_PATH.read_text(encoding='utf-8')
            updated_env = re.sub(r'LANGUAGE=.*', f'LANGUAGE={lang}', current_env)
            ENV_PATH.write_text(updated_env, encoding='utf-8')
        
        set_language(lang)
        return {'status': 'success', 'message': 'Language changed successfully'}
    
    return {'status': 'error', 'message': 'Invalid language selected'}