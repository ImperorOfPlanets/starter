# files/web/sections/reverse_proxy.py
"""
Модуль управления Reverse Proxy для веб-панели
"""

from flask import render_template, jsonify
from files.core.utils.loader_utils import get
from files.core.utils.log_utils import LogManager
from files.core.utils.globalVars_utils import get_global
from pathlib import Path
import subprocess
import shutil

logger = LogManager.get_logger('reverse_proxy_section')

# Функция перевода
def t(key: str, **kwargs) -> str:
    i18n = get('i18n')
    if i18n and hasattr(i18n, 'translate'):
        return i18n.translate(key, **kwargs)
    return key

# Конфигурация модуля для панели управления
this_section_in_control_panel = True
section_icon = "bi-diagram-3"
section_name = "Reverse Proxy"
section_order = 7


def index(data, session):
    """Главная страница модуля reverse-proxy"""
    reverse_proxy = get('reverse_proxy')
    registry = get('registry')
    
    if not reverse_proxy or not registry:
        return render_template(
            'sections/reverse_proxy/error.html',
            error_message="Модули reverse_proxy или registry не загружены",
            t=t
        )
    
    status = reverse_proxy.status()
    proxy_status = registry.get_reverse_proxy_status()
    network_name = reverse_proxy.PROXY_NETWORK
    is_running = reverse_proxy.is_running()
    is_needed = reverse_proxy.is_needed()
    
    return render_template(
        'sections/reverse_proxy/index.html',
        t=t,
        status=status,
        proxy_status=proxy_status,
        network_name=network_name,
        is_running=is_running,
        is_needed=is_needed
    )


def get_status(data, session):
    """Возвращает JSON со статусом reverse-proxy"""
    try:
        reverse_proxy = get('reverse_proxy')
        registry = get('registry')
        
        if not reverse_proxy:
            return {'status': 'error', 'message': 'Reverse proxy module not found'}
        
        status = reverse_proxy.status()
        proxy_status = registry.get_reverse_proxy_status() if registry else {'projects': []}
        
        return {
            'status': 'success',
            'running': status['running'],
            'needed': status['needed'],
            'projects': proxy_status.get('projects', []),
            'projects_count': proxy_status.get('projects_count', 0),
            'network': status['network']
        }
    except Exception as e:
        logger.error(f"Error getting reverse proxy status: {e}")
        return {'status': 'error', 'message': str(e)}


def start_proxy(data, session):
    """Запускает reverse-proxy"""
    try:
        reverse_proxy = get('reverse_proxy')
        if not reverse_proxy:
            return {'status': 'error', 'message': 'Reverse proxy module not found'}
        
        if reverse_proxy.start():
            return {'status': 'success', 'message': t('reverse_proxy_started')}
        else:
            return {'status': 'error', 'message': t('reverse_proxy_start_failed')}
    except Exception as e:
        logger.error(f"Error starting reverse proxy: {e}")
        return {'status': 'error', 'message': str(e)}


def stop_proxy(data, session):
    """Останавливает reverse-proxy"""
    try:
        reverse_proxy = get('reverse_proxy')
        if not reverse_proxy:
            return {'status': 'error', 'message': 'Reverse proxy module not found'}
        
        if reverse_proxy.stop():
            return {'status': 'success', 'message': t('reverse_proxy_stopped')}
        else:
            return {'status': 'error', 'message': t('reverse_proxy_stop_failed')}
    except Exception as e:
        logger.error(f"Error stopping reverse proxy: {e}")
        return {'status': 'error', 'message': str(e)}


def add_project(data, session):
    """Добавляет проект в reverse-proxy"""
    try:
        project_path = data.get('project_path')
        domain = data.get('domain')
        
        if not project_path or not domain:
            return {'status': 'error', 'message': 'Project path and domain required'}
        
        registry = get('registry')
        reverse_proxy = get('reverse_proxy')
        
        if not registry or not reverse_proxy:
            return {'status': 'error', 'message': 'Required modules not found'}
        
        project_path_obj = Path(project_path)
        if not project_path_obj.exists():
            return {'status': 'error', 'message': f'Project path not found: {project_path}'}
        
        # Регистрируем проект в реестре
        registry.register_project(
            path=str(project_path_obj.resolve()),
            subnet_octet=0,
            port=443,
            use_reverse_proxy=True,
            domain=domain,
            proxy_mode="auto"
        )
        
        # Адаптируем проект
        reverse_proxy.adapt_project(project_path_obj, project_path_obj.name)
        
        # Запускаем reverse-proxy если нужно
        reverse_proxy.start()
        
        return {
            'status': 'success',
            'message': t('reverse_proxy_project_added').format(domain=domain)
        }
        
    except Exception as e:
        logger.error(f"Error adding project to reverse proxy: {e}")
        return {'status': 'error', 'message': str(e)}


