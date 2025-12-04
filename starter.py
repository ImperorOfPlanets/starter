import argparse
import os
import platform
import subprocess
import sys
import time

from pathlib import Path

from files.core.utils.venv_requirements_manager import VenvRequirementsManager
from files.core.utils.globalVars_utils import get_global, set_global
from files.core.oss.default.system import SystemModule
from files.core.utils.log_utils import LogManager

# Устанавливает глобальные переменные
SystemModule.collect_basic_system_info()

def print_starter_processes():
    import psutil

    """Выводит список всех процессов starter.py"""
    print("\n" + "="*70)
    print("🚀 ПРОЦЕССЫ STARTER.PY")
    print("="*70)

    current_pid = os.getpid()
    script_name = Path(sys.argv[0]).name
    script_path = Path(sys.argv[0]).resolve()

    try:
        starter_processes = []
        
        # Ищем все процессы starter.py
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time', 'username']):
            try:
                cmdline = proc.info['cmdline'] or []
                if not cmdline:
                    continue
                    
                # Проверяем, является ли процесс starter.py
                for arg in cmdline:
                    if 'starter.py' in arg:
                        starter_processes.append({
                            'pid': proc.info['pid'],
                            'username': proc.info.get('username', 'N/A'),
                            'create_time': proc.info.get('create_time', 0),
                            'cmdline': ' '.join(cmdline),
                            'is_current': proc.info['pid'] == current_pid
                        })
                        break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        if not starter_processes:
            print("   Нет запущенных процессов starter.py")
            print("="*70 + "\n")
            return
        
        # Сортируем по времени создания (старые вверху)
        starter_processes.sort(key=lambda x: x.get('create_time', 0))
        
        print(f"   Всего процессов starter.py: {len(starter_processes)}")
        print(f"   Текущий PID: {current_pid}")
        print()
        
        # Выводим таблицу процессов
        print(f"{'PID':<8} {'Текущий':<10} {'Время запуска':<25} {'Команда'}")
        print(f"{'-'*8} {'-'*10} {'-'*25} {'-'*40}")
        
        for proc in starter_processes:
            pid = proc['pid']
            
            # Форматируем время
            if proc['create_time'] > 0:
                create_time = time.strftime('%Y-%m-%d %H:%M:%S', 
                                           time.localtime(proc['create_time']))
                # Вычисляем время работы
                uptime = time.time() - proc['create_time']
                if uptime > 3600:
                    uptime_str = f"{uptime/3600:.1f}ч"
                elif uptime > 60:
                    uptime_str = f"{uptime/60:.1f}м"
                else:
                    uptime_str = f"{uptime:.0f}с"
                time_str = f"{create_time} ({uptime_str})"
            else:
                time_str = "N/A"
            
            # Форматируем команду
            cmd = proc['cmdline']
            # Обрезаем слишком длинные команды
            if len(cmd) > 60:
                cmd = cmd[:57] + '...'
            
            # Определяем метку процесса
            marker = "▶ ТЕКУЩИЙ" if proc['is_current'] else "  "
            
            print(f"{marker:<10} {pid:<8} {time_str:<25} {cmd}")
        
        # Статистика
        current_count = sum(1 for p in starter_processes if p['is_current'])
        other_count = len(starter_processes) - current_count
        
        if other_count > 0:
            print(f"\n⚠️  ВНИМАНИЕ: Найдено {other_count} других процессов starter.py!")
            print("   Они могут мешать работе. Вы можете завершить их командой:")
            for proc in starter_processes:
                if not proc['is_current']:
                    print(f"     kill {proc['pid']}")
            
    except Exception as e:
        print(f"   ❌ Ошибка при получении процессов: {e}")

    print("="*70 + "\n")

def print_system_module_variables():
    """Выводит все переменные SystemModule, которые находятся в памяти"""
    print("\n" + "="*60)
    print("🔧 ПЕРЕМЕННЫЕ SYSTEMMODULE")
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

def reset_configuration():
    """Удаляет файл конфигурации и сбрасывает настройки"""
    base_dir = get_global('script_path')
    env_file = base_dir / '.env'

    if env_file.exists():
        try:
            env_file.unlink()
            print("✅ Файл конфигурации .env удален")
            return True
        except Exception as e:
            print(f"❌ Ошибка при удалении .env: {e}")
            return False
    else:
        print("ℹ️ Файл .env не найден, ничего удалять не нужно")
        return True

