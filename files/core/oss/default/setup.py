# files/core/oss/default/setup.py

import hashlib
import os
import secrets
import webbrowser
import subprocess
import shutil
import tempfile
import json
import platform
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Tuple, List

from files.core.base_module import BaseModule
from files.core.software.default.env import EnvModule
from files.core.oss.default.crypto import CryptoModule
from files.core.utils.globalVars_utils import get_global, set_global
from files.core.utils.loader_utils import get
from files.core.utils.log_utils import LogManager

logger = LogManager.get_logger()


class SetupModule(BaseModule):
    """Модуль первоначальной настройки приложения"""
    
    REQUIRED_ENV_VARS = [
        'LANGUAGE',
        'ADMIN_LOGIN', 
        'ADMIN_PASSWORD_HASH',
        'APP_SECRET_KEY',
        'TYPE_SERVER'
    ]
    
    @staticmethod
    def check() -> bool:
        return True
    
    @staticmethod
    def set_globals():
        pass
    
    @staticmethod
    def is_first_run() -> bool:
        """Проверяет, является ли этот запуск первым для ЭТОГО starter"""
        env_path = get_global('starter_env_path')
        if not env_path or not env_path.exists():
            return True
        
        env_class = get('env')
        if env_class:
            current_vars = env_class.read_env_file(env_path)
            return not all(var in current_vars for var in SetupModule.REQUIRED_ENV_VARS)
        
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                content = f.read()
                return not all(var in content for var in SetupModule.REQUIRED_ENV_VARS)
        except Exception:
            return True
    
    @staticmethod
    def is_server_already_setup() -> bool:
        """Проверяет, установлен ли уже сервер (по наличию docker-compose.yml или docker-compose.example)"""
        docker_path = get_global('docker_path')
        if not docker_path or not docker_path.exists():
            return False
        
        # Проверяем наличие ключевых файлов Docker
        compose_file = docker_path / "docker-compose.yml"
        compose_example = docker_path / "docker-compose.example"
        
        if compose_file.exists() or compose_example.exists():
            print(f"\n   ✅ Обнаружен существующий Docker конфиг:")
            if compose_file.exists():
                print(f"      📄 docker-compose.yml найден")
            if compose_example.exists():
                print(f"      📄 docker-compose.example найден")
            return True
        
        return False
    
    @staticmethod
    def generate_credentials() -> Dict[str, str]:
        """Генерирует учетные данные для первого запуска"""
        password = secrets.token_urlsafe(8)
        return {
            'login': 'admin_' + secrets.token_hex(2),
            'password': password,
            'password_hash': hashlib.sha256(password.encode()).hexdigest(),
            'app_secret_key': secrets.token_hex(32)
        }
    
    @staticmethod
    def get_available_languages():
        """Получает доступные языки через I18nModule"""
        languages = get('i18n', 'get_available_languages')
        return languages if languages is not None else {}
    
    @staticmethod
    def get_available_server_types():
        """Получает доступные типы серверов из конфигурации"""
        try:
            from files.configs.server_types import SERVER_TYPES
            return SERVER_TYPES
        except ImportError:
            logger.error("Не удалось загрузить конфигурацию типов серверов")
            return {}
    
    @staticmethod
    def get_available_drives_partitions() -> List[Dict]:
        """Получает список доступных дисков/разделов с их свободным местом"""
        system = platform.system()
        drives = []
        
        if system == 'Windows':
            import string
            import shutil
            
            for drive_letter in string.ascii_uppercase:
                drive_path = f"{drive_letter}:\\"
                if os.path.exists(drive_path):
                    try:
                        usage = shutil.disk_usage(drive_path)
                        free_gb = usage.free / (1024**3)
                        total_gb = usage.total / (1024**3)
                        
                        drives.append({
                            'path': drive_path,
                            'name': f"Диск {drive_letter}:",
                            'free_gb': free_gb,
                            'total_gb': total_gb,
                            'free_percent': (usage.free / usage.total) * 100,
                            'type': 'drive'
                        })
                    except Exception:
                        continue
        
        elif system == 'Linux':
            import subprocess
            import shutil
            
            try:
                result = subprocess.run(
                    ['df', '-B1', '--output=target,avail,size,used,pcent', '-x', 'tmpfs', '-x', 'devtmpfs'],
                    capture_output=True,
                    text=True,
                    check=True
                )
                
                lines = result.stdout.strip().split('\n')[1:]
                for line in lines:
                    if not line.strip():
                        continue
                    
                    parts = line.split()
                    if len(parts) >= 5:
                        mount_point = parts[0]
                        available_bytes = int(parts[1])
                        total_bytes = int(parts[2])
                        used_percent = parts[4].replace('%', '')
                        
                        available_gb = available_bytes / (1024**3)
                        total_gb = total_bytes / (1024**3)
                        
                        # Пропускаем системные разделы
                        if mount_point in ['/boot', '/boot/efi', '/dev', '/proc', '/sys', '/run']:
                            continue
                        
                        drives.append({
                            'path': mount_point,
                            'name': f"Раздел {mount_point}",
                            'free_gb': available_gb,
                            'total_gb': total_gb,
                            'free_percent': float(used_percent),
                            'type': 'partition'
                        })
            except Exception as e:
                print(f"   ⚠️ Ошибка получения разделов: {e}")
        
        elif system == 'Darwin':
            import shutil
            
            for path in ['/Applications', '/Users/Shared', str(Path.home())]:
                try:
                    usage = shutil.disk_usage(path)
                    free_gb = usage.free / (1024**3)
                    total_gb = usage.total / (1024**3)
                    
                    drives.append({
                        'path': path,
                        'name': f"macOS: {path}",
                        'free_gb': free_gb,
                        'total_gb': total_gb,
                        'free_percent': (usage.free / usage.total) * 100,
                        'type': 'folder'
                    })
                except Exception:
                    continue
        
        # Сортируем по свободному месту (по убыванию)
        drives.sort(key=lambda x: x['free_gb'], reverse=True)
        return drives
    
    @staticmethod
    def select_apps_root(interactive: bool = True) -> Path:
        """Интерактивный выбор папки для установки всех серверов"""
        
        # Пытаемся прочитать сохраненный путь
        config_path = Path.home() / '.starter_config'
        saved_path = None
        
        if config_path.exists():
            try:
                config = json.loads(config_path.read_text(encoding='utf-8'))
                saved_path = config.get('apps_root')
                if saved_path and Path(saved_path).exists():
                    print(f"\n   📁 Найден сохраненный путь: {saved_path}")
            except:
                pass
        
        if not interactive:
            # Неинтерактивный режим - используем сохраненный или стандартный
            if saved_path:
                return Path(saved_path)
            else:
                return Path("/apps")
        
        # Получаем доступные диски/разделы
        drives = SetupModule.get_available_drives_partitions()
        
        print("\n" + "=" * 70)
        print("📁 ВЫБОР ПАПКИ ДЛЯ УСТАНОВКИ СЕРВЕРОВ")
        print("=" * 70)
        print("\n💡 Все серверы (reverse-proxy, core, client и др.)")
        print("   будут установлены в выбранную папку в подпапку /apps\n")
        
        # Вариант 1: Предложенный по умолчанию (лучший диск)
        if drives:
            best_drive = drives[0]
            default_path = Path(best_drive['path']) / "apps"
            print(f"\n1. 📌 ПРЕДЛОЖЕННЫЙ (рекомендуемый)")
            print(f"   📁 {default_path}")
            print(f"   💾 {best_drive['name']} - {best_drive['free_gb']:.1f} GB свободно")
        
        # Вариант 2: Сохраненный ранее
        option_offset = 1
        if saved_path and (not drives or saved_path != default_path):
            print(f"\n2. 💾 ИСПОЛЬЗОВАТЬ СОХРАНЕННЫЙ")
            print(f"   📁 {saved_path}")
            option_offset = 2
        
        # Вариант 3: Другие доступные диски/разделы
        if len(drives) > 1:
            print(f"\n{option_offset + 1 if drives else 1}. 💿 ДРУГИЕ ДОСТУПНЫЕ ДИСКИ/РАЗДЕЛЫ:")
            for i, drive in enumerate(drives[1:4], 1):
                drive_path = Path(drive['path']) / "apps"
                print(f"   {i}. {drive['name']}")
                print(f"      📁 {drive_path}")
                print(f"      💾 {drive['free_gb']:.1f} GB свободно (всего {drive['total_gb']:.1f} GB)")
        
        # Вариант 4: Своя папка
        print(f"\n{option_offset + 2 if len(drives) > 1 else option_offset + 1}. 📂 ВВЕСТИ СВОЙ ПУТЬ")
        print(f"   Например: D:\\my_servers\\apps или /opt/myapps")
        
        # Вариант 5: Стандартный путь /apps
        default_apps_path = Path("/apps")
        print(f"\n{option_offset + 3 if len(drives) > 1 else option_offset + 2}. 📁 СТАНДАРТНЫЙ ПУТЬ")
        print(f"   📁 {default_apps_path}")
        
        # Выбор пользователя
        print("\n" + "-" * 70)
        
        while True:
            try:
                choice = input("Выберите вариант (1-5) или введите путь: ").strip()
                
                # Проверяем, не ввел ли пользователь путь напрямую
                if choice.startswith('/') or ':\\' in choice or choice.startswith('./') or choice.startswith('../'):
                    custom_path = Path(choice)
                    if custom_path.suffix:
                        custom_path = custom_path.parent
                    
                    if custom_path.name != 'apps':
                        custom_path = custom_path / 'apps'
                    
                    print(f"\n   ✅ Выбран пользовательский путь: {custom_path}")
                    return custom_path
                
                choice_num = int(choice)
                
                # Обработка варианта 1 (предложенный)
                if choice_num == 1 and drives:
                    selected_path = Path(drives[0]['path']) / "apps"
                    print(f"\n   ✅ Выбран ПРЕДЛОЖЕННЫЙ путь")
                    print(f"   📁 {selected_path}")
                    return selected_path
                
                # Обработка варианта 2 (сохраненный)
                if choice_num == 2 and saved_path:
                    print(f"\n   ✅ Используем сохраненный путь: {saved_path}")
                    return Path(saved_path)
                
                # Обработка варианта с дисками
                if choice_num == (option_offset + 1 if drives else 1) and len(drives) > 1:
                    print("\n   📀 ДОСТУПНЫЕ ДИСКИ/РАЗДЕЛЫ:")
                    for i, drive in enumerate(drives, 1):
                        drive_path = Path(drive['path']) / "apps"
                        print(f"   {i}. {drive['name']}")
                        print(f"      📁 {drive_path}")
                        print(f"      💾 {drive['free_gb']:.1f} GB свободно")
                    
                    disk_choice = input("\n   Выберите номер диска: ").strip()
                    if disk_choice.isdigit():
                        disk_idx = int(disk_choice) - 1
                        if 0 <= disk_idx < len(drives):
                            selected_path = Path(drives[disk_idx]['path']) / "apps"
                            print(f"\n   ✅ Выбран {drives[disk_idx]['name']}")
                            print(f"   📁 {selected_path}")
                            return selected_path
                
                # Обработка варианта "свой путь"
                if choice_num == (option_offset + 2 if len(drives) > 1 else option_offset + 1):
                    custom_path = input("   Введите путь: ").strip()
                    if custom_path:
                        path_obj = Path(custom_path)
                        if path_obj.name != 'apps':
                            path_obj = path_obj / 'apps'
                        print(f"\n   ✅ Выбран пользовательский путь: {path_obj}")
                        return path_obj
                
                # Обработка варианта "рядом со стартером"
                if choice_num == (option_offset + 3 if len(drives) > 1 else option_offset + 2):
                    print(f"\n   ✅ Используем путь рядом со стартером: {local_path}")
                    return local_path
                
                print("   ❌ Неверный выбор. Попробуйте снова.")
                
            except ValueError:
                print("   ❌ Введите число или полный путь")
            except KeyboardInterrupt:
                print("\n\n   ❌ Установка отменена")
                sys.exit(1)
    
    @staticmethod
    def save_apps_root(apps_root: Path):
        """Сохраняет выбранный путь в конфиг"""
        config_path = Path.home() / '.starter_config'
        try:
            config = {}
            if config_path.exists():
                config = json.loads(config_path.read_text(encoding='utf-8'))
            
            config['apps_root'] = str(apps_root)
            config['last_updated'] = datetime.now().isoformat()
            
            config_path.write_text(json.dumps(config, indent=2), encoding='utf-8')
            print(f"   💾 Путь сохранен в {config_path}")
        except Exception as e:
            print(f"   ⚠️ Не удалось сохранить путь: {e}")
    
    @staticmethod
    def get_apps_root(interactive: bool = True) -> Path:
        """Главная функция получения папки apps с возможностью выбора"""
        
        # Если уже установлена глобальная переменная
        cached_root = get_global('apps_root')
        if cached_root:
            return Path(cached_root)
        
        # Интерактивный выбор
        if interactive:
            apps_root = SetupModule.select_apps_root(interactive=True)
            SetupModule.save_apps_root(apps_root)
        else:
            # Неинтерактивный режим - используем стандартный путь
            apps_root = Path("/apps")
        
        # Создаем папку
        apps_root.mkdir(parents=True, exist_ok=True)
        
        # Сохраняем в глобальные переменные
        set_global('apps_root', apps_root)
        
        print(f"\n   ✅ ПАПКА ДЛЯ ВСЕХ СЕРВЕРОВ: {apps_root}")
        print(f"   📁 Все будущие серверы будут установлены сюда\n")
        
        return apps_root
    
    @staticmethod
    def get_installed_servers() -> List[Dict]:
        """Возвращает список уже установленных серверов"""
        apps_root = SetupModule.get_apps_root(interactive=False)
        installed = []
        
        for server_dir in apps_root.iterdir():
            if not server_dir.is_dir():
                continue
            
            starter_env = server_dir / "starter" / ".env"
            if starter_env.exists():
                env_vars = {}
                for line in starter_env.read_text().split('\n'):
                    if '=' in line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()
                
                installed.append({
                    'path': str(server_dir),
                    'type': env_vars.get('TYPE_SERVER', 'unknown'),
                    'name': env_vars.get('SERVER_NAME', server_dir.name),
                    'domain': env_vars.get('DOMAIN', ''),
                    'port': env_vars.get('PORT', ''),
                    'starter_path': str(server_dir / "starter"),
                    'folder_name': env_vars.get('FOLDER_NAME', server_dir.name)
                })
        
        return installed
    
    @staticmethod
    def is_server_already_installed(server_type: str) -> Tuple[bool, Optional[Dict]]:
        """Проверяет, установлен ли уже сервер данного типа"""
        from files.configs.server_types import SERVER_TYPES
        server_info = SERVER_TYPES.get(server_type, {})
        
        if server_info.get('can_have_multiple', True):
            return False, None
        
        installed = SetupModule.get_installed_servers()
        for server in installed:
            if server['type'] == server_type:
                return True, server
        
        return False, None
    
    @staticmethod
    def get_server_folder_name(server_type: str, server_info: Dict) -> str:
        """Генерирует имя папки для сервера"""
        default_folder = server_info.get('default_folder', server_type)
        
        if server_info.get('can_have_multiple', True):
            installed = SetupModule.get_installed_servers()
            count = sum(1 for s in installed if s['type'] == server_type)
            
            if count == 0:
                return default_folder
            else:
                return f"{default_folder}_{count + 1}"
        
        return default_folder
    
    @staticmethod
    def copy_starter_to_server(server_path: Path):
        """Копирует starter в папку сервера"""
        starter_src = get_global('starter_path')
        starter_dst = server_path / "starter"
        
        if not starter_src or not starter_src.exists():
            logger.error(f"Source starter not found: {starter_src}")
            return False
        
        starter_dst.mkdir(parents=True, exist_ok=True)
        
        # Копируем starter.py
        shutil.copy2(starter_src / "starter.py", starter_dst / "starter.py")
        
        # Копируем папку files
        files_src = starter_src / "files"
        files_dst = starter_dst / "files"
        if files_src.exists():
            if files_dst.exists():
                shutil.rmtree(files_dst)
            shutil.copytree(files_src, files_dst)
        
        # Копируем .env.example если есть
        env_example = starter_src / ".env.example"
        if env_example.exists():
            shutil.copy2(env_example, starter_dst / ".env.example")
        
        # Копируем requirements.txt если есть
        req_file = starter_src / "requirements.txt"
        if req_file.exists():
            shutil.copy2(req_file, starter_dst / "requirements.txt")
        
        print(f"   📋 Starter скопирован в {starter_dst}")
        return True
    
    @staticmethod
    def clone_repository(repo_url: str, target_path: Path, branch: str = "main") -> Tuple[bool, str]:
        """Клонирует репозиторий Git"""
        try:
            if target_path.exists():
                shutil.rmtree(target_path)
            
            target_path.mkdir(parents=True, exist_ok=True)
            
            cmd = ['git', 'clone', '--depth', '1', '--branch', branch, repo_url, str(target_path)]
            
            print(f"   📥 Клонирование репозитория: {repo_url}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode != 0:
                return False, f"Ошибка клонирования: {result.stderr}"
            
            return True, "Репозиторий успешно склонирован"
            
        except subprocess.TimeoutExpired:
            return False, "Таймаут при клонировании репозитория"
        except Exception as e:
            return False, f"Ошибка: {str(e)}"
    
    @staticmethod
    def select_server_type(interactive: bool = True) -> Tuple[Optional[str], Optional[Dict]]:
        """Выбор типа сервера с проверкой уже установленных"""
        from files.configs.server_types import get_sorted_server_types, SERVER_TYPES
        
        server_types_list = get_sorted_server_types()
        
        if not server_types_list:
            logger.warning("Не найдены конфигурации типов серверов")
            return 'client', SERVER_TYPES.get('client', {})
        
        if not interactive:
            return 'client', SERVER_TYPES.get('client', {})
        
        installed_servers = SetupModule.get_installed_servers()
        installed_types = [s['type'] for s in installed_servers]
        
        print("\n" + "=" * 60)
        print("📦 ДОСТУПНЫЕ ТИПЫ СЕРВЕРОВ")
        print("=" * 60)
        
        if installed_servers:
            print("\n✅ УЖЕ УСТАНОВЛЕНЫ:")
            for server in installed_servers:
                print(f"   • {server['name']} ({server['type']}) - {server['domain'] or 'порт ' + server['port']}")
            print()
        
        available = []
        for server_type, server_info in server_types_list:
            is_installed = server_type in installed_types
            is_singleton = not server_info.get('can_have_multiple', True)
            
            if is_installed and is_singleton:
                continue
            
            available.append((server_type, server_info))
        
        if not available:
            print("\n❌ НЕТ ДОСТУПНЫХ ДЛЯ УСТАНОВКИ СЕРВЕРОВ")
            print("   Все возможные серверы уже установлены!")
            return None, {}
        
        for i, (server_type, server_info) in enumerate(available, 1):
            proxy_mark = " 🌐 [REVERSE-PROXY]" if server_info.get('is_reverse_proxy') else ""
            print(f"{i}. {server_info['name']}{proxy_mark} - {server_info['description']}")
        
        print("\n" + "-" * 60)
        print("💡 Совет:")
        print("   • Reverse Proxy Server - установите первым, если планируете несколько серверов")
        print("   • Core/Client серверы требуют reverse-proxy для работы через порты 80/443")
        print("-" * 60)
        
        while True:
            try:
                choice = input(f"Выберите тип сервера (1-{len(available)}): ").strip()
                if choice.isdigit():
                    choice_num = int(choice)
                    if 1 <= choice_num <= len(available):
                        server_type, server_info = available[choice_num - 1]
                        print(f"\n✅ Выбран: {server_info['name']}")
                        print(f"   📝 {server_info['description']}")
                        
                        if server_info.get('is_reverse_proxy'):
                            print("\n   🌐 Reverse-proxy сервер будет установлен в отдельную папку")
                            print("   🔗 После установки другие серверы смогут подключаться к нему")
                        
                        return server_type, server_info
                print(f"Пожалуйста, введите число от 1 до {len(available)}")
            except (EOFError, KeyboardInterrupt):
                print("\nПрервано пользователем")
                return None, {}
    
    @staticmethod
    def setup_reverse_proxy_from_repo(repo_info: Dict, server_type: str, server_info: Dict) -> Tuple[bool, Dict]:
        """Устанавливает reverse-proxy сервер из репозитория"""
        try:
            repo_url = repo_info.get('url')
            branch = repo_info.get('branch', 'main')
            
            if not repo_url:
                return False, {'error': 'URL репозитория не указан'}
            
            # ========== ПРОВЕРКА: есть ли уже установленный сервер ==========
            if SetupModule.is_server_already_setup():
                print(f"\n   ✅ Сервер уже настроен! (найдены Docker файлы)")
                print(f"   📁 Путь: {get_global('project_path')}")
                print(f"   ⏭️ Пропускаем клонирование, используем существующую конфигурацию")
                
                # Получаем путь к .env файлу Starter
                starter_env_path = get_global('starter_env_path')
                
                # Читаем существующие переменные если файл есть
                existing_vars = {}
                if starter_env_path and starter_env_path.exists():
                    existing_vars = EnvModule.read_env_file(starter_env_path)
                
                # Генерируем учетные данные если их нет
                credentials = SetupModule.generate_credentials()
                need_save = False
                
                if 'ADMIN_LOGIN' not in existing_vars or not existing_vars['ADMIN_LOGIN']:
                    existing_vars['ADMIN_LOGIN'] = credentials['login']
                    existing_vars['ADMIN_PASSWORD_HASH'] = credentials['password_hash']
                    existing_vars['APP_SECRET_KEY'] = credentials['app_secret_key']
                    need_save = True
                    show_credentials = True
                else:
                    show_credentials = False
                
                # Устанавливаем тип сервера если его нет
                if 'TYPE_SERVER' not in existing_vars or not existing_vars['TYPE_SERVER']:
                    existing_vars['TYPE_SERVER'] = server_type
                    existing_vars['SERVER_NAME'] = server_info.get('name')
                    need_save = True
                
                # Устанавливаем язык по умолчанию если его нет
                if 'LANGUAGE' not in existing_vars or not existing_vars['LANGUAGE']:
                    existing_vars['LANGUAGE'] = 'ru'
                    need_save = True
                
                # Сохраняем .env файл если были изменения
                if need_save and starter_env_path:
                    # Читаем шаблон .env.example для сохранения структуры
                    env_example = get_global('starter_env_example_path')
                    if env_example and env_example.exists():
                        with open(env_example, 'r', encoding='utf-8') as f:
                            template_content = f.read()
                        _, template_lines = EnvModule.parse_env_content(template_content)
                        content = EnvModule.generate_env_content(existing_vars, template_lines)
                    else:
                        content = EnvModule.generate_env_content(existing_vars, [])
                    
                    starter_env_path.write_text(content, encoding='utf-8')
                    print(f"   ✅ .env файл создан/обновлен: {starter_env_path}")
                
                # Показываем учетные данные если они были созданы
                if show_credentials:
                    print("\n" + "="*60)
                    print("🔐 СОХРАНИТЕ УЧЕТНЫЕ ДАННЫЕ!")
                    print("="*60)
                    print(f"👤 Логин: {credentials['login']}")
                    print(f"🔑 Пароль: {credentials['password']}")
                    print("="*60 + "\n")
                
                info = {
                    'path': str(get_global('project_path')),
                    'docker_path': str(get_global('docker_path')),
                    'starter_path': str(get_global('starter_path')),
                    'existing': True
                }
                return True, info
            # ========== КОНЕЦ ПРОВЕРКИ ==========
            
            # Получаем корневую папку для всех серверов
            apps_root = SetupModule.get_apps_root(interactive=True)
            
            # Проверяем, не установлен ли уже reverse-proxy
            is_installed, installed_info = SetupModule.is_server_already_installed(server_type)
            if is_installed:
                print(f"\n   ⚠️ Reverse-proxy сервер уже установлен!")
                print(f"   📁 Путь: {installed_info['path']}")
                print(f"   🚀 Starter: {installed_info['starter_path']}")
                
                overwrite = input("\n   Хотите переустановить? (y/N): ").strip().lower()
                if overwrite != 'y':
                    return False, {'error': 'Установка отменена пользователем'}
            
            # Получаем имя папки
            folder_name = SetupModule.get_server_folder_name(server_type, server_info)
            
            # Создаем структуру папок в apps_root
            server_path = apps_root / folder_name
            docker_path = server_path / "docker"
            
            if server_path.exists():
                shutil.rmtree(server_path)
            
            server_path.mkdir(parents=True, exist_ok=True)
            docker_path.mkdir(parents=True, exist_ok=True)
            (server_path / "code").mkdir(exist_ok=True)
            (server_path / "storage").mkdir(exist_ok=True)
            
            # Копируем starter
            SetupModule.copy_starter_to_server(server_path)
            
            # Клонируем репозиторий
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp_path = Path(tmpdir) / "repo"
                success, message = SetupModule.clone_repository(repo_url, tmp_path, branch)
                
                if not success:
                    return False, {'error': message}
                
                # Копируем docker-compose.yml
                repo_compose = tmp_path / "docker" / "docker-compose.yml"
                if repo_compose.exists():
                    shutil.copy2(repo_compose, docker_path / "docker-compose.yml")
                    print(f"   ✅ docker-compose.yml скопирован")
                else:
                    # Пробуем скопировать docker-compose.example
                    repo_compose_example = tmp_path / "docker" / "docker-compose.example"
                    if repo_compose_example.exists():
                        shutil.copy2(repo_compose_example, docker_path / "docker-compose.example")
                        print(f"   ✅ docker-compose.example скопирован")
                    else:
                        return False, {'error': 'docker-compose.yml или docker-compose.example не найден в репозитории'}
                
                # Копируем .env.example
                repo_env_example = tmp_path / "docker" / ".env.example"
                if repo_env_example.exists():
                    shutil.copy2(repo_env_example, docker_path / ".env.example")
                    print(f"   ✅ .env.example скопирован")
            
            # Создаем директории
            (docker_path / "certs").mkdir(exist_ok=True)
            (docker_path / "vhost.d").mkdir(exist_ok=True)
            (docker_path / "html").mkdir(exist_ok=True)
            (docker_path / "acme.sh").mkdir(exist_ok=True)
            
            # Запрашиваем настройки
            print("\n   🌐 Настройка reverse-proxy:")
            domain = input("      🔤 Введите домен для reverse-proxy: ").strip()
            email = input("      📧 Введите email для Let's Encrypt: ").strip()
            
            if not domain:
                domain = "localhost"
            if not email:
                email = "admin@localhost"
            
            # Создаем .env для docker
            env_file = docker_path / ".env"
            env_file.write_text(f"""LETSENCRYPT_EMAIL={email}
DOMAIN={domain}
PROXY_NETWORK=global_reverse_proxy_network
""")
            
            # Создаем .env для starter
            starter_env = server_path / "starter" / ".env"
            starter_env.write_text(f"""# Server Configuration
TYPE_SERVER={server_type}
SERVER_NAME={server_info.get('name')}
SERVER_PATH={server_path}
DOCKER_PATH={docker_path}
DOMAIN={domain}
PORT=443
FOLDER_NAME={folder_name}
APPS_ROOT={apps_root}
""")
            
            info = {
                'path': str(server_path),
                'docker_path': str(docker_path),
                'starter_path': str(server_path / "starter"),
                'domain': domain,
                'email': email,
                'folder_name': folder_name,
                'apps_root': str(apps_root)
            }
            
            print(f"\n   ✅ Reverse-proxy успешно установлен!")
            print(f"   📁 Папка: {server_path}")
            print(f"   📂 Все серверы хранятся в: {apps_root}")
            print(f"   🌐 Домен: {domain}")
            print(f"   🚀 Для запуска: cd {server_path}/starter && python starter.py")
            
            return True, info
            
        except Exception as e:
            logger.error(f"Error setting up reverse proxy: {e}")
            return False, {'error': str(e)}
    
    @staticmethod
    def setup_regular_server(server_type: str, server_info: Dict) -> Tuple[bool, Dict]:
        """Устанавливает обычный сервер"""
        try:
            # ========== ПРОВЕРКА: есть ли уже установленный сервер ==========
            if SetupModule.is_server_already_setup():
                print(f"\n   ✅ Сервер уже настроен! (найдены Docker файлы)")
                print(f"   📁 Путь: {get_global('project_path')}")
                print(f"   ⏭️ Пропускаем клонирование, используем существующую конфигурацию")
                
                # Получаем путь к .env файлу Starter
                starter_env_path = get_global('starter_env_path')
                
                # Читаем существующие переменные если файл есть
                existing_vars = {}
                if starter_env_path and starter_env_path.exists():
                    existing_vars = EnvModule.read_env_file(starter_env_path)
                
                # Генерируем учетные данные если их нет
                credentials = SetupModule.generate_credentials()
                need_save = False
                
                if 'ADMIN_LOGIN' not in existing_vars or not existing_vars['ADMIN_LOGIN']:
                    existing_vars['ADMIN_LOGIN'] = credentials['login']
                    existing_vars['ADMIN_PASSWORD_HASH'] = credentials['password_hash']
                    existing_vars['APP_SECRET_KEY'] = credentials['app_secret_key']
                    need_save = True
                    show_credentials = True
                else:
                    show_credentials = False
                
                # Устанавливаем тип сервера если его нет
                if 'TYPE_SERVER' not in existing_vars or not existing_vars['TYPE_SERVER']:
                    existing_vars['TYPE_SERVER'] = server_type
                    existing_vars['SERVER_NAME'] = server_info.get('name')
                    need_save = True
                
                # Устанавливаем язык по умолчанию если его нет
                if 'LANGUAGE' not in existing_vars or not existing_vars['LANGUAGE']:
                    existing_vars['LANGUAGE'] = 'ru'
                    need_save = True
                
                # Сохраняем .env файл если были изменения
                if need_save and starter_env_path:
                    # Читаем шаблон .env.example для сохранения структуры
                    env_example = get_global('starter_env_example_path')
                    if env_example and env_example.exists():
                        with open(env_example, 'r', encoding='utf-8') as f:
                            template_content = f.read()
                        _, template_lines = EnvModule.parse_env_content(template_content)
                        content = EnvModule.generate_env_content(existing_vars, template_lines)
                    else:
                        content = EnvModule.generate_env_content(existing_vars, [])
                    
                    starter_env_path.write_text(content, encoding='utf-8')
                    print(f"   ✅ .env файл создан/обновлен: {starter_env_path}")
                
                # Показываем учетные данные если они были созданы
                if show_credentials:
                    print("\n" + "="*60)
                    print("🔐 СОХРАНИТЕ УЧЕТНЫЕ ДАННЫЕ!")
                    print("="*60)
                    print(f"👤 Логин: {credentials['login']}")
                    print(f"🔑 Пароль: {credentials['password']}")
                    print("="*60 + "\n")
                
                info = {
                    'path': str(get_global('project_path')),
                    'docker_path': str(get_global('docker_path')),
                    'starter_path': str(get_global('starter_path')),
                    'code_path': str(get_global('code_path')),
                    'storage_path': str(get_global('storage_path')),
                    'existing': True
                }
                return True, info
            # ========== КОНЕЦ ПРОВЕРКИ ==========
            
            # Получаем корневую папку для всех серверов
            apps_root = SetupModule.get_apps_root(interactive=True)
            
            # Проверяем, не установлен ли уже singleton сервер
            is_installed, installed_info = SetupModule.is_server_already_installed(server_type)
            if is_installed:
                print(f"\n   ⚠️ Сервер {server_info.get('name')} уже установлен!")
                print(f"   📁 Путь: {installed_info['path']}")
                
                if server_info.get('can_have_multiple', True):
                    print("   💡 Этот тип сервера может иметь несколько экземпляров")
                    print("   Будет создан новый экземпляр с номером")
                else:
                    overwrite = input("\n   Хотите переустановить? (y/N): ").strip().lower()
                    if overwrite != 'y':
                        return False, {'error': 'Установка отменена пользователем'}
            
            # Получаем имя папки
            folder_name = SetupModule.get_server_folder_name(server_type, server_info)
            
            # Создаем структуру папок в apps_root
            server_path = apps_root / folder_name
            docker_path = server_path / "docker"
            
            if server_path.exists() and not server_info.get('can_have_multiple', True):
                shutil.rmtree(server_path)
            
            server_path.mkdir(parents=True, exist_ok=True)
            docker_path.mkdir(parents=True, exist_ok=True)
            (server_path / "code").mkdir(exist_ok=True)
            (server_path / "storage").mkdir(exist_ok=True)
            
            # Копируем starter
            SetupModule.copy_starter_to_server(server_path)
            
            # Если есть репозиторий - клонируем код
            repo_info = server_info.get('repository')
            if repo_info and repo_info.get('url'):
                repo_url = repo_info.get('url')
                branch = repo_info.get('branch', 'main')
                code_path = server_path / "code"
                
                with tempfile.TemporaryDirectory() as tmpdir:
                    tmp_path = Path(tmpdir) / "repo"
                    success, message = SetupModule.clone_repository(repo_url, tmp_path, branch)
                    
                    if success:
                        for item in tmp_path.iterdir():
                            if item.name not in ['docker', '.git']:
                                dst = code_path / item.name
                                if item.is_dir():
                                    shutil.copytree(item, dst, dirs_exist_ok=True)
                                else:
                                    shutil.copy2(item, dst)
                        print(f"   📂 Код скопирован в {code_path}")
                        
                        repo_docker = tmp_path / "docker"
                        if repo_docker.exists():
                            for item in repo_docker.iterdir():
                                dst = docker_path / item.name
                                if item.is_dir():
                                    shutil.copytree(item, dst, dirs_exist_ok=True)
                                else:
                                    shutil.copy2(item, dst)
                            print(f"   🐳 Docker конфигурация скопирована")
            
            # Создаем .env для docker
            env_file = docker_path / ".env"
            if not env_file.exists():
                env_example = docker_path / ".env.example"
                if env_example.exists():
                    shutil.copy2(env_example, env_file)
                    print(f"   ✅ .env создан из .env.example")
            
            # Создаем .env для starter
            starter_env = server_path / "starter" / ".env"
            starter_env.write_text(f"""# Server Configuration
TYPE_SERVER={server_type}
SERVER_NAME={server_info.get('name')}
SERVER_PATH={server_path}
DOCKER_PATH={docker_path}
PORT={server_info.get('default_port', 8000)}
FOLDER_NAME={folder_name}
APPS_ROOT={apps_root}
""")
            
            info = {
                'path': str(server_path),
                'docker_path': str(docker_path),
                'starter_path': str(server_path / "starter"),
                'code_path': str(server_path / "code"),
                'storage_path': str(server_path / "storage"),
                'folder_name': folder_name,
                'apps_root': str(apps_root)
            }
            
            print(f"\n   ✅ Сервер {server_info.get('name')} успешно установлен!")
            print(f"   📁 Папка: {server_path}")
            print(f"   📂 Все серверы хранятся в: {apps_root}")
            print(f"   🚀 Для запуска: cd {server_path}/starter && python starter.py")
            
            return True, info
            
        except Exception as e:
            logger.error(f"Error setting up regular server: {e}")
            return False, {'error': str(e)}
    
    @staticmethod
    def first_run_setup(interactive: bool = True) -> Tuple[bool, Optional[Dict[str, str]]]:
        """Выполняет первоначальную настройку для ЭТОГО сервера"""
        
        # ========== ПРОВЕРКА: есть ли уже установленный сервер ==========
        if SetupModule.is_server_already_setup():
            print(f"\n{'='*50}")
            print("🔍 ОБНАРУЖЕНА СУЩЕСТВУЮЩАЯ КОНФИГУРАЦИЯ")
            print(f"{'='*50}")
            print(f"✅ Docker файлы уже существуют в: {get_global('docker_path')}")
            print(f"⏭️ Пропускаем первоначальную настройку")
            print(f"{'='*50}\n")
            
            # Получаем путь к .env файлу Starter
            starter_env_path = get_global('starter_env_path')
            
            # Читаем существующие переменные если файл есть
            existing_vars = {}
            if starter_env_path and starter_env_path.exists():
                existing_vars = EnvModule.read_env_file(starter_env_path)
            
            # Генерируем учетные данные если их нет
            credentials = SetupModule.generate_credentials()
            need_save = False
            
            if 'ADMIN_LOGIN' not in existing_vars or not existing_vars['ADMIN_LOGIN']:
                existing_vars['ADMIN_LOGIN'] = credentials['login']
                existing_vars['ADMIN_PASSWORD_HASH'] = credentials['password_hash']
                existing_vars['APP_SECRET_KEY'] = credentials['app_secret_key']
                need_save = True
                show_credentials = True
            else:
                show_credentials = False
            
            # Устанавливаем тип сервера если его нет
            if 'TYPE_SERVER' not in existing_vars or not existing_vars['TYPE_SERVER']:
                existing_vars['TYPE_SERVER'] = 'reverse_proxy'
                existing_vars['SERVER_NAME'] = 'Reverse Proxy Server'
                need_save = True
            
            # Устанавливаем язык по умолчанию если его нет
            if 'LANGUAGE' not in existing_vars or not existing_vars['LANGUAGE']:
                existing_vars['LANGUAGE'] = 'ru'
                need_save = True
            
            # Сохраняем .env файл если были изменения
            if need_save and starter_env_path:
                # Читаем шаблон .env.example для сохранения структуры
                env_example = get_global('starter_env_example_path')
                if env_example and env_example.exists():
                    with open(env_example, 'r', encoding='utf-8') as f:
                        template_content = f.read()
                    _, template_lines = EnvModule.parse_env_content(template_content)
                    content = EnvModule.generate_env_content(existing_vars, template_lines)
                else:
                    content = EnvModule.generate_env_content(existing_vars, [])
                
                starter_env_path.write_text(content, encoding='utf-8')
                print(f"   ✅ .env файл создан/обновлен: {starter_env_path}")
            
            # Показываем учетные данные если они были созданы
            if show_credentials:
                print("\n" + "="*60)
                print("🔐 СОХРАНИТЕ УЧЕТНЫЕ ДАННЫЕ!")
                print("="*60)
                print(f"👤 Логин: {credentials['login']}")
                print(f"🔑 Пароль: {credentials['password']}")
                print("="*60 + "\n")
            else:
                print("\n" + "="*60)
                print("🔐 СУЩЕСТВУЮЩИЕ УЧЕТНЫЕ ДАННЫЕ")
                print("="*60)
                print(f"👤 Логин: {existing_vars.get('ADMIN_LOGIN', 'unknown')}")
                print("🔑 Пароль: (установлен ранее, сохранен в .env)")
                print("="*60 + "\n")
            
            # Определяем тип сервера
            server_type = existing_vars.get('TYPE_SERVER', 'reverse_proxy')
            
            return True, {
                'server_type': server_type,
                'server_path': str(get_global('project_path')),
                'starter_path': str(get_global('starter_path')),
                'docker_path': str(get_global('docker_path')),
                'login': existing_vars.get('ADMIN_LOGIN', credentials.get('login')),
                'password': credentials.get('password') if show_credentials else None,
                'existing': True
            }
        # ========== КОНЕЦ ПРОВЕРКИ ==========
        
        if not SetupModule.is_first_run():
            return False, None

        print(f"\n{'='*50}")
        print("ВЫПОЛНЕНИЕ ПЕРВОНАЧАЛЬНОЙ НАСТРОЙКИ")
        print(f"Текущий starter: {get_global('starter_path')}")
        print(f"{'='*50}\n")

        # Используем дефолтные настройки без выбора серверов
        server_type = 'custom'
        server_info = {
            'name': 'Custom Server',
            'type': 'custom',
            'is_reverse_proxy': False
        }
        
        # Получаем папку apps
        apps_root = SetupModule.get_apps_root(interactive=False)
        
        # Создаем .env файл
        credentials = SetupModule.generate_credentials()
        starter_env_path = get_global('starter_env_path')
        
        if starter_env_path:
            env_content = f"""# Starter Configuration
LANGUAGE=ru
ADMIN_LOGIN={credentials['login']}
ADMIN_PASSWORD_HASH={credentials['password_hash']}
APP_SECRET_KEY={credentials['app_secret_key']}
TYPE_SERVER=custom
SERVER_NAME=Custom Server
PORT=2000
APPS_ROOT={apps_root}
"""
            starter_env_path.write_text(env_content, encoding='utf-8')
        
        print("\n" + "="*60)
        print("✅ УСТАНОВКА ЗАВЕРШЕНА")
        print("="*60)
        print(f"📂 Папка серверов: {apps_root}")
        print(f"🚀 Starter готов к работе")
        
        # Показываем адреса для доступа
        port = get_global('port', 2000)
        print("\n🌐 АДРЕСА ДЛЯ ДОСТУПА:")
        print("-" * 40)
        print(f"   https://localhost:{port}")
        print(f"   https://127.0.0.1:{port}")
        print("="*60 + "\n")
        
        return True, {
            'server_type': server_type,
            'server_name': server_info.get('name'),
            'server_path': str(apps_root),
            'starter_path': str(get_global('starter_path')),
            'docker_path': str(apps_root),
            'folder_name': 'apps',
            'apps_root': str(apps_root),
            'login': credentials['login'],
            'password': credentials['password']
        }
    
    @staticmethod
    def get_server_url() -> list:
        """Возвращает список всех URL сервера"""
        port = get_global('port', 2000)
        
        ips = get('network', 'get_all_local_ips')
        if ips is None:
            ips = []
        
        domain = get('env', 'get_env_var', 'DOMAIN', '')
        use_reverse_proxy = get('env', 'get_env_var', 'USE_REVERSE_PROXY', 'false') == 'true'
        
        urls = []
        
        if use_reverse_proxy and domain:
            urls.append(f"https://{domain}")
        
        if use_reverse_proxy:
            if ips:
                urls.extend([f"https://{ip}" for ip in ips])
            urls.append(f"https://localhost")
        else:
            if domain:
                urls.append(f"https://{domain}:{port}")
            if ips:
                urls.extend([f"https://{ip}:{port}" for ip in ips])
            urls.append(f"https://127.0.0.1:{port}")
        
        return urls
    
    @staticmethod
    def open_browser() -> None:
        """Открывает браузер при первом запуске"""
        is_docker = get_global('running_in_docker')
        use_reverse_proxy = get('env', 'get_env_var', 'USE_REVERSE_PROXY', 'false') == 'true'
        
        urls = SetupModule.get_server_url()
        
        primary_url = None
        
        port = get_global('port', 2000)
        primary_url = f"https://localhost:{port}"
        
        if not get_global('WERKZEUG', False) and primary_url:
            try:
                print(f"\n🌐 Открываем браузер: {primary_url}")
                webbrowser.open(primary_url)
            except Exception as e:
                logger.error(f"Не удалось открыть браузер: {e}")