# starter_files/web/sections/docker.py
import os
import platform
import socket
import subprocess
import json
import psutil

from datetime import datetime
from flask import render_template
from starter_files.utils.i18n_utils import t

from starter_files.utils.log_utils import get_logger
logger = get_logger()

this_section_in_control_panel = True
section_icon = "bi-box"
section_name = "Docker"
section_order = 3


# ======================== РОУТЫ ==================================================
def index(data, session):
    """Главная функция модуля docker, возвращает HTML с системной информацией"""
    # Рендерим шаблон с собранными данными
    return render_template(
        'sections/docker/index.html',
        t=t
    )

def info(data, session):
    """Функция модуля docker, возвращает HTML с информацией"""
    # Рендерим шаблон с собранными данными
    return render_template(
        'sections/docker/info.html',
        t=t,
        docker_info=get_docker_info(),
    )

def containers(data, session):
    """Функция модуля docker, возвращает HTML со списком контейнеров"""
    show_all = data.get('show_all', 'false') == 'true'
    return render_template(
        'sections/docker/containers.html',
        t=t,
        containers=get_containers(all=show_all),
        show_all=show_all
    )

def images(data, session):
    """Функция модуля docker, возвращает HTML со списком образов"""
    return render_template(
        'sections/docker/images.html',
        t=t,
        images=get_images()
    )

def logs(data, session):
    """Функция модуля docker, возвращает HTML с логами контейнера"""
    container_id = data.get('container_id')
    logs = ""
    if container_id:
        logs = get_logs(container_id)
    
    return render_template(
        'sections/docker/logs.html',
        t=t,
        logs=logs,
        container_id=container_id,
        containers=get_containers(all=True)
    )

def networks(data, session):
    """Функция модуля docker, возвращает HTML со списком сетей"""
    return render_template(
        'sections/docker/networks.html',
        t=t,
        networks=get_networks()
    )

def volumes(data, session):
    """Функция модуля docker, возвращает HTML со списком томов"""
    return render_template(
        'sections/docker/volumes.html',
        t=t,
        volumes=get_volumes()
    )