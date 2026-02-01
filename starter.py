import argparse
import json
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

# Устанавливает глобальные переменные - ОСТАВЛЯЕМ КАК ЕСТЬ!
SystemModule.collect_basic_system_info()

def print_starter_processes():
    """Выводит список всех процессов starter.py, фильтруя только те, что запущены из текущей директории."""
    print("\n" + "="*80)
    print("🚀 ПРОЦЕССЫ STARTER.PY (ТОЛЬКО ИЗ ТЕКУЩЕЙ ДИРЕКТОРИИ)")
    print("="*80)

    current_pid = os.getpid()
    current_script_path = Path(sys.argv[0]).resolve()

    try:
        import psutil
        starter_processes = []

        for proc in psutil.process_iter(['pid', 'cmdline', 'create_time', 'username']):
            try:
                cmdline = proc.info['cmdline'] or []
                if not cmdline:
                    continue

                # Ищем процессы, содержащие 'starter.py'
                for arg in cmdline:
                    if 'starter.py' in arg:
                        script_path = Path(arg).resolve()
                        is_own = (script_path == current_script_path)
                        starter_processes.append({
                            'pid': proc.info['pid'],
                            'cmdline': ' '.join(cmdline),
                            'script_path': str(script_path),
                            'is_own': is_own,
                            'is_current': proc.info['pid'] == current_pid,
                            'create_time': proc.info.get('create_time', 0),
                            'username': proc.info.get('username', 'N/A')
                        })
                        break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if not starter_processes:
            print("   Нет запущенных процессов starter.py")
            print("="*80 + "\n")
            return

        # Сортируем: сначала свои, потом чужие
        starter_processes.sort(key=lambda x: (not x['is_own'], -x['create_time']))

        print(f"   Текущий путь: {current_script_path}")
        print(f"   Всего найдено подходящих процессов: {len(starter_processes)}\n")

        for proc in starter_processes:
            print(f"PID: {proc['pid']}")
            print(f"Команда: {proc['cmdline']}")
            print(f"Путь: {proc['script_path']}")
            marker = "✅ СВОЙ" if proc['is_own'] else "❌ ЧУЖОЙ"
            print(f"Статус: {marker}")
            
            # Дополнительная информация
            if proc['create_time'] > 0:
                uptime = time.time() - proc['create_time']
                if uptime > 3600:
                    uptime_str = f"{uptime/3600:.1f}ч"
                elif uptime > 60:
                    uptime_str = f"{uptime/60:.1f}м"
                else:
                    uptime_str = f"{uptime:.0f}с"
                start_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(proc['create_time']))
                print(f"Запущен: {start_time} (работает: {uptime_str})")
            if proc['username'] != 'N/A':
                print(f"Пользователь: {proc['username']}")
            print("-" * 60)

        # Подсказка по завершению чужих процессов
        foreign_pids = [str(p['pid']) for p in starter_processes if not p['is_own']]
        if foreign_pids:
            print(f"⚠️  Чтобы завершить ЧУЖИЕ процессы, выполните:\n    kill {' '.join(foreign_pids)}")

    except ImportError:
        print("   ⚠️  Модуль psutil не установлен — невозможно определить процессы.")
    except Exception as e:
        print(f"   ❌ Ошибка при получении списка процессов: {e}")

    print("="*80 + "\n")

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
            'os', 'os_version', 'os_family', 'hostname', 
            'username', 'script_path', 'python_info',
            'is_service', 'running_in_docker'
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
    if base_dir is None:
        base_dir = Path(__file__).parent.absolute()
    
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
    logger = LogManager.get_logger('main')
    logger.info("Запуск в сервисном режиме...")
    sys.exit(0)

