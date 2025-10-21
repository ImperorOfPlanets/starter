import argparse
import os
import platform
import subprocess
import sys
import textwrap
from pathlib import Path

from starter_files.core.utils import venv_utils
from starter_files.core.utils.globalVars_utils import get_global
from starter_files.core.oss.default.system import SystemModule
from starter_files.core.utils.log_utils import LogManager

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
    from starter_files.core.utils.configurateApp_utils import configure_app
    from starter_files.core.utils.ssl_utils import get_ssl_context
    from starter_files.core.utils.firstSetup_utils import open_browser
    from dotenv import load_dotenv

    env_file = Path(get_global('script_path')) / '.env'
    load_dotenv(env_file)
    print(f"[DEBUG] Переменные окружения загружены из {env_file}")

    # Для отладки: проверка переменных окружения
    env_vars = ["APP_SECRET_KEY", "ADMIN_LOGIN", "ADMIN_PASSWORD_HASH", "PORT"]
    for var in env_vars:
        print(f"{var} = {os.environ.get(var, 'NOT_SET')}")

    app = configure_app()
    ssl_context = get_ssl_context()
    port = int(os.environ.get('PORT', 8000))
    open_browser()
    app.run(
        host='0.0.0.0',
        port=port,
        ssl_context=ssl_context,
        debug=True
    )

if __name__ == '__main__':
    # Первым делом проверяем/создаем venv фыв ыф
    if venv_utils.ensure_venv():
        sys.exit(0)

    # Проверка установки зависимостей
    try:
        import flask
        import dotenv
    except ImportError:
        from starter_files.core.utils.requirements_utils import install_and_restart
        install_and_restart()
    

    args = parse_args()
    
    # Инициализируем логгер
    LogManager.initialize(
        debug_mode=args.debug,
        service_mode=args.service
    )
    logger = LogManager.get_logger("main")

    # Устанавливаем глобальный обработчик исключений
    from starter_files.core.utils.exceptionHandler_utils import ExceptionHandler
    handler = ExceptionHandler()
    sys.excepthook = handler.handle_unhandled_exception
    logger.debug("Exception handler initialized")

    # Проверка на настроенность
    from starter_files.core.utils.firstSetup_utils import first_run_setup
    is_first_run, credentials = first_run_setup()
    if is_first_run and credentials:
        logger.info("First run setup completed")
        print("\n=== Первичная настройка завершена ===")
        print(f"Логин: {credentials['login']}")
        print(f"Пароль: {credentials['password']}")
        print("Сохраните эти данные!")
        print("="*50 + "\n")

        print("=== ПРОВЕРКА ОБНОВЛЕНИЙ ===")
        from starter_files.core.oss.default.updates import UpdatesModule
        config = UpdatesModule.get_updates_config()
        seconds = UpdatesModule.seconds_since_last_update('starter', config)
        print(f"Секунд с последнего обновления: {seconds}")
        print("===========================")

    # Собираем информацию о фаерволе
    from starter_files.core.oss.default.firewall import FirewallModule
    print("=== ПРОВЕРКА ПОРТОВ ===")
    firewall_info = FirewallModule.collect_firewall_info()
    
    if firewall_info['is_available']:
        print(f"Активный фаервол: {firewall_info['active_firewall']}")
    else:
        print("⚠️  Не обнаружен активный фаервол!")
    
    # Разрешенные порты в фаерволе
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
    
    # Слушающие порты
    if firewall_info['listening_ports']:
        print("\nСлушающие порты:")
        for port_info in firewall_info['listening_ports']:
            print(f"  - Порт {port_info['port']}/{port_info['protocol']} ({port_info.get('state', 'LISTEN')})")
    else:
        print("\nНет слушающих портов")
    
    print("===========================")

    logger.debug(f"Command line arguments: service={args.service}, debug={args.debug}")
    # Сервисный режим
    if args.service:
        logger.info("Starting service mode")
        start_service_mode()

    # Обычный режим
    logger.info("Starting interactive mode")
    start_interactive_mode()