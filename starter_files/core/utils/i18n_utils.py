import inspect
import os
import sys

from importlib import import_module
from pathlib import Path
from flask import g
from starter_files.core.utils.globalVars_utils import get_global

from starter_files.core.utils.log_utils import LogManager
LogManager.register_log_dir('translations', 'translations')
logger = LogManager.get_logger('translations')

# Глобальная переменная для кеширования языков
_AVAILABLE_LANGUAGES = None

# Функция получения языков
def get_current_language():
    env_path = get_global('script_path') / '.env'
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('LANGUAGE='):
                    return line.strip().split('=')[1]
    return 'en'

def set_language(lang_code: str):
    """Устанавливает язык в переменных окружения"""
    os.environ['LANGUAGE'] = lang_code.lower()

def get_available_languages(force_reload=False) -> dict:
    """Возвращает словарь доступных языков в формате для языкового селектора"""
    global _AVAILABLE_LANGUAGES
    
    if _AVAILABLE_LANGUAGES is not None and not force_reload:
        return _AVAILABLE_LANGUAGES
    
    base_dir = get_global('script_path')
    locales_dir = base_dir / 'starter_files' / 'web' / 'locales'
    logger.debug(f"Ищем переводы в директории: {locales_dir}")
    
    languages = {}
    
    if not locales_dir.exists():
        logger.info(f"ОШИБКА: Папка с локалями не найдена по пути: {locales_dir}")
        return languages
    
    for locale_file in locales_dir.glob('*.py'):
        if locale_file.stem == '__init__':
            continue
            
        lang_code = locale_file.stem
        
        try:
            section_path = f'starter_files.web.locales.{lang_code}'
            section = import_module(section_path)
            
            # Создаем запись языка с обязательными полями
            languages[lang_code] = {
                'this_language': section.translations.get('common', {}).get('this_language', lang_code),
                'this_language_code': section.translations.get('common', {}).get('this_language_code', lang_code),
                'translations': section.translations  # Полные данные переводов
            }
        except ImportError as e:
            logger.info(f"Ошибка импорта {lang_code}: {str(e)}")
            continue
    
    _AVAILABLE_LANGUAGES = languages
    return _AVAILABLE_LANGUAGES

def t(key: str, _section=None, _file=None, **kwargs) -> str:
    current_lang = os.getenv('LANGUAGE', 'en').lower()
    lang_data = get_available_languages().get(current_lang, {}).get('translations', {})

    # Получаем логгер (например, глобально или создайте локально)
    global logger
    
    # Если явно не переданы, пытаемся получить из глобального контекста Flask
    if _section is None:
        _section = getattr(g, 'current_section', None)
    if _file is None:
        _file = getattr(g, 'current_function', None)

    # Пытаемся определить путь шаблона для отладочной информации
    frame = inspect.currentframe().f_back
    template_path = None
    if frame:
        if '__file__' in frame.f_globals:
            template_path = Path(frame.f_globals['__file__'])
        elif '__file__' in frame.f_locals:
            template_path = Path(frame.f_locals['__file__'])
        if template_path:
            try:
                template_path = template_path.relative_to(Path.cwd())
            except ValueError:
                pass
    caller_info = f" (called from: {template_path}:{frame.f_lineno})" if (template_path and frame) else ''

    try:
        # common
        if 'common' in lang_data and key in lang_data['common']:
            return lang_data['common'][key].format(**kwargs)

        # sections
        if _section and _file:
            sections = lang_data.get('sections', {})
            if _section in sections:
                if _file in sections[_section]:
                    if key in sections[_section][_file]:
                        return sections[_section][_file][key].format(**kwargs)
                    else:
                        error_msg = f"NOT FOUND TRANSLATE [{current_lang}][sections][{_section}][{_file}][{key}]"
                        logger.warning(error_msg)
                        return error_msg
                else:
                    error_msg = f"NOT FOUND TRANSLATE [{current_lang}][sections][{_section}][{_file}]"
                    logger.warning(error_msg)
                    return error_msg
            else:
                error_msg = f"NOT FOUND TRANSLATE [{current_lang}][sections][{_section}]"
                logger.warning(error_msg)
                return error_msg

        # main
        parts = key.split('_', 1)
        if len(parts) == 2:
            section, sub_key = parts
            if 'main' in lang_data and section in lang_data['main']:
                if sub_key in lang_data['main'][section]:
                    return lang_data['main'][section][sub_key].format(**kwargs)
                else:
                    error_msg = f"NOT FOUND TRANSLATE [{current_lang}][main][{section}][{sub_key}]"
                    logger.warning(error_msg)
                    return error_msg
            else:
                error_msg = f"NOT FOUND TRANSLATE [{current_lang}][main][{section}]"
                logger.warning(error_msg)
                return error_msg

        error_msg = f"NOT FOUND TRANSLATE [{current_lang}][unknown][{key}]"
        logger.warning(error_msg)
        return error_msg

    finally:
        if frame:
            del frame

def return_basic(section_slug: str, field: str, default: str = None) -> str:
    """
    Получает базовую информацию о модуле из translations['sections'][section_slug]['basic']
    
    :param section_slug: техническое имя модуля (имя файла)
    :param field: поле для получения (title, description и т.д.)
    :param default: значение по умолчанию, если поле не найдено
    :return: значение поля или default
    """
    current_lang = os.getenv('LANGUAGE', 'en').lower()
    lang_data = get_available_languages().get(current_lang, {}).get('translations', {})
    
    # Прямой доступ к translations['sections'][section_slug]['basic'][field]
    value = lang_data.get('sections', {}).get(section_slug, {}).get('basic', {}).get(field)
    
    if value is not None:
        return value
    return default