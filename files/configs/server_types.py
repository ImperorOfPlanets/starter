# files/configs/server_types.py

"""
Секция `update` в SERVER_TYPES — контракт обновления сервера.

Значения по умолчанию живут в ServerstrategyModule.DEFAULT_UPDATE.
Здесь переопределяется только то, что отличается для конкретного типа.

Ключи:
  strategy            php_docker | python_docker | static_docker | composer_module
  auto_update         автообновление по расписанию (по умолчанию выкл)
  allow_dirty         разрешить pull при незакоммиченных изменениях
  force_reset         reset --hard вместо pull (ТЕРЯЕТ локальные правки)
  pull_mode           --ff-only (по умолчанию) | --rebase
  backup              git_bundle / docker_dir
  deps                composer / npm / npm_build / pip: True|False|'auto'
  docker              regenerate_compose / merge_env_example /
                      apply_storage_settings / build / restart
  migrate             True|False|'auto'  (artisan migrate --force)
  health_check        enabled / retries / interval
  rollback_on_failure откат на предыдущий коммит при провале проверки
  timeout             pull / deps / docker / migrate, секунды
"""

# Общий профиль для всех клиентов на PHP/Laravel.
# Клиенты отличаются только репозиторием и названием, порядок обновления
# у них одинаковый.
UPDATE_CLIENT_PHP = {
    'strategy': 'php_docker',
    'auto_update': False,
    'allow_dirty': False,
    'force_reset': False,
    'pull_mode': '--ff-only',
    'backup': {'git_bundle': True, 'docker_dir': True},
    'deps': {
        'composer': 'auto',   # только если composer.lock изменился
        'npm': 'auto',        # только если package.json есть в code/
        'npm_build': True,
    },
    'docker': {
        'regenerate_compose': True,
        'merge_env_example': True,
        'apply_storage_settings': True,
        'build': 'auto',      # только если Dockerfile изменился
        'restart': True,
    },
    'migrate': 'auto',
    'health_check': {'enabled': True, 'retries': 12, 'interval': 5},
    'rollback_on_failure': True,
    'timeout': {'pull': 180, 'deps': 900, 'docker': 900, 'migrate': 600},
}

# Профиль для python-сервисов: git + requirements.txt, без compose-регенерации
UPDATE_PYTHON = {
    'strategy': 'python_docker',
    'auto_update': False,
    'allow_dirty': False,
    'pull_mode': '--ff-only',
    'backup': {'git_bundle': True, 'docker_dir': True},
    'deps': {
        'composer': False,
        'npm': False,
        'pip': 'auto',        # только если requirements.txt изменился
    },
    'docker': {
        'regenerate_compose': True,
        'merge_env_example': True,
        'apply_storage_settings': False,
        'build': 'auto',
        'restart': True,
    },
    'migrate': False,
    'health_check': {'enabled': True, 'retries': 12, 'interval': 5},
    'rollback_on_failure': True,
    'timeout': {'pull': 180, 'deps': 600, 'docker': 900, 'migrate': 600},
}

