import argparse
import os
import platform
import subprocess
import sys
import textwrap
from pathlib import Path

from starter_files.utils import venv_utils
from starter_files.utils.globalVars_utils import GlobalVars, get_global
from starter_files.utils.molule_utils import get

# Получаем информацию о системе и записываем в глобальне переменные
# Но для этого считываем модуль СИСТЕМА и выполняем collect_basic_system_info
get('system','collect_basic_system_info')

def parse_args():
    """Парсит аргументы командной строки"""
    parser = argparse.ArgumentParser()
    parser.add_argument('--service', action='store_true', help='Запуск в сервисном режиме')
    parser.add_argument('--debug', action='store_true', help='Запуск в режиме отладки')
    return parser.parse_args()

def start_service_mode():
    """Запускает сервисный режим"""
    logger = get_global('logger')
    logger.info("Запуск в сервисном режиме...")
    sys.exit(0)

def print_bordered_message(message, title=None, width=70):
    """Печатает сообщение в рамке"""
    print()
    print('=' * width)
    
    if title:
        print(f" {title} ".center(width, '='))
        print('-' * width)
    
    wrapped_lines = []
    for line in message.split('\n'):
        wrapped_lines.extend(textwrap.wrap(line, width=width-4))
    
    for line in wrapped_lines:
        print(f"| {line.ljust(width-4)} |")
    
    print('=' * width)
    print()

def verify_environment():
    """Проверяет окружение перед запуском"""
    # Проверка версии Python
    if not get('system', 'check_python_version'):
        current_version = '.'.join(map(str, sys.version_info[:3]))
        message = f"""
        ТРЕБУЕТСЯ ВМЕШАТЕЛЬСТВО ПЕРВОГО ПРОГРАММИСТА!
        
        Обнаружена устаревшая версия Python: {current_version}
        Для корректной работы требуется Python 3.8 или выше.
        """
        print_bordered_message(message, title="ТРЕБОВАНИЕ К ПЕРВОМУ ПРОГРАММИСТУ", width=80)
        return False
    
    # Проверка .env файла (только в основном процессе)
    if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        env_path = get_global('script_path') / '.env'
        if not env_path.exists():
            print("Файл .env не найден! Создаем базовую конфигурацию...")
            from starter_files.utils.firstSetup_utils import first_run_setup
            is_first_run, credentials = first_run_setup()
            
            if is_first_run and credentials:                
                from dotenv import load_dotenv
                load_dotenv(env_path)
    
    return True

def start_interactive_mode():
    # Обычный режим
    from starter_files.utils.configurateApp_utils import configure_app
    from starter_files.utils.ssl_utils import get_ssl_context
    from starter_files.utils.firstSetup_utils import open_browser
    from dotenv import load_dotenv

    app = configure_app()
    ssl_context = get_ssl_context()
    open_browser()
    app.run(
        host='0.0.0.0',
        port=8000,
        ssl_context=ssl_context,
        debug=True
    )

if __name__ == '__main__':
    # Первым делом проверяем/создаем venv
    if venv_utils.ensure_venv():
        sys.exit(0)

    args = parse_args()
    
    # Проверяем окружение
    if not verify_environment():
        sys.exit(1)

    # Проверка установки зависимостей
    try:
        import flask
        import dotenv
    except ImportError:
        from starter_files.utils.requirements_utils import install_and_restart
        install_and_restart()

    # Устанавливаем глобальный обработчик исключений
    from starter_files.utils.exceptionHandler_utils import ExceptionHandler
    handler = ExceptionHandler()
    sys.excepthook = handler.handle_unhandled_exception

    # Сервисный режим
    if args.service:
        start_service_mode()

    # Обычный режим
    start_interactive_mode()