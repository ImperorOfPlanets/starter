"""
КОНФИГУРАЦИОННЫЙ ФАЙЛ СИСТЕМЫ ОБНОВЛЕНИЯ

Структура конфига:
1. PROJECTS - словарь проектов для обновления
2. BASE_DIRS - базовые директории системы
3. Настройки ограничений запусков
4. Флаги логирования
"""

# ========================
# 1. НАСТРОЙКИ ПРОЕКТОВ
# ========================
PROJECTS = {
    'starter': {
        # URL для скачивания архива проекта (обязательный параметр)
        'DOWNLOAD_URL':'https://gitflic.ru/project/imperor/starter/file/downloadAll?branch=master&format=zip',
        
        # Шаблоны файлов для отслеживания изменений (обязательный параметр)
        # Формат: список строк с glob-шаблонами
        'TARGETS': [
            #'.gitignore',
            'README.md',
            'starter.py',
            'starter_files/**',
            '.env.example'
        ],
        'IGNORED': [
            "starter_files/updates/**",  # Рекурсивно игнорируем updates
            "starter_files/logs/**",     # Рекурсивно игнорируем logs
            "starter_files/web/ssl/**",  # Рекурсивно игнорируем ssl
            "starter_files/web/sessions/**",  # Рекурсивно игнорируем sessions
            "venv/**",  # Рекурсивно игнорируем sessions,
            "**/__pycache__/**",
            "**/*.pyc"
        ],
        
        # Автоматически перезапускать приложение после обновления (опционально)
        'RESTART_AFTER_UPDATE': True
    },
    
    'docker': {
        'DOWNLOAD_URL':'https://gitflic.ru/project/imperor/docker/file/downloadAll?branch=master&format=zip',
        
        'TARGETS': [
            'configs/browser/*',
            'configs/init/*',
            'configs/mariadb/mariadb.cnf',
            'configs/mariadb/conf.d/logging.cnf',
            'configs/nginx/confs/templates/default.conf.template',
            'configs/php/cli/*',
            'configs/php/fpm/*',
            'configs/scripts/*',
            'configs/supervisor/supervisord.conf',
            'configs/transformer/app.py',
            'configs/transformer/requirements.txt',
            'configs/transformer/start.sh',
            'dockerfiles/*',
            'configs/voice/*',
            'configs/voicetts/*',
            '.env.example',
            '.gitignore',
            'Инструкция',
            'check_files.py',
            'docker-compose.example',
            'generate_compose.py'
        ],

        # Шаблоны файлов для ИГНОРИРОВАНИЯ при проверке изменений (опционально)
        'IGNORED': [
            'configs/vpn/*',
            'configs/nginx/certs/*',
            'logs',
            '.env'
        ],
        # Дополнительные файлы для включения в бэкапы (опционально)
        'ADD_IN_BACKUPS': [
            'configs/vpn',
            'configs/nginx',
            'logs',
            'shared',
            '.env'
        ],
        # Критические файлы для docker-проекта, если их нет то считается новой установкой
        'CRITICAL_FILES': [
            'docker-compose.example'
        ],
        'RESTART_AFTER_UPDATE': True,
        
        # Специальные функции для обработки обновлений (опционально)
        # Формат: {'относительный_путь': 'имя_функции'}
        'FUNCTIONS_IF_UPDATE': {
            '.env.example': 'copy_environment_variables'
        }
    }
}

# ========================
# 2. БАЗОВЫЕ ДИРЕКТОРИИ
# ========================
BASE_DIRS = {
    # Директория для распаковки скачанных архивов
    'extracted': './extracted',
    
    # Директория для хранения резервных копий перед обновлением
    'backups': './backups'
}

# ==============================
# 3. НАСТРОЙКИ ОГРАНИЧЕНИЙ ЗАПУСКОВ
# ==============================
from pathlib import Path

# Максимальное количество запусков системы за период
MAX_RUNS_PER_PERIOD = 5

# Длительность периода контроля в минутах
PERIOD_MINUTES = 5

# Файл для записи логов запусков (формат: timestamp)
EXECUTION_LOG_FILE = Path('starter_files') / 'logs' / 'execute.log'

# ========================
# 4. НАСТРОЙКИ ЛОГИРОВАНИЯ
# ========================

# Логировать процесс распаковки архивов (список файлов)
LOGS_EXTRACT = True

# Логировать детали сравнения файлов (хеши, изменения)
LOGS_CHANGES = True

# Логировать процесс создания резервных копий
LOGS_BACKUP = True

# ========================
# 5. НАСТРОЙКИ ПЛАНИРОВЩИКА
# ========================
SCHEDULER_CONFIG = {
    'check_containers': {
        'interval_minutes': 5,
        'function': 'check_docker_containers',
        'enabled': True
    },
    'check_updates': {
        'interval_minutes': 60,
        'function': 'check_for_updates',
        'enabled': True
    },
    'cleanup_logs': {
        'interval_minutes': 1440,  # 24 часа
        'function': 'cleanup_old_logs',
        'enabled': True
    }
}

"""
ГЛОССАРИЙ ШАБЛОНОВ

CRITICAL_FILES - список файлов, обязательных для работы проекта. 
Если отсутствует хотя бы один файл из списка - 
система считает установку новой и выполняет 
полную копию файлов из архива.

Формат: относительные пути от BASE_PATH
Пример: ['main.py', 'configs/base.yaml']
---------------------------------------------------------------
Синтаксис glob-шаблонов для TARGETS/IGNORED:
  *       - любое количество символов в имени файла/папки
  **      - любое количество вложенных папок
  ?       - любой один символ
  [seq]   - любой символ из последовательности
  [!seq]  - любой символ не из последовательности

Примеры:
  'docs/*.txt'    - все .txt файлы в папке docs
  'src/**'        - всё содержимое src (включая подпапки)
  'data?.csv'     - data1.csv, dataA.csv (но не data10.csv)

Особенности:
- Все пути проверяются ОТНОСИТЕЛЬНО BASE_PATH проекта
- Шаблоны применяются к полному пути файла
- Регистрозависимость зависит от ОС
"""