# Модули, которые ставятся внутрь клиента через composer require.
# Обновление модуля — это composer update пакета внутри чужого code/,
# плюс миграции и пересоздание php-контейнера.
UPDATE_COMPOSER_MODULE = {
    'strategy': 'composer_module',
    'auto_update': False,
    'backup': {'git_bundle': False, 'docker_dir': False},
    'deps': {'composer': True, 'npm': False, 'pip': False},
    'migrate': True,
    'docker': {'restart': False, 'regenerate_compose': False,
               'merge_env_example': False, 'apply_storage_settings': False},
    'rollback_on_failure': True,
    'timeout': {'pull': 60, 'deps': 900, 'docker': 300, 'migrate': 600},
}


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
        # Явная стратегия: nginx + сертификаты, зависимостей нет
        'strategy': 'static_docker',
        'update': {
            'deps': {'composer': False, 'npm': False, 'pip': False},
            'migrate': False,
        },
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
        'is_client': True,
        'update': UPDATE_CLIENT_PHP,
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
        'is_client': True,
        'update': UPDATE_CLIENT_PHP,
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
        'update': UPDATE_PYTHON,
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
        'update': UPDATE_PYTHON,
        'repo_root': True,
        'repository': {
            'url': 'https://gitflic.ru/project/imperor/genvoice.git',
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
        'update': UPDATE_PYTHON,
        'repo_root': True,
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
        'update': UPDATE_PYTHON,
        'repository': {
            'url': 'https://gitflic.ru/project/imperor/browser.git',
            'branch': 'master'
        }
    },
    'slam': {
        'name': 'SLAM — карта комнаты',
        'name_en': 'SLAM Room Mapping',
        'name_cn': 'SLAM 房间建图',
        'description': 'Карта комнаты с камеры телефона: визуальная одометрия, детекция объектов, память «где что находится»',
        'description_en': 'Room mapping from phone camera: visual odometry, object detection, "where is it" memory',
        'description_cn': '用手机摄像头进行房间建图：视觉里程计、物体检测、「东西在哪」记忆',
        'requires_reverse_proxy': False,
        'requires_auth': False,
        'is_reverse_proxy': False,
        'has_web_interface': False,
        'default_port': 8009,
        'order': 6,
        'can_have_multiple': True,
        # Репозиторий содержит три сервиса (.py) и docker/ с композом.
        # Стартер клонирует его в <путь>/code, поэтому .py лежат в корне репо,
        # а docker/ — под docker/, как и требует install_server.
        'default_folder': 'slam_server',
        'update': UPDATE_PYTHON,
        'repo_root': True,
        'repository': {
            'url': 'https://gitflic.ru/project/imperor/slam-api.git',
            'branch': 'master'
        },
        # Подсказка для UI: какие порты занимает стек
        'ports': {
            'slam': 8007,
            'yolo': 8008,
            'api': 8009,
        },
        # Зависимости: кадры можно складывать в файловый сервер
        'optional_servers': ['fileserver'],
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
        'update': UPDATE_PYTHON,
        'repository': {
            'url': 'https://gitflic.ru/project/imperor/yolo.git',
            'branch': 'master'
        }
    },
    'carto_v2': {
        'name': 'Картография v2',
        'name_en': 'Cartography v2',
        'name_cn': '制图 v2',
        'description': 'Дистрибутивная картография и семантическое сканирование помещений v2: AR-поза клиента, EMA, многолучевая триангуляция, зоны OPEN/CLOSED/FORBIDDEN/PRIVATE, фолбэк-SLAM на LK-потоке. Интерфейс совместим с slam v1',
        'description_en': 'Distributed mapping and semantic space scanning v2: client AR-pose, EMA, multi-ray triangulation, OPEN/CLOSED/FORBIDDEN/PRIVATE zones, LK-flow fallback SLAM. Interface compatible with slam v1',
        'description_cn': '分布式制图与语义空间扫描 v2：客户端 AR 位姿、EMA、多射线三角测量、OPEN/CLOSED/FORBIDDEN/PRIVATE 区域、LK 流回退 SLAM。接口与 slam v1 兼容',
        'requires_reverse_proxy': False,
        'requires_auth': False,
        'is_reverse_proxy': False,
        'has_web_interface': True,
        'default_port': 8009,
        'order': 8,
        'can_have_multiple': True,
        'default_folder': 'carto-v2',
        # Корневой репозиторий: git в корне проекта, code/ и docker/ — внутри
        # (как у core/stt/streams), а не git внутри code/ (как у Laravel).
        'repo_root': True,
        'docker_compose_path': 'docker/docker-compose.yml',
        'env_example_path': 'docker/.env.example',
        'update': UPDATE_PYTHON,
        'repository': {
            'url': 'https://gitflic.ru/project/imperor/cartography.git',
            'branch': 'master'
        },
        'ports': {
            'api': 8009,
            'yolo': 8008,
        },
        'optional_servers': ['yolo', 'fileserver'],
    },
    'log_scanner': {
        'name': 'Мониторинг логов',
        'name_en': 'Log Scanner',
        'name_cn': '日志扫描器',
        'description': 'Сканирование логов всех проектов локальной моделью: правила + TF-IDL/LogReg классификация по уровням critical/error/security/warning',
        'description_en': 'Scan logs of all projects with a local model: rules + TF-IDF/LogReg classification into critical/error/security/warning',
        'description_cn': '使用本地模型扫描所有项目的日志：规则 + TF-IDF/LogReg 分类为 critical/error/security/warning',
        'requires_reverse_proxy': False,
        'requires_auth': False,
        'is_reverse_proxy': False,
        'has_web_interface': True,
        'default_port': 8011,
        'order': 20,
        'can_have_multiple': True,
        'default_folder': 'log-scanner',
        'repo_root': True,
        'docker_compose_path': 'docker/docker-compose.yml',
        'env_example_path': 'docker/.env.example',
        'update': UPDATE_PYTHON,
        'repository': {
            'url': '',
            'branch': 'master'
        },
        'ports': {'api': 8011},
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
        'update': UPDATE_PYTHON,
        'repo_root': True,
        'repository': {
            'url': 'https://gitflic.ru/project/imperor/translator.git',
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
        'update': UPDATE_PYTHON,
        'repository': {
            'url': 'https://gitflic.ru/project/imperor/sfera.git',
            'branch': 'master'
        }
    },
    'iskra': {
        'name': 'ИСКРА — клинические рекомендации',
        'name_en': 'ISKRA — Clinical Recommendations',
        'name_cn': 'ИСКРА — 临床指南',
        'description': 'Интеллектуальная система клинических рекомендаций Минздрава РФ: агент-секретарь, поиск по 755 КР, PWA, админка',
        'description_en': 'Clinical recommendations system for Minzdrav: agent gate, search over 755 documents, PWA, admin panel',
        'description_cn': '卫生部临床指南智能系统：智能体网关、755 份文档检索、PWA、管理后台',
        'requires_reverse_proxy': True,
        'requires_auth': True,
        'is_reverse_proxy': False,
        'has_web_interface': True,
        'default_port': 8082,
        'order': 13,
        'can_have_multiple': False,
        'default_folder': 'cr-on-opencode',
        'update': UPDATE_PYTHON,
        'repository': {
            'url': 'https://gitflic.ru/project/imperor/iskra.git',
            'branch': 'master'
        },
        'ports': {
            'https': 8082,
            'http': 8084,
            'nginx_http': 80,
        },
        # Справочник ОКПДТР подтягивается раз в месяц по расписанию,
        # жёсткой зависимости от парсера нет — есть своя копия должностей.
        'used_by': [],
        'depends_on': [],
        'references': [
            {'path': '../cr-system/src/data', 'description': '755 клинических рекомендаций Минздрава РФ (только чтение)'},
            {'path': '../OKPDTR-SYNC/src/data', 'description': 'Справочник ОКПДТР — обновление раз в месяц, опционально'},
        ],
    },
    'okpdtr-sync': {
        'name': 'ОКПДТР парсер',
        'name_en': 'OKPDTR Parser',
        'name_cn': 'ОКПДТР 解析器',
        'description': 'Парсер классификатора профессий ОКПДТР (ОК 016-2025): скачивание, проверка, обновление, раздача по HTTP',
        'description_en': 'OKPDTR classifier parser (OK 016-2025): download, verify, update, HTTP distribution',
        'description_cn': 'ОКПДТР 分类解析器 (ОК 016-2025)：下载、校验、更新、HTTP 分发',
        'requires_reverse_proxy': False,
        'requires_auth': False,
        'is_reverse_proxy': False,
        'has_web_interface': False,
        'default_port': 8083,
        'order': 12,
        'can_have_multiple': False,
        'default_folder': 'OKPDTR-SYNC',
        'update': UPDATE_PYTHON,
        'repository': {
            'url': 'https://gitflic.ru/project/imperor/okpdtr-sync.git',
            'branch': 'master'
        },
        # Данные ОКПДТР читают другие проекты (ИСКРА и др.)
        'used_by': ['cr-on-opencode'],
    },
    'fileserver': {
        'name': 'Файловое хранилище',
        'name_en': 'File Storage',
        'name_cn': '文件存储',
        'description': 'Хранение и раздача файлов: фото, видео, документы. Выбор размера хранилища или FTP',
        'description_en': 'File storage and sharing: photos, videos, documents. Choose storage size or FTP',
        'description_cn': '文件存储和共享：照片、视频、文档。可选择存储容量或 FTP',
        'requires_reverse_proxy': True,
        'requires_auth': False,
        'is_reverse_proxy': False,
        'has_web_interface': True,
        'default_port': 8000,
        'order': 11,
        'can_have_multiple': True,
        'default_folder': 'filesserver',
        'update': UPDATE_PYTHON,
        'repository': {
            'url': 'https://gitflic.ru/project/imperor/files-server.git',
            'branch': 'master'
        },
        'ports': {
            'nginx_http': 8000,
            'nginx_https': 8001,
            'php': 8002,
            'mariadb': 8003,
        },
        # Кто обращается к файловому серверу за кадрами/файлами
        'used_by': ['slam', 'clientv2'],
        # Пользователь выбирает при установке: размер хранилища ИЛИ FTP.
        # Эти значения попадают в docker/.env при установке сервера.
        'storage_settings': {
            'STORAGE_TYPE': 'local',        # local | ftp
            'STORAGE_QUOTA_GB': '50',       # размер хранилища, ГБ (0 = без лимита)
            'STORAGE_QUOTA_GB_CHOICES': ['10', '50', '100', '500', '1000', '0'],
            'FTP_HOST': '',
            'FTP_PORT': '21',
            'FTP_USER': '',
            'FTP_PASSWORD': '',
            'FTP_PATH': '/upload',
        },
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
        'update': UPDATE_PYTHON,
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
        'update': UPDATE_PYTHON,
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
        'update': UPDATE_PYTHON,
        'repo_root': True,
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
        'requires_auth': True,
        'is_reverse_proxy': False,
        'has_web_interface': True,
        'default_port': 8080,
        'order': 18,
        'can_have_multiple': True,
        'default_folder': 'streams',
        'update': UPDATE_PYTHON,
        'repo_root': True,
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
        'update': UPDATE_PYTHON,
        'repository': {
            'url': 'https://gitflic.ru/project/imperor/social-bridge.git',
            'branch': 'master'
        }
    },
    'wall': {
        'name': 'Стена/Посты',
        'name_en': 'Wall/Posts',
        'name_cn': '墙/帖子',
        'description': 'Модуль клиента — ставится внутрь через composer require',
        'description_en': 'Post publication and wall (client module)',
        'description_cn': '帖子发布和墙（客户端模块）',
        'requires_reverse_proxy': False,
        'requires_auth': False,
        'is_reverse_proxy': False,
        'has_web_interface': True,
        'default_port': None,
        'order': 100,
        'can_have_multiple': False,
        'default_folder': 'client-wall',
        'is_module': True,
        'composer_package': 'imperor/wall',
        'module_path': 'C:/control/WALL',
        'update': UPDATE_COMPOSER_MODULE,
        'repository': {
            'url': 'https://gitflic.ru/project/imperor/client-wall.git',
            'branch': 'master'
        }
    },
    'shop': {
        'name': 'Магазин',
        'name_en': 'Shop',
        'name_cn': '商店',
        'description': 'Модуль клиента — ставится внутрь через composer require',
        'description_en': 'Online store with catalog and cart (client module)',
        'description_cn': '带目录和购物车的网上商店（客户端模块）',
        'requires_reverse_proxy': False,
        'requires_auth': False,
        'is_reverse_proxy': False,
        'has_web_interface': True,
        'default_port': None,
        'order': 200,
        'can_have_multiple': False,
        'default_folder': 'client-shop',
        'is_module': True,
        'composer_package': 'imperor/shop',
        'module_path': 'C:/control/SHOP',
        'update': UPDATE_COMPOSER_MODULE,
        'repository': {
            'url': 'https://gitflic.ru/project/imperor/client-shop.git',
            'branch': 'master'
        }
    },
    'pages': {
        'name': 'Страницы',
        'name_en': 'Pages',
        'name_cn': '页面',
        'description': 'Модуль клиента — ставится внутрь через composer require',
        'description_en': 'CMS pages (client module)',
        'description_cn': 'CMS页面（客户端模块）',
        'requires_reverse_proxy': False,
        'requires_auth': False,
        'is_reverse_proxy': False,
        'has_web_interface': True,
        'default_port': None,
        'order': 300,
        'can_have_multiple': False,
        'default_folder': 'client-pages',
        'is_module': True,
        'composer_package': 'imperor/pages',
        'module_path': 'C:/control/PAGES',
        'update': UPDATE_COMPOSER_MODULE,
        'repository': {
            'url': 'https://gitflic.ru/project/imperor/client-pages.git',
            'branch': 'master'
        }
    },
    'payments': {
        'name': 'Платежи',
        'name_en': 'Payments',
        'name_cn': '支付',
        'description': 'Модуль клиента — ставится внутрь через composer require',
        'description_en': 'Payment processing (client module)',
        'description_cn': '支付处理（客户端模块）',
        'requires_reverse_proxy': False,
        'requires_auth': False,
        'is_reverse_proxy': False,
        'has_web_interface': True,
        'default_port': None,
        'order': 400,
        'can_have_multiple': False,
        'default_folder': 'client-payments',
        'is_module': True,
        'composer_package': 'imperor/payments',
        'module_path': 'C:/control/PAYMENTS',
        'update': UPDATE_COMPOSER_MODULE,
        'repository': {
            'url': 'https://gitflic.ru/project/imperor/client-payments.git',
            'branch': 'master'
        }
    },
    'roles': {
        'name': 'Роли',
        'name_en': 'Roles',
        'name_cn': '角色',
        'description': 'Модуль клиента — ставится внутрь через composer require',
        'description_en': 'Roles and permissions myidon.site (client module)',
        'description_cn': 'myidon.site的角色和权限（客户端模块）',
        'requires_reverse_proxy': False,
        'requires_auth': False,
        'is_reverse_proxy': False,
        'has_web_interface': True,
        'default_port': None,
        'order': 500,
        'can_have_multiple': False,
        'default_folder': 'client-roles',
        'is_module': True,
        'composer_package': 'imperor/client-roles',
        'module_path': 'C:/control/ROLES',
        'update': UPDATE_COMPOSER_MODULE,
        'repository': {
            'url': 'https://gitflic.ru/project/imperor/client-roles.git',
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
