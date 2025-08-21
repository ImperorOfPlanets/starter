import json
from flask import render_template, jsonify, request
from starter_files.core.utils.loader_utils import get

this_section_in_control_panel = True
section_icon = "bi-shield"
section_name = "Firewall"
section_order = 4

# ======================== РОУТЫ ==================================================
def index(data, session):
    """Главная функция модуля firewall, возвращает HTML с обзором"""
    firewall_info = get('firewall', 'get_firewall_info') or {}
    return render_template(
        'sections/firewall/index.html',
        firewall_info=firewall_info
    )

def open_ports(data, session):
    """Функция модуля firewall, возвращает HTML с открытыми портами"""
    firewall_info = get('firewall', 'get_firewall_info') or {}
    return render_template(
        'sections/firewall/open_ports.html',
        firewall_info=firewall_info
    )

def listening_ports(data, session):
    """Функция модуля firewall, возвращает HTML с прослушивающими портами"""
    listening_ports = get('firewall', 'get_listening_ports') or []
    return render_template(
        'sections/firewall/listening_ports.html',
        listening_ports=listening_ports
    )

def rules(data, session):
    """Функция модуля firewall, возвращает HTML с правилами"""
    rules = get('firewall', 'get_rules') or []
    return render_template(
        'sections/firewall/rules.html',
        rules=rules
    )

def actions(data, session):
    """Функция модуля firewall, возвращает HTML с действиями"""
    return render_template('sections/firewall/actions.html')

# ======================== API-КОНТРОЛЛЕРЫ ========================================
def open_port(data, session):
    """Открытие порта в фаерволе"""
    port = data.get('port')
    protocol = data.get('protocol')
    service = data.get('service', '')
    
    if not port or not protocol:
        return {'status': 'error', 'message': 'Missing parameters'}
    
    result = get('firewall', 'open_port', {
        'port': port,
        'protocol': protocol,
        'service': service
    }) or {'status': 'error', 'message': 'Unknown error'}
    
    return result

def close_port(data, session):
    """Закрытие порта в фаерволе"""
    port = data.get('port')
    protocol = data.get('protocol')
    
    if not port or not protocol:
        return {'status': 'error', 'message': 'Missing parameters'}
    
    result = get('firewall', 'close_port', {
        'port': port,
        'protocol': protocol
    }) or {'status': 'error', 'message': 'Unknown error'}
    
    return result

def restart_firewall(data, session):
    """Перезапуск фаервола"""
    result = get('firewall', 'restart_firewall') or {'status': 'error', 'message': 'Unknown error'}
    return result

def flush_rules(data, session):
    """Сброс правил фаервола"""
    result = get('firewall', 'flush_rules') or {'status': 'error', 'message': 'Unknown error'}
    return result

def save_rules(data, session):
    """Сохранение правил фаервола"""
    result = get('firewall', 'save_rules') or {'status': 'error', 'message': 'Unknown error'}
    return result

def block_all_ports(data, session):
    """Блокировка всех портов"""
    result = get('firewall', 'block_all_ports') or {'status': 'error', 'message': 'Unknown error'}
    return result