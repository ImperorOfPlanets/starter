"""
Модуль синхронизации серверов с myidon.site
Загружает публичные серверы из API myidon.site и добавляет в локальную конфигурацию
"""

import requests
from typing import Dict, List, Optional
from files.core.utils.globalVars_utils import get_global, set_global
from files.core.utils.log_utils import LogManager

logger = LogManager.get_logger('myidon_sync')

MYIDON_API_BASE = 'https://myidon.site/api'


class MyidonSyncModule:
    """Синхронизация серверов с myidon.site"""

    @staticmethod
    def get_service_token() -> Optional[str]:
        """Получить сервисный токен для API запросов"""
        try:
            client_id = get_global('myidon_client_id', '2')
            client_secret = get_global('myidon_client_secret', '09jbrDjVY4yj64pTPHi0sEnYxCyaBllOlRbADNjF')

            response = requests.post(f'{MYIDON_API_BASE}/../oauth/token', data={
                'grant_type': 'client_credentials',
                'client_id': client_id,
                'client_secret': client_secret,
            }, timeout=10)

            if response.status_code == 200:
                return response.json().get('access_token')
        except Exception as e:
            logger.error(f"Failed to get myidon token: {e}")
        return None

    @staticmethod
    def fetch_public_servers() -> List[Dict]:
        """Получить список публичных серверов из myidon.site"""
        token = MyidonSyncModule.get_service_token()
        if not token:
            logger.warning("Cannot fetch servers: no token")
            return []

        try:
            response = requests.get(f'{MYIDON_API_BASE}/servers', headers={
                'Authorization': f'Bearer {token}',
                'Accept': 'application/json',
            }, timeout=10)

            if response.status_code == 200:
                data = response.json()
                servers = data.get('servers', [])
                # Фильтруем только публичные (requires_auth=0)
                return [s for s in servers if not s.get('requires_auth', True)]
        except Exception as e:
            logger.error(f"Failed to fetch servers from myidon: {e}")
        return []

    @staticmethod
    def sync_with_myidon() -> Dict:
        """Синхронизировать локальные типы серверов с myidon.site"""
        from files.configs.server_types import SERVER_TYPES

        remote_servers = MyidonSyncModule.fetch_public_servers()
        if not remote_servers:
            return {'status': 'warning', 'message': 'No servers fetched from myidon'}

        added = 0
        updated = 0

        for server in remote_servers:
            slug = server.get('slug', '')
            if not slug:
                continue

            if slug in SERVER_TYPES:
                # Сервер уже есть — обновляем если нужно
                local = SERVER_TYPES[slug]
                remote_url = server.get('repository_url', '')
                if remote_url and local.get('repository', {}).get('url') != remote_url:
                    local['repository']['url'] = remote_url
                    updated += 1
                    logger.info(f"Updated repository for {slug}: {remote_url}")
            else:
                # Новый сервер — добавляем
                SERVER_TYPES[slug] = {
                    'name': server.get('name', slug),
                    'name_en': server.get('name', slug),
                    'description': server.get('description', ''),
                    'description_en': server.get('description', ''),
                    'requires_reverse_proxy': bool(server.get('requires_reverse_proxy', False)),
                    'requires_auth': False,
                    'is_reverse_proxy': False,
                    'has_web_interface': bool(server.get('has_web_interface', False)),
                    'default_port': server.get('default_port', 8000),
                    'order': server.get('order', 999),
                    'can_have_multiple': True,
                    'default_folder': slug,
                    'docker_compose_path': 'docker/docker-compose.yml',
                    'env_example_path': 'docker/.env.example',
                    'repository': {
                        'url': server.get('repository_url', ''),
                        'branch': 'main',
                    }
                }
                added += 1
                logger.info(f"Added server type from myidon: {slug}")

        return {
            'status': 'success',
            'added': added,
            'updated': updated,
            'total_remote': len(remote_servers),
            'total_local': len(SERVER_TYPES),
        }

    @staticmethod
    def set_globals():
        """Установить глобальные переменные для модуля"""
        set_global('myidon_client_id', '2')
        set_global('myidon_client_secret', '09jbrDjVY4yj64pTPHi0sEnYxCyaBllOlRbADNjF')
