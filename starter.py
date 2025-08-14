import argparse
import os
import platform
import subprocess
import sys
import textwrap
from pathlib import Path

from starter_files.utils import venv_utils
from starter_files.utils.globalVars_utils import get_global
from starter_files.utils.oss.default.system import SystemModule

# Устанавливает глобальные переменные
SystemModule.collect_basic_system_info()

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

    from starter_files.utils.firstSetup_utils import first_run_setup
    is_first_run, credentials = first_run_setup()
    if is_first_run and credentials:
        print("\n=== Первичная настройка завершена ===")
        print(f"Логин: {credentials['login']}")
        print(f"Пароль: {credentials['password']}")
        print("Сохраните эти данные!")
        print("="*50 + "\n")

    if os.environ.get('WERKZEUG_RUN_MAIN') is None:
        # Основной процесс FLASK - ПЕРЕЗАПУСКАЕТЬСЯ КОТОРЫЙ
        from dotenv import load_dotenv
        env_file = Path(get_global('script_path')) / '.env'
        load_dotenv(env_file)
        print(f"[DEBUG] Переменные окружения загружены из {env_file}")


    args = parse_args()

    # Сервисный режим
    if args.service:
        start_service_mode()

    # Обычный режим
    start_interactive_mode()