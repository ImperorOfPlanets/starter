import argparse
import os
import platform
import subprocess
import sys
import textwrap
from pathlib import Path

from files.core.utils import venv_utils
from files.core.utils.globalVars_utils import get_global, set_global
from files.core.oss.default.system import SystemModule
from files.core.utils.log_utils import LogManager

# Устанавливает глобальные переменные
SystemModule.collect_basic_system_info()

def print_system_module_variables():
    """Выводит все переменные SystemModule, которые находятся в памяти"""
    print("\n" + "="*60)
    print("🔧 ПЕРЕМЕННЫЕ SYSTEMMODULE В ПАМЯТИ")
    print("="*60)
    
    try:
        # Получаем все атрибуты SystemModule
        all_attributes = dir(SystemModule)
        
        # Фильтруем только публичные атрибуты (не начинающиеся с _)
        public_attributes = [attr for attr in all_attributes if not attr.startswith('_')]
        
        print("📋 Доступные атрибуты SystemModule:")
        for attr in sorted(public_attributes):
            try:
                value = getattr(SystemModule, attr)
                # Форматируем вывод в зависимости от типа данных
                if callable(value):
                    print(f"   🔷 {attr}: <method>")
                elif isinstance(value, (dict, list, tuple)) and len(str(value)) > 100:
                    print(f"   📦 {attr}: {type(value).__name__} (размер: {len(str(value))} chars)")
                else:
                    print(f"   ✅ {attr}: {value}")
            except Exception as e:
                print(f"   ❌ {attr}: <error: {str(e)}>")
                
        # Дополнительно выводим содержимое глобальных переменных
        print("\n📋 Глобальные переменные (globalVars):")
        global_vars = [
            'os_name', 'os_version', 'os_arch', 'hostname', 
            'username', 'script_path', 'current_path', 'python_version',
            'is_admin', 'is_service', 'hardware_info'
        ]
        
        for var_name in global_vars:
            try:
                value = get_global(var_name)
                if value is not None:
                    if isinstance(value, (dict, list)) and len(str(value)) > 50:
                        print(f"   📦 {var_name}: {type(value).__name__} (размер: {len(str(value))} chars)")
                    else:
                        print(f"   ✅ {var_name}: {value}")
                else:
                    print(f"   ⚠️  {var_name}: <not set>")
            except Exception as e:
                print(f"   ❌ {var_name}: <error: {str(e)}>")
                
    except Exception as e:
        print(f"   💥 Ошибка при получении переменных SystemModule: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("="*60 + "\n")

def parse_args():
    """Парсит аргументы командной строки"""
    parser = argparse.ArgumentParser()
    parser.add_argument('--service', action='store_true', help='Запуск в сервисном режиме')
    parser.add_argument('--debug', action='store_true', help='Запуск в режиме отладки')
    parser.add_argument('--no-update', action='store_true', help='Пропустить автоматическое обновление')
    parser.add_argument('--show-vars', action='store_true', help='Показать переменные SystemModule')
    return parser.parse_args()

def start_service_mode():
    """Запускает сервисный режим"""
    logger = get_global('logger')
    logger.info("Запуск в сервисном режиме...")
    sys.exit(0)

def start_interactive_mode():
    """Запускает интерактивный режим с веб-интерфейсом"""
    # Обычный режим
    from files.core.utils.configurateApp_utils import configure_app
    from files.core.utils.ssl_utils import get_ssl_context
    from files.core.utils.firstSetup_utils import open_browser
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
    
    # ЧТЕНИЕ ПОРТА ИЗ .env С ЗНАЧЕНИЕМ ПО УМОЛЧАНИЮ
    port = int(os.environ.get('PORT') or 8000)
    
    print(f"[INFO] Запуск приложения на порту: {port}")
    
    open_browser()
    app.run(
        host='0.0.0.0',
        port=port,
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
        from files.core.utils.requirements_utils import install_and_restart
        install_and_restart()
    
    args = parse_args()
    
    # Инициализируем логгер
    LogManager.initialize(
        debug_mode=args.debug,
        service_mode=args.service
    )
    logger = LogManager.get_logger("main")

    # Устанавливаем глобальный обработчик исключений
    from files.core.utils.exceptionHandler_utils import ExceptionHandler
    handler = ExceptionHandler()
    sys.excepthook = handler.handle_unhandled_exception
    logger.debug("Exception handler initialized")

    # Показываем переменные SystemModule если запрошено
    if args.show_vars:
        print_system_module_variables()

    # Проверка на настроенность
    from files.core.utils.firstSetup_utils import first_run_setup
    is_first_run, credentials = first_run_setup()
    if is_first_run and credentials:
        logger.info("First run setup completed")
        print("\n=== Первичная настройка завершена ===")
        print(f"Логин: {credentials['login']}")
        print(f"Пароль: {credentials['password']}")
        print("Сохраните эти данные!")
        print("="*50 + "\n")

    # Собираем информацию о фаерволе
    from files.core.oss.default.firewall import FirewallModule
    print("\n" + "="*60)
    print("🔒 ПРОВЕРКА ФАЕРВОЛА И ПОРТОВ")
    print("="*60)
    
    firewall_info = FirewallModule.collect_firewall_info()
    
    if firewall_info['is_available']:
        print(f"   Активный фаервол: {firewall_info['active_firewall']}")
    else:
        print("   ⚠️  Не обнаружен активный фаервол!")
    
    # Разрешенные порты в фаерволе
    if firewall_info['all_ports_open']:
        print("\n   ✅ Все порты разрешены")
        if firewall_info['open_ports']:
            print(f"   Причина: {firewall_info['open_ports'][0]['service']}")
    elif firewall_info['open_ports']:
        print("\n   Разрешенные порты в фаерволе:")
        for port_info in firewall_info['open_ports']:
            service_info = f" ({port_info.get('service', '')})" if port_info.get('service') else ""
            print(f"     - Порт {port_info['port']}/{port_info['protocol']}{service_info}")
    else:
        print("\n   Нет явно разрешенных портов в фаерволе")
    
    # Слушающие порты
    if firewall_info['listening_ports']:
        print("\n   Слушающие порты:")
        for port_info in firewall_info['listening_ports']:
            print(f"     - Порт {port_info['port']}/{port_info['protocol']} ({port_info.get('state', 'LISTEN')})")
    else:
        print("\n   Нет слушающих портов")
    
    print("="*60)

    logger.debug(f"Command line arguments: service={args.service}, debug={args.debug}")
    
    # Сервисный режим
    if args.service:
        logger.info("Starting service mode")
        start_service_mode()

    # Обычный режим
    logger.info("Starting interactive mode")
    start_interactive_mode()