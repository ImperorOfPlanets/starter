import argparse
import sys

from starter_files.utils.configurate_app import configure_app
from starter_files.utils.first_setup_utils import first_run_setup, is_first_run, open_browser
from starter_files.utils.logger import get_logger

# Получаем аргументы запуска
def parse_args():
    """Парсит аргументы командной строки"""
    parser = argparse.ArgumentParser()
    parser.add_argument('--service', action='store_true', help='Запуск в сервисном режиме')
    return parser.parse_args()

args = parse_args()

# Инициализируем логгер
logger = get_logger()

if __name__ == '__main__':
    # Сервисный режим
    if args.service:
           
        if is_first_run():
            logger.error("Первоначальная настройка не выполнена!")
            sys.exit(1)
        logger.info("Запуск в сервисном режиме...")

    # Обычный режим
    else:
        # Инициализация приложения
        app = configure_app()

        # Передаем в приложение логгер
        app.logger = logger

        is_first_run_flag, credentials = first_run_setup()
        
        if is_first_run_flag and credentials:
            logger.info("\n=== Учетные данные ===")
            logger.info(f"Язык интерфейса: {credentials['language']}")
            logger.info(f"Логин: {credentials['login']}")
            logger.info(f"Пароль: {credentials['password']}")
            logger.info("="*30)

        # Импорт и регистрация роутов
        from starter_files.web.routes import routes
        app.register_blueprint(routes)

        # ssl
        from starter_files.web.utils.ssl import get_ssl_context
        ssl_context = get_ssl_context()

        open_browser()
        
        # Запуск сервера
        app.run(
            host='0.0.0.0',
            port=8000,
            ssl_context=ssl_context,
            debug=True
        )