def remove_project(data, session):
    """Удаляет проект из reverse-proxy"""
    try:
        project_path = data.get('project_path')
        
        if not project_path:
            return {'status': 'error', 'message': 'Project path required'}
        
        registry = get('registry')
        reverse_proxy = get('reverse_proxy')
        
        if not registry:
            return {'status': 'error', 'message': 'Registry module not found'}
        
        project_path_obj = Path(project_path).resolve()
        project = registry.get_project_by_path(str(project_path_obj))
        
        if not project:
            return {'status': 'error', 'message': 'Project not found in registry'}
        
        # Обновляем запись в реестре (отключаем reverse-proxy)
        registry.register_project(
            path=str(project_path_obj),
            subnet_octet=0,
            port=0,
            use_reverse_proxy=False
        )
        
        # Останавливаем reverse-proxy если больше нет проектов
        if reverse_proxy:
            reverse_proxy.stop()
        
        return {
            'status': 'success',
            'message': t('reverse_proxy_project_removed')
        }
        
    except Exception as e:
        logger.error(f"Error removing project from reverse proxy: {e}")
        return {'status': 'error', 'message': str(e)}


def get_projects(data, session):
    """Возвращает JSON со списком проектов в reverse-proxy"""
    try:
        registry = get('registry')
        if not registry:
            return {'status': 'error', 'message': 'Registry module not found'}
        
        projects = registry.get_proxy_projects()
        
        formatted_projects = []
        for proj in projects:
            formatted_projects.append({
                'path': proj['path'],
                'name': proj.get('name', Path(proj['path']).name),
                'domain': proj.get('proxy_config', {}).get('domain', 'Not set'),
                'status': proj.get('status', 'unknown'),
                'last_seen': proj.get('last_seen')
            })
        
        return {
            'status': 'success',
            'projects': formatted_projects,
            'count': len(formatted_projects)
        }
        
    except Exception as e:
        logger.error(f"Error getting proxy projects: {e}")
        return {'status': 'error', 'message': str(e)}


def restart_proxy(data, session):
    """Перезапускает reverse-proxy"""
    try:
        reverse_proxy = get('reverse_proxy')
        if not reverse_proxy:
            return {'status': 'error', 'message': 'Reverse proxy module not found'}
        
        reverse_proxy.stop()
        if reverse_proxy.start():
            return {'status': 'success', 'message': t('reverse_proxy_restarted')}
        else:
            return {'status': 'error', 'message': t('reverse_proxy_restart_failed')}
            
    except Exception as e:
        logger.error(f"Error restarting reverse proxy: {e}")
        return {'status': 'error', 'message': str(e)}


# ========== НОВЫЕ ФУНКЦИИ ДЛЯ УПРАВЛЕНИЯ REVERSE-PROXY ДЛЯ ТЕКУЩЕГО ПРОЕКТА ==========

