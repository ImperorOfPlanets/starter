from flask import Blueprint, current_app, g, jsonify, render_template, request, session, Response, redirect, url_for
from importlib import import_module
from pathlib import Path
from typing import List, Dict, Any

from files.core.utils.globalVars_utils import get_global
from files.core.utils.log_utils import LogManager
from files.core.utils.loader_utils import get, collect_modules_info

logger = LogManager.get_logger()

routes = Blueprint('routes', __name__)

# Для раздела разработчикам
def get_modules_index(refresh: bool = False) -> List[Dict[str, Any]]:
    return collect_modules_info(refresh=refresh)

# Функция получения секций для панель управления
def get_current_sections_in_panel():
    sections_in_control_panel = []
    groups = {}
    group_order = {}
    
    starter_path = get_global('starter_path')
    sections_dir = starter_path / 'files' / 'web' / 'sections'
    
    if not sections_dir.exists():
        logger.error(f"Sections directory not found: {sections_dir}")
        return [], {}
    
    for section_file in sections_dir.glob('*.py'):
        if section_file.stem == '__init__':
            continue
            
        section_slug = section_file.stem

        try:
            section = import_module(f'files.web.sections.{section_slug}')
            
            if getattr(section, 'this_section_in_control_panel', False):
                i18n = get('i18n')
                section_name = None
                
                if i18n:
                    # Ищем перевод в sections.dashboard.basic.title и т.д.
                    section_name = i18n.return_basic(section_slug, 'title')
                
                if section_name is None:
                    section_name = getattr(section, 'section_name', section_slug.replace('_', ' ').title())

                section_info = {
                    'section_slug': section_slug,
                    'section_name': section_name,
                    'section_icon': getattr(section, 'section_icon', 'bi-box'),
                    'section_order': getattr(section, 'section_order', 99),
                    'section_group': getattr(section, 'section_group', None),
                    'section_group_name': getattr(section, 'section_group_name', None),
                    'section_group_icon': getattr(section, 'section_group_icon', 'bi-folder'),
                }
                
                grp = section_info['section_group']
                if grp:
                    if grp not in groups:
                        # Ищем перевод для группы в sections.{grp}.basic.title
                        group_name = section_info['section_group_name'] or grp.title()
                        if i18n:
                            translated = i18n.return_basic(grp, 'title')
                            if translated:
                                group_name = translated
                        
                        groups[grp] = {
                            'group_slug': grp,
                            'group_name': group_name,
                            'group_icon': section_info['section_group_icon'],
                            'sections': [],
                            'order': section_info['section_order']
                        }
                    groups[grp]['sections'].append(section_info)
                    section_info['_group'] = grp
                else:
                    sections_in_control_panel.append(section_info)
                
        except Exception as e:
            logger.error(f"Error loading section {section_slug}: {e}", exc_info=True)
            continue
    
    # Sort non-grouped sections
    sections_in_control_panel.sort(key=lambda x: x['section_order'])
    
    # Sort sections within each group
    for grp_key in groups:
        groups[grp_key]['sections'].sort(key=lambda x: x['section_order'])
    
    # Sort groups by their first section's order
    sorted_groups = dict(sorted(groups.items(), key=lambda item: item[1]['order']))
    
    logger.info(f"Total sections: {len(sections_in_control_panel)}, groups: {len(sorted_groups)}")
    return sections_in_control_panel, sorted_groups

@routes.context_processor
def inject_variables():
    i18n = get('i18n')
    if i18n:
        languages = i18n.get_available_languages()
        current_language = i18n.get_current_language()
        t = i18n.translate
    else:
        languages = {}
        current_language = 'en'
        t = lambda key, **kwargs: key
    
    # ========== ГЕНЕРАЦИЯ ССЫЛКИ ДЛЯ MYIDON ==========
    myidon_auth_url = '#'
    try:
        oauth_module = get('oauth')
        if oauth_module and hasattr(oauth_module, 'is_configured') and oauth_module.is_configured():
            myidon_auth_url = oauth_module.get_authorization_url()
            logger.debug(f"MyIDon auth URL generated: {myidon_auth_url}")
        else:
            logger.warning("OAuth not configured, myidon_auth_url set to '#'")
    except Exception as e:
        logger.error(f"Error generating MyIDon auth URL: {e}")
    
    sections_list, sections_groups = get_current_sections_in_panel()
    
    return {
        'languages': languages,
        'current_language': current_language,
        'sections_in_control_panel': sections_list,
        'sections_groups': sections_groups,
        't': t,
        'myidon_auth_url': myidon_auth_url
    }

@routes.route('/', methods=['GET'])
def index():
    i18n = get('i18n')
    if i18n:
        lang = i18n.get_current_language()
        i18n.set_language(lang)
        languages = i18n.get_available_languages()
        t = i18n.translate
    else:
        lang = 'en'
        languages = {}
        t = lambda key, **kwargs: key
    
    return render_template('index.html', current_language=lang, languages=languages, t=t, logged_in='username' in session)

