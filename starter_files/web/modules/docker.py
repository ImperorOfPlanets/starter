# starter_files/web/modules/docker.py
import os
import platform
import socket
import subprocess
import json
import psutil

from datetime import datetime
from flask import render_template
from starter_files.utils.i18n import t

from starter_files.utils.logger import get_logger
logger = get_logger()

this_module_in_control_panel = True
module_icon = "bi-box"
module_name = "Docker"
module_order = 3

# ======================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==================================================

def get_docker_info():
    """Собирает информацию о Docker"""
    info = {
        'version': 'N/A',
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

    try:
        # Получаем версию Docker
        result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            info['version'] = result.stdout.strip()

        # Получаем статистику контейнеров
        result = subprocess.run(['docker', 'ps', '-a', '--format', '{{.State}}'], capture_output=True, text=True)
        if result.returncode == 0:
            states = result.stdout.splitlines()
            info['containers']['total'] = len(states)
            info['containers']['running'] = states.count('running')
            info['containers']['paused'] = states.count('paused')
            info['containers']['stopped'] = states.count('exited') + states.count('created')

        # Получаем количество образов
        result = subprocess.run(['docker', 'images', '-q'], capture_output=True, text=True)
        if result.returncode == 0:
            info['images'] = len(result.stdout.splitlines())

        # Получаем статистику системы Docker
        result = subprocess.run(['docker', 'system', 'df', '--format', '{{json .}}'], capture_output=True, text=True)
        if result.returncode == 0:
            try:
                system_data = json.loads(result.stdout)
                info['system']['disk_usage'] = system_data.get('Size', 'N/A')
            except json.JSONDecodeError:
                pass

        # Получаем статистику использования ресурсов
        result = subprocess.run(['docker', 'stats', '--no-stream', '--format', '{{json .}}'], capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            cpu_total = 0.0
            mem_total = 0.0
            count = 0
            for line in result.stdout.splitlines():
                try:
                    stats = json.loads(line)
                    cpu_total += float(stats['CPUPerc'].replace('%', ''))
                    mem_total += float(stats['MemPerc'].replace('%', ''))
                    count += 1
                except (json.JSONDecodeError, KeyError, ValueError):
                    continue
            if count > 0:
                info['system']['cpu_usage'] = f"{cpu_total/count:.1f}%"
                info['system']['memory_usage'] = f"{mem_total/count:.1f}%"

        # Получаем информацию о Docker Compose
        try:
            result = subprocess.run(['docker-compose', 'ls', '--format', 'json'], capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                projects = json.loads(result.stdout)
                info['compose']['projects'] = len(projects)
                info['compose']['services'] = sum(len(p.get('Services', [])) for p in projects)
        except:
            pass

    except Exception as e:
        print(f"Error collecting Docker info: {str(e)}")

    return info

def get_containers(all=False):
    """Получает список контейнеров"""
    containers = []
    try:
        format_str = '{{.ID}}|{{.Names}}|{{.Image}}|{{.Status}}|{{.Ports}}|{{.RunningFor}}|{{.Size}}'
        cmd = ['docker', 'ps', '--format', format_str]
        if all:
            cmd.append('-a')
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                parts = line.split('|')
                if len(parts) >= 7:
                    containers.append({
                        'id': parts[0],
                        'name': parts[1],
                        'image': parts[2],
                        'status': parts[3],
                        'ports': parts[4],
                        'running_for': parts[5],
                        'size': parts[6]
                    })
    except Exception as e:
        print(f"Error getting containers: {str(e)}")
    return containers

def get_images():
    """Получает список образов"""
    images = []
    try:
        format_str = '{{.ID}}|{{.Repository}}|{{.Tag}}|{{.CreatedSince}}|{{.CreatedAt}}|{{.Size}}'
        result = subprocess.run(['docker', 'images', '--format', format_str], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                parts = line.split('|')
                if len(parts) >= 6:
                    images.append({
                        'id': parts[0],
                        'repository': parts[1],
                        'tag': parts[2],
                        'created_since': parts[3],
                        'created_at': parts[4],
                        'size': parts[5]
                    })
    except Exception as e:
        print(f"Error getting images: {str(e)}")
    return images

def get_logs(container_id, tail=100):
    """Получает логи контейнера"""
    try:
        result = subprocess.run(['docker', 'logs', '--tail', str(tail), container_id], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout
    except Exception as e:
        print(f"Error getting logs: {str(e)}")
    return ""

def get_networks():
    """Получает список сетей"""
    networks = []
    try:
        format_str = '{{.ID}}|{{.Name}}|{{.Driver}}|{{.Scope}}|{{.IPv6}}|{{.Internal}}|{{.Created}}'
        result = subprocess.run(['docker', 'network', 'ls', '--format', format_str], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                parts = line.split('|')
                if len(parts) >= 7:
                    networks.append({
                        'id': parts[0],
                        'name': parts[1],
                        'driver': parts[2],
                        'scope': parts[3],
                        'ipv6': parts[4],
                        'internal': parts[5],
                        'created': parts[6]
                    })
    except Exception as e:
        print(f"Error getting networks: {str(e)}")
    return networks

def get_volumes():
    """Получает список томов"""
    volumes = []
    try:
        format_str = '{{.Name}}|{{.Driver}}|{{.Scope}}|{{.Mountpoint}}|{{.Labels}}|{{.CreatedAt}}'
        result = subprocess.run(['docker', 'volume', 'ls', '--format', format_str], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                parts = line.split('|')
                if len(parts) >= 6:
                    volumes.append({
                        'name': parts[0],
                        'driver': parts[1],
                        'scope': parts[2],
                        'mountpoint': parts[3],
                        'labels': parts[4],
                        'created_at': parts[5]
                    })
    except Exception as e:
        print(f"Error getting volumes: {str(e)}")
    return volumes

def container_action(data, session):
    """Выполняет действие с контейнером (старт/стоп и т.д.)"""
    action = data.get('action')
    container_id = data.get('container_id')
    
    if not action or not container_id:
        return {'status': 'error', 'message': t('invalid_parameters')}
    
    try:
        if action == 'start':
            subprocess.run(['docker', 'start', container_id], check=True)
            return {'status': 'success', 'message': t('container_started')}
        elif action == 'stop':
            subprocess.run(['docker', 'stop', container_id], check=True)
            return {'status': 'success', 'message': t('container_stopped')}
        elif action == 'restart':
            subprocess.run(['docker', 'restart', container_id], check=True)
            return {'status': 'success', 'message': t('container_restarted')}
        elif action == 'remove':
            subprocess.run(['docker', 'rm', container_id], check=True)
            return {'status': 'success', 'message': t('container_removed')}
        else:
            return {'status': 'error', 'message': t('invalid_action')}
    except subprocess.CalledProcessError as e:
        return {'status': 'error', 'message': f"{t('action_failed')}: {str(e)}"}

def image_action(data, session):
    """Выполняет действие с образом (удаление и т.д.)"""
    action = data.get('action')
    image_id = data.get('image_id')
    
    if not action or not image_id:
        return {'status': 'error', 'message': t('invalid_parameters')}
    
    try:
        if action == 'remove':
            subprocess.run(['docker', 'rmi', image_id], check=True)
            return {'status': 'success', 'message': t('image_removed')}
        else:
            return {'status': 'error', 'message': t('invalid_action')}
    except subprocess.CalledProcessError as e:
        return {'status': 'error', 'message': f"{t('action_failed')}: {str(e)}"}

def restart_docker(data, session):
    """Перезапускает Docker сервис"""
    try:
        if platform.system() == 'Windows':
            subprocess.run(['net', 'stop', 'docker'], check=True)
            subprocess.run(['net', 'start', 'docker'], check=True)
        else:
            subprocess.run(['sudo', 'systemctl', 'restart', 'docker'], check=True)
        return {'status': 'success', 'message': t('docker_restarted_successfully')}
    except subprocess.CalledProcessError as e:
        return {'status': 'error', 'message': t('failed_to_restart_docker') + f": {str(e)}"}

def prune_system(data, session):
    """Очищает неиспользуемые объекты Docker"""
    try:
        subprocess.run(['docker', 'system', 'prune', '-f'], check=True)
        return {'status': 'success', 'message': t('system_pruned_successfully')}
    except subprocess.CalledProcessError as e:
        return {'status': 'error', 'message': t('failed_to_prune_system') + f": {str(e)}"}

# ======================== РОУТЫ ==================================================
def index(data, session):
    """Главная функция модуля docker, возвращает HTML с системной информацией"""
    # Рендерим шаблон с собранными данными
    return render_template(
        'modules/docker/index.html',
        t=t
    )

def info(data, session):
    """Функция модуля docker, возвращает HTML с информацией"""
    # Рендерим шаблон с собранными данными
    return render_template(
        'modules/docker/info.html',
        t=t,
        docker_info=get_docker_info(),
    )

def containers(data, session):
    """Функция модуля docker, возвращает HTML со списком контейнеров"""
    show_all = data.get('show_all', 'false') == 'true'
    return render_template(
        'modules/docker/containers.html',
        t=t,
        containers=get_containers(all=show_all),
        show_all=show_all
    )

def images(data, session):
    """Функция модуля docker, возвращает HTML со списком образов"""
    return render_template(
        'modules/docker/images.html',
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
        'modules/docker/logs.html',
        t=t,
        logs=logs,
        container_id=container_id,
        containers=get_containers(all=True)
    )

def networks(data, session):
    """Функция модуля docker, возвращает HTML со списком сетей"""
    return render_template(
        'modules/docker/networks.html',
        t=t,
        networks=get_networks()
    )

def volumes(data, session):
    """Функция модуля docker, возвращает HTML со списком томов"""
    return render_template(
        'modules/docker/volumes.html',
        t=t,
        volumes=get_volumes()
    )