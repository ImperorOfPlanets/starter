"""
КОНФИГУРАЦИЯ РЕПОЗИТОРИЕВ ДЛЯ ОБНОВЛЕНИЯ STARTER

Структура:
- Каждый репозиторий содержит URL для скачивания архива
- Приоритет определяется порядком в списке (первый - основной)
- Система будет пробовать репозитории по порядку до первого успешного
"""

STARTER_REPOSITORIES = [
    {
        'name': 'Основной репозиторий',
        'url': 'https://gitflic.ru/project/imperor/starter/file/downloadAll?branch=master&format=zip',
        'branch': 'master',
        'priority': 1,
        'description': 'Основной репозиторий стартера'
    },
    {
        'name': 'Резервный репозиторий',
        'url': 'https://gitflic.ru/project/imperor/starter/file/downloadAll?branch=main&format=zip',
        'branch': 'main', 
        'priority': 2,
        'description': 'Резервный репозиторий на случай недоступности основного'
    },
    {
        'name': 'Dev репозиторий',
        'url': 'https://gitflic.ru/project/imperor/starter/file/downloadAll?branch=develop&format=zip',
        'branch': 'develop',
        'priority': 3,
        'description': 'Репа для разработки (нестабильная версия)'
    }
]

# Конфигурация файлов для обновления стартера
STARTER_CONFIG = {
    'TARGETS': [
        'README.md',
        'starter.py', 
        'files/**',
        '.env.example',
        'requirements.txt'
    ],
    'IGNORED': [
        "files/update/**",
        "files/logs/**",
        "files/web/ssl/**", 
        "files/web/sessions/**",
        "venv/**",
        "**/__pycache__/**",
        "**/*.pyc",
        "*.log",
        ".git/**"
    ],
    'CRITICAL_FILES': [
        'starter.py',
        'files/__init__.py',
        'files/core/__init__.py'
    ],
    'RESTART_AFTER_UPDATE': True,
    'MAX_RETRIES': 3,
    'TIMEOUT': 30
}

# Настройки проверки обновлений
UPDATE_CHECK_CONFIG = {
    'CHECK_INTERVAL_MINUTES': 60,
    'AUTO_UPDATE': False,
    'NOTIFY_AVAILABLE': True,
    'MIN_CHECK_INTERVAL': 30
}