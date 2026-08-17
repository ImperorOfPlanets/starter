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
        'name': 'Конструктор помощников',
        'description': 'Создание и настройка AI-помощников для пользователей (Laravel)',
        'requires_reverse_proxy': True,
        'requires_auth': False,
        'is_reverse_proxy': False,
        'has_web_interface': True,
        'default_port': 8000,
        'order': 1,
        'can_have_multiple': True,
        'default_folder': 'client',
        'docker_compose_path': 'docker/docker-compose.yml',
        'env_example_path': 'docker/.env.example',
        'repository': {
            'name': 'GitFlic',
            'url': 'https://gitflic.ru/project/imperor/client.git',
            'branch': 'main'
        }
    },
    'embeddings': {
        'name': 'Генератор векторов',
        'description': 'Создание эмбеддингов для документов и поиска по ним',
        'requires_reverse_proxy': False,
        'requires_auth': False,
        'is_reverse_proxy': False,
        'has_web_interface': False,
        'default_port': 5000,
        'order': 2,
        'can_have_multiple': True,
        'default_folder': 'embeddings',
        'repository': {
            'name': 'GitFlic',
            'url': 'https://gitflic.ru/project/imperor/embeddings.git',
            'branch': 'main'
        }
    },
    'tts': {
        'name': 'Голосовой сервер',
        'description': 'Синтез речи из текста — озвучка данных (CosyVoice)',
        'requires_reverse_proxy': False,
        'requires_auth': False,
        'is_reverse_proxy': False,
        'has_web_interface': False,
        'default_port': 5001,
        'order': 3,
        'can_have_multiple': True,
        'default_folder': 'tts',
        'repository': {
            'name': 'GitFlic',
            'url': 'https://gitflic.ru/project/imperor/tts.git',
            'branch': 'main'
        }
    },
    'stt': {
        'name': 'Распознавание речи',
        'description': 'Преобразование голоса в текст (Vosk, SpeechBrain)',
        'requires_reverse_proxy': False,
        'requires_auth': False,
        'is_reverse_proxy': False,
        'has_web_interface': False,
        'default_port': 5002,
        'order': 4,
        'can_have_multiple': True,
        'default_folder': 'stt',
        'repository': {
            'name': 'GitFlic',
            'url': 'https://gitflic.ru/project/imperor/stt.git',
            'branch': 'main'
        }
    },
    'browser': {
        'name': 'Автоматизация браузера',
        'description': 'Парсинг сайтов и автоматизация действий в интернете (Playwright)',
        'requires_reverse_proxy': False,
        'requires_auth': False,
        'is_reverse_proxy': False,
        'has_web_interface': False,
        'default_port': 8000,
        'order': 5,
        'can_have_multiple': True,
        'default_folder': 'browser',
        'repository': {
            'name': 'GitFlic',
            'url': 'https://gitflic.ru/project/imperor/browser.git',
            'branch': 'main'
        }
    },
    'slam': {
        'name': 'Навигация дронов',
        'description': 'Картографирование и локализация в реальном времени (ORB-SLAM3)',
        'requires_reverse_proxy': False,
        'requires_auth': False,
        'is_reverse_proxy': False,
        'has_web_interface': False,
        'default_port': 8007,
        'order': 6,
        'can_have_multiple': True,
        'default_folder': 'slam',
        'repository': {
            'name': 'GitFlic',
            'url': 'https://gitflic.ru/project/imperor/slam.git',
            'branch': 'main'
        }
    },
    'yolo': {
        'name': 'Детекция объектов',
        'description': 'Распознавание объектов на фото и видео (YOLO)',
        'requires_reverse_proxy': False,
        'requires_auth': False,
        'is_reverse_proxy': False,
        'has_web_interface': False,
        'default_port': 8008,
        'order': 7,
        'can_have_multiple': True,
        'default_folder': 'yolo',
        'repository': {
            'name': 'GitFlic',
            'url': 'https://gitflic.ru/project/imperor/yolo.git',
            'branch': 'main'
        }
    },
    'voice': {
        'name': 'Голосовой помощник',
        'description': 'Полная обработка голоса: распознавание + синтез + клонирование',
        'requires_reverse_proxy': False,
        'requires_auth': False,
        'is_reverse_proxy': False,
        'has_web_interface': False,
        'default_port': 5000,
        'order': 9,
        'can_have_multiple': True,
        'default_folder': 'voice',
        'repository': {
            'name': 'GitFlic',
            'url': 'https://gitflic.ru/project/imperor/voice.git',
            'branch': 'main'
        }
    },
    'simulator': {
        'name': 'Симулятор дронов',
        'description': 'Тестирование полётов в виртуальной среде (Betaflight + Gazebo)',
        'requires_reverse_proxy': False,
        'requires_auth': False,
        'is_reverse_proxy': False,
        'has_web_interface': True,
        'default_port': 8443,
        'order': 10,
        'can_have_multiple': True,
        'default_folder': 'simulator',
        'docker_compose_path': 'docker/docker-compose.yml',
        'env_example_path': 'docker/.env.example',
        'repository': {
            'name': 'GitFlic',
            'url': 'https://gitflic.ru/project/imperor/sfera.git',
            'branch': 'main'
        }
    },
    'fileserver': {
        'name': 'Файловое хранилище',
        'description': 'Хранение и раздача файлов: фото, видео, документы (Laravel)',
        'requires_reverse_proxy': True,
        'requires_auth': False,
        'is_reverse_proxy': False,
        'has_web_interface': True,
        'default_port': 8000,
        'order': 11,
        'can_have_multiple': True,
        'default_folder': 'fileserver',
        'docker_compose_path': 'docker/docker-compose.yml',
        'env_example_path': 'docker/.env.example',
        'repository': {
            'name': 'GitFlic',
            'url': 'https://gitflic.ru/project/imperor/filesserver.git',
            'branch': 'main'
        }
    },
    'localbackup': {
        'name': 'Локальный бэкап',
        'description': 'Резервное копирование данных на локальном сервере',
        'requires_reverse_proxy': False,
        'requires_auth': False,
        'is_reverse_proxy': False,
        'has_web_interface': False,
        'default_port': 8000,
        'order': 12,
        'can_have_multiple': True,
        'default_folder': 'localbackup',
        'repository': {
            'name': 'GitFlic',
            'url': 'https://gitflic.ru/project/imperor/localbackup.git',
            'branch': 'main'
        }
    },
    'phone': {
        'name': 'Мобильное приложение',
        'description': 'Android-приложение для управления дроном с телефона (Fly Assistant)',
        'requires_reverse_proxy': False,
        'requires_auth': False,
        'is_reverse_proxy': False,
        'has_web_interface': False,
        'default_port': 0,
        'order': 13,
        'can_have_multiple': True,
        'default_folder': 'phone',
        'repository': {
            'name': 'GitFlic',
            'url': 'https://gitflic.ru/project/imperor/phone.git',
            'branch': 'main'
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
