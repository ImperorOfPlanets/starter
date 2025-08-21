from flask import render_template
from starter_files.core.utils.i18n_utils import t

# Конфигурация модуля для панели управления
this_section_in_control_panel = True
section_icon = "bi-cloud-arrow-down"
section_name = "Updates"
section_order = 10

def index(data, session):
    """Главная страница модуля"""
    return render_template(
        'sections/updates/index.html',
        t=t,
        message=t('updates_placeholder_message')
    )

def info(data, session):
    """Страница информации об обновлениях"""
    return render_template(
        'sections/updates/info.html',
        t=t,
        message=t('updates_placeholder_info')
    )