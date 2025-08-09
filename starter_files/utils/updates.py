import os
import shutil
import zipfile
import requests
import hashlib
import json
import sys
import subprocess

from pathlib import Path
from datetime import datetime,timedelta

from starter_files.config import PROJECTS

from datetime import datetime

from starter_files.untils.logger import logger

# TEST

def start_updates_projects():

    # Определяем общее время запуска
    LAUNCH_TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M%S')
    version_log = Path('last_files_projects.txt')


    # Переменная для хранения изменений
    PROJECTS_UPDATES = {}

    # Переменная для хранения сгенерированных путей
    PROJECTS_UPDATES_FOLDERS = {}

    # РАСПАКОВЫВАЕМ ФАЙЛЫ
    for project_name, project_config in PROJECTS.items():

        print(f"\n[Проект {project_name}] Начало обработки")

        PROJECTS_UPDATES[project_name] = {}

        # Генерация уникальных путей для каждого проекта
        if project_name not in PROJECTS_UPDATES_FOLDERS:

            # Сохраняем пути для дальнейшего использования
            PROJECTS_UPDATES_FOLDERS[project_name] = {
                'EXTRACTED_DIR': getPathDir(LAUNCH_TIMESTAMP, project_name, 'extracted'),
                'BACKUPS_DIR': getPathDir(LAUNCH_TIMESTAMP, project_name, 'backups'),
                'BASE_PATH': Path(project_config['BASE_PATH'])
            }

            print(f"\n[Скачивание] Проект: {project_name}")
            print(f"URL: {project_config['DOWNLOAD_URL']}")
            print(f"Целевая директория: {PROJECTS_UPDATES_FOLDERS[project_name]['EXTRACTED_DIR']}")

            # Скачивание и распаковка
            try:
                # Получаем хеши новых файлов
                PROJECTS_UPDATES[project_name]['EXTRACTED_HASHES'] = download_and_extract(url=project_config['DOWNLOAD_URL'],extract_dir=PROJECTS_UPDATES_FOLDERS[project_name]['EXTRACTED_DIR'])
                print(f"Файлы распакованы в: {PROJECTS_UPDATES_FOLDERS[project_name]['EXTRACTED_DIR']}")

                # Проверка новой установки (только если есть CRITICAL_FILES)
                if 'CRITICAL_FILES' in project_config:
                    if is_new_installation(project_config):
                        print(f"[Новая установка] Копирование всех файлов...")
                        shutil.copytree(
                            PROJECTS_UPDATES_FOLDERS[project_name]['EXTRACTED_DIR'],
                            Path(project_config['BASE_PATH']),
                            dirs_exist_ok=True
                        )
                        continue  # Пропускаем обновление

                # Получаем хеши текущих файлов
                PROJECTS_UPDATES[project_name]['CURRENT_HASHES'] = get_current_hashes(project_config)

                # Поиск изменений
                PROJECTS_UPDATES[project_name]['CHANGES']= find_changes(PROJECTS_UPDATES[project_name]['CURRENT_HASHES'], PROJECTS_UPDATES[project_name]['EXTRACTED_HASHES'], project_config)

                if PROJECTS_UPDATES[project_name]['CHANGES']['updated'] or PROJECTS_UPDATES[project_name]['CHANGES']['new'] or PROJECTS_UPDATES[project_name]['CHANGES']['removed']:
                    print("\nОбнаружены изменения:")

                    print(f"Новые файлы: {len(PROJECTS_UPDATES[project_name]['CHANGES']['new'])}")
                    for f in PROJECTS_UPDATES[project_name]['CHANGES']['new']:
                        print(f"  + {f}")

                    print(f"Измененные файлы: {len(PROJECTS_UPDATES[project_name]['CHANGES']['updated'])}")
                    for f in PROJECTS_UPDATES[project_name]['CHANGES']['updated']:
                        print(f"  ~ {f}")

                    print(f"Удаленные файлы: {len(PROJECTS_UPDATES[project_name]['CHANGES']['removed'])}")
                    for f in PROJECTS_UPDATES[project_name]['CHANGES']['removed']:
                        print(f"  - {f}")

                    # Создаем резервные копии передаем изменения, конфигурация проекта
                    create_backups(project_name,project_config,PROJECTS_UPDATES_FOLDERS[project_name]['BACKUPS_DIR'],PROJECTS_UPDATES[project_name])

                    # Применяем обновления
                    apply_updates(PROJECTS_UPDATES[project_name]['CHANGES'], PROJECTS_UPDATES_FOLDERS[project_name]['EXTRACTED_DIR'], project_config)
                    
                    # Проверка функций для обновленных файлов
                    if project_config.get('FUNCTIONS_IF_UPDATE'):
                        special_files = project_config['FUNCTIONS_IF_UPDATE']
                        updated_files = PROJECTS_UPDATES[project_name]['CHANGES']['updated']
                        
                        for rel_path in updated_files:
                            if rel_path in special_files:
                                function_name = special_files[rel_path]
                                try:
                                    # Импорт и вызов функции
                                    module = __import__('starter_files.variables_functions', fromlist=[function_name])
                                    func = getattr(module, function_name)
                                    
                                    # Выполняем функцию с путями
                                    func(projects_updates=PROJECTS_UPDATES[project_name],projects_folders=PROJECTS_UPDATES_FOLDERS[project_name])
                                    
                                    print(f"[Логи] Выполнена функция {function_name} для файла {rel_path}")
                                        
                                except Exception as e:
                                    print(f"[Ошибка] Функция {function_name} для {rel_path}: {str(e)}")

                        # Перезапуск для проектов без CRITICAL_FILES или обычных обновлений
                        if project_config.get('RESTART_AFTER_UPDATE', False):
                            restart_application()
                
                else:
                    print("\nИзменений не обнаружено")
            except Exception as e:
                print(f"\nОшибка при обновлении: {str(e)}")
                continue

    return LAUNCH_TIMESTAMP, PROJECTS_UPDATES, PROJECTS_UPDATES_FOLDERS

