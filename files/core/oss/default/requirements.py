"""
Модуль управления зависимостями (аналог SystemModule)
Отвечает за виртуальное окружение и установку пакетов
"""

import os
import sys
import platform
import subprocess
import venv
import shutil
import time
import re
from pathlib import Path
from typing import Dict, Optional, Tuple, List

from files.core.base_module import BaseModule
from files.core.utils.globalVars_utils import get_global, set_global
from files.core.utils.log_utils import LogManager

logger = LogManager.get_logger('requirements')


class RequirementsModule(BaseModule):
    """Модуль управления зависимостями"""
    
    _is_installation_process = False
    
    @staticmethod
    def check() -> bool:
        return True
    
    @staticmethod
    def set_globals():
        """Устанавливает глобальные переменные"""
        starter_path = get_global('starter_path')
        venv_dir = starter_path / "venv"
        reqs_dir = starter_path / "files" / "requirements"
        
        set_global('venv_dir', venv_dir)
        set_global('requirements_dir', reqs_dir)
        set_global('requirements_file', None)
        
        logger.info(f"VENV directory: {venv_dir}")
        logger.info(f"Requirements directory: {reqs_dir}")
    
    # ========== ИНФОРМАЦИЯ О VENV ==========
    
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
        venv_dir = RequirementsModule.get_venv_dir()
        
        if platform.system() == "Windows":
            python_exe = venv_dir / "Scripts" / "python.exe"
            python_exe_alt = venv_dir / "Scripts" / "python"
            python_exe_alt2 = venv_dir / "Scripts" / "pythonw.exe"
        else:
            python_exe = venv_dir / "bin" / "python"
            python_exe_alt = venv_dir / "bin" / "python3"
            python_exe_alt2 = None
        
        for python_path in [python_exe, python_exe_alt, python_exe_alt2]:
            if python_path and python_path.exists():
                return python_path
        
        return None
    
    # ========== РАБОТА С REQUIREMENTS ==========
    
    @staticmethod
    def detect_os_info() -> Dict[str, str]:
        """Определяет информацию об ОС для поиска правильного requirements файла"""
        raw_name = get_global('os', 'unknown')
        raw_family = get_global('os_family', 'unknown')
        raw_version = get_global('os_version', 'unknown')
        
        # Приводим к нижнему регистру для поиска папок
        os_name = raw_name.lower() if raw_name != 'unknown' else 'unknown'
        os_family = raw_family.lower() if raw_family != 'unknown' else 'unknown'
        
        return {
            'name': os_name,
            'family': os_family,
            'version': raw_version,
            'system': platform.system().lower(),
            'architecture': platform.machine()
        }
    
    @staticmethod
    def find_requirements() -> Optional[Path]:
        """Ищет файл requirements с учетом ОС и версии"""
        reqs_dir = get_global('requirements_dir')
        os_info = RequirementsModule.detect_os_info()
        
        print("\n" + "═" * 70)
        print("🔍 ПОИСК ФАЙЛА ЗАВИСИМОСТЕЙ")
        print("═" * 70)
        
        print(f"📁 Директория поиска: {reqs_dir}")
        print(f"   Существует: {'✅' if reqs_dir.exists() else '❌ НЕТ!'}")
        
        # ========== ПОДРОБНОЕ ЛОГИРОВАНИЕ ==========
        print(f"\n🔍 [DEBUG] ПАРАМЕТРЫ ПОИСКА:")
        print(f"   reqs_dir = {reqs_dir}")
        print(f"   os_info['name'] = '{os_info['name']}'")
        print(f"   os_info['family'] = '{os_info['family']}'")
        print(f"   os_info['version'] = '{os_info['version']}'")
        print(f"   os_info['system'] = '{os_info['system']}'")
        
        if reqs_dir.exists():
            print(f"\n📁 СОДЕРЖИМОЕ ДИРЕКТОРИИ {reqs_dir}:")
            print("-" * 50)
            for item in sorted(reqs_dir.iterdir()):
                if item.is_dir():
                    print(f"   📁 ПАПКА: {item.name}/")
                    for subitem in sorted(item.iterdir()):
                        if subitem.is_file():
                            size = subitem.stat().st_size
                            print(f"      📄 ФАЙЛ: {subitem.name} ({size} байт)")
                else:
                    size = item.stat().st_size
                    print(f"   📄 ФАЙЛ: {item.name} ({size} байт)")
            print("-" * 50)
        else:
            print(f"\n❌ ДИРЕКТОРИЯ НЕ СУЩЕСТВУЕТ!")
        # ========== КОНЕЦ ЛОГИРОВАНИЯ ==========
        
        if not reqs_dir.exists():
            print(f"\n❌ Директория requirements не найдена!")
            print(f"   Создайте папку: {reqs_dir}")
            return None
        
        print(f"\n🖥️  ИНФОРМАЦИЯ ОБ ОС:")
        print(f"   os_name: '{os_info['name']}'")
        print(f"   os_family: '{os_info['family']}'")
        print(f"   os_version: '{os_info['version']}'")
        print(f"   system: '{os_info['system']}'")
        
        # Список путей для поиска
        search_paths = []
        
        print(f"\n🔎 ПУТИ ДЛЯ ПОИСКА (В ПОРЯДКЕ ПРИОРИТЕТА):")
        print("-" * 50)
        
        # 1. Версия ОС
        if os_info['name'] != 'unknown' and os_info['version'] != 'unknown':
            path = reqs_dir / os_info['name'] / f"{os_info['version']}.txt"
            search_paths.append(('specific_version', path))
            print(f"   1. specific_version: {os_info['name']}/{os_info['version']}.txt")
            print(f"      Полный путь: {path}")
        
        # 2. Имя ОС / default
        if os_info['name'] != 'unknown':
            path = reqs_dir / os_info['name'] / "default.txt"
            search_paths.append(('os_name_default', path))
            print(f"   2. os_name_default: {os_info['name']}/default.txt")
            print(f"      Полный путь: {path}")
        
        # 3. Семейство ОС / default
        if os_info['family'] != 'unknown':
            path = reqs_dir / os_info['family'] / "default.txt"
            search_paths.append(('os_family_default', path))
            print(f"   3. os_family_default: {os_info['family']}/default.txt")
            print(f"      Полный путь: {path}")
        
        # 4. Глобальный default
        path = reqs_dir / "default.txt"
        search_paths.append(('global_default', path))
        print(f"   4. global_default: default.txt")
        print(f"      Полный путь: {path}")
        
        print(f"\n🔎 РЕЗУЛЬТАТЫ ПОИСКА:")
        print("-" * 50)
        
        for source, path in search_paths:
            exists = "✅ НАЙДЕН" if path.exists() else "❌ не найден"
            if path.exists():
                size = path.stat().st_size
                print(f"   {source:25s} -> {path} [{exists}] ({size} байт)")
            else:
                print(f"   {source:25s} -> {path} [{exists}]")
            
            if path.exists():
                print(f"\n   🎯 ВЫБРАН ФАЙЛ: {path.name}")
                print(f"      Источник: {source}")
                print(f"      Полный путь: {path}")
                print(f"      Размер: {path.stat().st_size} байт")
                
                # Показываем содержимое файла
                print(f"\n   📄 СОДЕРЖИМОЕ ФАЙЛА {path.name}:")
                print("   " + "-" * 40)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        for i, line in enumerate(lines[:15], 1):
                            line = line.rstrip()
                            if line:
                                print(f"   {i:2d}. {line[:80]}")
                        if len(lines) > 15:
                            print(f"   ... и еще {len(lines) - 15} строк")
                except Exception as e:
                    print(f"      Ошибка чтения: {e}")
                print("   " + "-" * 40)
                
                # Детальный анализ файла
                RequirementsModule._debug_requirements_file(path)
                
                set_global('requirements_file', path)
                set_global('requirements_source', source)
                return path
        
        print("\n" + "═" * 70)
        print("❌ НЕ НАЙДЕНО НИ ОДНОГО ФАЙЛА requirements!")
        print("═" * 70)
        print("\n💡 РЕШЕНИЕ:")
        print(f"   1. Создайте папку: {reqs_dir}")
        print(f"   2. Создайте файл: {reqs_dir / 'default.txt'}")
        print(f"   3. Или создайте: {reqs_dir / os_info['name'] / 'default.txt'}")
        print("═" * 70 + "\n")
        
        return None
    
    @staticmethod
    def _debug_requirements_file(path: Path):
        """Выводит детальную диагностику requirements файла"""
        print(f"\n📄 ДЕТАЛЬНЫЙ АНАЛИЗ ФАЙЛА: {path.name}")
        print("=" * 60)
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            print(f"📊 СТАТИСТИКА ФАЙЛА:")
            print(f"   Размер: {path.stat().st_size} байт")
            print(f"   Всего строк: {len(lines)}")
            
            # Фильтруем пустые строки и комментарии
            non_empty_lines = []
            comment_lines = []
            
            for line in lines:
                stripped = line.strip()
                if not stripped:
                    continue
                if stripped.startswith('#'):
                    comment_lines.append(stripped)
                else:
                    non_empty_lines.append(stripped)
            
            print(f"   Строк с комментариями: {len(comment_lines)}")
            print(f"   Строк с зависимостями: {len(non_empty_lines)}")
            
            if non_empty_lines:
                print(f"\n📦 СПИСОК ПАКЕТОВ ИЗ ФАЙЛА:")
                for i, line in enumerate(non_empty_lines, 1):
                    match = re.match(r'^([a-zA-Z0-9_\-]+)', line)
                    if match:
                        pkg_name = match.group(1)
                        print(f"   {i:2d}. {pkg_name}")
                        if ';' in line:
                            print(f"       (условная установка: {line.split(';')[1].strip()})")
                    else:
                        print(f"   {i:2d}. {line[:60]}")
            else:
                print(f"\n   ⚠️ ВНИМАНИЕ: Файл не содержит пакетов!")
            
            # Проверяем наличие критических пакетов для трея
            critical_tray = {
                'pystray': 'pystray (иконка в трее)',
                'pillow': 'Pillow (иконка в трее)',
                'plyer': 'plyer (уведомления)'
            }
            
            content_lower = content.lower()
            print(f"\n🎯 ПРОВЕРКА ПАКЕТОВ ДЛЯ ТРЕЯ:")
            for pkg, name in critical_tray.items():
                found = pkg in content_lower
                print(f"   {'✅' if found else '❌'} {name}")
            
        except Exception as e:
            print(f"   ❌ Ошибка чтения файла: {e}")
        
        print("=" * 60)
    
    @staticmethod
    def check_all_requirements(requirements_path: Path) -> Dict[str, List[str]]:
        """
        Проверяет каждую библиотеку из requirements файла.
        Возвращает словарь с установленными и отсутствующими пакетами.
        """
        result = {
            'installed': [],
            'missing': [],
            'total': 0
        }
        
        print("\n" + "═" * 70)
        print("📦 ПРОВЕРКА ЗАВИСИМОСТЕЙ ИЗ ФАЙЛА")
        print("═" * 70)
        print(f"📄 Файл: {requirements_path}")
        print("-" * 50)
        
        try:
            with open(requirements_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # Парсим имя пакета (до >, <, =, [, ;)
                match = re.match(r'^([a-zA-Z0-9_\-]+)', line)
                if not match:
                    continue
                
                package_name = match.group(1)
                result['total'] += 1
                
                # Преобразуем имя пакета в имя модуля
                module_name = package_name.replace('-', '_')
                
                try:
                    __import__(module_name)
                    result['installed'].append(package_name)
                    print(f"   ✅ {package_name} - УСТАНОВЛЕН")
                except ImportError:
                    result['missing'].append(package_name)
                    print(f"   ❌ {package_name} - НЕ УСТАНОВЛЕН")
                except Exception as e:
                    result['missing'].append(package_name)
                    print(f"   ⚠️ {package_name} - ОШИБКА: {e}")
        
        except Exception as e:
            print(f"   ❌ Ошибка чтения файла: {e}")
        
        print("-" * 50)
        print(f"📊 ИТОГО: {len(result['installed'])}/{result['total']} установлено")
        if result['missing']:
            print(f"   ❌ ОТСУТСТВУЮТ: {', '.join(result['missing'])}")
        print("═" * 70 + "\n")
        
        return result
    
    # ========== ПРОВЕРКА МОДУЛЕЙ ==========
    
    @staticmethod
    def check_critical_modules() -> Dict[str, bool]:
        """Проверяет только критические модули (для fallback)"""
        modules = {
            'flask': 'Flask',
            'flask_session': 'Flask-Session',
            'dotenv': 'python-dotenv',
            'OpenSSL': 'pyOpenSSL',
            'psutil': 'psutil',
            'yaml': 'PyYAML',
            'requests': 'requests'
        }
        
        results = {}
        print(f"\n   🔍 ПРОВЕРКА УСТАНОВЛЕННЫХ МОДУЛЕЙ:")
        for module_name, package_name in modules.items():
            try:
                __import__(module_name)
                results[package_name] = True
                print(f"      ✅ {package_name} - установлен")
                logger.debug(f"Модуль {module_name} установлен")
            except ImportError:
                results[package_name] = False
                print(f"      ❌ {package_name} - НЕ УСТАНОВЛЕН")
                logger.debug(f"Модуль {module_name} НЕ установлен")
        
        return results
    
    # ========== СОЗДАНИЕ VENV ==========
    
    @staticmethod
    def create_venv() -> Tuple[bool, str]:
        """Создает виртуальное окружение"""
        try:
            venv_dir = RequirementsModule.get_venv_dir()
            
            print("\n" + "═" * 60)
            print("🔧 СОЗДАНИЕ ВИРТУАЛЬНОГО ОКРУЖЕНИЯ")
            print("═" * 60)
            
            if venv_dir.exists():
                print(f"⚠️  Виртуальное окружение уже существует: {venv_dir}")
                venv_python = RequirementsModule.get_venv_python()
                if venv_python and venv_python.exists():
                    print(f"   ✅ Python в venv найден: {venv_python}")
                    return True, "Venv уже существует"
                else:
                    print(f"   ⚠️  Python в venv не найден, пересоздаем...")
                    shutil.rmtree(venv_dir, ignore_errors=True)
            
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
            
            if not venv_dir.exists():
                return False, "Не удалось создать venv"
            
            print(f"✅ Виртуальное окружение создано за {elapsed:.1f} секунд")
            print(f"📁 Путь: {venv_dir}")
            
            venv_python = RequirementsModule.get_venv_python()
            if venv_python:
                print(f"🐍 Python в venv: {venv_python}")
            
            return True, "Venv создан успешно"
            
        except Exception as e:
            return False, f"Ошибка создания venv: {str(e)}"
    
    # ========== УСТАНОВКА ЗАВИСИМОСТЕЙ ==========
    
    @staticmethod
    def install_requirements(requirements_path: Path, python_path: Path) -> Tuple[bool, str]:
        """Устанавливает зависимости из requirements файла"""
        try:
            RequirementsModule._is_installation_process = True
            
            print(f"\n📥 УСТАНОВКА ЗАВИСИМОСТЕЙ")
            print(f"   Файл: {requirements_path.name}")
            print(f"   Python: {python_path}")
            print("   ⏱️  Это может занять несколько минут...")
            
            start_time = time.time()
            
            # Показываем список пакетов к установке
            with open(requirements_path, 'r', encoding='utf-8') as f:
                packages = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            
            print(f"\n   📦 ПАКЕТОВ К УСТАНОВКЕ: {len(packages)}")
            for i, pkg in enumerate(packages[:15], 1):
                print(f"      {i}. {pkg}")
            if len(packages) > 15:
                print(f"      ... и еще {len(packages) - 15} пакетов")
            
            # Обновляем pip
            print("\n   📦 Обновление pip...")
            subprocess.run(
                [str(python_path), '-m', 'pip', 'install', '--upgrade', 'pip'],
                capture_output=True,
                timeout=60,
                check=False
            )
            
            # Устанавливаем зависимости
            print("   📦 Установка пакетов...")
            print("   ⏳ Пожалуйста, подождите...")
            
            result = subprocess.run(
                [str(python_path), '-m', 'pip', 'install', '-r', str(requirements_path)],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            install_time = time.time() - start_time
            
            if result.returncode == 0:
                print(f"\n   ✅ Установка завершена за {install_time:.1f} секунд")
                # Проверяем результат установки
                RequirementsModule.check_all_requirements(requirements_path)
                return True, "Зависимости установлены"
            else:
                error = result.stderr[:500] if result.stderr else "Неизвестная ошибка"
                print(f"\n   ❌ Ошибка: {error}")
                return False, error
                
        except subprocess.TimeoutExpired:
            return False, "Таймаут установки (более 5 минут)"
        except Exception as e:
            return False, str(e)
        finally:
            RequirementsModule._is_installation_process = False
    
    @staticmethod
    def install_missing_modules(missing_modules: List[str]) -> Tuple[bool, str]:
        """Устанавливает отсутствующие модули (fallback)"""
        if not missing_modules:
            return True, "Нет модулей для установки"
        
        venv_python = RequirementsModule.get_venv_python()
        if not venv_python:
            return False, "Не найден Python в venv"
        
        print(f"\n📦 Установка отсутствующих модулей: {', '.join(missing_modules)}")
        
        packages = []
        for module in missing_modules:
            if module == 'Flask-Session':
                packages.append('Flask-Session')
            elif module == 'python-dotenv':
                packages.append('python-dotenv')
            elif module == 'pyOpenSSL':
                packages.append('pyopenssl')
            else:
                packages.append(module.lower())
        
        try:
            result = subprocess.run(
                [str(venv_python), '-m', 'pip', 'install'] + packages,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                print(f"   ✅ Установлены: {', '.join(packages)}")
                return True, "Модули установлены"
            else:
                return False, result.stderr[:200]
        except Exception as e:
            return False, str(e)
    
    # ========== ОСНОВНЫЕ МЕТОДЫ ==========
    
    @staticmethod
    def ensure_requirements() -> bool:
        """
        Гарантирует наличие всех зависимостей.
        """
        print("\n" + "═" * 70)
        print("🔧 ПРОВЕРКА И НАСТРОЙКА ЗАВИСИМОСТЕЙ")
        print("═" * 70)
        
        # 1. Если уже в venv - проверяем все модули из requirements
        if RequirementsModule.in_venv():
            print("✅ Уже в виртуальном окружении")
            
            # Находим файл requirements
            requirements_path = RequirementsModule.find_requirements()
            
            if requirements_path:
                # Проверяем все зависимости из файла
                check_result = RequirementsModule.check_all_requirements(requirements_path)
                
                if not check_result['missing']:
                    print("✅ Все зависимости из requirements установлены")
                    return True
                
                print(f"\n⚠️ Отсутствуют модули: {', '.join(check_result['missing'])}")
                success, msg = RequirementsModule.install_missing_modules(check_result['missing'])
                if success:
                    print("✅ Недостающие модули установлены")
                    return True
                else:
                    print(f"❌ {msg}")
                    return False
            else:
                # Если нет requirements, проверяем только критические
                print("⚠️ Файл requirements не найден, проверяем только критические модули")
                module_status = RequirementsModule.check_critical_modules()
                missing = [name for name, installed in module_status.items() if not installed]
                
                if not missing:
                    print("✅ Все критические зависимости установлены")
                    return True
                
                print(f"\n⚠️ Отсутствуют критические модули: {', '.join(missing)}")
                success, msg = RequirementsModule.install_missing_modules(missing)
                if success:
                    print("✅ Недостающие модули установлены")
                    return True
                else:
                    print(f"❌ {msg}")
                    return False
        
        # 2. Проверяем существует ли venv
        venv_dir = RequirementsModule.get_venv_dir()
        venv_python = RequirementsModule.get_venv_python()
        
        if venv_dir.exists() and venv_python and venv_python.exists():
            print(f"⚠️  Виртуальное окружение существует, но мы не в нем")
            print(f"   📁 Путь: {venv_dir}")
            print(f"   🐍 Python: {venv_python}")
            RequirementsModule.restart_in_venv()
            return False
        
        # 3. Создаем venv
        print("\n📦 Виртуальное окружение не найдено, создаем...")
        success, message = RequirementsModule.create_venv()
        if not success:
            print(f"❌ {message}")
            return False
        
        # 4. Находим requirements
        requirements_path = RequirementsModule.find_requirements()
        if not requirements_path:
            print("❌ Не найден файл requirements.txt")
            return False
        
        # 5. Устанавливаем зависимости
        print("\n📥 Установка зависимостей...")
        venv_python = RequirementsModule.get_venv_python()
        if not venv_python:
            print("❌ Не найден Python в venv")
            return False
            
        success, message = RequirementsModule.install_requirements(requirements_path, venv_python)
        
        if not success:
            print(f"❌ {message}")
            return False
        
        # 6. Перезапуск в venv
        print("\n🔄 Перезапуск в виртуальном окружении...")
        RequirementsModule.restart_in_venv()
        return True
    
    @staticmethod
    def restart_in_venv():
        """Перезапускает приложение в venv"""
        try:
            venv_python = RequirementsModule.get_venv_python()
            if not venv_python:
                print("\n❌ Не найден Python в venv")
                sys.exit(1)
            
            script_path = get_global('script_path')
            if not script_path:
                print("\n❌ Не найден путь к скрипту")
                sys.exit(1)
                
            cmd_parts = [str(venv_python), str(script_path)]
            
            for arg in sys.argv[1:]:
                if arg != '--new':
                    cmd_parts.append(arg)
            
            print("\n" + "═" * 70)
            print("✅ АВТОМАТИЧЕСКАЯ НАСТРОЙКА ЗАВЕРШЕНА")
            print("═" * 70)
            print("📦 Виртуальное окружение создано и зависимости установлены!")
            print(f"🐍 Python в venv: {venv_python}")
            print("\n🔄 ПЕРЕЗАПУСК В VENV...")
            print("═" * 70 + "\n")
            
            os.execv(str(venv_python), cmd_parts)
            
        except Exception as e:
            print(f"\n❌ Ошибка перезапуска: {e}")
            sys.exit(1)
    
    @staticmethod
    def get_debug_info() -> Dict:
        venv_dir = RequirementsModule.get_venv_dir()
        venv_python = RequirementsModule.get_venv_python()
        
        return {
            'in_venv': RequirementsModule.in_venv(),
            'venv_dir': str(venv_dir),
            'venv_exists': venv_dir.exists(),
            'venv_python': str(venv_python) if venv_python else None,
            'venv_python_exists': venv_python.exists() if venv_python else False,
            'modules_status': RequirementsModule.check_critical_modules(),
            'requirements_file': str(get_global('requirements_file')) if get_global('requirements_file') else None
        }
    
    @staticmethod
    def print_debug_info():
        info = RequirementsModule.get_debug_info()
        
        print("\n" + "═" * 70)
        print("🔍 ОТЛАДОЧНАЯ ИНФОРМАЦИЯ DEPENDENCIES")
        print("═" * 70)
        
        print(f"\n📦 ВИРТУАЛЬНОЕ ОКРУЖЕНИЕ:")
        print(f"   В venv: {'✅ Да' if info['in_venv'] else '❌ Нет'}")
        print(f"   Путь: {info['venv_dir']}")
        print(f"   Существует: {'✅' if info['venv_exists'] else '❌'}")
        print(f"   Python в venv: {info['venv_python']}")
        
        print(f"\n📦 КРИТИЧЕСКИЕ МОДУЛИ:")
        for module, installed in info['modules_status'].items():
            status = "✅" if installed else "❌"
            print(f"   {status} {module}")
        
        print(f"\n📄 ФАЙЛ ЗАВИСИМОСТЕЙ:")
        print(f"   {info['requirements_file'] or 'Не найден'}")
        
        print("═" * 70 + "\n")