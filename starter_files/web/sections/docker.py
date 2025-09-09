import os
import platform
import socket
import subprocess
import json
import psutil
import threading
import uuid

from datetime import datetime
from typing import Dict, List, Optional, Any
from flask import render_template, jsonify, Response

from starter_files.core.utils.i18n_utils import t
from starter_files.core.utils.log_utils import LogManager
logger = LogManager.get_logger()

from starter_files.core.utils.loader_utils import get
from starter_files.core.utils.globalVars_utils import get_global

from starter_files.core.software.default.settings import SettingsModule
from starter_files.core.software.default.docker import DockerModule

this_section_in_control_panel = True
section_icon = "bi-box"
section_name = "Docker"
section_order = 3

# Стандартная структура для информации о Docker
DEFAULT_DOCKER_INFO = {
    'version': 'N/A',
    'installed': False,
    'compose_installed': False,
    'containers': {
        'total': 0,
        'running': 0,
        'paused': 0,
        'stopped': 0
    },
    'images': 0,
    'system': {
        'cpu_usage': 'N/A',
        'memory_usage': 'N/A',
        'disk_usage': 'N/A'
    },
    'compose': {
        'projects': 0,
        'services': 0
    }
}

# ======================== РОУТЫ ==================================================
def index(data, session):
    """Главная функция модуля docker, возвращает HTML с системной информацией"""
    return render_template(
        'sections/docker/index.html',
        t=t
    )

def info(data, session):
    docker_installed = get_global('docker_installed', False)
    docker_compose_installed = get_global('docker_compose_installed', False)
    
    docker_info = DEFAULT_DOCKER_INFO.copy()
    if docker_installed:
        try:
            full_info = get('docker', 'get_docker_info')
            if full_info:
                docker_info.update(full_info)
        except Exception as e:
            logger.error(f"Error getting docker info: {str(e)}")
    
    docker_info['installed'] = docker_installed
    docker_info['compose_installed'] = docker_compose_installed
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Получаем PROJECTNAME
    project_name = get_global('project_name', 'default_project')  # пример
    
    # Проверяем статус проектного контейнера
    project_running = DockerModule.is_project_running(project_name)
    
    return render_template(
        'sections/docker/info.html',
        t=t,
        docker_info=docker_info,
        current_time=current_time,
        project_name=project_name,
        project_running=project_running
    )

def containers(data, session):
    """Функция модуля docker, возвращает HTML со списком контейнеров"""
    show_all = data.get('show_all', 'false') == 'true'
    containers = []
    
    # Проверяем установлен ли Docker из глобальных переменных
    docker_installed = get_global('docker_installed', False)
    
    if docker_installed:
        try:
            containers = get('docker', 'get_containers', all=show_all) or []
        except Exception as e:
            logger.error(f"Error getting containers: {str(e)}")
            containers = []
    
    return render_template(
        'sections/docker/containers.html',
        t=t,
        containers=containers,
        show_all=show_all,
        docker_installed=docker_installed
    )

def images(data, session):
    """Функция модуля docker, возвращает HTML со списком образов"""
    images = []
    docker_installed = get_global('docker_installed', False)
    
    if docker_installed:
        try:
            images = get('docker', 'get_images') or []
        except Exception as e:
            logger.error(f"Error getting images: {str(e)}")
            images = []
    
    return render_template(
        'sections/docker/images.html',
        t=t,
        images=images,
        docker_installed=docker_installed
    )

def logs(data, session):
    """Функция модуля docker, возвращает HTML с логами контейнера"""
    container_id = data.get('container_id')
    logs = ""
    containers_list = []
    docker_installed = get_global('docker_installed', False)
    
    if docker_installed:
        try:
            if container_id:
                logs = get('docker', 'get_logs', container_id) or ""
            containers_list = get('docker', 'get_containers', all=True) or []
        except Exception as e:
            logger.error(f"Error getting logs: {str(e)}")
            logs = ""
            containers_list = []
    
    return render_template(
        'sections/docker/logs.html',
        t=t,
        logs=logs,
        container_id=container_id,
        containers=containers_list,
        docker_installed=docker_installed
    )

