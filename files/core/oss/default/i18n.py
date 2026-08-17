"""
Модуль интернационализации
"""

import inspect
import os
import sys
from importlib import import_module
from pathlib import Path
from flask import g

from files.core.base_module import BaseModule
from files.core.utils.globalVars_utils import get_global, set_global
from files.core.utils.log_utils import LogManager

logger = LogManager.get_logger('i18n')

# Глобальная переменная для кеширования языков
_AVAILABLE_LANGUAGES = None


class I18nModule(BaseModule):
    """Модуль интернационализации"""
    
    @staticmethod
    def check() -> bool:
        return True
    
    @staticmethod
    def set_globals():
        """Устанавливает глобальные переменные"""
        starter_path = get_global('starter_path')
        if starter_path:
            locales_dir = starter_path / 'files' / 'web' / 'locales'
            set_global('locales_dir', locales_dir)
            # Регистрируем директорию для логов переводов
            LogManager.register_log_dir('translations', 'translations')
            logger.debug(f"Locales directory set to: {locales_dir}")
    
    @staticmethod
    def get_current_language() -> str:
        """Возвращает текущий язык из .env"""
        env_path = get_global('starter_env_path')
        if env_path and env_path.exists():
            try:
                with open(env_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.startswith('LANGUAGE='):
                            return line.strip().split('=', 1)[1].strip()
            except Exception as e:
                logger.error(f"Error reading LANGUAGE from .env: {e}")
        return 'en'
    
    @staticmethod
    def set_language(lang_code: str):
        """Устанавливает язык в переменных окружения"""
        os.environ['LANGUAGE'] = lang_code.lower()
        logger.info(f"Language set to: {lang_code}")
    
    @staticmethod
    def get_available_languages(force_reload=False) -> dict:
        """Возвращает словарь доступных языков"""
        global _AVAILABLE_LANGUAGES
        
        if _AVAILABLE_LANGUAGES is not None and not force_reload:
            return _AVAILABLE_LANGUAGES
        
        locales_dir = get_global('locales_dir')
        if not locales_dir or not locales_dir.exists():
            logger.warning(f"Locales directory not found: {locales_dir}")
            return {}
        
        languages = {}
        for locale_file in locales_dir.glob('*.py'):
            if locale_file.stem == '__init__':
                continue
            
            lang_code = locale_file.stem
            
            try:
                # Динамический импорт модуля перевода
                import importlib.util
                spec = importlib.util.spec_from_file_location(
                    f"files.web.locales.{lang_code}",
                    str(locale_file)
                )
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[spec.name] = module
                    spec.loader.exec_module(module)
                    
                    languages[lang_code] = {
                        'this_language': getattr(module, 'translations', {}).get('common', {}).get('this_language', lang_code),
                        'this_language_code': getattr(module, 'translations', {}).get('common', {}).get('this_language_code', lang_code),
                        'translations': getattr(module, 'translations', {})
                    }
                    logger.debug(f"Loaded language: {lang_code}")
            except Exception as e:
                logger.warning(f"Error loading language {lang_code}: {e}")
                continue
        
        _AVAILABLE_LANGUAGES = languages
        logger.info(f"Loaded {len(languages)} languages")
        return languages
    
    @staticmethod
    def translate(key: str, _section=None, _file=None, **kwargs) -> str:
        """Переводит ключ на текущий язык"""
        current_lang = os.getenv('LANGUAGE', 'en').lower()
        lang_data = I18nModule.get_available_languages().get(current_lang, {}).get('translations', {})
        
        # Если явно не переданы, пытаемся получить из глобального контекста Flask
        if _section is None:
            _section = getattr(g, 'current_section', None)
        if _file is None:
            _file = getattr(g, 'current_function', None)
        
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
            
            # main
            parts = key.split('_', 1)
            if len(parts) == 2:
                section, sub_key = parts
                if 'main' in lang_data and section in lang_data['main']:
                    if sub_key in lang_data['main'][section]:
                        return lang_data['main'][section][sub_key].format(**kwargs)
            
            if _AVAILABLE_LANGUAGES is None:
                # Если языки еще не загружены, возвращаем ключ
                return key
            
            logger.debug(f"Translation not found: {key}")
            return f"NOT FOUND: {key}"
            
        except Exception as e:
            logger.warning(f"Translation error for {key}: {e}")
            return key
    
    @staticmethod
    def return_basic(section_slug: str, field: str, default: str = None) -> str:
        """Получает базовую информацию о модуле"""
        current_lang = os.getenv('LANGUAGE', 'en').lower()
        lang_data = I18nModule.get_available_languages().get(current_lang, {}).get('translations', {})
        
        value = lang_data.get('sections', {}).get(section_slug, {}).get('basic', {}).get(field)
        return value if value is not None else default


# Алиасы для обратной совместимости
def t(key: str, _section=None, _file=None, **kwargs) -> str:
    return I18nModule.translate(key, _section, _file, **kwargs)