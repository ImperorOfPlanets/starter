import hashlib
import os
import secrets

from pathlib import Path
from typing import Dict, Optional, Tuple
from files.core.utils.env_utils import read_env_file, parse_env_content, generate_env_content
from files.core.utils.i18n_utils import get_available_languages
from files.core.utils.loader_utils import get
from files.core.utils.globalVars_utils import get_global
from files.core.utils.log_utils import LogManager

logger = LogManager.get_logger()

# Обязательные переменные для первоначальной настройки asd sa
REQUIRED_ENV_VARS = [
    'LANGUAGE',
    'ADMIN_LOGIN', 
    'ADMIN_PASSWORD_HASH',
    'APP_SECRET_KEY',
    'TYPE_SERVER'
]

def is_first_run() -> bool:
    """Проверяет, является ли этот запуск первым"""
    base_dir = get_global('script_path')
    env_path = base_dir / '.env'

    logger.info(f"[DEBUG] Проверка .env файла: {env_path.resolve()}")

    if not env_path.exists():
        return True
    current_vars = read_env_file(env_path)
    return not all(var in current_vars for var in REQUIRED_ENV_VARS)

def generate_credentials() -> Dict[str, str]:
    """Генерирует учетные данные для первого запуска"""
    password = secrets.token_urlsafe(8)
    return {
        'login': 'admin_' + secrets.token_hex(2),
        'password': password,
        'password_hash': hashlib.sha256(password.encode()).hexdigest(),
        'app_secret_key': secrets.token_hex(32)
    }

def first_run_setup(interactive: bool = True) -> Tuple[bool, Optional[Dict[str, str]]]:
    """
    Выполняет первоначальную настройку приложения
    
    Args:
        interactive: Режим с пользовательским интерфейсом (False для сервисного режима)
    
    Returns:
        Tuple: (is_first_run: bool, credentials: Optional[dict])
    """
    # Проверяем только в основном процессе
    if not is_first_run():
        return False, None

    logger.info(f"[DEBUG] script_path глобальная переменная: {get_global('script_path')}")
    # Получаем путь относительно запускаемого скрипта
    base_dir = get_global('script_path')
    env_path = base_dir / '.env'
    env_example_path = base_dir / '.env.example'
    logger.info(f"[DEBUG] Путь для .env: {env_path}")
    logger.info(f"[DEBUG] Путь для .env.example: {env_example_path}")

    # Выводим информацию о создании файла
    print(f"\n{'='*50}")
    print("ВЫПОЛНЕНИЕ ПЕРВОНАЧАЛЬНОЙ НАСТРОЙКИ")
    print(f"Создаем файл конфигурации: {env_path}")
    print(f"Используем шаблон: {env_example_path}")
    print(f"{'='*50}\n")

    if not env_example_path.exists():
        print(f"Файл шаблона .env.example не найден в {base_dir}")
        return False, None

    # Выводим информацию о создании файла
    print(f"\nСоздаем файл конфигурации: {env_path}")

    with open(env_example_path, 'r', encoding='utf-8') as f:
        example_content = f.read()
    
    example_vars, example_lines = parse_env_content(example_content)
    credentials = generate_credentials()
    
    if interactive:
        languages = get_available_languages()
        print("\n=== Первоначальная настройка ===")
        print("Доступные языки:")
        
        for i, (code, data) in enumerate(languages.items(), 1):
            print(f"{i}. {data['this_language']} ({code})")
        
        while True:
            try:
                choice = input(f"Выберите язык (1-{len(languages)}): ")
                if choice.isdigit() and 1 <= int(choice) <= len(languages):
                    lang_code = list(languages.keys())[int(choice)-1]
                    credentials['language'] = languages[lang_code]['this_language']
                    break
                print(f"Пожалуйста, введите число от 1 до {len(languages)}")
            except (EOFError, KeyboardInterrupt):
                print("\nПрервано пользователем")
                return False, None
    else:
        lang_code = 'en'  # Язык по умолчанию для сервисного режима
        credentials['language'] = 'English'

    example_vars.update({
        'LANGUAGE': lang_code,
        'ADMIN_LOGIN': credentials['login'],
        'ADMIN_PASSWORD_HASH': credentials['password_hash'],
        'APP_SECRET_KEY': credentials['app_secret_key'],
    })

    with open(env_path, 'w', encoding='utf-8') as f:
        f.write(generate_env_content(example_vars, example_lines))

    if interactive:
        print("\n=== Учетные данные ===")
        print(f"Язык интерфейса: {credentials['language']}")
        print(f"Логин: {credentials['login']}")
        print(f"Пароль: {credentials['password']} (сохраните этот пароль!)")
        print("="*30)

    return True, {
        'login': credentials['login'],
        'password': credentials['password'],
        'language': credentials['language'],
        'app_secret_key': credentials['app_secret_key']
    }

