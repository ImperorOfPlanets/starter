# starter.py
import argparse
import os
import platform
import sys
import time
import atexit
import subprocess
from pathlib import Path
from datetime import datetime

from files.core.utils.globalVars_utils import get_global, set_global
from files.core.utils.log_utils import LogManager
from files.core.oss.default.system import SystemModule

# ❌ НЕ ИМПОРТИРУЕМ get ЗДЕСЬ! Он будет импортирован в функциях где нужен


def parse_args():
    parser = argparse.ArgumentParser(description='Starter Server Manager')
    parser.add_argument('--service', action='store_true', help='Запуск в сервисном режиме')
    parser.add_argument('--new', action='store_true', help='Удалить настройки и начать заново')
    parser.add_argument('--status', action='store_true', help='Показать статус процессов')
    parser.add_argument('--kill-all', action='store_true', help='Убить все процессы Starter')
    parser.add_argument('--cleanup', action='store_true', help='Очистить потерянные процессы')
    parser.add_argument('--install-service', action='store_true', help='Установить системный сервис')
    parser.add_argument('--uninstall-service', action='store_true', help='Удалить системный сервис')
    parser.add_argument('--install-cron', action='store_true', help='Установить CRON задачу')
    return parser.parse_args()


def reset_configuration():
    """Сброс конфигурации"""
    env_path = get_global('starter_env_path')
    if env_path and env_path.exists():
        try:
            env_path.unlink()
            print("✅ Файл конфигурации .env удален")
            return True
        except Exception as e:
            print(f"❌ Ошибка при удалении .env: {e}")
            return False
    print("ℹ️ Файл .env не найден")
    return True


def check_and_install_service():
    """Проверяет и устанавливает сервис (только при первой установке)"""
    from files.core.utils.loader_utils import get
    
    service_module = get('service')
    
    if not service_module or not service_module.check():
        return
    
    try:
        is_installed = service_module.is_service_installed()
        
        if not is_installed:
            result = service_module.install_service()
            if result['status'] == 'success':
                print("   ✅ Сервис успешно установлен!")
            elif result['status'] == 'skipped':
                pass  # systemd недоступен, сообщение уже выведено
            else:
                print(f"   ⚠️ Сервис не установлен: {result.get('message')}")
        else:
            print("   ✅ Системный сервис уже установлен")
            
    except Exception as e:
        print(f"   ⚠️ Ошибка при работе с сервисом: {e}")


def check_and_install_cron():
    """Предлагает установить CRON задачу (для Linux/macOS)"""
    system = platform.system()
    
    if system in ['Linux', 'Darwin']:
        print("\n⏰ Настройка CRON для автозапуска...")
        try:
            # Проверяем, есть ли уже задача в CRON
            result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
            current_cron = result.stdout if result.returncode == 0 else ""
            
            starter_path = get_global('starter_path')
            starter_script = starter_path / "starter.py"
            venv_python = starter_path / "venv" / "bin" / "python"
            
            if not venv_python.exists():
                venv_python = Path(sys.executable)
            
            cron_job = f"@reboot {venv_python} {starter_script} --service\n"
            
            if cron_job not in current_cron:
                choice = input("   Хотите добавить задачу в CRON для автозапуска? (y/N): ").strip().lower()
                if choice == 'y':
                    # Добавляем задачу
                    new_cron = current_cron + cron_job
                    process = subprocess.run(['crontab', '-'], input=new_cron, text=True, capture_output=True)
                    if process.returncode == 0:
                        print("   ✅ CRON задача успешно добавлена!")
                    else:
                        print(f"   ❌ Ошибка добавления CRON задачи: {process.stderr}")
            else:
                print("   ✅ CRON задача уже существует")
                
        except FileNotFoundError:
            print("   ⚠️ CRON не доступен на этой системе")
        except Exception as e:
            print(f"   ⚠️ Ошибка при настройке CRON: {e}")


def start_service_mode():
    """Режим работы как сервис/демон"""
    logger = LogManager.get_logger('main')
    logger.info("Запуск в сервисном режиме...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Сервис остановлен")
        sys.exit(0)


