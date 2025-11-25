"""
КОНФИГУРАЦИЯ ТИПОВ СЕРВЕРОВ И ИХ РЕПОЗИТОРИЕВ
"""

SERVER_TYPES = {
    'client': {
        'name': 'Client Server',
        'description': 'Стандартный веб-сервер кликента бота',
        'repositories': [
            {
                'name': 'main',
                'url': 'https://gitflic.ru/project/imperor/client.git',
                'branch': 'master'
            }
        ]
    },
    'tei': {
        'name': 'Emmbendings Server',
        'description': 'Сервер c ПО для получения векторовссссссс',
        'repositories': [
            {
                'name': 'main',
                'url': 'https://gitflic.ru/project/imperor/api-server.git',
                'branch': 'master'
            }
        ]
    },
    'TTS': {
        'name': 'TTS Server',
        'description': 'Сервер баз данных',
        'repositories': [
            {
                'name': 'main', 
                'url': 'https://gitflic.ru/project/imperor/db-server.git',
                'branch': 'master'
            }
        ]
    },
    'STT': {
        'name': 'STT Server',
        'description': 'Сервер мониторинга',
        'repositories': [
            {
                'name': 'main',
                'url': 'https://gitflic.ru/project/imperor/monitoring-server.git',
                'branch': 'master'
            }
        ]
    },
    'BROWSER': {
        'name': 'Browser Server',
        'description': 'Сервер мониторинга',
        'repositories': [
            {
                'name': 'main',
                'url': 'https://gitflic.ru/project/imperor/monitoring-server.git',
                'branch': 'master'
            }
        ]
    }
}

# Структура репозиториев
REPO_STRUCTURE = {
    'code': 'code/',      # Папка с кодом приложения
    'docker': 'docker/',  # Папка с Docker конфигурацией
    'docs': 'docs/'       # Документация (опционально)
}