def get_available_server_types():
    """Получает доступные типы серверов из конфигурации"""
    try:
        from files.configs.server_types import SERVER_TYPES
        return SERVER_TYPES
    except ImportError:
        logger.error("Не удалось загрузить конфигурацию типов серверов")
        return {}

def detect_server_type_from_folder():
    """Пытается определить тип сервера по структуре папок"""
    base_dir = get_global('script_path')
    
    # Проверяем наличие common папки для определения типа
    common_dir = base_dir / 'common'
    if common_dir.exists():
        return 'common'
    
    # Проверяем другие признаки
    docker_dir = base_dir / 'docker'
    if docker_dir.exists():
        docker_compose_file = docker_dir / 'docker-compose.yml'
        if docker_compose_file.exists():
            try:
                with open(docker_compose_file, 'r') as f:
                    content = f.read()
                    if 'tei' in content.lower():
                        return 'tei'
                    elif 'tts' in content.lower():
                        return 'TTS'
                    elif 'stt' in content.lower():
                        return 'STT'
                    elif 'browser' in content.lower():
                        return 'BROWSER'
            except:
                pass
    
    return 'client'  # тип по умолчанию

def select_server_type(interactive: bool = True):
    """Выбор типа сервера"""
    server_types = get_available_server_types()
    
    if not server_types:
        logger.warning("Не найдены конфигурации типов серверов")
        return None
    
    if not interactive:
        # В сервисном режиме пытаемся определить автоматически
        detected_type = detect_server_type_from_folder()
        if detected_type in server_types:
            return detected_type
        return list(server_types.keys())[0]  # первый доступный тип
    
    # Интерактивный выбор
    print("\n=== Выбор типа сервера ===")
    print("Доступные типы серверов:")
    
    type_list = list(server_types.keys())
    for i, server_type in enumerate(type_list, 1):
        server_info = server_types[server_type]
        print(f"{i}. {server_info['name']} - {server_info['description']}")
    
    print(f"{len(type_list) + 1}. Автоопределение")
    
    while True:
        try:
            choice = input(f"Выберите тип сервера (1-{len(type_list) + 1}): ")
            if choice.isdigit():
                choice_num = int(choice)
                if 1 <= choice_num <= len(type_list):
                    selected_type = type_list[choice_num - 1]
                    break
                elif choice_num == len(type_list) + 1:
                    # Автоопределение
                    selected_type = detect_server_type_from_folder()
                    if selected_type in server_types:
                        print(f"Автоопределен тип: {server_types[selected_type]['name']}")
                        break
                    else:
                        print("Не удалось определить тип сервера автоматически")
                        continue
            print(f"Пожалуйста, введите число от 1 до {len(type_list) + 1}")
        except (EOFError, KeyboardInterrupt):
            print("\nПрервано пользователем")
            return None
    
    return selected_type

def get_server_url() -> list:
    """Возвращает список всех URL сервера с учетом порта"""
    docker_port = os.environ.get('dockerPort', '8000')
    ips = get('network','get_all_local_ips')
    # Выводим в консоль
    logger.info("Список локальных IP из кеша: %s", ips)

    return [f"https://{ip}:{docker_port}" for ip in ips]

def open_browser() -> None:
    """
    Открывает браузер только при первом запуске вне Docker.
    В Docker-контейнере выводит специальный URL для доступа с хоста.
    """
    is_docker = get_global('running_in_docker')
    docker_port = os.environ.get('dockerPort', '8000')
    urls = get_server_url()

    logger.info("\nСервер запущен. Доступен по адресам:")
    
    # Основной URL для вывода/открытия
    primary_url = None

    if is_docker:
        # В Docker - показываем специальный URL для доступа с хоста
        docker_url = f"https://localhost:{docker_port}"
        logger.info(docker_url)
        logger.info("(Это Docker-контейнер. Используйте этот URL на хост-машине)")
        if logger:
            logger.info(f"Docker-контейнер: доступ через {docker_url}")
        primary_url = docker_url
    else:
        # Не в Docker - показываем все IP
        for url in urls:
            logger.info(url)
            if logger:
                logger.info(f"Сервер запущен: {url}")
        primary_url = urls[0] if urls else None
    '''
    # Открываем браузер только если не в Docker и это основной процесс
    if not is_docker and primary_url and os.environ.get('WERKZEUG_RUN_MAIN') is None:
        try:
            webbrowser.open(primary_url)
        except Exception as e:
            error_msg = f"Не удалось открыть браузер: {e}"
            if logger:
                logger.error(error_msg)
            logger.info(error_msg)'''