def parse_args():
    """Парсит аргументы командной строки"""
    parser = argparse.ArgumentParser()
    parser.add_argument('--service', action='store_true', help='Запуск в сервисном режиме')
    parser.add_argument('--debug', action='store_true', help='Запуск в режиме отладки')
    parser.add_argument('--no-update', action='store_true', help='Пропустить автоматическое обновление')
    parser.add_argument('--show-vars', action='store_true', help='Показать переменные SystemModule')
    parser.add_argument('--new', action='store_true', help='Удалить настройки и начать заново')
    return parser.parse_args()

def start_service_mode():
    """Запускает сервисный режим"""
    logger = get_global('logger')
    logger.info("Запуск в сервисном режиме...")
    sys.exit(0)

def start_interactive_mode():
    """Запускает интерактивный режим с веб-интерфейсом"""
    from files.core.utils.configurateApp_utils import configure_app
    from files.core.utils.ssl_utils import get_ssl_context
    from files.core.utils.firstSetup_utils import open_browser
    from dotenv import load_dotenv

    env_file = Path(get_global('script_path')) / '.env'
    load_dotenv(env_file)
    print(f"[DEBUG] Переменные окружения загружены из {env_file}")

    # Для отладки: проверка переменных окружения
    env_vars = ["APP_SECRET_KEY", "ADMIN_LOGIN", "ADMIN_PASSWORD_HASH", "PORT", "TYPE_SERVER"]
    for var in env_vars:
        value = os.environ.get(var, 'NOT_SET')
        print(f"{var} = {value}")

    app = configure_app()
    ssl_context = get_ssl_context()

    # ПОЛУЧАЕМ ПОРТ ИЗ ГЛОБАЛЬНЫХ ПЕРЕМЕННЫХ - КЛЮЧЕВАЯ ИСПРАВЛЕНИЕ
    port = get_global('port')  # ← Убираем значение по умолчанию
    if port is None:
        # Если порт не установлен в глобальных переменных, пробуем получить из env
        port_from_env = os.environ.get('PORT', '8000')
        try:
            port = int(port_from_env)
        except ValueError:
            port = 8000
        print(f"[WARNING] Порт не найден в глобальных переменных, используем из env: {port}")

    print(f"[INFO] Запуск приложения на порту: {port}")

    open_browser()
    app.run(
        host='0.0.0.0',
        port=port,
        ssl_context=ssl_context,
        debug=True
    )