def start_interactive_mode():
    """Интерактивный режим с веб-интерфейсом"""
    from files.core.utils.loader_utils import get  # <-- Импорт ТОЛЬКО здесь
    from files.core.utils.app_flask import configure_app
    from dotenv import load_dotenv

    logger = LogManager.get_logger('starter')
    
    env_path = get_global('starter_env_path')
    if env_path and env_path.exists():
        load_dotenv(env_path, override=True)
        print(f"[DEBUG] Переменные окружения загружены из {env_path}")
    else:
        print(f"[WARNING] Файл .env не найден")
    
    port_from_env = os.environ.get('PORT')
    if port_from_env:
        set_global('port', int(port_from_env))
        print(f"[DEBUG] Порт из .env: {port_from_env}")
    
    ssl_module = get('ssl')
    network_module = get('network')
    setup_module = get('setup')
    tray_module = get('tray')
    
    ssl_context = None
    if ssl_module:
        try:
            cert_file, key_file = ssl_module.generate_self_signed_cert()
            ssl_context = (str(cert_file), str(key_file))
            print(f"   ✅ SSL certificates loaded")
            logger.info(f"SSL certificates loaded: {cert_file}")
        except Exception as e:
            print(f"   ❌ Failed to generate SSL certificates: {e}")
            logger.error(f"Failed to generate SSL certificates: {e}")
    
    port = get_global('port', 2000)
    protocol = 'https' if ssl_context else 'http'
    
    if network_module:
        ips = network_module.get_all_local_ips()
    else:
        ips = ['127.0.0.1']
    
    print("\n" + "="*60)
    print("🌐 СЕРВЕР ЗАПУЩЕН!")
    print("="*60)
    print(f"   🔗 Локальный доступ: {protocol}://127.0.0.1:{port}")
    for ip in ips:
        if ip != '127.0.0.1':
            print(f"   🔗 Сетевой доступ:   {protocol}://{ip}:{port}")
    print(f"   📡 Порт: {port}")
    print("="*60 + "\n")
    print("🛑 Для остановки нажмите Ctrl+C")
    print("")
    
    if setup_module:
        setup_module.open_browser()
    
    # Запуск иконки в трее
    if tray_module:
        if tray_module.is_available():
            print("🖥️ Запуск иконки в системном трее...")
            tray_module.run_tray()
        else:
            print("   ⚠️ Библиотеки для трея не установлены (pystray, Pillow)")
            print("   💡 Установите: pip install pystray Pillow")
    else:
        print("   ⚠️ Tray module not found")
    
    app = configure_app()
    try:
        app.run(
            host='0.0.0.0', 
            port=port, 
            ssl_context=ssl_context, 
            debug=False, 
            use_reloader=False,
            threaded=True, 
            processes=1
        )
    except KeyboardInterrupt:
        print("\n\n🛑 Получен сигнал остановки от пользователя")
        raise
    finally:
        if tray_module:
            tray_module.stop_tray()