def download_and_extract(url, extract_dir):
    """Скачивание и распаковка архива с возвратом хешей файлов."""
    from starter_files.config import LOGS_EXTRACT
    file_hashes = {}

    try:
        # Создание целевой директории
        os.makedirs(extract_dir, exist_ok=True)
        print(f"Создана директория: {extract_dir}")

        # Скачивание архива во временный файл в extract_dir
        archive_filename = f"temp.zip"
        archive_path = os.path.join(extract_dir, archive_filename)
        print(f"Скачивание архива в: {archive_path}")
        
        # Загрузка архива
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(archive_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        print(f"Успешно скачан архив ({os.path.getsize(archive_path)} bytes)")

        # Распаковка архива
        if LOGS_EXTRACT:
            print(f"[Распаковка] Содержимое архива:")

        with zipfile.ZipFile(archive_path, 'r') as zip_ref:
            if LOGS_EXTRACT:
                # Логирование структуры архива
                for file in zip_ref.namelist():
                    print(f"  - {file}")
            zip_ref.extractall(extract_dir)
        print("Архив успешно распакован")

        # Удаление временного архива
        os.remove(archive_path)
        print(f"Временный архив удален: {archive_path}")

        # Сбор хешей распакованных файлов
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                file_path = os.path.join(root, file)
                # Получение относительного пути
                relative_path = os.path.relpath(file_path, extract_dir)
                # Вычисление хеша SHA-256
                with open(file_path, 'rb') as f:
                    file_data = f.read()
                    file_hash = hashlib.sha256(file_data).hexdigest()
                file_hashes[relative_path] = file_hash
                if LOGS_EXTRACT:
                    print(f"Файл: {relative_path}, хеш: {file_hash}")

        return file_hashes

    except Exception as e:
        print(f"[Ошибка] {str(e)}")
        # Удаление временного архива при ошибке
        if 'archive_path' in locals() and os.path.exists(archive_path):
            os.remove(archive_path)
        raise

def getPathDir(launch_timestamp, project_name, type_dir):
    """
    Генерирует путь к директории для конкретного типа каталога.
    
    :param launch_timestamp: Метка времени запуска
    :param project_name: Имя проекта
    :param type_dir: Тип директории ('TEMP' или 'EXTRACTION')
    :return: Полный путь к файлу/дириктории
    """
    return Path(type_dir) / project_name / launch_timestamp

def load_version_data(version_log, project_name):
    """Загружает данные о предыдущих версиях"""
    if not version_log.exists():
        return {}
    
    with open(version_log, 'r') as f:
        data = json.load(f)
        return data.get(project_name, {})

def get_current_hashes(project_config):
    """Получает хеши текущих файлов проекта"""
    base_path = Path(project_config['BASE_PATH'])
    targets = project_config['TARGETS']
    ignored = project_config.get('IGNORED', [])
    
    current_hashes = {}
    
    for pattern in targets:
        for path in base_path.glob(pattern):
            if not path.is_file():
                continue
                
            rel_path = path.relative_to(base_path)
            
            if is_ignored(str(rel_path), ignored, base_path):
                continue
                
            with open(path, 'rb') as f:
                current_hashes[str(rel_path)] = hashlib.sha256(f.read()).hexdigest()
    
    return current_hashes

def find_changes(old_hashes, new_hashes, config):
    """Определяет изменения между версиями"""
    from starter_files.config import LOGS_CHANGES

    ignored = config.get('IGNORED', [])
    targets = config['TARGETS']
    base_path = Path(config['BASE_PATH'])
    
    changes = {'new': [],'updated': [],'removed': [] }
    log_data = []

    if LOGS_CHANGES:
            log_data.append("\n[Детали изменений]")
            log_data.append("Сравнение хешей файлов:")
    # Проверка новых и измененных файлов
    for rel_path, new_hash in new_hashes.items():

        if not is_target(rel_path, targets, base_path):
            if LOGS_CHANGES:
                log_data.append(f"{rel_path} - Пропущен (не входит в TARGETS)") 
            continue

        if is_ignored(rel_path, ignored, base_path):
            if LOGS_CHANGES:
                log_data.append(f"{rel_path} - Пропущен (соответствует IGNORED паттерну)")
            continue
            
        old_hash = old_hashes.get(rel_path)

        if LOGS_CHANGES:
            if not old_hash:
                log_data.append(f"{rel_path} - Новый файл (хеш: {new_hash})")
            elif old_hash != new_hash:
                log_data.append(
                    f"{rel_path} - Изменен\n"
                    f"  Старый хеш: {old_hash}\n"
                    f"  Новый хеш: {new_hash}"
                )

        if not old_hash:
            changes['new'].append(rel_path)
        elif old_hash != new_hash:
            changes['updated'].append(rel_path)
    
    # Проверка удаленных файлов
    for rel_path in old_hashes:

        # Фильтрация целей
        if not is_target(rel_path, targets, base_path):
            if LOGS_CHANGES:
                log_data.append(f"{rel_path} - Удаление пропущено (не входит в TARGETS)")
            continue

        # Проверка игнорирования
        if is_ignored(rel_path, ignored, base_path):
            if LOGS_CHANGES:
                log_data.append(f"{rel_path} - Удаление пропущено (соответствует IGNORED)")
            continue

        if rel_path not in new_hashes:
            reason = "Удален в новой версии"
            if LOGS_CHANGES:
                old_hash = old_hashes[rel_path]
                log_data.append(
                    f"{rel_path} - {reason}\n"
                    f"  Последний известный хеш: {old_hash}"
                )
            changes['removed'].append({'path': rel_path, 'reason': reason})

    # Вывод собранных логов
    if LOGS_CHANGES and log_data:
        print("\n".join(log_data))
    
    return changes

def is_target(rel_path, target_patterns, base_path):
    """Проверяет, соответствует ли файл целевому шаблону."""
    # Нормализуем путь к POSIX-стилю (с /)
    normalized_path = Path(rel_path).as_posix()
    
    for pattern in target_patterns:
        # Преобразуем шаблон в POSIX-стиль
        posix_pattern = pattern.replace('\\', '/')
        if Path(normalized_path).match(posix_pattern):
            return True
    return False

def is_ignored(rel_path, ignored_patterns, base_path):
    """Проверяет, должен ли файл быть проигнорирован"""
    abs_path = str(base_path / rel_path)
    for pattern in ignored_patterns:
        if Path(abs_path).match(pattern):
            return True
    return False

def create_backups(project_name, project_config, backup_dir,project_updates):
    """Создает полный бэкап файлов TARGETS и ADD_IN_BACKUPS с логированием"""
    backup_dir = Path(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    # Создаем лог-файл
    log_file = backup_dir / "backups_log.txt"
    log_data = []
    
    # Загрузка предыдущих версий
    current_hashes = get_current_hashes(project_config)
    
    # Получаем параметры из конфига
    targets = project_config['TARGETS']
    ignored = project_config.get('IGNORED', [])
    add_in_backups = project_config.get('ADD_IN_BACKUPS', [])
    base_path = Path(project_config['BASE_PATH'])
    
    log_data.append(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Начало бэкапа проекта {project_name}")
    
    # Копируем файлы из TARGETS предыдущей версии
    copied_files = set()
    for rel_path in project_updates['CURRENT_HASHES']:
        src = base_path / rel_path
        if is_target(rel_path, targets, base_path) and not is_ignored(rel_path, ignored, base_path):
            if src.exists():
                dst = backup_dir / rel_path
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                copied_files.add(rel_path)
                log_data.append(f"Скопирован TARGET: {rel_path}")
    
    # Копируем ADD_IN_BACKUPS
    for pattern in add_in_backups:
        for abs_path in base_path.glob(pattern):
            if abs_path.is_file():
                rel_path = abs_path.relative_to(base_path)
                dst = backup_dir / rel_path
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(abs_path, dst)
                log_data.append(f"Скопирован ADD_IN_BACKUPS: {rel_path}")
            elif abs_path.is_dir():
                for file_path in abs_path.rglob('*'):
                    if file_path.is_file():
                        rel_path = file_path.relative_to(base_path)
                        dst = backup_dir / rel_path
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(file_path, dst)
                        log_data.append(f"Скопирован ADD_IN_BACKUPS: {rel_path}")
    
    # Записываем логи
    log_data.append(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Бэкап завершен. Скопировано: {len(copied_files)} файлов")
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write("\n".join(log_data) + "\n\n")
    
    print(f"Создан полный бэкап в {backup_dir}")
    print(f"Логи бэкапа сохранены в {log_file}")

def apply_updates(changes, extracted_dir, config):
    """Применяет обновления к файлам проекта"""
    base_path = Path(config['BASE_PATH'])
    
    # Обработка новых и измененных файлов
    for rel_path in changes['new'] + changes['updated']:
        src = extracted_dir / rel_path
        dst = base_path / rel_path
        
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    # Обработка удаленных файлов (исправлено)
    for entry in changes['removed']:
        rel_path = entry['path']
        target = base_path / rel_path
        if target.exists():
            target.unlink()

def handle_special_file(rel_path, config, base_path):
    """Обрабатывает файлы с особыми функциями обновления"""
    function_name = config['FUNCTIONS_IF_UPDATE'][rel_path]
    try:
        module = __import__('starter_files.variables_functions', fromlist=[function_name])
        func = getattr(module, function_name)
        func(base_path / rel_path)
    except Exception as e:
        print(f"Ошибка при обработке специального файла {rel_path}: {str(e)}")

def is_new_installation(project_config):
    """Проверяет, является ли установка новой"""
    base_path = Path(project_config['BASE_PATH'])
    critical_files = project_config.get('CRITICAL_FILES', [])
    
    # Если нет критических файлов - используем первый файл из TARGETS
    if not critical_files:
        if project_config['TARGETS']:
            critical_files = [project_config['TARGETS'][0]]
        else:
            raise ValueError("Не заданы критические файлы для проекта")
    
    # Проверяем существование всех критических файлов
    return not all((base_path / Path(f)).exists() for f in critical_files)

def restart_application():
    """Перезапускает приложение"""
    python = sys.executable
    # Добавляем флаг --after-update в аргументы
    new_args = [python] + sys.argv + ['--after-update']
    subprocess.Popen(new_args)
    sys.exit()