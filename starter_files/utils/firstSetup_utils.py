import hashlib
import os
import secrets
import sys
import webbrowser

from pathlib import Path
from typing import Dict, Optional, Tuple
from starter_files.utils.envStarter_utils import read_env_file, parse_env_content, generate_env_content
from starter_files.utils.i18n_utils import get_available_languages
from starter_files.utils.molule_utils import get
from starter_files.utils.globalVars_utils import get_global

# Обязательные переменные для первоначальной настройки asd sa
REQUIRED_ENV_VARS = [
    'LANGUAGE',
    'ADMIN_LOGIN', 
    'ADMIN_PASSWORD_HASH',
    'APP_SECRET_KEY'
]

def is_first_run(env_path: Path = Path('.env')) -> bool:
    """Проверяет, является ли этот запуск первым"""
    if env_path is None:
        base_dir = get_global('script_path')
        env_path = base_dir / '.env'

    print(f"[DEBUG] Проверка .env файла: {env_path.resolve()}")

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

    print(f"[DEBUG] script_path глобальная переменная: {get_global('script_path')}")
    # Получаем путь относительно запускаемого скрипта
    base_dir = get_global('script_path')
    env_path = base_dir / '.env'
    env_example_path = base_dir / '.env.example'
    print(f"[DEBUG] Путь для .env: {env_path}")
    print(f"[DEBUG] Путь для .env.example: {env_example_path}")

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
            choice = input(f"Выберите язык (1-{len(languages)}): ")
            if choice.isdigit() and 1 <= int(choice) <= len(languages):
                lang_code = list(languages.keys())[int(choice)-1]
                credentials['language'] = languages[lang_code]['this_language']
                break
            print(f"Пожалуйста, введите число от 1 до {len(languages)}")
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

def get_server_url() -> list:
    """Возвращает список всех URL сервера с учетом порта"""
    from starter_files.utils.globalVars_utils import get_global
    from starter_files.utils.molule_utils import get

    docker_port = os.environ.get('dockerPort', '8000')
    ips = get('network','get_all_local_ips')

    return [f"https://{ip}:{docker_port}" for ip in ips]

def open_browser(logger=None):
    """Открывает браузер только при первом запуске"""
    urls = get_server_url()

    print("Сервер запущен. Доступен по адресам:")
    for url in urls:
        print(url)

    if logger:
        for url in urls:
            logger.info(f"Сервер запущен: {url}")

    if os.environ.get('WERKZEUG_RUN_MAIN') is None:
        try:
            webbrowser.open(urls[0])  # Открываем первый
        except Exception as e:
            if logger:
                logger.error(f"Не удалось открыть браузер: {e}")
            print(f"Не удалось открыть браузер: {e}")

