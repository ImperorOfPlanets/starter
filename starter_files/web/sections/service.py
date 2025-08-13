import platform
import subprocess
from flask import render_template
from starter_files.utils.i18n_utils import t
from starter_files.utils.logger import get_logger

logger = get_logger()

# Конфигурация модуля для панели управления
this_section_in_control_panel = True
section_icon = "bi-gear"
section_name = "Service"
section_order = 6

SERVICE_NAME = "starter-service"

def index(data, session):
    """Главная страница модуля"""
    status = get_service_status()
    return render_template(
        'sections/service/index.html',
        service_status=status,
        service_name=SERVICE_NAME,
        t=t
    )

def info(data, session):
    """Страница информации о сервисе"""
    status = get_service_status()
    return render_template(
        'sections/service/info.html',
        service_status=status,
        service_name=SERVICE_NAME,
        t=t
    )