def start_interactive_mode():
    """Запускает интерактивный режим с веб-интерфейсом"""
    from files.core.utils.configurateApp_utils import configure_app
    from files.core.utils.ssl_utils import get_ssl_context
    from files.core.utils.firstSetup_utils import open_browser
    from dotenv import load_dotenv

    base_dir = get_global('script_path')
    env_file = base_dir / '.env'
    
    if env_file.exists():
        load_dotenv(env_file)
        print(f"[DEBUG] Переменные окружения загружены из {env_file}")
    else:
        print(f"[WARNING] Файл .env не найден: {env_file}")

    # Для отладки: проверка переменных окружения
    env_vars = ["APP_SECRET_KEY", "ADMIN_LOGIN", "ADMIN_PASSWORD_HASH", "PORT", "TYPE_SERVER"]
    for var in env_vars:
        value = os.environ.get(var, 'NOT_SET')
        print(f"{var} = {value}")

    app = configure_app()
    ssl_context = get_ssl_context()

    # ПОЛУЧАЕМ ПОРТ ИЗ ГЛОБАЛЬНЫХ ПЕРЕМЕННЫХ
    port = get_global('port')
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
    debug=get_global('DEBUG')
    # Всегда слушаем все интерфейсы
    app.run(host='0.0.0.0', port=port, ssl_context=ssl_context, debug=True)

