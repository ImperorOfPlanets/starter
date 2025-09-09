import platform
from flask import render_template, jsonify, request
from typing import Dict, Any, List, Tuple
from dataclasses import asdict

from starter_files.core.utils.i18n_utils import t
from starter_files.core.utils.log_utils import LogManager
from starter_files.core.oss.default.network import NetworkModule

logger = LogManager.get_logger()

this_section_in_control_panel = True
section_icon = "bi-diagram-3"
section_name = "Network"
section_order = 2

def index(data: Dict[str, Any], session: Dict[str, Any]):
    """Главная страница модуля - всегда возвращает HTML"""
    try:
        # Получаем устройства используя доступные утилиты
        physical_devices, virtual_devices = NetworkModule.get_network_devices_with_tools()
        
        # Получаем список доступных сетевых утилит
        available_tools = NetworkModule.detect_available_network_tools()
        
        # Всегда возвращаем HTML, игнорируя Accept header
        html_content = render_template(
            'sections/network/index.html',
            physical_devices=physical_devices,
            virtual_devices=virtual_devices,
            available_tools=available_tools,
            current_device=None,
            t=t
        )
        
        return html_content
        
    except Exception as e:
        logger.error(f"Error in network index: {str(e)}")
        error_html = render_template(
            'error.html',
            error_message="Ошибка при загрузке сетевых устройств",
            error_details=str(e)
        )
        return error_html

def get_device_details(data: Dict[str, Any], session: Dict[str, Any]):
    """Получение полной информации об устройстве - возвращает HTML"""
    try:
        device_name = data.get('device_name')
        if not device_name:
            return "<div class='alert alert-danger'>Не указано имя устройства</div>"

        physical_devices, virtual_devices = NetworkModule.get_network_devices_with_tools()
        all_devices = physical_devices + virtual_devices
        
        device = next((d for d in all_devices if d.name == device_name), None)
        
        if not device:
            return "<div class='alert alert-danger'>Устройство не найдено</div>"
        
        # Возвращаем чистый HTML
        return render_template('sections/network/device.html', device=device, t=t)
        
    except Exception as e:
        logger.error(f"Error getting device details: {str(e)}")
        return f"<div class='alert alert-danger'>Ошибка: {str(e)}</div>"

def get_network_tools(data: Dict[str, Any], session: Dict[str, Any]):
    """Возвращает информацию о доступных сетевых утилитах - JSON"""
    try:
        available_tools = NetworkModule.detect_available_network_tools()
        
        return jsonify({
            'status': 'success',
            'tools': available_tools
        })
        
    except Exception as e:
        logger.error(f"Error getting network tools: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

def refresh_network(data: Dict[str, Any], session: Dict[str, Any]):
    """Обновляет сетевую информацию - JSON"""
    try:
        # Принудительно обновляем информацию
        physical_devices, virtual_devices = NetworkModule.get_network_devices_with_tools()
        available_tools = NetworkModule.detect_available_network_tools()
        
        # Конвертируем устройства в dict для JSON
        physical_dicts = [asdict(device) for device in physical_devices]
        virtual_dicts = [asdict(device) for device in virtual_devices]
        
        return jsonify({
            'status': 'success',
            'physical_devices': physical_dicts,
            'virtual_devices': virtual_dicts,
            'available_tools': available_tools,
            'message': 'Network information refreshed'
        })
        
    except Exception as e:
        logger.error(f"Error refreshing network: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        })