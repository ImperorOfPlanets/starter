"""
Модуль работы с API myidon.site для получения списка серверов.
Кеширует результаты чтобы не дёргать API при каждом действии.
"""

import time
import requests
from typing import Dict, List, Optional
from files.core.utils.log_utils import LogManager

logger = LogManager.get_logger('serverapi')

# Кеш: {token_hash: {data, timestamp}}
_cache = {}
CACHE_TTL = 300  # 5 минут


def _cache_key(token: str) -> str:
    """Хеш токена для ключа кеша"""
    import hashlib
    return hashlib.md5(token.encode()).hexdigest()


def _get_cached(token: str) -> Optional[Dict]:
    """Получить из кеша если не протух"""
    key = _cache_key(token)
    if key in _cache:
        entry = _cache[key]
        if time.time() - entry['timestamp'] < CACHE_TTL:
            return entry['data']
        else:
            del _cache[key]
    return None


def _set_cache(token: str, data: Dict):
    """Сохранить в кеш"""
    key = _cache_key(token)
    _cache[key] = {'data': data, 'timestamp': time.time()}


def clear_cache(token: str = None):
    """Очистить кеш"""
    if token:
        key = _cache_key(token)
        _cache.pop(key, None)
    else:
        _cache.clear()


def get_myidon_url() -> str:
    """Получить URL myidon.site из конфига"""
    try:
        from files.core.software.default.oauth import OauthModule
        return OauthModule.MYIDON_URL
    except Exception:
        return 'https://myidon.site'


def fetch_available_servers(oauth_token: str) -> List[Dict]:
    """
    GET /api/server/available
    Возвращает все доступные серверы с репозиториями.
    """
    cached = _get_cached(oauth_token)
    if cached and 'available' in cached:
        return cached['available']

    try:
        url = f"{get_myidon_url()}/api/server/available"
        response = requests.get(
            url,
            headers={
                'Authorization': f'Bearer {oauth_token}',
                'Accept': 'application/json'
            },
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            servers = data.get('servers', [])
            logger.info(f"Fetched {len(servers)} available servers from myidon.site")
            # ПОЛНЫЙ ДАМП ОТВЕТА API
            import json as _json
            logger.info(f"=== FULL API RESPONSE ===")
            logger.info(_json.dumps(data, indent=2, ensure_ascii=False))
            logger.info(f"=== END API RESPONSE ===")

            # Обновляем кеш
            cache_data = _get_cached(oauth_token) or {}
            cache_data['available'] = servers
            _set_cache(oauth_token, cache_data)

            return servers
        else:
            logger.warning(f"Failed to fetch available servers: {response.status_code}")
            return []

    except Exception as e:
        logger.error(f"Error fetching available servers: {e}")
        return []


def fetch_user_servers(oauth_token: str) -> List[Dict]:
    """
    GET /api/server/user-servers
    Возвращает одобренные серверы пользователя.
    """
    cached = _get_cached(oauth_token)
    if cached and 'user_servers' in cached:
        return cached['user_servers']

    try:
        url = f"{get_myidon_url()}/api/server/user-servers"
        response = requests.get(
            url,
            headers={
                'Authorization': f'Bearer {oauth_token}',
                'Accept': 'application/json'
            },
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            servers = data.get('servers', [])
            logger.info(f"Fetched {len(servers)} user servers from myidon.site")
            # ПОЛНЫЙ ДАМП ОТВЕТА API
            import json as _json
            logger.info(f"=== FULL USER SERVERS RESPONSE ===")
            logger.info(_json.dumps(data, indent=2, ensure_ascii=False))
            logger.info(f"=== END USER SERVERS RESPONSE ===")

            cache_data = _get_cached(oauth_token) or {}
            cache_data['user_servers'] = servers
            _set_cache(oauth_token, cache_data)

            return servers
        else:
            logger.warning(f"Failed to fetch user servers: {response.status_code}")
            return []

    except Exception as e:
        logger.error(f"Error fetching user servers: {e}")
        return []


def check_server_access(oauth_token: str, slug: str) -> bool:
    """
    GET /api/server/access/{slug}
    Проверяет доступ пользователя к конкретному серверу.
    """
    try:
        url = f"{get_myidon_url()}/api/server/access/{slug}"
        response = requests.get(
            url,
            headers={
                'Authorization': f'Bearer {oauth_token}',
                'Accept': 'application/json'
            },
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            return data.get('access', False)
        return False

    except Exception as e:
        logger.error(f"Error checking access for {slug}: {e}")
        return False


def merge_server_types(local_types: Dict, api_servers: List[Dict], user_servers: List[Dict], approved_keys: set = None) -> Dict:
    """
    Объединяет локальные серверы с серверами из API.
    
    Логика:
    - Локальные серверы всегда доступны
    - Из API добавляются серверы из approved_keys (если переданы) 
    - Или все серверы не требующие auth
    - API серверы могут перезаписать локальные (если slug совпадает)
    """
    merged = dict(local_types)
    
    # Если approved_keys не передан — собираем из user_servers
    if approved_keys is None:
        approved_keys = set()
        for s in user_servers:
            slug = s.get('server_type') or s.get('slug')
            if slug:
                approved_keys.add(slug)
        # Fallback: если есть заявки но slug пуст — показываем все auth-required
        if not approved_keys and user_servers:
            for api_server in api_servers:
                if api_server.get('requires_auth', False):
                    approved_keys.add(api_server.get('slug', ''))
    
    logger.info(f"merge_server_types: approved_keys={approved_keys}")
    
    # Добавляем серверы из API
    for server in api_servers:
        slug = server.get('slug')
        if not slug:
            continue
        
        # Проверяем доступ: slug в approved или не требует auth
        requires_auth = server.get('requires_auth', False)
        has_access = slug in approved_keys or not requires_auth
        
        if not has_access:
            continue
        
        # Формируем repository из API данных
        repos = server.get('repositories', [])
        repository = None
        if repos:
            repo = repos[0]  # берём первый репозиторий
            repository = {
                'url': repo.get('url', ''),
                'branch': repo.get('branch', 'main'),
                'auth_type': repo.get('auth_type', 'token'),
                'credentials': repo.get('credentials', ''),
                'name': repo.get('name', 'Основной'),
            }
        
        # Преобразуем API формат в локальный формат
        api_type = {
            'name': server.get('name', slug),
            'description': server.get('description', ''),
            'requires_reverse_proxy': server.get('requires_reverse_proxy', False),
            'requires_auth': requires_auth,
            'is_reverse_proxy': slug == 'reverse_proxy',
            'has_web_interface': server.get('has_web_interface', True),
            'default_port': server.get('default_port', 8000),
            'order': server.get('order', 50),
            'can_have_multiple': server.get('can_have_multiple', True),
            'default_folder': slug,
            'repository': repository,
            'from_api': True,  # маркер что из API
            'api_id': server.get('id'),
        }
        
        # Если slug уже есть в локальных — обновляем репозиторий
        if slug in merged:
            existing = merged[slug]
            if repository and not existing.get('repository', {}).get('url', '').startswith('https://github.com/your-org'):
                # Локальный репозиторий placeholder — заменяем на API
                existing['repository'] = repository
                existing['from_api'] = True
                logger.info(f"Updated repo for {slug} from API")
        else:
            merged[slug] = api_type
            logger.info(f"Added server type from API: {slug}")
    
    return merged
