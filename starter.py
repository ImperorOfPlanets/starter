import argparse
import os
import platform
import subprocess
import sys
import textwrap
from pathlib import Path

try:
    from starter_files.core.utils import venv_utils
    from starter_files.core.utils.globalVars_utils import get_global
    from starter_files.core.oss.default.system import SystemModule
    from starter_files.core.utils.log_utils import LogManager
    print("Импорт модулей starter_files.core.utils и starter_files.core.oss.default прошел успешно")
except ImportError as e:
    print(f"Критическая ошибка импорта: {e}")
    print("Проверьте структуру папок и наличие файлов в starter_files/")
    sys.exit(1)

try:
    SystemModule.collect_basic_system_info()
    print("SystemModule.collect_basic_system_info() выполнен успешно")
except Exception as e:
    print(f"Ошибка в SystemModule.collect_basic_system_info(): {e}")
    sys.exit(1)

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--service', action='store_true', help='Запуск в сервисном режиме')
    parser.add_argument('--debug', action='store_true', help='Запуск в режиме отладки')
    return parser.parse_args()

def start_service_mode():
    try:
        logger = get_global('logger')
        logger.info("Запуск в сервисном режиме...")
        logger.info("start_service_mode() выполнен успешно")
        # В сервисном режиме не выводим ничего в консоль
    except Exception as e:
        # В сервисном режиме логируем ошибку, но не выводим в консоль
        try:
            logger = get_global('logger')
            logger.error(f"Ошибка в start_service_mode(): {e}")
        except:
            # Если логгер недоступен, выводим в stderr
            print(f"Ошибка в start_service_mode(): {e}", file=sys.stderr)
        sys.exit(1)
    sys.exit(0)

def start_interactive_mode():
    try:
        from starter_files.core.utils.configurateApp_utils import configure_app
        from starter_files.core.utils.ssl_utils import get_ssl_context
        from starter_files.core.utils.firstSetup_utils import open_browser
        from dotenv import load_dotenv

        env_file = Path(get_global('script_path')) / '.env'
        logger.info(f"Загрузка переменных окружения из {env_file}")
        load_dotenv(env_file)
        logger.info(f"Переменные окружения загружены из {env_file}")

        env_vars = ["APP_SECRET_KEY", "ADMIN_LOGIN", "ADMIN_PASSWORD_HASH", "PORT"]
        for var in env_vars:
            value = os.environ.get(var, 'NOT_SET')
            logger.debug(f"Переменная окружения {var} = {value}")
            if value == 'NOT_SET':
                logger.warning(f"Переменная окружения {var} не установлена")

        app = configure_app()
        ssl_context = get_ssl_context()
        port = int(os.environ.get('PORT', 8000))
        open_browser()
        logger.info("start_interactive_mode() выполнен успешно")
        app.run(
            host='0.0.0.0',
            port=port,
            ssl_context=ssl_context,
            debug=True
        )
    except Exception as e:
        logger.error(f"Ошибка в start_interactive_mode(): {e}")
        sys.exit(1)