@routes.route('/', methods=['POST'])
def handle_sections():
    section_name = request.form.get('section')
    action_name = request.form.get('action')
    
    logger.info(f"=== HANDLE SECTIONS ===")
    logger.info(f"Section: {section_name}, Action: {action_name}")
    logger.info(f"Session logged_in: {session.get('logged_in', False)}")
    logger.info(f"Form data: {dict(request.form)}")
    
    if not section_name or not action_name:
        return jsonify({'status': 'error', 'message': 'Section and action required'}), 400
    
    # Сохраняем в глобальном контексте
    g.current_section = section_name
    g.current_function = action_name
    
    try:
        # Пытаемся импортировать модуль
        module_path = f'files.web.sections.{section_name}'
        logger.info(f"Attempting to import: {module_path}")
        
        section = import_module(module_path)
        logger.info(f"Module imported successfully: {section}")
        
        # Проверяем наличие функции
        if not hasattr(section, action_name):
            logger.error(f"Function '{action_name}' not found in module {section_name}")
            logger.info(f"Available functions in {section_name}: {[x for x in dir(section) if not x.startswith('_')]}")
            return jsonify({'status': 'error', 'message': f'Action {action_name} not found in {section_name}'}), 404
        
        data = {k: v for k, v in request.form.items() if k not in ['section', 'action']}
        logger.info(f"Calling {section_name}.{action_name} with data: {data}")
        
        # Вызываем функцию с обработкой ошибок
        try:
            result = getattr(section, action_name)(data, session)
            logger.info(f"Function returned, result type: {type(result)}")
            
            # Если результат - строка, выводим первые 200 символов для отладки
            if isinstance(result, str):
                logger.info(f"Result preview: {result[:200]}...")
            
        except Exception as call_error:
            logger.error(f"Error calling {section_name}.{action_name}: {call_error}", exc_info=True)
            import traceback
            logger.error(traceback.format_exc())
            # Всегда возвращаем JSON при ошибках
            return jsonify({'status': 'error', 'message': f'{type(call_error).__name__}: {str(call_error)}'}), 500

        if isinstance(result, Response):
            return result

        if 'text/html' in request.accept_mimetypes:
            if isinstance(result, str):
                return result
            elif isinstance(result, dict) and 'html' in result:
                return result['html']
            else:
                logger.error(f"HTML response not available, result type: {type(result)}")
                return jsonify({'status': 'error', 'message': 'HTML response not available'}), 406
        else:
            return jsonify(result)
        
    except ImportError as e:
        logger.error(f"Import error for section '{section_name}': {str(e)}", exc_info=True)
        import traceback
        logger.error(traceback.format_exc())
        # Всегда возвращаем JSON
        return jsonify({'status': 'error', 'message': f'Import error: {str(e)}'}), 500
        
    except Exception as e:
        logger.error(f"Error in section '{section_name}.{action_name}': {str(e)}", exc_info=True)
        import traceback
        logger.error(traceback.format_exc())
        # Всегда возвращаем JSON
        return jsonify({'status': 'error', 'message': f'{type(e).__name__}: {str(e)}'}), 500


# ============================================================================
# OAuth CALLBACK МАРШРУТ
# ============================================================================

@routes.route('/oauth/callback', methods=['GET'])
def oauth_callback():
    """
    Обработчик callback от MyIDon после OAuth авторизации.
    Принимает code и state из URL, передает их в auth модуль для обработки.
    """
    logger.info("=== OAUTH CALLBACK ROUTE ===")
    
    # Получаем параметры из URL
    code = request.args.get('code')
    state = request.args.get('state')
    error = request.args.get('error')
    
    logger.info(f"Code: {code[:20] if code else 'None'}...")
    logger.info(f"State: {state[:20] if state else 'None'}...")
    logger.info(f"Error: {error}")
    
    # Если есть ошибка от провайдера
    if error:
        logger.error(f"OAuth error from provider: {error}")
        return redirect(url_for('routes.index'))
    
    # Если нет code - ошибка
    if not code:
        logger.error("No code in OAuth callback")
        return redirect(url_for('routes.index'))
    
    # Получаем модуль auth
    try:
        from files.web.sections.auth import oauth_callback as auth_oauth_callback
    except ImportError:
        logger.error("Auth module not found!")
        return "Auth module not available", 500

    # Вызываем обработчик
    try:
        result = auth_oauth_callback({
            'code': code,
            'state': state,
            'error': error
        }, session)

        logger.info(f"OAuth callback result: {result}")

        if result.get('status') == 'success':
            redirect_url = result.get('redirect', url_for('routes.index'))
            logger.info(f"Redirecting to: {redirect_url}")
            return redirect(redirect_url)
        else:
            error_msg = result.get('message', 'Unknown error')
            logger.error(f"OAuth callback error: {error_msg}")
            return redirect(url_for('routes.index'))

    except Exception as e:
        logger.error(f"Error in OAuth callback route: {e}", exc_info=True)
        return redirect(url_for('routes.index'))


# ============================================================================
# VPN API МАРШРУТЫ
# ============================================================================

@routes.route('/api/vpn/request', methods=['POST'])
def vpn_request():
    from files.core.utils.loader_utils import get as module_get
    data = request.get_json(force=True, silent=True) or {}
    login_server = data.get('login_server') or get_global('headscale_login_server', '')
    auth_key = data.get('auth_key')

    if not login_server:
        return jsonify({'status': 'error', 'message': 'HEADSCALE_LOGIN_SERVER not configured'})

    try:
        result = module_get('tailscale', 'connect_tailscale', login_server, auth_key)
        return jsonify(result)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})


@routes.route('/api/vpn/disconnect', methods=['POST'])
def vpn_disconnect():
    from files.core.utils.loader_utils import get as module_get
    try:
        result = module_get('tailscale', 'disconnect_tailscale')
        return jsonify(result)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})


@routes.route('/api/vpn/status', methods=['POST'])
def vpn_status():
    from files.core.utils.loader_utils import get as module_get
    try:
        status = module_get('tailscale', 'get_tailscale_status')
        return jsonify(status)
    except Exception as e:
        return jsonify({'connected': False, 'status_text': 'Error', 'ip': None,
                        'hostname': None, 'version': None, 'backend_state': None})