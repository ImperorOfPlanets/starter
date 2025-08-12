import argparse
import os
import platform
import subprocess
import sys
import textwrap
from pathlib import Path
from starter_files.utils import venv_utils

def parse_args():
    """Парсит аргументы командной строки"""
    parser = argparse.ArgumentParser()
    parser.add_argument('--service', action='store_true', help='Запуск в сервисном режиме')
    return parser.parse_args()

def start_service_mode():
    logger.info("Запуск в сервисном режиме...")
    sys.exit(0)

def start_interactive_mode():
    # Обычный режим
    from starter_files.utils.configurate_app import configure_app
    from starter_files.web.utils.ssl import get_ssl_context
    from starter_files.utils.first_setup_utils import open_browser
    from dotenv import load_dotenv

    # Проверка .env
    script_dir = Path(sys.argv[0]).absolute().parent
    env_path = script_dir / '.env'
    print("Путь до файла файла .env ...")
    print(env_path)
    if env_path.exists():
        load_dotenv(env_path, override=True)

    app = configure_app()
    ssl_context = get_ssl_context()
    open_browser()
    app.run(
        host='0.0.0.0',
        port=8000,
        ssl_context=ssl_context,
        debug=True
    )

def print_bordered_message(message, title=None, width=70):
    """Печатает сообщение в рамке"""
    print()
    print('=' * width)
    
    if title:
        print(f" {title} ".center(width, '='))
        print('-' * width)
    
    # Разбиваем сообщение на строки с переносом слов
    wrapped_lines = []
    for line in message.split('\n'):
        wrapped_lines.extend(textwrap.wrap(line, width=width-4))
    
    # Печатаем строки с отступами
    for line in wrapped_lines:
        print(f"| {line.ljust(width-4)} |")
    
    print('=' * width)
    print()

def check_python_version():
    """Проверяет версию Python и выводит сообщения"""
    current_version = sys.version.split()[0]
    version_info = sys.version_info
    
    print(f"Current Python version: {current_version}")
    print(f"Python executable: {sys.executable}")
    
    if version_info < (3, 8):
        # Формируем информационное сообщение для первого программиста
        message = f"""
        ТРЕБУЕТСЯ ВМЕШАТЕЛЬСТВО ПЕРВОГО ПРОГРАММИСТА!
        
        Обнаружена устаревшая версия Python: {current_version}
        Для корректной работы требуется Python 3.8 или выше.
        
        Причина:
        Установщик не смог автоматически установить Python 3.8+ 
        для вашей системы.
        
        Решение:
        1. Откройте файл конфигурации variables.sh
        2. Найдите секцию для вашей ОС: {get_os_info()}
        3. Добавьте команды для установки Python 3.8+
        4. Протестируйте установку на чистой системе
        
        После исправления скрипт будет работать корректно.
        """
        
        print_bordered_message(
            message, 
            title="ТРЕБОВАНИЕ К ПЕРВОМУ ПРОГРАММИСТУ", 
            width=80
        )
        return False
    
    # Сообщение для второго программиста
    message = f"""
    ВЕРСИЯ PYTHON СООТВЕТСТВУЕТ ТРЕБОВАНИЯМ ({current_version})
    
    Дальнейшая работа скрипта выполняется в зоне ответственности
    второго программиста.
    
    Вы можете продолжать разработку функционала приложения,
    не беспокоясь о совместимости версий Python.
    """
    
    print_bordered_message(
        message, 
        title="РАБОТА ВТОРОГО ПРОГРАММИСТА", 
        width=80
    )
    return True

def get_os_info():
    """Возвращает информацию об ОС в формате (дистрибутив, версия)"""
    try:
        if os.path.exists('/etc/os-release'):
            with open('/etc/os-release') as f:
                data = f.read()
            
            os_info = {}
            for line in data.splitlines():
                if '=' in line:
                    key, value = line.split('=', 1)
                    os_info[key] = value.strip().strip('"')
            
            distro = os_info.get('ID', '').lower()
            version = os_info.get('VERSION_ID', '')
            
            return f"{distro}-{version}"
    
    except Exception:
        pass
    
    return f"{platform.system().lower()}-{platform.release()}"

if __name__ == '__main__':
    
    # Первым делом проверяем/создаем venv
    if venv_utils.ensure_venv():
        # Если произошел перезапуск в venv, этот код не выполнится
        # После перезапуска мы продолжим с начала скрипта уже в venv
        sys.exit(0)

    args = parse_args()

    # Первым делом проверяем версию Python
    if not check_python_version():
        # Если версия не соответствует, завершаем работу
        print("\nУстановка прервана: требуется корректировка конфигурации.")
        # sys.exit(1)

    # Проверка установки зависимостей
    try:
        import flask
        import dotenv
    except ImportError:
        from starter_files.utils.requirements_check import install_and_restart
        install_and_restart()

    # Получаем инфомрацию о системе и зхаписываем в глоабльыне переменные
    from starter_files.utils.sysinfo import collect_basic_system_info
    collect_basic_system_info()

    # Устанавливаем глобальный обработчик исключений
    from starter_files.utils.exception_handler import ExceptionHandler
    handler = ExceptionHandler()
    sys.excepthook = handler.handle_unhandled_exception

    # Проверка и установка всех нужных утилит в зависимсости от ОС

    # Проверка только в основном процессе
    if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        # Проверка .env
        script_dir = Path(sys.argv[0]).absolute().parent
        env_path = script_dir / '.env'
        if not env_path.exists():
            print("Файл .env не найден! Создаем базовую конфигурацию...")
            from starter_files.utils.first_setup_utils import first_run_setup
            is_first_run, credentials = first_run_setup()
            
            if is_first_run and credentials:                
                # Перечитываем .env после создания
                from dotenv import load_dotenv
                load_dotenv(env_path)

    # Сервисный режим
    if args.service:
        start_service_mode()

    # Обычный режим
    start_interactive_mode()

