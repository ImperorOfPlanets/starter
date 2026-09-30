# files/web/sections/applications.py
import requests
from flask import render_template, jsonify, session

from files.core.utils.globalVars_utils import get_global
from files.core.utils.loader_utils import get
from files.core.utils.log_utils import LogManager

logger = LogManager.get_logger()

this_section_in_control_panel = True
section_icon = "bi-clipboard-list"
section_name = "Applications"
section_order = 5


def t(key: str, **kwargs) -> str:
    i18n = get('i18n')
    if i18n and hasattr(i18n, 'translate'):
        return i18n.translate(key, **kwargs)
    return key


def get_myidon_url() -> str:
    return get_global('myidon_url', 'https://myidon.site')


def get_oauth_token() -> str:
    """Получаем OAuth токен из сессии или из глобальных переменных"""
    token = session.get('oauth_token')
    if token:
        return token
    
    # Пытаемся получить из глобальных переменных
    oauth_module = get('oauth')
    if oauth_module and hasattr(oauth_module, 'get_access_token'):
        return oauth_module.get_access_token()
    
    return None


def fetch_user_applications() -> list:
    """Получаем одобренные заявки пользователя с myidon.site"""
    myidon_url = get_myidon_url()
    token = get_oauth_token()
    
    if not token:
        logger.warning("No OAuth token available for fetching applications")
        return []
    
    try:
        response = requests.get(
            f"{myidon_url}/api/user/applications",
            headers={
                'Authorization': f'Bearer {token}',
                'Accept': 'application/json'
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get('applications', [])
        else:
            logger.error(f"Failed to fetch applications: {response.status_code} - {response.text}")
            return []
            
    except Exception as e:
        logger.error(f"Error fetching applications: {e}", exc_info=True)
        return []


def index(data, session):
    """Главная страница раздела Заявки"""
    applications = fetch_user_applications()
    
    # Обогащаем данные для отображения
    for app in applications:
        app['type_display'] = get_type_display(app.get('type', ''))
        app['status_display'] = get_status_display(app.get('status', ''))
        app['data_display'] = format_application_data(app)
    
    return render_template(
        'sections/applications/index.html',
        applications=applications,
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


def refresh(data, session):
    """Обновляет список заявок"""
    applications = fetch_user_applications()
    return jsonify({
        'status': 'success',
        'count': len(applications),
        'applications': applications
    })
