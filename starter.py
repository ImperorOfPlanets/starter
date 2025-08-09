import argparse
import os
import sys

def parse_args():
    """Парсит аргументы командной строки"""
    parser = argparse.ArgumentParser()
    parser.add_argument('--service', action='store_true', help='Запуск в сервисном режиме')
    return parser.parse_args()

def main():
    args = parse_args()
    
    # Первичная проверка зависимостей
    try:
        import flask  # Ключевая зависимость для проверки
    except ImportError:
        from starter_files.utils.requirements_check import install_and_restart
        install_and_restart()

    # Основное приложение
    from starter_files.utils.logger import get_logger
    logger = get_logger()

    # Сервисный режим
    if args.service:
        from starter_files.utils.first_setup_utils import is_first_run
        
        if is_first_run():
            logger.error("Первоначальная настройка не выполнена!")
            sys.exit(1)
        logger.info("Запуск в сервисном режиме...")
        # Здесь должна быть логика сервисного режима
        sys.exit(0)

    # Обычный режим
    from starter_files.utils.configurate_app import configure_app
    from starter_files.web.routes import routes
    from starter_files.web.utils.ssl import get_ssl_context
    from starter_files.utils.first_setup_utils import first_run_setup, open_browser

    app = configure_app()
    app.logger = logger

    is_first_run_flag, credentials = first_run_setup()
    
    if is_first_run_flag and credentials:
        logger.info("\n=== Учетные данные ===")
        logger.info(f"Язык интерфейса: {credentials['language']}")
        logger.info(f"Логин: {credentials['login']}")
        logger.info(f"Пароль: {credentials['password']}")
        logger.info("="*30)

    app.register_blueprint(routes)
    ssl_context = get_ssl_context()
    open_browser()
    
    app.run(
        host='0.0.0.0',
        port=8000,
        ssl_context=ssl_context,
        debug=True
    )

if __name__ == '__main__':
    main()