def main():
    print("\n" + "=" * 60)
    print("🚀 ЗАПУСК СТАРТЕРА СЕРВЕРА")
    print("=" * 60)
    print(f"Текущий PID: {os.getpid()}")
    print(f"Python: {sys.executable}")
    print(f"ОС: {platform.system()}")

    args = parse_args()
    set_global('is_service', args.service)

    # ============================================================
    # ЭТАП 1: SystemModule - сбор информации о системе
    # ============================================================
    print("\n🔧 ЭТАП 1: SystemModule - сбор информации о системе")
    print("-" * 40)
    SystemModule.collect_basic_system_info()
    print(f"   ✅ starter_path: {get_global('starter_path')}")

    # ============================================================
    # ПРОВЕРКА НА ДОЧЕРНИЙ ПРОЦЕСС WERKZEUG
    # ============================================================
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        print("\n🔄 Обнаружен дочерний процесс Werkzeug. Пропускаем инициализацию.")
        
        if get_global('port') is None:
            from files.core.software.default.env import EnvModule
            env_vars = EnvModule.read_env_file(get_global('starter_env_path'))
            if 'PORT' in env_vars:
                set_global('port', int(env_vars['PORT']))
                print(f"   🐛 (fallback) Порт из .env: {get_global('port')}")
        
        LogManager.initialize(debug_mode=get_global('DEBUG', False))
        start_interactive_mode()
        return

    # ============================================================
    # ЭТАП 2: LogManager - инициализация логирования
    # ============================================================
    print("\n📝 ЭТАП 2: LogManager - инициализация логирования")
    print("-" * 40)
    LogManager.initialize(
        debug_mode=get_global('DEBUG', False),
        service_mode=args.service
    )
    logger = LogManager.get_logger('main')
    logger.info("Логирование инициализировано")
    print("   ✅ Логгер создан")

    # ============================================================
    # ЭТАП 3: --new (сброс конфигурации)
    # ============================================================
    if args.new:
        print("\n🔄 ЭТАП 3: Сброс конфигурации")
        print("-" * 40)
        if reset_configuration():
            logger.info("Конфигурация сброшена")
            print("   ✅ Конфигурация сброшена")
            print("   🔄 Перезапустите программу без --new")
            sys.exit(0)
        else:
            logger.error("Ошибка сброса конфигурации")
            sys.exit(1)

    # ============================================================
    # ЭТАП 4: Предварительные команды (status, kill-all, cleanup)
    # ============================================================
    try:
        from files.core.oss.default.process import ProcessModule
        ProcessModule.set_globals()
        
        if args.status:
            ProcessModule.print_status()
            sys.exit(0)
        
        if args.kill_all:
            print("\n💀 Убиваем все процессы Starter...")
            result = ProcessModule.kill_all_processes(exclude_current=False)
            print(f"   ✅ Убито процессов: {len(result.get('killed', []))}")
            sys.exit(0)
        
        if args.cleanup:
            ProcessModule.cleanup_orphaned()
            sys.exit(0)
            
    except ImportError:
        pass
    except Exception as e:
        print(f"   ⚠️ Ошибка: {e}")

    # ============================================================
    # ЭТАП 5: Проверка зависимостей и VENV
    # ============================================================
    print("\n📦 ЭТАП 5: Проверка зависимостей и виртуального окружения")
    print("-" * 40)
    from files.core.oss.default.requirements import RequirementsModule
    RequirementsModule.set_globals()
    RequirementsModule.print_debug_info()
    
    if not RequirementsModule.ensure_requirements():
        print("   ❌ Ошибка настройки окружения")
        logger.error("Requirements setup failed")
        sys.exit(1)
    print("   ✅ Зависимости настроены")

    # ============================================================
    # ЭТАП 6: Первоначальная настройка (если нет .env)
    # ============================================================
    env_path = get_global('starter_env_path')
    need_first_setup = not env_path.exists()
    
    if need_first_setup and not args.service:
        print("\n🔐 ЭТАП 6: ПЕРВОНАЧАЛЬНАЯ НАСТРОЙКА")
        print("-" * 40)
        try:
            from files.core.oss.default.setup import SetupModule
            
            # Выбор типа сервера и установка
            is_first, credentials = SetupModule.first_run_setup(interactive=True)
            
            if is_first and credentials:
                print("\n" + "="*60)
                print("🔐 СОХРАНИТЕ УЧЕТНЫЕ ДАННЫЕ!")
                print("="*60)
                print(f"👤 Логин: {credentials['login']}")
                print(f"🔑 Пароль: {credentials['password']}")
                if credentials.get('master_password'):
                    print(f"🔐 Мастер-пароль: {credentials['master_password']}")
                print("="*60 + "\n")
                
                # Установка сервиса/CRON (ТОЛЬКО ПРИ ПЕРВОНАЧАЛЬНОЙ УСТАНОВКЕ)
                check_and_install_service()
                
                # Перезапуск в VENV
                from files.core.oss.default.requirements import RequirementsModule
                RequirementsModule.set_globals()
                if not RequirementsModule.in_venv():
                    print("\n📦 Создание виртуального окружения...")
                    RequirementsModule.restart_in_venv()
                    return
                    
        except Exception as e:
            print(f"   ❌ Ошибка установки: {e}")
            logger.error(f"First run setup failed: {e}")
            sys.exit(1)

    # ============================================================
    # ЭТАП 7: Управление процессами
    # ============================================================
    print("\n🔧 ЭТАП 7: Управление процессами")
    print("-" * 40)
    
    process_module = None
    try:
        from files.core.oss.default.process import ProcessModule
        process_module = ProcessModule
        process_module.set_globals()
        
        print("   🧹 Очистка потерянных процессов...")
        process_module.cleanup_orphaned()
        
        print("   📝 Регистрация процесса...")
        result = process_module.register_process()
        print(f"      PID: {result['pid']}, is_child: {result['is_child']}")
        
        print("   ⚡ Настройка обработчиков сигналов...")
        process_module.setup_signal_handlers()
        
        print("   🔗 Связывание процессов...")
        process_module.bind_processes()
        
        atexit.register(process_module.unregister_process)
        
        print("   ✅ Управление процессами активировано")
        
    except ImportError as e:
        print(f"   ⚠️ Модуль process не найден: {e}")
    except Exception as e:
        print(f"   ⚠️ Ошибка инициализации process модуля: {e}")
        logger.error(f"Process module init failed: {e}")

    # ============================================================
    # ЭТАП 8: Загрузка модулей
    # ============================================================
    print("\n📦 ЭТАП 8: Загрузка модулей")
    print("-" * 40)
    try:
        from files.core.utils.loader_utils import load_modules, initialize_global_modules
        modules = load_modules()
        print(f"   ✅ Загружено {len(modules)} модулей")
        initialize_global_modules()
        logger.info(f"Loaded {len(modules)} modules")
    except Exception as e:
        print(f"   ⚠️ Ошибка загрузки модулей: {e}")
        logger.warning(f"Module loading failed: {e}")

    # ============================================================
    # ЭТАП 8.1: Инициализация серверов и пользователей
    # ============================================================
    print("\n👥 ЭТАП 8.1: Серверы и пользователи")
    print("-" * 40)
    try:
        from files.core.oss.default.servers import ServersModule
        servers = ServersModule.get_all()
        print(f"   ✅ Серверов в реестре: {len(servers)}")

        # Проверяем есть ли ADMIN_LOGIN в .env
        env_path = get_global('starter_env_path')
        env_has_admin = False
        if env_path and env_path.exists():
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip().startswith('ADMIN_LOGIN=') and len(line.split('=', 1)[1].strip()) > 0:
                        env_has_admin = True
                        break

        if not env_has_admin:
            import secrets
            import string
            import hashlib

            admin_login = 'admin_' + secrets.token_hex(2)
            admin_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
            password_hash = hashlib.sha256(admin_password.encode()).hexdigest()

            if env_path and env_path.exists():
                with open(env_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                new_lines = []
                login_found = False
                hash_found = False
                for line in lines:
                    if line.startswith('ADMIN_LOGIN='):
                        new_lines.append(f'ADMIN_LOGIN={admin_login}\n')
                        login_found = True
                    elif line.startswith('ADMIN_PASSWORD_HASH='):
                        new_lines.append(f'ADMIN_PASSWORD_HASH={password_hash}\n')
                        hash_found = True
                    else:
                        new_lines.append(line)
                if not login_found:
                    new_lines.append(f'ADMIN_LOGIN={admin_login}\n')
                if not hash_found:
                    new_lines.append(f'ADMIN_PASSWORD_HASH={password_hash}\n')
                with open(env_path, 'w', encoding='utf-8') as f:
                    f.writelines(new_lines)

            print("\n" + "=" * 60)
            print("🔐 СОЗДАН АДМИНСКИЙ АККАУНТ")
            print("=" * 60)
            print(f"   👤 Логин:  {admin_login}")
            print(f"   🔑 Пароль: {admin_password}")
            print("=" * 60 + "\n")
        else:
            print(f"   ✅ Admin login настроен в .env")
    except Exception as e:
        print(f"   ⚠️ Ошибка инициализации серверов/пользователей: {e}")
        logger.error(f"Servers/Users init failed: {e}")

    # ============================================================
    # ЭТАП 9: Команды установки/удаления сервиса
    # ============================================================
    if args.install_service:
        print("\n🔧 УСТАНОВКА СИСТЕМНОГО СЕРВИСА")
        print("-" * 40)
        from files.core.utils.loader_utils import get
        service_module = get('service')
        if service_module and service_module.check():
            result = service_module.install_service()
            if result['status'] == 'success':
                print("   ✅ Сервис успешно установлен!")
            else:
                print(f"   ❌ Ошибка: {result.get('message')}")
        else:
            print("   ❌ Service module not available for this OS")
        sys.exit(0)
    
    if args.uninstall_service:
        print("\n🔧 УДАЛЕНИЕ СИСТЕМНОГО СЕРВИСА")
        print("-" * 40)
        from files.core.utils.loader_utils import get
        service_module = get('service')
        if service_module and service_module.check():
            result = service_module.uninstall_service()
            if result['status'] == 'success':
                print("   ✅ Сервис успешно удален!")
            else:
                print(f"   ❌ Ошибка: {result.get('message')}")
        else:
            print("   ❌ Service module not available for this OS")
        sys.exit(0)
    
    if args.install_cron:
        print("\n⏰ УСТАНОВКА CRON ЗАДАЧИ")
        print("-" * 40)
        check_and_install_cron()
        sys.exit(0)

    # ============================================================
    # ЭТАП 10: Реестр проектов
    # ============================================================
    print("\n📋 ЭТАП 10: Состояние реестра проектов")
    print("-" * 40)
    try:
        from files.core.oss.default.registry import RegistryModule
        import json
        registry_path = RegistryModule.get_registry_path()
        print(f"   📁 Файл реестра: {registry_path}")
        
        if registry_path.exists():
            with open(registry_path, 'r', encoding='utf-8') as f:
                registry_data = json.load(f)
            projects = registry_data.get('projects', [])
            
            if projects:
                print(f"   📌 Найдено проектов: {len(projects)}")
                for i, proj in enumerate(projects, 1):
                    path = proj.get('path', 'unknown')
                    octet = proj.get('subnet_octet', 0)
                    port = proj.get('port', 0)
                    status = proj.get('status', 'unknown')
                    print(f"   Проект #{i}: {os.path.basename(path)} | октет: {octet} | порт: {port} | статус: {status}")
            else:
                print("   📌 Реестр пуст")
        else:
            print("   📌 Файл реестра не существует")
            
            # Регистрируем текущий проект
            project_path = get_global('project_path')
            if project_path:
                print(f"   📝 Регистрация текущего проекта...")
                RegistryModule.register_initializing(str(project_path))
                print(f"   ✅ Проект зарегистрирован в реестре")
                
    except Exception as e:
        print(f"   ⚠️ Ошибка: {e}")

    # ============================================================
    # ЭТАП 11: Проверка порта стартера
    # ============================================================
    if not get_global('WERKZEUG'):
        print("\n🌐 ЭТАП 11: Проверка порта стартера")
        print("-" * 40)

        starter_port = get_global('port', 2000)

        # Проверяем занят ли порт
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', starter_port))
        sock.close()

        if result == 0:
            print(f"   ❌ Порт {starter_port} уже занят!")
            print(f"   🛑 Остановите占用此端口的 процесс или измените PORT в .env")
            logger.error(f"Port {starter_port} is already in use")
            sys.exit(1)
        else:
            print(f"   ✅ Порт {starter_port} свободен")
            set_global('port', starter_port)
            os.environ["PORT"] = str(starter_port)

    # ============================================================
    # ЭТАП 12: Обновление реестра
    # ============================================================
    if not get_global('WERKZEUG'):
        print("\n🔖 ЭТАП 12: Обновление реестра проекта")
        print("-" * 40)
        try:
            from files.core.oss.default.registry import RegistryModule
            project_path = get_global('project_path')
            if project_path:
                subnet_octet = get_global('subnet_octet', 0)
                port = get_global('port', 0)
                
                RegistryModule.register_project(
                    str(project_path), 
                    subnet_octet, 
                    port,
                    use_reverse_proxy=False
                )
                print(f"   ✅ Проект зарегистрирован с параметрами:")
                print(f"      📌 Октет: {subnet_octet}")
                print(f"      📌 Порт: {port}")
        except Exception as e:
            print(f"   ⚠️ Ошибка: {e}")

    # ============================================================
    # ЭТАП 13: Фаервол
    # ============================================================
    print("\n🔒 ЭТАП 13: Настройка фаервола")
    print("-" * 40)
    try:
        from files.core.oss.default.firewall import FirewallModule
        current_port = get_global('port')
        if current_port:
            FirewallModule.ensure_port_open(current_port, 'tcp')
            print(f"   ✅ Порт {current_port} открыт")
    except Exception as e:
        print(f"   ⚠️ Ошибка: {e}")

    # ============================================================
    # ЭТАП 14: Запуск
    # ============================================================
    print("\n" + "=" * 60)
    print("🎯 ЗАПУСК")
    print("=" * 60)
    
    if process_module:
        process_module.print_status()

    if args.service:
        print("🔧 Сервисный режим")
        start_service_mode()
    else:
        print("🚀 Интерактивный режим")
        logger.info("Starting interactive mode")
        start_interactive_mode()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Программа остановлена пользователем")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)