def networks(data, session):
    """Функция модуля docker, возвращает HTML со списком сетей"""
    networks = []
    docker_installed = get_global('docker_installed', False)
    
    if docker_installed:
        try:
            networks = get('docker', 'get_networks') or []
        except Exception as e:
            logger.error(f"Error getting networks: {str(e)}")
            networks = []
    
    return render_template(
        'sections/docker/networks.html',
        t=t,
        networks=networks,
        docker_installed=docker_installed
    )

def volumes(data, session):
    """Функция модуля docker, возвращает HTML со списком томов"""
    volumes = []
    docker_installed = get_global('docker_installed', False)
    
    if docker_installed:
        try:
            volumes = get('docker', 'get_volumes') or []
        except Exception as e:
            logger.error(f"Error getting volumes: {str(e)}")
            volumes = []
    
    return render_template(
        'sections/docker/volumes.html',
        t=t,
        volumes=volumes,
        docker_installed=docker_installed
    )

# ======================== API-КОНТРОЛЛЕРЫ ========================================
def container_action(data, session):
    """Обработка действий с контейнерами (start, stop, restart, remove)"""
    container_id = data.get('container_id')
    action = data.get('action')
    
    if not container_id or not action:
        return {'status': 'error', 'message': 'Missing parameters'}
    
    # Проверяем установлен ли Docker из глобальных переменных
    docker_installed = get_global('docker_installed', False)
    if not docker_installed:
        return {'status': 'error', 'message': 'Docker is not installed'}
    
    try:
        result = get('docker', 'container_action', {
            'action': action,
            'container_id': container_id
        }) or {'status': 'error', 'message': 'Unknown error'}
    except Exception as e:
        logger.error(f"Error performing container action: {str(e)}")
        result = {'status': 'error', 'message': 'Docker service unavailable'}
    
    return result

def image_action(data, session):
    """Обработка действий с образами (remove)"""
    image_id = data.get('image_id')
    action = data.get('action')
    
    if not image_id or not action:
        return {'status': 'error', 'message': 'Missing parameters'}
    
    docker_installed = get_global('docker_installed', False)
    if not docker_installed:
        return {'status': 'error', 'message': 'Docker is not installed'}
    
    try:
        result = get('docker', 'image_action', {
            'action': action,
            'image_id': image_id
        }) or {'status': 'error', 'message': 'Unknown error'}
    except Exception as e:
        logger.error(f"Error performing image action: {str(e)}")
        result = {'status': 'error', 'message': 'Docker service unavailable'}
    
    return result

def restart_docker(data, session):
    """Перезапуск Docker сервиса"""
    docker_installed = get_global('docker_installed', False)
    if not docker_installed:
        return {'status': 'error', 'message': 'Docker is not installed'}
    
    try:
        result = get('docker', 'restart_docker') or {'status': 'error', 'message': 'Unknown error'}
    except Exception as e:
        logger.error(f"Error restarting docker: {str(e)}")
        result = {'status': 'error', 'message': 'Docker service unavailable'}
    
    return result

def prune_system(data, session):
    """Очистка неиспользуемых объектов Docker"""
    docker_installed = get_global('docker_installed', False)
    if not docker_installed:
        return {'status': 'error', 'message': 'Docker is not installed'}
    
    try:
        result = get('docker', 'prune_system') or {'status': 'error', 'message': 'Unknown error'}
    except Exception as e:
        logger.error(f"Error pruning system: {str(e)}")
        result = {'status': 'error', 'message': 'Docker service unavailable'}
    
    return result

# ======================== ПРОЕКТ ========================================
def start_project(data, session):
    try:
        settings = SettingsModule.get_settings()
        result = DockerModule.run_compose(settings)
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

