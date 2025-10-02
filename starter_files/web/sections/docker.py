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
    """Запуск проекта с возвратом ID для отслеживания логов"""
    try:
        # Записываем результат в файл
        log_file_name = f"start_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        sp = get_global('script_path')
        starts_log_dir = sp / 'starter_files' / 'logs' / 'starts'
        log_file = starts_log_dir / log_file_name
        
        # Запускаем в отдельном потоке
        def run_project():
            try:
                result = DockerModule.run_compose(log_file)
                

                with open(log_file, 'a', encoding='utf-8') as f:
                    if result:
                        f.write("PROJECT START COMPLETED SUCCESSFULLY\n")
                    else:
                        f.write("PROJECT START FAILED\n")
            except Exception as e:
                with open(log_file, 'a', encoding='utf-8') as f:
                    f.write(f"ERROR: {str(e)}\n")
        
        thread = threading.Thread(target=run_project)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'status': 'started',
            'message': 'Project start initiated',
            'log_file': log_file_name
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

def get_project_logs(data, session):
    """Получение логов запуска проекта"""
    log_file_name = data.get('log_file')
    if not log_file_name:
        return jsonify({
            'status': 'error',
            'message': 'Log file name required',
            'logs': '',
            'completed': False,
            'success': False
        })

    sp = get_global('script_path')
    starts_log_dir = sp / 'starter_files' / 'logs' / 'starts'
    log_file = starts_log_dir / log_file_name
    
    if not log_file.exists():
        return jsonify({
            'status': 'error',
            'message': 'Log file not found',
            'logs': '',
            'completed': False,
            'success': False
        })
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            logs = f.read()
        
        # Проверяем завершение
        completed = "PROJECT START COMPLETED" in logs or "PROJECT START FAILED" in logs
        success = "PROJECT START COMPLETED SUCCESSFULLY" in logs
        
        return jsonify({
            'status': 'success',
            'logs': logs,
            'completed': completed,
            'success': success
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'logs': '',
            'completed': False,
            'success': False
        })

def download_project_logs(data, session):
    """Скачивание логов запуска проекта"""
    log_file_name = data.get('log_file')
    if not log_file_name:
        return "Log file name required", 400
    
    sp = get_global('script_path')
    starts_log_dir = sp / 'starter_files' / 'logs' / 'starts'
    log_file = starts_log_dir / log_file_name
    
    if not log_file.exists():
        return "Log file not found", 404
    
    try:
        from flask import send_file
        return send_file(
            log_file,
            as_attachment=True,
            download_name=log_file_name,
            mimetype='text/plain'
        )
    except Exception as e:
        return str(e), 500

def get_launch_history(data, session):
    """Получение истории запусков"""
    try:
        sp = get_global('script_path')
        starts_log_dir = sp / 'starter_files' / 'logs' / 'starts'
        
        if not starts_log_dir.exists():
            return jsonify({'status': 'success', 'history': []})
        
        history = []
        for log_file in starts_log_dir.glob('start_*.log'):
            try:
                stat = log_file.stat()
                content = log_file.read_text(encoding='utf-8', errors='ignore')
                
                # Определяем статус по содержимому
                if "PROJECT START COMPLETED SUCCESSFULLY" in content:
                    status = "success"
                elif "PROJECT START FAILED" in content or "ERROR:" in content:
                    status = "failed"
                else:
                    status = "running"
                
                history.append({
                    'filename': log_file.name,
                    'timestamp': stat.st_mtime,
                    'formatted_date': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                    'size': stat.st_size,
                    'status': status
                })
            except Exception as e:
                print(f"Error processing log file {log_file.name}: {e}")
                continue
        
        return jsonify({'status': 'success', 'history': history})
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

def delete_log_file(data, session):
    """Удаление файла лога"""
    try:
        log_file_name = data.get('log_file')
        if not log_file_name:
            return jsonify({'status': 'error', 'message': 'Log file name required'})
        
        sp = get_global('script_path')
        starts_log_dir = sp / 'starter_files' / 'logs' / 'starts'
        log_file = starts_log_dir / log_file_name
        
        if not log_file.exists():
            return jsonify({'status': 'error', 'message': 'Log file not found'})
        
        # Удаляем файл
        log_file.unlink()
        
        return jsonify({'status': 'success', 'message': 'Log file deleted'})
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})
