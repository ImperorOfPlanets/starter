# files/configs/server_types.py

SERVER_TYPES = {
    'reverse_proxy': {
        'name': 'Reverse Proxy',
        'description': 'SSL-сертификаты и маршрутизация трафика (Nginx + Let\'s Encrypt)',
        'requires_reverse_proxy': False,
        'requires_auth': False,
        'is_reverse_proxy': True,
        'has_web_interface': True,
        'default_port': 80,
        'order': 0,
        'can_have_multiple': False,
        'default_folder': 'reverse_proxy',
        'repository': {
            'url': 'https://gitflic.ru/project/imperor/revers-prroksi',
            'branch': 'main',
            'type': 'git',
            'docker_compose_path': 'docker/docker-compose.yml',
            'env_example_path': 'docker/.env.example'
        }
    },
    'client': {
        'name': 'AI Помощник',
        'description': 'Персональный AI-ассистент с мульти-агентной системой, чатом, голосом и управлением серверами',
        'requires_reverse_proxy': True,
        'requires_auth': False,
        'is_reverse_proxy': False,
        'has_web_interface': True,
        'default_port': 80,
        'order': 1,
        'can_have_multiple': True,
        'default_folder': 'client',
        'docker_compose_path': 'docker/docker-compose.yml',
        'env_example_path': 'docker/.env.example',
        'repository': {
            'name': 'GitFlic',
            'url': 'https://gitflic.ru/project/imperor/client.git',
            'branch': 'master'
        }
    },
    'wake_word': {
        'name': 'Обнаружение имён',
        'description': 'Обучение и использование моделей обнаружения wake words (ключевых фраз/имён)',
        'requires_reverse_proxy': False,
        'requires_auth': False,
        'is_reverse_proxy': False,
        'has_web_interface': True,
        'default_port': 8010,
        'order': 17,
        'can_have_multiple': True,
        'default_folder': 'wake_word',
        'docker_compose_path': 'docker/docker-compose.yml',
        'env_example_path': 'docker/.env.example',
        'repository': {
            'name': 'GitFlic',
            'url': 'https://gitflic.ru/project/imperor/wake-word.git',
            'branch': 'master'
        }
    }
}


def get_sorted_server_types():
    """Возвращает список типов серверов, отсортированный по полю order"""
    return sorted(SERVER_TYPES.items(), key=lambda x: x[1].get('order', 999))


def get_singleton_servers():
    """Возвращает список типов серверов, которые могут быть установлены только в одном экземпляре"""
    return [stype for stype, info in SERVER_TYPES.items() if not info.get('can_have_multiple', True)]


def get_multi_servers():
    """Возвращает список типов серверов, которые могут быть установлены в нескольких экземплярах"""
    return [stype for stype, info in SERVER_TYPES.items() if info.get('can_have_multiple', True)]


DEFAULT_TARGETS_CONFIG = {
    'auto_update': False,
    'check_interval': 3600,
    'targets': {}
}
