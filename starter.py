import argparse
import os
import platform
import subprocess
import sys
from pathlib import Path

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

if __name__ == '__main__':
    args = parse_args()

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