def get_current_project_config(data, session):
    """Получает текущие настройки reverse-proxy для проекта"""
    try:
        project_path = get_global('project_path')
        registry = get('registry')
        
        if not project_path or not registry:
            return {
                'status': 'success',
                'data': {
                    'use_reverse_proxy': False,
                    'domain': ''
                }
            }
        
        project_data = registry.get_project_by_path(str(project_path))
        
        if project_data:
            proxy_config = project_data.get('proxy_config', {})
            return {
                'status': 'success',
                'data': {
                    'use_reverse_proxy': proxy_config.get('enabled', False),
                    'domain': proxy_config.get('domain', ''),
                    'registered_at': proxy_config.get('registered_at')
                }
            }
        
        return {
            'status': 'success',
            'data': {
                'use_reverse_proxy': False,
                'domain': ''
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting current project config: {e}")
        return {'status': 'error', 'message': str(e)}


def enable_for_current_project(data, session):
    """Включает reverse-proxy для текущего проекта"""
    try:
        domain = data.get('domain', '').strip()
        
        if not domain:
            return {'status': 'error', 'message': 'Domain name required'}
        
        project_path = get_global('project_path')
        if not project_path:
            return {'status': 'error', 'message': 'Project path not found'}
        
        registry = get('registry')
        reverse_proxy = get('reverse_proxy')
        
        if not registry or not reverse_proxy:
            return {'status': 'error', 'message': 'Required modules not found'}
        
        project_path_obj = Path(project_path)
        
        # 1. Проверяем, существует ли reverse-proxy сервер
        reverse_proxy_path = project_path_obj.parent / "reverse-proxy"
        
        # 2. Если нет - создаем reverse-proxy сервер
        if not (reverse_proxy_path / "docker-compose.yml").exists():
            result = _create_reverse_proxy_server(reverse_proxy_path)
            if not result['success']:
                return {'status': 'error', 'message': result['message']}
        
        # 3. Регистрируем проект в реестре
        registry.register_project(
            path=str(project_path_obj.resolve()),
            subnet_octet=0,
            port=443,
            use_reverse_proxy=True,
            domain=domain,
            proxy_mode="enabled",
            project_type="client"
        )
        
        # 4. Адаптируем проект для reverse-proxy
        reverse_proxy.adapt_project(project_path_obj, project_path_obj.name, domain)
        
        # 5. Запускаем reverse-proxy
        reverse_proxy.start()
        
        # 6. Перезапускаем проект
        _restart_project(project_path_obj)
        
        return {
            'status': 'success',
            'message': f'Reverse proxy enabled for {domain}',
            'url': f'https://{domain}'
        }
        
    except Exception as e:
        logger.error(f"Error enabling reverse proxy: {e}")
        return {'status': 'error', 'message': str(e)}


def disable_for_current_project(data, session):
    """Отключает reverse-proxy для текущего проекта"""
    try:
        project_path = get_global('project_path')
        if not project_path:
            return {'status': 'error', 'message': 'Project path not found'}
        
        registry = get('registry')
        reverse_proxy = get('reverse_proxy')
        
        if not registry:
            return {'status': 'error', 'message': 'Registry module not found'}
        
        project_path_obj = Path(project_path)
        
        # 1. Обновляем реестр
        registry.register_project(
            path=str(project_path_obj.resolve()),
            subnet_octet=0,
            port=0,
            use_reverse_proxy=False
        )
        
        # 2. Восстанавливаем оригинальный docker-compose
        _restore_original_compose(project_path_obj)
        
        # 3. Проверяем, есть ли еще проекты в reverse-proxy
        proxy_projects = registry.get_proxy_projects()
        
        # 4. Если нет - останавливаем reverse-proxy сервер
        if len(proxy_projects) == 0 and reverse_proxy:
            reverse_proxy.stop()
        
        # 5. Перезапускаем проект
        _restart_project(project_path_obj)
        
        return {
            'status': 'success',
            'message': 'Reverse proxy disabled for this project'
        }
        
    except Exception as e:
        logger.error(f"Error disabling reverse proxy: {e}")
        return {'status': 'error', 'message': str(e)}


# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

def _create_reverse_proxy_server(reverse_proxy_path: Path) -> dict:
    """Создает reverse-proxy сервер в отдельной папке"""
    try:
        reverse_proxy_path.mkdir(parents=True, exist_ok=True)
        
        compose_content = f"""
version: '3.8'

networks:
  global_reverse_proxy_network:
    name: global_reverse_proxy_network
    driver: bridge

services:
  nginx-proxy:
    image: nginxproxy/nginx-proxy:alpine
    container_name: global-nginx-proxy
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/tmp/docker.sock:ro
      - ./certs:/etc/nginx/certs
      - ./vhost.d:/etc/nginx/vhost.d
      - ./html:/usr/share/nginx/html
    networks:
      - global_reverse_proxy_network

  acme-companion:
    image: nginxproxy/acme-companion
    container_name: global-acme-companion
    restart: unless-stopped
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./certs:/etc/nginx/certs
      - ./vhost.d:/etc/nginx/vhost.d
      - ./html:/usr/share/nginx/html
      - ./acme.sh:/etc/acme.sh
    environment:
      - DEFAULT_EMAIL={get_global('LETSENCRYPT_EMAIL', 'admin@localhost')}
      - NGINX_PROXY_CONTAINER=global-nginx-proxy
    depends_on:
      - nginx-proxy
    networks:
      - global_reverse_proxy_network
"""
        
        compose_file = reverse_proxy_path / "docker-compose.yml"
        compose_file.write_text(compose_content)
        
        for dir_name in ['certs', 'vhost.d', 'html', 'acme.sh']:
            (reverse_proxy_path / dir_name).mkdir(exist_ok=True)
        
        subprocess.run(
            ['docker-compose', 'up', '-d'],
            cwd=reverse_proxy_path,
            check=True,
            capture_output=True
        )
        
        registry = get('registry')
        if registry:
            registry.set_reverse_proxy_global(
                enabled=True,
                network="global_reverse_proxy_network",
                container_name="global-nginx-proxy"
            )
        
        return {'success': True, 'message': 'Reverse proxy server created'}
        
    except Exception as e:
        logger.error(f"Error creating reverse proxy server: {e}")
        return {'success': False, 'message': str(e)}


def _restart_project(project_path: Path):
    """Перезапускает проект"""
    try:
        docker_path = project_path / "docker"
        if docker_path.exists():
            subprocess.run(
                ['docker-compose', 'down'],
                cwd=docker_path,
                check=False,
                capture_output=True
            )
            subprocess.run(
                ['docker-compose', 'up', '-d'],
                cwd=docker_path,
                check=True,
                capture_output=True
            )
    except Exception as e:
        logger.error(f"Error restarting project: {e}")


def _restore_original_compose(project_path: Path):
    """Восстанавливает оригинальный docker-compose.yml из .example"""
    try:
        compose_example = project_path / "docker" / "docker-compose.example"
        compose_file = project_path / "docker" / "docker-compose.yml"
        
        if compose_example.exists() and compose_file.exists():
            shutil.copy2(compose_example, compose_file)
    except Exception as e:
        logger.error(f"Error restoring original compose: {e}")