def main():
    """Основная функция запуска"""
    # ========== ПЕРВЫЙ ЭТАП: БАЗОВАЯ ИНИЦИАЛИЗАЦИЯ ==========
    print("\n" + "=" * 60)
    print("🚀 ЗАПУСК СТАРТЕРА СЕРВЕРА")
    print("=" * 60)
    print(f"Текущий PID: {os.getpid()}")

    # Инициализация логгера
    args = parse_args()
    LogManager.initialize(debug_mode=args.debug, service_mode=args.service)
    
    # Теперь можно создавать логгер
    logger = LogManager.get_logger("main")
    logger.info("Запуск приложения...")
    
    # 1. Выводим путь до стартера
    print(f"✅ script_path установлен: {get_global('script_path')}")

    # 2. Парсим аргументы (только для --new на этом этапе)
    if '--new' in sys.argv:
        print("🔄 Сброс конфигурации (аргумент --new обнаружен)...")
        if reset_configuration():
            print("🔄 Перезапуск для новой настройки...")
            new_args = [sys.executable] + [arg for arg in sys.argv if arg != '--new']
            subprocess.run(new_args)
            sys.exit(0)
        else:
            print("❌ Не удалось сбросить конфигурацию")
            sys.exit(1)
    
    # ========== ВТОРОЙ ЭТАП: ИНИЦИАЛИЗАЦИЯ SYSTEM MODULE ==========
    print("\n🔧 ИНИЦИАЛИЗАЦИЯ SYSTEM MODULE")
    print("="*60)
    
    try:
        # Собираем системную информацию (вызываем повторно для актуальности)
        sys_info = SystemModule.collect_basic_system_info()
        print(f"✅ Системная информация собрана")
        
        # Для отладки: покажем ключевые переменные
        print("\n📋 КЛЮЧЕВЫЕ СИСТЕМНЫЕ ПЕРЕМЕННЫЕ:")
        print(f"  os: {get_global('os')}")
        print(f"  os_version: {get_global('os_version')}")
        print(f"  os_family: {get_global('os_family')}")
        print(f"  hostname: {get_global('hostname')}")
        print(f"  running_in_docker: {get_global('running_in_docker')}")
    except Exception as e:
        print(f"❌ Ошибка инициализации SystemModule: {e}")
        import traceback
        traceback.print_exc()

    # ========== РАННЯЯ РЕГИСТРАЦИЯ ПРОЕКТА ==========
    print("\n🔖 РЕГИСТРАЦИЯ ПРОЕКТА В РЕЕСТРЕ")
    print("="*60)
    try:
        from files.core.utils.registry_manager import RegistryManager
        base_dir = get_global('script_path')
        print(f"✅ script_path установлен: {base_dir}")
        print(f"[DEBUG] Тип base_dir: {type(base_dir)}")
        print(f"[DEBUG] Значение base_dir: {repr(base_dir)}")
        if base_dir:
            RegistryManager.register_initializing(base_dir)
            print(f"✅ Проект зарегистрирован: {base_dir}")
        else:
            print("❌ Не удалось получить script_path для регистрации")
    except Exception as e:
        print(f"⚠️ Ошибка регистрации проекта: {e}")
    
    # ========== ТРЕТИЙ ЭТАП: ЗАГРУЗКА МОДУЛЕЙ ==========
    print("\n📦 ЗАГРУЗКА МОДУЛЕЙ")
    print("="*60)
    
    try:
        from files.core.utils.loader_utils import load_modules, initialize_global_modules
        modules = load_modules()
        print(f"✅ Модули загружены: {len(modules)} модулей")
        
        initialize_global_modules()
        print("✅ Глобальные переменные модулей инициализированы")
    except Exception as e:
        print(f"⚠️  Ошибка загрузки модулей: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n📦 МОДУЛИ ЗАГРУЖЕНЫ ВКЛЮЧАЕМ ВОЗМОЖНОСТЬ С НИМИ ВЗАИМОДЕЙСТВОВАТЬ")
    print("="*60)
    
    # ========== ЧЕТВЕРТЫЙ ЭТАП: ПОКАЗАТЬ ПЕРЕМЕННЫЕ ДЛЯ ОТЛАДКИ ==========
    print("\n📊 СИСТЕМНАЯ ИНФОРМАЦИЯ")
    print("="*60)
    print_system_module_variables()

    # ========== ПЯТЫЙ ЭТАП: VENV И ЗАВИСИМОСТИ ==========
    print("\n📦 ИНФОРМАЦИЯ О ВИРТУАЛЬНОМ ОКРУЖЕНИИ")
    print("="*60)
    
    try:
        VenvRequirementsManager.print_debug_info()
    except Exception as e:
        print(f"⚠️  Ошибка при получении информации о VENV: {e}")
    
    # ========== ШЕСТОЙ ЭТАП: АВТОМАТИЧЕСКАЯ НАСТРОЙКА VENV ==========
    print("\n🔧 АВТОМАТИЧЕСКАЯ НАСТРОЙКА ОКРУЖЕНИЯ")
    print("="*60)
    
    # Проверяем, нужно ли создавать venv и устанавливать зависимости
    try:
        venv_dir = VenvRequirementsManager.get_venv_dir()
        venv_exists = venv_dir.exists() if venv_dir else False
        
        if not venv_exists:
            print("📁 Виртуальное окружение не найдено, создаем...")
            success, message = VenvRequirementsManager.create_venv()
            if success:
                print(f"✅ {message}")
            else:
                print(f"❌ {message}")
                print("\n💡 Попробуйте создать venv вручную:")
                print(f"  python -m venv {venv_dir}")
        else:
            print("✅ Виртуальное окружение уже существует")
        
        # Проверяем критические зависимости
        print("\n🔍 ПРОВЕРКА КРИТИЧЕСКИХ ЗАВИСИМОСТЕЙ")
        print("-"*60)
        
        try:
            import flask
            import dotenv
            import OpenSSL
            print("✅ Критические зависимости уже установлены")
                
        except ImportError as e:
            print(f"❌ Отсутствуют критические зависимости: {e}")
            
            # Пытаемся установить автоматически
            print("\n🔄 Автоматическая установка зависимостей...")
            success, message = VenvRequirementsManager.install_requirements_with_progress()
            
            if success:
                print(f"✅ {message}")
                print("\n🔄 Перезапуск после установки зависимостей...")
                time.sleep(2)
                VenvRequirementsManager.restart_in_venv()
            else:
                print(f"❌ {message}")
                print("\n💡 Установите зависимости вручную:")
                venv_python = VenvRequirementsManager.get_venv_python()
                if venv_python:
                    print(f"  {venv_python} -m pip install flask python-dotenv pyopenssl psutil")
                
    except Exception as e:
        print(f"❌ Ошибка при настройке окружения: {e}")
        import traceback
        traceback.print_exc()
    
    # ========== СЕДЬМОЙ ЭТАП: ИНИЦИАЛИЗАЦИЯ ЛОГГЕРА ==========
    print("\n📝 НАСТРОЙКА ЛОГГИРОВАНИЯ")
    print("="*60)
    
    args = parse_args()
    
    try:
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
        
        print("✅ Логгер инициализирован")
    except Exception as e:
        print(f"❌ Ошибка инициализации логгера: {e}")
        logger = None


    # ========== ВОСЬМОЙ ЭТАП: ОПРЕДЕЛЕНИЕ ПОДСЕТИ И ПОРТА ==========
    print("\n🌐 ОПРЕДЕЛЕНИЕ ПОДСЕТИ И ПОРТА")
    print("="*60)
    try:
        from files.core.utils.loader_utils import get
        result = get('docker','allocate_network_and_ports')
        print(f"   📌 OCTET      = {result['octet']}")
        print(f"   📌 BASE_PORT  = {result['base_port']}")
        print(f"   📌 PREFIX     = {result['network_prefix']}")
    except Exception as e:
        print(f"❌ Ошибка выделения сети: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print("="*60 + "\n")

    # ========== ДЕВЯТЫЙ ЭТАП: ПЕРВИЧНАЯ НАСТРОЙКА ПРИЛОЖЕНИЯ ==========
    print("\n🔐 ПЕРВИЧНАЯ НАСТРОЙКА ПРИЛОЖЕНИЯ")
    print("="*60)
    
    try:
        from files.core.utils.firstSetup_utils import first_run_setup
        is_first_run, credentials = first_run_setup()
        if is_first_run and credentials:
            if logger:
                logger.info("First run setup completed")
            print("\n" + "="*50)
            print("🎉 ПЕРВИЧНАЯ НАСТРОЙКА ЗАВЕРШЕНА")
            print("="*50)
            print(f"👤 Логин: {credentials['login']}")
            print(f"🔑 Пароль: {credentials['password']}")
            print("💾 Сохраните эти данные!")
            print("="*50 + "\n")
        else:
            print("✅ Настройка уже выполнена ранее")
    except Exception as e:
        print(f"❌ Ошибка первичной настройки: {e}")
    
    # ========== ДЕСЯТЫЙ ЭТАП: НАСТРОЙКА ФАЕРВОЛА И ПОРТОВ ==========
    print("\n🔒 НАСТРОЙКА ФАЕРВОЛА И ПОРТОВ")
    print("="*60)
    
    try:
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

        # Автоматическое открытие порта 8000
        print("\n🔓 АВТОМАТИЧЕСКАЯ НАСТРОЙКА ПОРТА 8000")
        print("-"*60)
        FirewallModule.ensure_port_open(8000, 'tcp')

        print("="*60)
    except Exception as e:
        print(f"❌ Ошибка настройки фаервола: {e}")
    
    # ========== ОДИННАДЦАТЫЙ ЭТАП: ПРОЦЕССЫ ПЕРЕД ЗАПУСКОМ ==========
    print("\n" + "=" * 60)
    print("🎯 ГОТОВО К ЗАПУСКУ СЕРВЕРА")
    print("=" * 60)
    
    # Показываем процессы еще раз перед запуском
    print_starter_processes()

    # ========== ЗАПУСК РЕЖИМА ==========
    if args.service:
        print("🔧 ЗАПУСК В СЕРВИСНОМ РЕЖИМЕ")
        print("="*60)
        start_service_mode()
    else:
        print("🚀 ЗАПУСК ИНТЕРАКТИВНОГО РЕЖИМА")
        print("="*60)
        if logger:
            logger.info("Starting interactive mode")
        start_interactive_mode()

if __name__ == '__main__':
    main()