# files/configs/server_types.py

SERVER_TYPES = {
    'reverse_proxy': {
        'name': 'Reverse Proxy',
        'name_en': 'Reverse Proxy',
        'name_cn': '反向代理',
        'description': 'SSL-сертификаты и маршрутизация трафика (Nginx + Let\'s Encrypt)',
        'description_en': 'SSL certificates and traffic routing (Nginx + Let\'s Encrypt)',
        'description_cn': 'SSL证书和流量路由（Nginx + Let\'s Encrypt）',
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
        'name_en': 'AI Assistant',
        'name_cn': 'AI 助手',
        'description': 'Персональный AI-ассистент с мульти-агентной системой, чатом, голосом и управлением серверами',
        'description_en': 'Personal AI assistant with multi-agent system, chat, voice and server management',
        'description_cn': '具有多代理系统、聊天、语音和服务器管理功能的个人AI助手',
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
    'clientv2': {
        'name': 'AI Помощник v2',
        'name_en': 'AI Assistant v2',
        'name_cn': 'AI 助手 v2',
        'description': 'Персональный AI-ассистент v2 с мульти-агентной системой и оптимизированным Docker',
        'description_en': 'Personal AI assistant v2 with multi-agent system and optimized Docker',
        'description_cn': '具有多代理系统和优化Docker的个人AI助手v2',
        'requires_reverse_proxy': True,
        'requires_auth': False,
        'is_reverse_proxy': False,
        'has_web_interface': True,
        'default_port': 80,
        'order': 1,
        'can_have_multiple': True,
        'default_folder': 'clientv2',
        'docker_compose_path': 'docker/docker-compose.yml',
        'env_example_path': 'docker/.env.example',
        'repository': {
            'url': 'https://gitflic.ru/project/imperor/clientv2.git',
            'branch': 'master'
        }
    },
    'embeddings': {
        'name': 'Генератор векторов',
        'name_en': 'Vector Generator',
        'name_cn': '向量生成器',
        'description': 'Создание эмбеддингов для документов и поиска по ним',
        'description_en': 'Creating embeddings for documents and search',
        'description_cn': '为文档创建嵌入向量并进行搜索',
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
        'name_en': 'Voice Server',
        'name_cn': '语音服务器',
        'description': 'Синтез речи из текста — озвучка данных (CosyVoice)',
        'description_en': 'Text-to-speech synthesis (CosyVoice)',
        'description_cn': '文本转语音合成（CosyVoice）',
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
        'name_en': 'Speech Recognition',
        'name_cn': '语音识别',
        'description': 'Преобразование голоса в текст (Vosk, SpeechBrain)',
        'description_en': 'Voice-to-text conversion (Vosk, SpeechBrain)',
        'description_cn': '语音转文本（Vosk, SpeechBrain）',
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
        'name_en': 'Browser Automation',
        'name_cn': '浏览器自动化',
        'description': 'Парсинг сайтов и автоматизация действий в интернете (Playwright)',
        'description_en': 'Website parsing and internet automation (Playwright)',
        'description_cn': '网站解析和互联网自动化（Playwright）',
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
        'name_en': 'Drone Navigation',
        'name_cn': '无人机导航',
        'description': 'Картографирование и локализация в реальном времени (ORB-SLAM3)',
        'description_en': 'Mapping and real-time localization (ORB-SLAM3)',
        'description_cn': '地图构建和实时定位（ORB-SLAM3）',
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
        'name_en': 'Object Detection',
        'name_cn': '物体检测',
        'description': 'Распознавание объектов на фото и видео (YOLO)',
        'description_en': 'Object recognition in photos and video (YOLO)',
        'description_cn': '照片和视频中的物体识别（YOLO）',
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
        'name_en': 'Voice Assistant',
        'name_cn': '语音助手',
        'description': 'Полная обработка голоса: распознавание + синтез + клонирование',
        'description_en': 'Full voice processing: recognition + synthesis + cloning',
        'description_cn': '完整语音处理：识别+合成+克隆',
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
        'name_en': 'Drone Simulator',
        'name_cn': '无人机模拟器',
        'description': 'Тестирование полётов в виртуальной среде (Betaflight + Gazebo)',
        'description_en': 'Flight testing in virtual environment (Betaflight + Gazebo)',
        'description_cn': '虚拟环境中的飞行测试（Betaflight + Gazebo）',
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
        'name_en': 'File Storage',
        'name_cn': '文件存储',
        'description': 'Хранение и раздача файлов: фото, видео, документы (Laravel)',
        'description_en': 'File storage and sharing: photos, videos, documents (Laravel)',
        'description_cn': '文件存储和共享：照片、视频、文档（Laravel）',
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
        'name_en': 'Mobile App',
        'name_cn': '移动应用',
        'description': 'Android-приложение для управления дроном с телефона (Fly Assistant)',
        'description_en': 'Android app for drone control from phone (Fly Assistant)',
        'description_cn': '用于手机控制无人机的Android应用（Fly Assistant）',
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
        'name_en': 'Opencode Server',
        'name_cn': 'Opencode 服务器',
        'description': 'OpenCode HTTPS сервер с Nginx (AI-ассистент)',
        'description_en': 'OpenCode HTTPS server with Nginx (AI assistant)',
        'description_cn': 'OpenCode HTTPS服务器（AI助手）',
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
        'name_en': 'Wake Word Detection',
        'name_cn': '唤醒词检测',
        'description': 'Обучение и использование моделей обнаружения wake words (ключевых фраз/имён)',
        'description_en': 'Wake word detection models training and usage',
        'description_cn': '唤醒词检测模型训练和使用',
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
        'name_en': 'Streaming',
        'name_cn': '流媒体',
        'description': 'Управление стримами: OBS, VK, Twitch, YouTube (Laravel)',
        'description_en': 'Stream management: OBS, VK, Twitch, YouTube (Laravel)',
        'description_cn': '流媒体管理：OBS, VK, Twitch, YouTube（Laravel）',
        'requires_reverse_proxy': True,
        'requires_auth': False,
        'is_reverse_proxy': False,
        'has_web_interface': True,
        'default_port': 8080,
        'order': 18,
        'can_have_multiple': True,
        'default_folder': 'streams',
        'repository': {
            'url': 'https://gitflic.ru/project/imperor/sfera-strimer.git',
            'branch': 'master'
        }
    },
    'social_bridge': {
        'name': 'Social Bridge',
        'name_en': 'Social Bridge',
        'name_cn': '社交桥接',
        'description': 'Мульти-платформенный роутер сообщений: Telegram, VK, Max с Amnezia WG VPN',
        'description_en': 'Multi-platform message router: Telegram, VK, Max with Amnezia WG VPN',
        'description_cn': '多平台消息路由器：Telegram, VK, Max 配合 Amnezia WG VPN',
        'requires_reverse_proxy': False,
        'requires_auth': False,
        'is_reverse_proxy': False,
        'has_web_interface': True,
        'default_port': 5000,
        'order': 19,
        'can_have_multiple': True,
        'default_folder': 'social-router',
        'docker_compose_path': 'docker/docker-compose.yml',
        'env_example_path': 'docker/.env.example',
        'repository': {
            'url': 'https://gitflic.ru/project/imperor/social-bridge.git',
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