def main():
    """Основная функция запуска"""
    # 1. СРАЗУ выводим список процессов starter.py
    print("\n" + "=" * 60)
    print("🚀 ЗАПУСК СТАРТЕРА СЕРВЕРА")
    print("=" * 60)
    # print_starter_processes()

    # 2. Анализируем аргументы (только для --new на этом этапе)
    # Парсим аргументы вручную для --new, чтобы обработать его до создания venv
    if '--new' in sys.argv:
        print("🔄 Сброс конфигурации (аргумент --new обнаружен)...")
        if reset_configuration():
            print("🔄 Перезапуск для новой настройки...")
            # Перезапускаем скрипт без аргумента --new
            import subprocess
            new_args = [sys.executable] + [arg for arg in sys.argv if arg != '--new']
            subprocess.run(new_args)
            sys.exit(0)
        else:
            print("❌ Не удалось сбросить конфигурацию")
            sys.exit(1)

    # 3. Показываем глобальные переменные SystemModule
    print("\n📊 СИСТЕМНАЯ ИНФОРМАЦИЯ")
    print("="*60)
    print_system_module_variables()

    # 4. Показываем отладочную информацию о VENV
    print("\n📦 ИНФОРМАЦИЯ О ВИРТУАЛЬНОМ ОКРУЖЕНИИ")
    print("="*60)
    VenvRequirementsManager.print_debug_info()

    # 5. Автоматическая настройка venv и установка зависимостей
    print("\n🔧 АВТОМАТИЧЕСКАЯ НАСТРОЙКА ОКРУЖЕНИЯ")
    print("="*60)
    if VenvRequirementsManager.first_run_setup():
        # Если была выполнена настройка и перезапуск, этот код не выполнится
        print("⚠️  Перезапуск не произошел. Продолжаем работу...")
        time.sleep(2)

    # Теперь парсим все остальные аргументы
    args = parse_args()

    # 6. Проверяем, что мы в виртуальном окружении
    if not VenvRequirementsManager.in_venv():
        print("\n" + "!" * 60)
        print("⚠️  ВНИМАНИЕ: СКРИПТ НЕ ЗАПУЩЕН В ВИРТУАЛЬНОМ ОКРУЖЕНИИ!")
        print("!" * 60)
        
        response = input("\n❓ Продолжить без виртуального окружения? (y/N): ")
        if response.lower() != 'y':
            print("\n🔄 Завершение работы...")
            print("\n💡 РЕКОМЕНДУЕМЫЕ ДЕЙСТВИЯ:")
            print("1. Запустите скрипт снова - он автоматически создаст venv")
            print("2. Создайте venv вручную: python -m venv venv")
            print("3. Активируйте venv:")
            print("   Windows: venv\\Scripts\\activate")
            print("   Linux/Mac: source venv/bin/activate")
            print("4. Запустите скрипт снова")
            sys.exit(1)
        else:
            print("\n⚠️  ПРОДОЛЖАЕМ РАБОТУ БЕЗ VENV. МОГУТ ВОЗНИКНУТЬ ПРОБЛЕМЫ!")
            time.sleep(3)

    # 7. Проверка критических зависимостей
    print("\n🔍 ПРОВЕРКА КРИТИЧЕСКИХ ЗАВИСИМОСТЕЙ")
    print("="*60)
    try:
        import flask
        import dotenv
        import OpenSSL
        print("✅ Критические зависимости загружены успешно")
    except ImportError as e:
        print(f"\n❌ ОТСУТСТВУЮТ КРИТИЧЕСКИЕ ЗАВИСИМОСТИ: {e}")
        
        # Пробуем установить зависимости в текущем окружении
        venv_python = VenvRequirementsManager.get_venv_python()
        if venv_python and VenvRequirementsManager.get_venv_dir().exists():
            requirements = VenvRequirementsManager.find_requirements()
            if requirements:
                print("\n🔄 Попытка автоматической установки зависимостей...")
                try:
                    print("Устанавливаем Flask, python-dotenv, pyOpenSSL...")
                    start_time = time.time()
                    result = subprocess.run([
                        str(venv_python), "-m", "pip", "install",
                        "flask", "python-dotenv", "pyopenssl",
                        "--no-warn-script-location"
                    ], capture_output=True, text=True, timeout=300)
                    
                    if result.returncode == 0:
                        print("✅ Зависимости установлены. Перезапуск...")
                        time.sleep(2)
                        VenvRequirementsManager.restart_in_venv()
                    else:
                        print(f"❌ Ошибка установки: {result.stderr[:500]}")
                except subprocess.TimeoutExpired:
                    print("❌ Таймаут установки зависимостей (более 5 минут)")
                except Exception as install_error:
                    print(f"❌ Ошибка установки: {install_error}")
        
        print("\n📋 РУЧНАЯ УСТАНОВКА ЗАВИСИМОСТЕЙ:")
        print("  pip install flask python-dotenv pyopenssl")
        sys.exit(1)

    # 8. Инициализируем логгер
    print("\n📝 НАСТРОЙКА ЛОГГИРОВАНИЯ")
    print("="*60)
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

    # 9. Показать переменные если запрошено
    if args.show_vars:
        print("\n📋 ЗАПРОШЕНЫ ПЕРЕМЕННЫЕ SYSTEMMODULE")
        print("="*60)
        print_system_module_variables()

    logger.debug(f"Command line arguments: service={args.service}, debug={args.debug}")

    # 10. Проверка на первоначальную настройку
    from files.core.utils.firstSetup_utils import first_run_setup
    is_first_run, credentials = first_run_setup()
    if is_first_run and credentials:
        logger.info("First run setup completed")
        print("\n" + "="*50)
        print("🎉 ПЕРВИЧНАЯ НАСТРОЙКА ЗАВЕРШЕНА")
        print("="*50)
        print(f"👤 Логин: {credentials['login']}")
        print(f"🔑 Пароль: {credentials['password']}")
        print("💾 Сохраните эти данные!")
        print("="*50 + "\n")

    # 11. Собираем информацию о фаерволе
    print("\n🔒 ПРОВЕРКА ФАЕРВОЛА И ПОРТОВ")
    print("="*60)
    from files.core.oss.default.firewall import FirewallModule
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

    # 12. Сервисный режим
    if args.service:
        logger.info("Starting service mode")
        start_service_mode()

    # 13. Финальный запуск
    print("\n" + "=" * 60)
    print("🎯 ГОТОВО К ЗАПУСКУ СЕРВЕРА")
    print("=" * 60)
    
    # Показываем процессы еще раз перед запуском
    print_starter_processes()

    # Запуск интерактивного режима
    print("🚀 ЗАПУСК СЕРВЕРА...")
    logger.info("Starting interactive mode")
    start_interactive_mode()


if __name__ == '__main__':
    main()