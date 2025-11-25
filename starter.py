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

def parse_args():
    """Парсит аргументы командной строки"""
    parser = argparse.ArgumentParser()
    parser.add_argument('--service', action='store_true', help='Запуск в сервисном режиме')
    parser.add_argument('--debug', action='store_true', help='Запуск в режиме отладки')
    parser.add_argument('--no-update', action='store_true', help='Пропустить автоматическое обновление')
    return parser.parse_args()

def check_and_apply_updates():
    """Проверяет и применяет обновления с выводом на экран"""
    print("\n" + "="*60)
    print("🔄 ПРОВЕРКА ОБНОВЛЕНИЙ")
    print("="*60)
    
    try:
        from files.core.oss.default.updates import UpdatesModule
        from files.configs.configs import PROJECTS
        
        config = UpdatesModule.get_updates_config()
        
        for project_name, project_config in PROJECTS.items():
            print(f"\n📦 Проект: {project_name}")
            print(f"   URL: {project_config['DOWNLOAD_URL']}")
            
            # Проверяем, нужно ли проверять обновления
            if UpdatesModule.should_check_updates(project_name, config):
                print("   🔍 Проверяем наличие обновлений...")
                
                # Выполняем обновление
                result = UpdatesModule.update_project(project_name, project_config)
                
                if result['changes_count'] == -1:
                    print("   ✅ Новая установка выполнена")
                elif result['changes_count'] > 0:
                    print(f"   ✅ Обновление применено! Изменений: {result['changes_count']}")
                    if result['need_restart']:
                        print("   ⚠️  Требуется перезапуск приложения")
                else:
                    print("   ✅ Актуальная версия, обновлений не требуется")
                    
                # Показываем лог обновления
                log_content = UpdatesModule.get_update_log(result['update_id'])
                print(f"   📋 Лог обновления сохранен: {result['update_id']}.log")
                
            else:
                seconds = UpdatesModule.seconds_since_last_update(project_name, config)
                print(f"   ⏰ Проверка не требуется (последняя проверка {int(seconds)} сек назад)")
                
    except Exception as e:
        print(f"   ❌ Ошибка при проверке обновлений: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("="*60 + "\n")

def show_update_history():
    """Показывает историю обновлений"""
    try:
        from files.core.oss.default.updates import UpdatesModule
        
        print("\n" + "="*60)
        print("📊 ИСТОРИЯ ОБНОВЛЕНИЙ")
        print("="*60)
        
        history = UpdatesModule.get_update_history('all')
        
        if not history['history']:
            print("   История обновлений пуста")
            return
            
        for update in history['history'][:5]:  # Показываем последние 5 записей
            status_icons = {
                'completed': '✅',
                'error': '❌',
                'in_progress': '🔄',
                'unknown': '❓'
            }
            icon = status_icons.get(update['status'], '❓')
            print(f"   {icon} {update['project']} - {update['timestamp'].split('T')[0]} - {update['status']}")
            
    except Exception as e:
        print(f"   ❌ Ошибка при получении истории: {str(e)}")

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
    port = int(os.environ.get('PORT', 8000))
    
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

    # АВТОМАТИЧЕСКАЯ ПРОВЕРКА ОБНОВЛЕНИЙ ПРИ ЗАПУСКЕ
    if not args.no_update:
        check_and_apply_updates()
        show_update_history()
    else:
        print("\n⏭️  Автоматическое обновление пропущено (используйте --no-update)")

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