"""
Модуль Reverse Proxy — проверка статуса, подключение, регистрация
"""
import subprocess
import requests
import json
from typing import Dict, Optional
from pathlib import Path
from files.core.base_module import BaseModule
from files.core.utils.globalVars_utils import get_global, set_global
from files.core.utils.log_utils import LogManager

logger = LogManager.get_logger('reverse_proxy')


class ReverseProxyModule(BaseModule):
    """Модуль управления Reverse Proxy"""

    @staticmethod
    def check() -> bool:
        return True

    @staticmethod
    def set_globals():
        """Устанавливает глобальные переменные"""
        status = ReverseProxyModule.get_status()
        set_global('reverse_proxy_installed', status.get('installed', False))
        set_global('reverse_proxy_running', status.get('running', False))
        set_global('reverse_proxy_api_available', status.get('api_available', False))
        
        proxy_path = get_global('project_path')
        if proxy_path:
            reverse_proxy_dir = proxy_path.parent / 'revers-proxy'
            set_global('reverse_proxy_path', str(reverse_proxy_dir))
        
        logger.info(f"Reverse Proxy status: {status}")

    @staticmethod
    def get_status() -> Dict:
        """Получение полного статуса reverse proxy"""
        status = {
            'installed': False,
            'running': False,
            'api_available': False,
            'containers': [],
            'api_port': 5000,
            'path': None
        }

        # Определяем путь к reverse-proxy
        reverse_proxy_path = get_global('reverse_proxy_path')
        if not reverse_proxy_path:
            # Ищем относительно стартера
            starter_path = get_global('starter_path')
            if starter_path:
                reverse_proxy_path = Path(starter_path).parent / 'revers-proxy'
            else:
                reverse_proxy_path = Path('C:/control/revers-proxy')
        
        status['path'] = str(reverse_proxy_path)

        # Проверяем установлен ли (есть docker-compose.yml)
        compose_file = reverse_proxy_path / 'docker' / 'docker-compose.yml'
        if compose_file.exists():
            status['installed'] = True
        
        # Проверяем запущен ли (контейнеры)
        try:
            result = subprocess.run(
                ['docker', 'ps', '-a', '--filter', 'name=revers-proxy', '--format', '{{.Names}} {{.Status}}'],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    parts = line.split(' ', 1)
                    if len(parts) == 2:
                        status['containers'].append({
                            'name': parts[0],
                            'status': parts[1]
                        })
                status['running'] = any('Up' in c['status'] for c in status['containers'])
        except Exception as e:
            logger.error(f"Error checking containers: {e}")

        # Проверяем API
        try:
            response = requests.get(
                f'http://localhost:{status["api_port"]}/api/health',
                timeout=3
            )
            if response.status_code == 200:
                status['api_available'] = True
                data = response.json()
                status['containers_in_network'] = data.get('containers_in_network', 0)
        except Exception:
            pass

        return status

    @staticmethod
    def get_api_url() -> str:
        """URL API reverse proxy"""
        port = get_global('reverse_proxy_api_port', 5000)
        return f'http://localhost:{port}'

    @staticmethod
    def check_api_health() -> bool:
        """Проверка доступности API"""
        try:
            response = requests.get(
                f'{ReverseProxyModule.get_api_url()}/api/health',
                timeout=3
            )
            return response.status_code == 200
        except Exception:
            return False

    @staticmethod
    def get_servers() -> list:
        """Получение списка серверов в proxy сети"""
        try:
            result = subprocess.run(
                ['docker', 'network', 'inspect', 'proxy_net',
                 '--format', '{{range .Containers}}{{.Name}} {{end}}'],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                return result.stdout.strip().split()
            return []
        except Exception:
            return []

    @staticmethod
    def connect_container(container_name: str) -> bool:
        """Подключение контейнера к proxy сети"""
        try:
            result = subprocess.run(
                ['docker', 'network', 'connect', 'proxy_net', container_name],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                logger.info(f"Connected {container_name} to proxy_net")
                return True
            else:
                logger.error(f"Failed to connect: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Connect error: {e}")
            return False

    @staticmethod
    def disconnect_container(container_name: str) -> bool:
        """Отключение контейнера от proxy сети"""
        try:
            result = subprocess.run(
                ['docker', 'network', 'disconnect', 'proxy_net', container_name],
                capture_output=True, text=True, timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False

    @staticmethod
    def register_domain(domain: str, target: str, server_name: str = '', 
                       container_name: str = '') -> Dict:
        """Регистрация домена через API"""
        try:
            response = requests.post(
                f'{ReverseProxyModule.get_api_url()}/api/proxy',
                json={
                    'domain': domain,
                    'target': target,
                    'server_name': server_name,
                    'container_name': container_name
                },
                timeout=10
            )
            return response.json()
        except Exception as e:
            logger.error(f"Register domain error: {e}")
            return {'status': 'error', 'message': str(e)}

    @staticmethod
    def unregister_domain(domain: str) -> bool:
        """Удаление домена через API"""
        try:
            # Находим ID по домену
            response = requests.get(
                f'{ReverseProxyModule.get_api_url()}/api/proxy',
                timeout=5
            )
            if response.status_code == 200:
                entries = response.json().get('entries', [])
                for entry in entries:
                    if entry['domain'] == domain:
                        requests.delete(
                            f'{ReverseProxyModule.get_api_url()}/api/proxy/{entry["id"]}',
                            timeout=5
                        )
                        return True
            return False
        except Exception:
            return False

    @staticmethod
    def get_proxy_entries() -> list:
        """Получение списка проксирований"""
        try:
            response = requests.get(
                f'{ReverseProxyModule.get_api_url()}/api/proxy',
                timeout=5
            )
            if response.status_code == 200:
                return response.json().get('entries', [])
            return []
        except Exception:
            return []

    @staticmethod
    def generate_docker_compose_with_proxy(server_type: str, server_name: str,
                                          subnet_octet: int, port: int) -> str:
        """Генерация docker-compose.yml с подключением к proxy_net"""
        project_name = server_type.replace('_', '-')
        
        return f"""services:
  {project_name}:
    image: alpine:latest
    container_name: {project_name}
    restart: unless-stopped
    ports:
      - "{port}:{port}"
    volumes:
      - ../code:/app
    working_dir: /app
    command: sh -c "echo '{server_name} is running' && sleep infinity"
    networks:
      - default
      - proxy_net

networks:
  default:
    driver: bridge
    ipam:
      config:
        - subnet: 172.{subnet_octet}.0.0/16
          gateway: 172.{subnet_octet}.0.1
  proxy_net:
    external: true
    name: proxy_net
"""
