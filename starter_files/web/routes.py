import os
import sys

from flask import Blueprint, current_app, g, jsonify, render_template, request, session, Response
from importlib import import_module
from pathlib import Path

from starter_files.utils.i18n_utils import get_available_languages, t, set_language, get_current_language, return_basic
from starter_files.utils.globalVars_utils import get_global
from starter_files.utils.log_utils import get_logger

routes = Blueprint('routes', __name__)

# Функция получения модулей для панель управления
def get_current_sections_in_panel():
    sections_in_control_panel = []
    
    starter_path = get_global('script_path')

    sections_dir = starter_path / 'starter_files' / 'web' / 'sections'
    
    for section_file in sections_dir.glob('*.py'):
        if section_file.stem == '__init__':
            continue
            
        section_slug = section_file.stem

        try:
            section = import_module(f'starter_files.web.sections.{section_slug}')
            
            if getattr(section, 'this_section_in_control_panel', False):
                # Получаем мета-информацию через функцию t()
                section_title = t(f'sections.{section_slug}.basic.title', default=getattr(section, 'section_name', section_slug.replace('_', ' ').title()))

                section_info = {
                    'section_slug': section_slug,
                    'section_name': return_basic(section_slug, 'title', getattr(section, 'section_name', section_slug.replace('_', ' ').title())),
                    'section_icon': getattr(section, 'section_icon', 'bi-box'),
                    'section_order': getattr(section, 'section_order', 99)
                }
                sections_in_control_panel.append(section_info)
                
        except Exception as e:
            print(f"Error loading section {section_slug}: {str(e)}")
    
    return sorted(sections_in_control_panel, key=lambda x: x['section_order'])

@routes.context_processor
def inject_variables():
    return {
        'languages': get_available_languages(),
        'current_language': get_current_language(),
        'sections_in_control_panel': get_current_sections_in_panel()
    }

@routes.route('/', methods=['GET'])
def index():

    # Получаем текущий язык
    lang = get_current_language()
    # Устанавливаем текущий язык
    set_language(lang)
    # Получаем список доступных языков
    languages = get_available_languages()
    
    return render_template('index.html', current_language=lang, languages=languages, t=t, logged_in='username' in session)

@routes.route('/', methods=['POST'])
def handle_sections():
    section_name = request.form.get('section')
    action_name = request.form.get('action')
    
    if not section_name or not action_name:
        return jsonify({'status': 'error', 'message': 'Section and action required'}), 400
    
    # Сохраняем в глобальном контексте, чтобы функция t() могла определить модуль и файл
    g.current_section = section_name
    g.current_function = action_name
    
    try:
        section = import_module(f'starter_files.web.sections.{section_name}')
        
        if not hasattr(section, action_name):
            return jsonify({'status': 'error', 'message': 'Action not found'}), 404
        
        data = {k: v for k, v in request.form.items() if k not in ['section', 'action']}
        result = getattr(section, action_name)(data, session)

        # Добавленная проверка типа результата
        if isinstance(result, Response):
            return result  # Возвращаем Response как есть

        # Обработка результата с учётом Accept заголовка
        if 'text/html' in request.accept_mimetypes:
            if isinstance(result, str):
                return result
            elif isinstance(result, dict) and 'html' in result:
                return result['html']
            else:
                return jsonify({'status': 'error', 'message': 'HTML response not available'}), 406
        else:
            return jsonify(result)
        
    except Exception as e:
        if 'text/html' in request.accept_mimetypes:
            return f"Error: {str(e)}", 500
        return jsonify({'status': 'error', 'message': str(e)}), 500