import os

from flask import Blueprint, current_app, g, jsonify, render_template, request, session
from importlib import import_module
from pathlib import Path

from starter_files.utils.i18n import get_available_languages, t, set_language, get_current_language, return_basic
from starter_files.utils.logger import get_logger

routes = Blueprint('routes', __name__)

# Функция получения модулей для панель управления
def get_current_modules_in_panel():
    modules_in_control_panel = []
    modules_dir = Path(__file__).parent / 'modules'
    
    for module_file in modules_dir.glob('*.py'):
        if module_file.stem == '__init__':
            continue
            
        module_slug = module_file.stem

        try:
            module = import_module(f'starter_files.web.modules.{module_slug}')
            
            if getattr(module, 'this_module_in_control_panel', False):
                # Получаем мета-информацию через функцию t()
                module_title = t(f'modules.{module_slug}.basic.title', default=getattr(module, 'module_name', module_slug.replace('_', ' ').title()))

                module_info = {
                    'module_slug': module_slug,
                    'module_name': return_basic(module_slug, 'title', getattr(module, 'module_name', module_slug.replace('_', ' ').title())),
                    'module_icon': getattr(module, 'module_icon', 'bi-box'),
                    'module_order': getattr(module, 'module_order', 99)
                }
                modules_in_control_panel.append(module_info)
                
        except Exception as e:
            print(f"Error loading module {module_slug}: {str(e)}")
    
    return sorted(modules_in_control_panel, key=lambda x: x['module_order'])

@routes.context_processor
def inject_variables():
    return {
        'languages': get_available_languages(),
        'current_language': get_current_language(),
        'modules_in_control_panel': get_current_modules_in_panel()
    }

@routes.route('/', methods=['GET'])
def index():
    try:
        # Получаем текущий язык
        lang = get_current_language()
        # Устанавливаем текущий язык
        set_language(lang)
        # Получаем список доступных языков
        languages = get_available_languages()
        
        return render_template('index.html', current_language=lang, languages=languages, t=t, logged_in='username' in session)
    except Exception as e:
        current_app.logger.exception("Критическая ошибка рендеринга шаблона index.html")
        return render_template('error.html', error_message="Внутренняя ошибка сервера", error_details=str(e)), 500

@routes.route('/', methods=['POST'])
def handle_modules():
    module_name = request.form.get('module')
    action_name = request.form.get('action')
    
    if not module_name or not action_name:
        return jsonify({'status': 'error', 'message': 'Module and action required'}), 400
    
    # Сохраняем в глобальном контексте, чтобы функция t() могла определить модуль и файл
    g.current_module = module_name
    g.current_function = action_name
    
    try:
        module = import_module(f'starter_files.web.modules.{module_name}')
        
        if not hasattr(module, action_name):
            return jsonify({'status': 'error', 'message': 'Action not found'}), 404
        
        data = {k: v for k, v in request.form.items() if k not in ['module', 'action']}
        result = getattr(module, action_name)(data, session)
        
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