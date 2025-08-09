from flask import render_template
from starter_files.utils.i18n import t

# Конфигурация модуля для панели управления
this_module_in_control_panel = True
module_icon = "bi-cloud-arrow-down"
module_name = "Updates"
module_order = 10

def index(data, session):
    """Главная страница модуля"""
    return render_template(
        'modules/updates/index.html',
        t=t,
        message=t('updates_placeholder_message')
    )

def info(data, session):
    """Страница информации об обновлениях"""
    return render_template(
        'modules/updates/info.html',
        t=t,
        message=t('updates_placeholder_info')
    )