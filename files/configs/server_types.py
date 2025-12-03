"""
КОНФИГУРАЦИЯ ТИПОВ СЕРВЕРОВ И ИХ РЕПОЗИТОРИЕВ
"""

SERVER_TYPES = {
    'client': {
        'name': 'Client Server',
        'description': 'Веб-сервер для клиентской части бота с пользовательским интерфейсом',
        'repositories': [
            {
                'name': 'main',
                'url': 'https://gitflic.ru/project/imperor/client.git',
                'branch': 'master',
                'targets_config': 'targets.json'  # Конфиг целей обновления
            }
        ]
    },
    'tei': {
        'name': 'Text Embeddings Server',
        'description': 'Сервер для работы с текстовыми эмбеддингами (векторными представлениями)',
        'repositories': [
            {
                'name': 'main',
                'url': 'https://gitflic.ru/project/imperor/api-server.git',
                'branch': 'master',
                'targets_config': 'targets.json'
            }
        ]
    },
    'TTS': {
        'name': 'Text-to-Speech Server',
        'description': 'Сервер для синтеза речи из текста (Text-to-Speech)',
        'repositories': [
            {
                'name': 'main', 
                'url': 'https://gitflic.ru/project/imperor/tts-server.git',
                'branch': 'master',
                'targets_config': 'targets.json'
            }
        ]
    },
    'STT': {
        'name': 'Speech-to-Text Server',
        'description': 'Сервер для распознавания речи и преобразования аудио в текст',
        'repositories': [
            {
                'name': 'main',
                'url': 'https://gitflic.ru/project/imperor/stt-server.git',
                'branch': 'master',
                'targets_config': 'targets.json'
            }
        ]
    },
    'BROWSER': {
        'name': 'Browser Automation Server',
        'description': 'Сервер для автоматизации работы с браузером и веб-скрапинга',
        'repositories': [
            {
                'name': 'main',
                'url': 'https://gitflic.ru/project/imperor/browser-server.git',
                'branch': 'master',
                'targets_config': 'targets.json'
            }
        ]
    }
}

# Структура репозиториев по умолчанию
DEFAULT_REPO_STRUCTURE = {
    'code': 'code/',      # Папка с кодом приложения
    'docker': 'docker/',  # Папка с Docker конфигурацией
    'docs': 'docs/'       # Документация (опционально)
}

# Конфигурация целей обновления по умолчанию
DEFAULT_TARGETS_CONFIG = {
    'TARGETS': [
        'code/**',
        'docker/**',
        '.env.example',
        'README.md',
        'requirements.txt',
        '*.py',
        '*.yaml',
        '*.yml'
    ],
    'IGNORED': [
        '**/__pycache__/**',
        '**/*.pyc',
        '**/.git/**',
        '**/node_modules/**',
        '**/.venv/**',
        '**/venv/**',
        '**/logs/**',
        '**/tmp/**'
    ],
    'CRITICAL_FILES': [
        'docker/docker-compose.yml',
        'docker/docker-compose.example',
        'code/requirements.txt',
        'code/main.py'
    ],
    'RESTART_AFTER_UPDATE': True
}