if __name__ == '__main__':
    args = parse_args()

    try:
        LogManager.initialize(
            debug_mode=args.debug,
            service_mode=args.service
        )
        logger = LogManager.get_logger("main")
        logger.info("LogManager.initialize() выполнен успешно")
    except Exception as e:
        print(f"Ошибка в LogManager.initialize(): {e}")
        sys.exit(1)

    if args.debug:
        logger.info("Проверка виртуального окружения...")
    try:
        venv_result = venv_utils.ensure_venv()
        if venv_result:
            logger.info("Перезапуск в виртуальном окружении")
            sys.exit(0)
        if args.debug:
            logger.info("venv_utils.ensure_venv() выполнен успешно")
    except Exception as e:
        logger.error(f"Ошибка в venv_utils.ensure_venv(): {e}")
        sys.exit(1)

    if args.debug:
        logger.info("Проверка установки зависимостей...")
    try:
        import flask
        import flask_session
        import dotenv
        if args.debug:  # Выводим только в дебаг режиме
            logger.info("Зависимости flask, flask_session и dotenv найдены")
    except ImportError as e:
        logger.warning(f"Зависимости не найдены: {e}")
        from starter_files.core.utils.requirements_utils import install_and_restart
        install_and_restart()

    from starter_files.core.utils.exceptionHandler_utils import ExceptionHandler
    handler = ExceptionHandler()
    sys.excepthook = handler.handle_unhandled_exception
    if args.debug:
        logger.debug("Exception handler initialized")

    from starter_files.core.utils.firstSetup_utils import first_run_setup
    is_first_run, credentials = first_run_setup()
    if is_first_run and credentials:
        logger.info("First run setup completed")
        if not args.service:  # Выводим только в интерактивном режиме
            print("\n=== Первичная настройка завершена ===")
            print(f"Логин: {credentials['login']}")
            print(f"Пароль: {credentials['password']}")
            print("Сохраните эти данные!")
            print("="*50 + "\n")

            if args.debug:  # Проверку обновлений только в дебаг режиме
                print("=== ПРОВЕРКА ОБНОВЛЕНИЙ ===")
                from starter_files.core.oss.default.updates import UpdatesModule
                config = UpdatesModule.get_updates_config()
                seconds = UpdatesModule.seconds_since_last_update('starter', config)
                print(f"Секунд с последнего обновления: {seconds}")
                print("===========================")

    from starter_files.core.oss.default.firewall import FirewallModule
    if args.debug:  # Выводим информацию о портах только в дебаг режиме
        print("=== ПРОВЕРКА ПОРТОВ ===")
    firewall_info = FirewallModule.collect_firewall_info()

    if args.debug:  # Выводим информацию о фаерволе только в дебаг режиме
        if firewall_info['is_available']:
            print(f"Активный фаервол: {firewall_info['active_firewall']}")
        else:
            print("Внимание: Не обнаружен активный фаервол!")

        if firewall_info['all_ports_open']:
            print("\n✅ Все порты разрешены")
            if firewall_info['open_ports']:
                print(f"Причина: {firewall_info['open_ports'][0]['service']}")
        elif firewall_info['open_ports']:
            print("\nРазрешенные порты в фаерволе:")
            for port_info in firewall_info['open_ports']:
                service_info = f" ({port_info.get('service', '')})" if port_info.get('service') else ""
                print(f"  - Порт {port_info['port']}/{port_info['protocol']}{service_info}")
        else:
            print("\nНет явно разрешенных портов в фаерволе")

        if firewall_info['listening_ports']:
            print("\nСлушающие порты:")
            for port_info in firewall_info['listening_ports']:
                print(f"  - Порт {port_info['port']}/{port_info['protocol']} ({port_info.get('state', 'LISTEN')})")
        else:
            print("\nНет слушающих портов")

    # Автоматически открываем порт для веб-интерфейса
    port = int(os.environ.get('PORT', 8000))
    port_open = any(p.get('port') == str(port) for p in firewall_info['open_ports']) or firewall_info['all_ports_open']

    if firewall_info['is_available']:
        if not port_open:
            logger.info(f"Открываем порт {port}/tcp для веб-интерфейса...")
            if FirewallModule.open_port(port, 'tcp'):
                logger.info(f"Порт {port}/tcp успешно открыт")
            else:
                logger.warning(f"Не удалось открыть порт {port}/tcp автоматически")
        else:
            logger.info(f"Порт {port}/tcp уже открыт в фаерволе")
    else:
        logger.warning(f"Фаервол не обнаружен. Убедитесь, что порт {port} доступен для подключений.")

    logger.debug(f"Command line arguments: service={args.service}, debug={args.debug}")
    if args.service:
        logger.info("Starting service mode")
        start_service_mode()
    else:
        logger.info("Starting interactive mode")
        start_interactive_mode()