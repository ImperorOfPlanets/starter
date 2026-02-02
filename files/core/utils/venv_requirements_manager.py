"""
Управление виртуальным окружением и зависимостями
"""
import argparse
import datetime
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
import venv


from pathlib import Path
from typing import Optional, Tuple, Dict

from files.core.utils.globalVars_utils import get_global, set_global
from files.core.utils.log_utils import LogManager

class VenvRequirementsManager:
    """Менеджер виртуального окружения и зависимостей"""

    _is_installation_process = False  # Флаг, что мы в процессе установки
    
    @staticmethod
    def get_debug_info() -> Dict:
        """Получает полную отладочную информацию о состоянии окружения"""
        info = {
            'timestamp': datetime.datetime.now().isoformat(),
            'python_version': sys.version,
            'platform': platform.platform(),
            'current_python': sys.executable,
            'in_venv': VenvRequirementsManager.in_venv(),
            'venv_path': None,
            'venv_exists': False,
            'venv_created_time': None,
            'venv_size': 0,
            'venv_python_path': None,
            'process_info': {},
            'dependencies_status': {},
            'performance_metrics': {},
            'installation_target': None
        }
        
        # Информация о процессе
        try:
            import psutil
            process = psutil.Process()
            cmdline = ' '.join(process.cmdline())
            info['process_info'] = {
                'pid': process.pid,
                'ppid': process.ppid(),
                'name': process.name(),
                'cmdline': cmdline,
                'memory_usage_mb': process.memory_info().rss / 1024 / 1024,
                'cpu_percent': process.cpu_percent(),
                'threads': process.num_threads(),
                'status': process.status()
            }

            # Определяем куда идет установка
            if 'pip install' in cmdline:
                # Смотрим аргументы pip
                if '--user' in cmdline or '--system' in cmdline:
                    info['installation_target'] = 'SYSTEM (пользовательский уровень)'
                else:
                    info['installation_target'] = 'CURRENT ENV (текущее окружение)'
            elif VenvRequirementsManager._is_installation_process:
                info['installation_target'] = 'VENV (через subprocess)'
            else:
                info['installation_target'] = 'N/A (не установка)'

        except ImportError:
            info['process_info'] = {}
            info['installation_target'] = 'N/A (psutil не установлен)'
        except:
            info['process_info'] = {}
            info['installation_target'] = 'N/A (ошибка получения информации)'
        
        # Информация о venv
        venv_dir = VenvRequirementsManager.get_venv_dir()
        info['venv_path'] = str(venv_dir)
        
        if venv_dir.exists():
            info['venv_exists'] = True
            
            # Время создания
            try:
                create_time = datetime.datetime.fromtimestamp(venv_dir.stat().st_ctime)
                info['venv_created_time'] = create_time.isoformat()
                info['venv_age_days'] = (datetime.datetime.now() - create_time).days
            except:
                pass
            
            # Размер venv
            try:
                total_size = 0
                for file in venv_dir.rglob('*'):
                    if file.is_file():
                        total_size += file.stat().st_size
                info['venv_size_mb'] = total_size / 1024 / 1024
            except:
                pass
            
            # Путь к Python в venv
            venv_python = VenvRequirementsManager.get_venv_python()
            if venv_python:
                info['venv_python_path'] = str(venv_python)
                info['venv_python_exists'] = venv_python.exists()
                
                # Проверяем, используем ли мы этот Python
                info['using_venv_python'] = (Path(sys.executable) == venv_python)
        
        # Проверяем основные зависимости
        info['dependencies_status'] = VenvRequirementsManager.check_critical_dependencies()
        
        # Метрики производительности
        try:
            import psutil
            memory_info = psutil.virtual_memory()
            memory_total_gb = memory_info.total / 1024 / 1024 / 1024
            memory_available_gb = memory_info.available / 1024 / 1024 / 1024
        except ImportError:
            memory_total_gb = 0
            memory_available_gb = 0

        info['performance_metrics'] = {
            'load_avg': os.getloadavg() if hasattr(os, 'getloadavg') else [],
            'cpu_count': os.cpu_count(),
            'memory_total_gb': memory_total_gb,
            'memory_available_gb': memory_available_gb
        }
        
        return info
    
    @staticmethod
    def print_debug_info(title: str = "ОТЛАДОЧНАЯ ИНФОРМАЦИЯ VENV"):
        """Выводит отладочную информацию в консоль при каждом запуске"""
        info = VenvRequirementsManager.get_debug_info()
        
        # Форматируем вывод для лучшей читаемости
        print("\n" + "═" * 70)
        print(f"🔍 {title}")
        print("═" * 70)
        
        # Основная информация
        print(f"📅 Время запуска: {info['timestamp'][11:19]}")
        print(f"🐍 Python версия: {info['python_version'].split()[0]}")
        print(f"🖥️  Платформа: {info['platform']}")
        print(f"📍 Исполняемый файл: {Path(info['current_python']).name}")
        
        # Состояние venv - ВАЖНЕЙШАЯ ИНФОРМАЦИЯ
        print(f"\n📦 СОСТОЯНИЕ ВИРТУАЛЬНОГО ОКРУЖЕНИЯ:")
        
        # Определяем текущее состояние
        if not info['venv_exists']:
            status = "❌ VENV НЕ СУЩЕСТВУЕТ"
            details = f"Путь: {info['venv_path']}"
        elif not info.get('venv_python_exists'):
            status = "⚠️  VENV ПОВРЕЖДЕН"
            details = f"Python не найден в {info['venv_path']}"
        elif not info['in_venv']:
            if info.get('using_venv_python'):
                status = "✅ В VENV (явный путь)"
                details = f"Используется: {Path(info['venv_python_path']).name}"
            else:
                status = "⚠️  НЕ В VENV (запущен в системном Python)"
                details = f"Venv существует, но не активирован"
        else:
            status = "✅ В VENV"
            details = f"Используется venv из: {Path(info['venv_path']).name}"
        
        print(f"   Статус: {status}")
        print(f"   {details}")
        
        if info['venv_exists']:
            print(f"   📁 Размер: {info.get('venv_size_mb', 0):.1f} MB")
            print(f"   🕐 Возраст: {info.get('venv_age_days', 'N/A')} дней")
            if info.get('venv_python_path'):
                print(f"   🐍 Python в venv: {info['venv_python_path']}")
        
        # Цель установки зависимостей
        if info.get('installation_target'):
            print(f"\n🎯 ЦЕЛЬ УСТАНОВКИ ЗАВИСИМОСТЕЙ:")
            print(f"   {info['installation_target']}")
            
            if 'SYSTEM' in info['installation_target'] and info['venv_exists']:
                print(f"   ⚠️  ВНИМАНИЕ: Зависимости будут установлены в СИСТЕМНЫЙ Python!")
                print(f"   💡 Используйте: {info['venv_python_path']} -m pip install ...")
        
        # Порт
        print(f"\n📡 ПОРТ: {info['port']}")
        
        # Информация о процессе
        if info['process_info']:
            print(f"\n🔄 ИНФОРМАЦИЯ О ПРОЦЕССЕ:")
            proc = info['process_info']
            
            # Определяем тип процесса
            cmdline = proc.get('cmdline', '')
            process_type = "❓ Неизвестный процесс"
            
            if 'starter.py' in cmdline:
                if 'pip install' in cmdline or '-m pip' in cmdline:
                    process_type = "🔧 ПРОЦЕСС УСТАНОВКИ ЗАВИСИМОСТЕЙ"
                else:
                    process_type = "⭐ ОСНОВНОЙ ПРОЦЕСС STARTER.PY"
            elif 'python' in cmdline and 'pip' in cmdline:
                process_type = "📦 ПРОЦЕСС УСТАНОВКИ PIP"
            
            print(f"   Тип: {process_type}")
            print(f"   PID: {proc.get('pid')}")
            print(f"   Память: {proc.get('memory_usage_mb', 0):.1f} MB")
            print(f"   Статус: {proc.get('status', 'N/A')}")
        
        # Статус зависимостей
        deps = info['dependencies_status']
        print(f"\n📦 КРИТИЧЕСКИЕ ЗАВИСИМОСТИ:")
        
        missing_deps = []
        for dep, installed in deps.items():
            status = "✅ Установлен" if installed else "❌ ОТСУТСТВУЕТ"
            print(f"   {dep}: {status}")
            if not installed:
                missing_deps.append(dep)
        
        if missing_deps:
            print(f"   ⚠️  Отсутствуют: {', '.join(missing_deps)}")
        
        print("═" * 70 + "\n")
    
    @staticmethod
    def check_critical_dependencies() -> Dict[str, bool]:
        """Проверяет наличие критических зависимостей"""
        deps = {}
        try:
            import flask
            deps['Flask'] = True
        except:
            deps['Flask'] = False
            
        try:
            import dotenv
            deps['python-dotenv'] = True
        except:
            deps['python-dotenv'] = False
            
        try:
            import OpenSSL
            deps['pyOpenSSL'] = True
        except:
            deps['pyOpenSSL'] = False
            
        return deps
    
    @staticmethod
    def parse_args():
        """Парсит аргументы командной строки"""
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument('--update', action='store_true')
        
        # Парсим только известные аргументы, чтобы не конфликтовать с другими парсерами
        args, _ = parser.parse_known_args()
        return args

    @staticmethod
    def in_venv() -> bool:
        """Проверяет, находится ли скрипт в виртуальном окружении"""
        return (
            hasattr(sys, 'real_prefix') or
            (hasattr(sys, 'base_prefix') and sys.prefix != sys.base_prefix) or
            os.environ.get('VIRTUAL_ENV') is not None
        )
    
    @staticmethod
    def get_venv_dir() -> Path:
        return get_global('starter_path') / "venv"
    
    @staticmethod
    def get_venv_python() -> Optional[Path]:
        """Получает путь к Python в venv"""
        venv_dir = VenvRequirementsManager.get_venv_dir()
        
        if platform.system() == "Windows":
            python_exe = venv_dir / "Scripts" / "python.exe"
            python_exe_alt = venv_dir / "Scripts" / "python"
            python_exe_alt2 = venv_dir / "Scripts" / "pythonw.exe"
        else:
            python_exe = venv_dir / "bin" / "python"
            python_exe_alt = venv_dir / "bin" / "python3"
            python_exe_alt2 = None
        
        # Проверяем существование файлов
        for python_path in [python_exe, python_exe_alt, python_exe_alt2]:
            if python_path and python_path.exists():
                return python_path
        
        return None
    
    @staticmethod
    def create_venv() -> Tuple[bool, str]:
        """Создает виртуальное окружение с учетом порта"""
        try:
            venv_dir = VenvRequirementsManager.get_venv_dir()
            
            print("\n" + "═" * 60)
            print("🔧 ЭТАП 1: СОЗДАНИЕ ВИРТУАЛЬНОГО ОКРУЖЕНИЯ")
            print("═" * 60)
            
            # Удаляем старый venv если он есть
            if venv_dir.exists():
                print("📂 Удаляем старое окружение...")
                try:
                    start_time = time.time()
                    shutil.rmtree(venv_dir, ignore_errors=True)
                    elapsed = time.time() - start_time
                    print(f"   ✅ Удалено за {elapsed:.1f} секунд")
                    time.sleep(0.5)
                except Exception as e:
                    print(f"⚠️  Не удалось удалить старый venv: {e}")
            
            # Создаем новый venv
            print("📦 Создаем новое окружение...")
            start_time = time.time()
            builder = venv.EnvBuilder(
                with_pip=True,
                upgrade_deps=True,
                clear=True,
                symlinks=False,
                system_site_packages=False
            )
            builder.create(venv_dir)
            elapsed = time.time() - start_time
            
            # Проверяем создание
            if not venv_dir.exists():
                return False, "Не удалось создать venv"
            
            print(f"✅ Виртуальное окружение создано за {elapsed:.1f} секунд")
            print(f"📁 Путь: {venv_dir}")
            
            # Показываем Python в venv
            venv_python = VenvRequirementsManager.get_venv_python()
            if venv_python:
                print(f"🐍 Python в venv: {venv_python}")

            return True, "Venv создан успешно"
            
        except Exception as e:
            return False, f"Ошибка создания venv: {str(e)}"
    
    @staticmethod
    def install_requirements_with_progress() -> Tuple[bool, str]:
        """Устанавливает зависимости в venv через subprocess"""
        try:
            # Устанавливаем флаг, что мы в процессе установки
            VenvRequirementsManager._is_installation_process = True
            
            venv_python = VenvRequirementsManager.get_venv_python()
            if not venv_python:
                return False, "❌ Не найден Python в venv"
            
            requirements_path = VenvRequirementsManager.find_requirements()
            if not requirements_path:
                return False, "❌ Не найден файл requirements.txt"

            print("\n" + "═" * 60)
            print(f"📦 ЭТАП 2: УСТАНОВКА ЗАВИСИМОСТЕЙ В VENV")
            print("═" * 60)
            print(f"📄 Файл зависимостей: {requirements_path.name}")
            print(f"📁 Виртуальное окружение: {VenvRequirementsManager.get_venv_dir().name}")
            print(f"🐍 Используется Python: {venv_python}")
            print(f"📍 Установка в: VENV (не в систему!)")
            
            # Создаем временный файл для вывода
            with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as log_file:
                log_path = log_file.name
            
            try:
                # 1. Обновляем pip В VENV
                print("\n🔄 Обновляем pip в venv...")
                start_time = time.time()
                update_cmd = [
                    str(venv_python),
                    "-m",
                    "pip",
                    "install",
                    "--upgrade",
                    "pip",
                    "--disable-pip-version-check"
                ]
                
                print(f"   Команда: {' '.join(update_cmd)}")
                result = subprocess.run(
                    update_cmd,
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                pip_time = time.time() - start_time
                
                if result.returncode != 0:
                    print(f"⚠️  Не удалось обновить pip: {result.stderr[:200]}")
                else:
                    print(f"✅ Pip в venv обновлен за {pip_time:.1f} секунд")
                
                # 2. Устанавливаем зависимости В VENV
                print("\n📥 Устанавливаем пакеты в venv...")
                print("   ⏱️  Это может занять несколько минут...")
                
                start_time = time.time()
                install_cmd = [
                    str(venv_python),
                    "-m",
                    "pip",
                    "install",
                    "-r",
                    str(requirements_path),
                    "--no-warn-script-location"
                ]
                
                print(f"   Команда: {' '.join(install_cmd[:5])}...")
                print("\n   Прогресс установки: ", end="", flush=True)
                
                # Запускаем установку
                process = subprocess.Popen(
                    install_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )
                
                # Мониторим процесс
                dots = 0
                output_lines = []
                while True:
                    output = process.stdout.readline()
                    if output == '' and process.poll() is not None:
                        break
                    if output:
                        output_lines.append(output.strip())
                        # Показываем прогресс
                        dots += 1
                        if dots % 10 == 0:
                            print(".", end="", flush=True)
                
                process.wait()
                install_time = time.time() - start_time
                
                if process.returncode == 0:
                    # Анализируем вывод
                    for line in output_lines:
                        if 'Successfully installed' in line:
                            print(f"\n\n✅ УСТАНОВКА В VENV ЗАВЕРШЕНА!")
                            print(f"   {line}")
                            break
                    
                    print(f"   ⏱️  Время установки: {install_time:.1f} секунд")
                    
                    # Проверяем, что установлено в venv
                    print("\n🔍 Проверяем установленные пакеты в venv...")
                    check_cmd = [str(venv_python), "-m", "pip", "list"]
                    result = subprocess.run(check_cmd, capture_output=True, text=True)
                    
                    if result.returncode == 0:
                        # Ищем критические зависимости
                        for dep in ['flask', 'python-dotenv', 'pyopenssl']:
                            if dep in result.stdout.lower():
                                print(f"   ✅ {dep}: установлен в venv")
                            else:
                                print(f"   ❌ {dep}: НЕ найден в venv")
                    
                    return True, "Установка в venv завершена"
                else:
                    # Показываем ошибки
                    error_msg = "\n".join(output_lines[-10:]) if output_lines else "Неизвестная ошибка"
                    print(f"\n\n❌ ОШИБКА УСТАНОВКИ В VENV!")
                    print(f"   ⏱️  Время до ошибки: {install_time:.1f} секунд")
                    print(f"   📋 Ошибка: {error_msg}")
                    
                    return False, f"Ошибка установки в venv: {error_msg}"
                    
            except subprocess.TimeoutExpired:
                return False, "Таймаут установки зависимостей (более 5 минут)"
            except Exception as e:
                return False, f"Ошибка: {str(e)}"
            finally:
                # Удаляем временный файл
                try:
                    os.unlink(log_path)
                except:
                    pass
                VenvRequirementsManager._is_installation_process = False
                
        except Exception as e:
            VenvRequirementsManager._is_installation_process = False
            return False, f"Критическая ошибка: {str(e)}"
    
    @staticmethod
    def restart_in_venv():
        """Показывает команду для запуска в venv и завершает работу"""
        try:
            venv_python = VenvRequirementsManager.get_venv_python()
            if not venv_python:
                print("\n❌ КРИТИЧЕСКАЯ ОШИБКА: Не найден Python в venv")
                print("   Путь к ожидаемому venv: {}".format(VenvRequirementsManager.get_venv_dir()))
                sys.exit(1)

            # Формируем команду для запуска
            cmd_parts = [str(venv_python), str(get_global('script_path'))]
            
            # Добавляем остальные аргументы (кроме --new)
            for arg in sys.argv[1:]:
                if arg != '--new':
                    cmd_parts.append(arg)
            
            # Формируем команду для отображения
            cmd_str = ' '.join(cmd_parts)
            
            print("\n" + "═" * 70)
            print("✅ АВТОМАТИЧЕСКАЯ НАСТРОЙКА ЗАВЕРШЕНА")
            print("═" * 70)
            print("📦 Виртуальное окружение создано и зависимости установлены!")
            print("🐍 Python в venv: {}".format(venv_python))
            
            if platform.system() == "Windows":
                print("\n📋 КОМАНДА ДЛЯ ЗАПУСКА В VENV (Windows):")
                print(f"  {cmd_str}")
                
                print("\n📋 АЛЬТЕРНАТИВНЫЕ СПОСОБЫ ЗАПУСКА:")
                print("  1. Активировать venv и запустить:")
                print(f"     {venv_python.parent}\\activate")
                print(f"     python {get_global('script_path').name}")
                
                print("\n  2. Использовать activate.bat:")
                print(f"     call {venv_python.parent}\\activate.bat")
                print(f"     python {get_global('script_path').name}")
                
            else:
                print("\n📋 КОМАНДА ДЛЯ ЗАПУСКА В VENV (Linux/Mac):")
                print(f"  {cmd_str}")
                
                print("\n📋 АЛЬТЕРНАТИВНЫЕ СПОСОБЫ ЗАПУСКА:")
                print("  1. Активировать venv и запустить:")
                print(f"     source {venv_python.parent}/activate")
                print(f"     python {get_global('script_path').name}")
                
                print("\n  2. Прямой запуск:")
                print(f"     {venv_python} {get_global('script_path').name}")
            
            print("\n" + "═" * 70)
            print("🔄 ЗАВЕРШАЕМ РАБОТУ. ЗАПУСТИТЕ КОМАНДУ ВЫШЕ ДЛЯ ПРОДОЛЖЕНИЯ.")
            print("═" * 70 + "\n")
            
            # Завершаем работу
            sys.exit(0)
            
        except Exception as e:
                print(f"\n❌ ФАТАЛЬНАЯ ОШИБКА в restart_in_venv: {e}")
                import traceback
                traceback.print_exc()
                sys.exit(1)
    
    @staticmethod
    def first_run_setup() -> bool:
        """
        Выполняет полную настройку при первом запуске:
        1. Создает venv
        2. Устанавливает зависимости
        3. Показывает команду для запуска
        
        Returns:
            bool: True если настройка выполнена
        """
        # Если уже в venv - пропускаем настройку
        if VenvRequirementsManager.in_venv():
            print("✅ Уже в виртуальном окружении, пропускаем автоматическую настройку")
            return False

        print("\n" + "═" * 60)
        print("🎯 ОБНАРУЖЕН ПЕРВЫЙ ЗАПУСК - АВТОМАТИЧЕСКАЯ НАСТРОЙКА")
        print("═" * 60)
        print(f"🐍 Текущий Python: {Path(sys.executable).name}")
        
        # Проверяем, существует ли уже venv
        venv_dir = VenvRequirementsManager.get_venv_dir()
        if venv_dir.exists():
            venv_python = VenvRequirementsManager.get_venv_python()
            if venv_python and venv_python.exists():
                print(f"\n⚠️  Виртуальное окружение уже существует: {venv_dir}")
                print(f"🐍 Python в venv: {venv_python}")
                print("\n📋 ДЛЯ ЗАПУСКА В VENV ИСПОЛЬЗУЙТЕ КОМАНДУ:")

                cmd = f"{venv_python} {get_global('script_path')}"

                print(f"  {cmd}")
                print("\n🔄 Завершаем работу...")
                sys.exit(0)
        
        # 1. Создаем venv
        print("\n🚀 ЭТАП 1/3: СОЗДАНИЕ VENV")
        success, message = VenvRequirementsManager.create_venv()
        if not success:
            print(f"\n❌ Ошибка: {message}")
            print("\n💡 Попробуйте создать виртуальное окружение вручную:")
            print(f"  python -m venv venv")
            return False
        
        # 2. Устанавливаем зависимости В VENV
        print("\n🚀 ЭТАП 2/3: УСТАНОВКА ЗАВИСИМОСТЕЙ В VENV")
        print("Это может занять несколько минут...")
        
        # Показываем прогресс
        start_time = time.time()
        success, message = VenvRequirementsManager.install_requirements_with_progress()
        elapsed_time = time.time() - start_time
        
        if not success:
            print(f"\n❌ Ошибка: {message}")
            print(f"⏱️  Время выполнения: {elapsed_time:.1f} секунд")
            print("\n💡 Попробуйте установить зависимости вручную:")
            print(f"  {VenvRequirementsManager.get_venv_python()} -m pip install -r requirements.txt")
            return False
        
        print(f"\n✅ Зависимости установлены в venv за {elapsed_time:.1f} секунд")
        
        # 3. Показываем команду для запуска и завершаем работу
        print("\n🚀 ЭТАП 3/3: НАСТРОЙКА ЗАВЕРШЕНА")
        
        print("\n" + "═" * 60)
        print("✅ АВТОМАТИЧЕСКАЯ НАСТРОЙКА УСПЕШНО ЗАВЕРШЕНА")
        print("═" * 60)
        print(f"⏱️  Общее время настройки: {elapsed_time:.1f} секунд")
        print(f"🐍 Python в venv: {VenvRequirementsManager.get_venv_python()}")
        print("═" * 60 + "\n")
        
        VenvRequirementsManager.restart_in_venv()
        return True  # Если дошли сюда, значит что-то пошло не так
    
    @staticmethod
    def find_requirements() -> Optional[Path]:
        """Находит файл requirements.txt с учетом ОС"""
        try:
            # Определяем корень проекта

            reqs_dir = get_global('starter_path') / "files" / "requirements"
            
            # Получаем информацию об ОС
            os_name = get_global('os', '').lower()
            os_family = get_global('os_family', '').lower()
            
            print(f"🔍 Поиск зависимостей для ОС:")
            print(f"   os_name: {os_name}")
            print(f"   os_family: {os_family}")
            print(f"   reqs_dir: {reqs_dir}")
            
            # Список возможных папок для поиска в порядке приоритета
            possible_folders = []
            
            # 1. Папка с именем ОС (например, linux)
            if os_name and os_name != 'unknown':
                possible_folders.append(os_name)
            
            # 2. Папка с семейством ОС (например, debian)
            if os_family and os_family != 'unknown':
                possible_folders.append(os_family)
            
            # 3. Специальные случаи
            if os_family in ['debian', 'ubuntu']:
                possible_folders.append('linux')
            elif os_family in ['rhel', 'centos', 'fedora']:
                possible_folders.append('linux')
            
            # Убираем дубликаты
            possible_folders = list(dict.fromkeys(possible_folders))
            
            print(f"   Проверяемые папки: {possible_folders}")
            
            # Ищем файл в папках
            for folder in possible_folders:
                folder_path = reqs_dir / folder
                if folder_path.exists():
                    print(f"   ✅ Папка найдена: {folder}")
                    
                    # Проверяем разные имена файлов
                    possible_files = [
                        folder_path / "default.txt",
                        folder_path / "requirements.txt",
                        folder_path / f"{folder}.txt"
                    ]
                    
                    for req_file in possible_files:
                        if req_file.exists():
                            print(f"   📄 Найден файл: {req_file}")
                            return req_file
            
            # Если ничего не нашли в папках, используем общий default.txt
            general_default = reqs_dir / "default.txt"
            if general_default.exists():
                print(f"📄 Используем общий файл: {general_default}")
                return general_default
            
        except Exception as e:
            print(f"❌ Ошибка поиска requirements: {e}")
            import traceback
            traceback.print_exc()
            return None