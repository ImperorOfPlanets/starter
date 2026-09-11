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
        'default_folder': 'revers-proxy',
        'repository': {
            'url': 'https://gitflic.ru/project/imperor/revers-prroksi.git',
            'branch': 'master',
            'type': 'git',
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
            'url': 'https://gitflic.ru/project/imperor/client.git',
            'branch': 'master'
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
            'url': 'https://gitflic.ru/project/imperor/embeddings.git',
            'branch': 'master'
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
        'default_folder': 'voice',
        'repository': {
            'url': 'https://gitflic.ru/project/imperor/voice.git',
            'branch': 'master'
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
        'default_folder': 'voice',
        'repository': {
            'url': 'https://gitflic.ru/project/imperor/voice.git',
            'branch': 'master'
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
            'url': 'https://gitflic.ru/project/imperor/browser.git',
            'branch': 'master'
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
        'default_folder': 'slam-api',
        'repository': {
            'url': 'https://gitflic.ru/project/imperor/slam-api.git',
            'branch': 'master'
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
            'url': 'https://gitflic.ru/project/imperor/yolo.git',
            'branch': 'master'
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
            'url': 'https://gitflic.ru/project/imperor/voice.git',
            'branch': 'master'
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
        'default_folder': 'sfera',
        'repository': {
            'url': 'https://gitflic.ru/project/imperor/sfera.git',
            'branch': 'master'
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
        'default_folder': 'filesserver',
        'repository': {
            'url': 'https://gitflic.ru/project/imperor/files-server.git',
            'branch': 'master'
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
            'url': 'https://gitflic.ru/project/imperor/phono-app.git',
            'branch': 'master'
        }
    },
    'opencode': {
        'name': 'Opencode Server',
        'description': 'OpenCode HTTPS сервер с Nginx (AI-ассистент)',
        'requires_reverse_proxy': False,
        'requires_auth': True,
        'is_reverse_proxy': False,
        'has_web_interface': True,
        'default_port': 2002,
        'order': 14,
        'can_have_multiple': True,
        'default_folder': 'opencode-server',
        'repository': {
            'url': 'https://gitflic.ru/project/imperor/opencode-server.git',
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
        'repository': {
            'url': 'https://gitflic.ru/project/imperor/wake-word.git',
            'branch': 'master'
        }
    },
    'streams': {
        'name': 'Стриминг',
        'description': 'Управление стримами: OBS, VK, Twitch, YouTube (Laravel)',
        'requires_reverse_proxy': True,
        'requires_auth': False,
        'is_reverse_proxy': False,
        'has_web_interface': True,
        'default_port': 8080,
        'order': 18,
        'can_have_multiple': True,
        'default_folder': 'streams2',
        'repository': {
            'url': 'https://gitflic.ru/project/imperor/sfera-strimer.git',
            'branch': 'master'
        }
    }
}


def get_sorted_server_types():
    return sorted(SERVER_TYPES.items(), key=lambda x: x[1].get('order', 999))


def get_singleton_servers():
    return [stype for stype, info in SERVER_TYPES.items() if not info.get('can_have_multiple', True)]


def get_multi_servers():
    return [stype for stype, info in SERVER_TYPES.items() if info.get('can_have_multiple', True)]


DEFAULT_TARGETS_CONFIG = {
    'auto_update': False,
    'check_interval': 3600,
    'targets': {}
}
