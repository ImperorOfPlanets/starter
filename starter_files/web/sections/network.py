import platform
from flask import render_template, jsonify
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass

from starter_files.core.i18n_utils import t
from starter_files.core.log_utils import LogManager
logger = LogManager.get_logger()

this_section_in_control_panel = True
section_icon = "bi-diagram-3"
section_name = "Network"
section_order = 2

def index(data: Dict[str, Any], session: Dict[str, Any]):
    """Главная страница модуля с минимальными данными"""
    try:
        physical_devices, virtual_devices = get_basic_devices_info()
        
        return render_template(
            'sections/network/index.html',
            physical_devices=physical_devices,
            virtual_devices=virtual_devices,
            current_device=None,
            t=t
        )
    except Exception as e:
        logger.error(f"Error in network index: {str(e)}")
        return render_template(
            'error.html',
            error_message="Ошибка при загрузке сетевых устройств",
            error_details=str(e)
        ), 500

def get_device_details(data: Dict[str, Any], session: Dict[str, Any]):
    """Получение полной информации об устройстве только при клике"""
    try:
        device_name = data.get('device_name')
        if not device_name:
            # Возвращаем HTML с ошибкой (без JSON)
            return "<div class='alert alert-danger'>Не указано имя устройства</div>"

        physical_devices, virtual_devices = get_network_devices()
        all_devices = physical_devices + virtual_devices
        
        device = next((d for d in all_devices if d.name == device_name), None)
        
        if not device:
            return "<div class='alert alert-danger'>Устройство не найдено</div>"
        
        # Возвращаем чистый HTML (без JSON)
        return render_template('sections/network/device.html', device=device, t=t)
        
    except Exception as e:
        logger.error(f"Error getting device details: {str(e)}")
        return f"<div class='alert alert-danger'>Ошибка: {str(e)}</div>"