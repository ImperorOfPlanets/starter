# files/web/sections/applications.py
"""
Веб-секция для отображения заявок пользователя
Использует модуль ApplicationsModule из ядра
"""

from flask import render_template, jsonify

from files.core.utils.loader_utils import get
from files.core.utils.log_utils import LogManager

logger = LogManager.get_logger()

this_section_in_control_panel = True
section_icon = "bi-clipboard"
section_name = "Applications"
section_order = 5


def t(key: str, **kwargs) -> str:
    i18n = get('i18n')
    if i18n and hasattr(i18n, 'translate'):
        return i18n.translate(key, **kwargs)
    return key


def index(data, session_obj):
    """Главная страница раздела Заявки"""
    # Проверяем авторизацию через сессию (как servers.py)
    oauth_token = session_obj.get('oauth_token')
    
    if not oauth_token:
        return render_template(
            'sections/applications/index.html',
            applications=[],
            oauth_required=True,
            t=t
        )
    
    # Получаем заявки из сессии (как servers.py)
    user_applications = session_obj.get('user_applications', [])
    
    # Обогащаем данные для отображения
    for app in user_applications:
        app['type_display'] = get_type_display(app.get('type', ''))
        app['status_display'] = get_status_display(app.get('status', ''))
        app['data_display'] = format_application_data(app)
    
    return render_template(
        'sections/applications/index.html',
        applications=user_applications,
        oauth_required=False,
        t=t
    )


def get_type_display(app_type: str) -> str:
    """Возвращает читаемое название типа заявки"""
    type_names = {
        'server_type': t('application_type_server'),
        'tailscale': t('application_type_tailscale'),
        'starter': t('application_type_starter'),
        'personal': t('application_type_personal'),
        'business': t('application_type_business'),
        'city': t('application_type_city'),
        'callback': t('application_type_callback'),
        'websocket': t('application_type_websocket'),
        'vk_callback': t('application_type_vk_callback'),
        'wecom': t('application_type_wecom'),
        'telegram_bot': t('application_type_telegram_bot'),
    }
    return type_names.get(app_type, app_type.replace('_', ' ').title())


def get_status_display(status: str) -> str:
    """Возвращает читаемое название статуса"""
    status_names = {
        'draft': t('status_draft'),
        'submitted': t('status_submitted'),
        'in_review': t('status_in_review'),
        'approved': t('status_approved'),
        'rejected': t('status_rejected'),
        'cancelled': t('status_cancelled'),
    }
    return status_names.get(status, status.replace('_', ' ').title())


def format_application_data(app: dict) -> dict:
    """Форматирует данные заявки для отображения"""
    app_data = app.get('data', {})
    result = {}
    
    if app.get('type') == 'server_type':
        result['name'] = app_data.get('repository_name', '-')
        result['description'] = app_data.get('repository_description', '-')
        result['type_key'] = app_data.get('repository_type_key', '-')
        result['expected_users'] = app_data.get('expected_users', '-')
    elif app.get('type') == 'tailscale':
        result['name'] = t('vpn_access')
        result['description'] = app_data.get('network_description', '-')
        result['devices_count'] = app_data.get('devices_count', '-')
        result['vpn_purpose'] = app_data.get('vpn_purpose', '-')
    elif app.get('type') == 'starter':
        result['name'] = app_data.get('company_name', '-')
        result['description'] = app_data.get('project_description', '-')
        result['purpose'] = app_data.get('repository_purpose', '-')
    else:
        result['name'] = app_data.get('company_name', app_data.get('full_name', '-'))
        result['description'] = app_data.get('business_description', app_data.get('personal_purpose', '-'))
    
    # Добавляем Tailscale информацию если есть
    tailscale = app.get('tailscale')
    if tailscale:
        result['tailscale_ip'] = tailscale.get('tailscale_ip', '-')
        result['tailscale_status'] = tailscale.get('status', '-')
    
    # Добавляем OAuth информацию если есть
    oauth_client = app.get('oauth_client')
    if oauth_client:
        result['oauth_client_id'] = oauth_client.get('id', '-')
    
    return result


def refresh(data, session_obj):
    """Обновляет список заявок через API"""
    applications_module = get('applications')
    
    if not applications_module:
        return jsonify({'status': 'error', 'message': 'Module not found'})
    
    oauth_token = session_obj.get('oauth_token')
    if not oauth_token:
        return jsonify({'status': 'error', 'message': 'Not authenticated'})
    
    # Устанавливаем токен в модуль и обновляем заявки
    applications_module.set_access_token(oauth_token)
    applications = applications_module.refresh_applications()
    
    # Обновляем заявки в сессии
    session_obj['user_applications'] = applications
    
    return jsonify({
        'status': 'success',
        'count': len(applications),
        'applications': applications
    })
