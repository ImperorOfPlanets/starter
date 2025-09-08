from starter_files.core.base_module import BaseModule

import json
import os
import shutil
import zipfile
import requests
import hashlib
import sys
import subprocess
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple, List, Optional

class UpdatesModule(BaseModule):
    """
    Модуль для управления обновлениями проектов
    Основные пути конфигурации:
    - BASE_TEMP_DIR: Базовый каталог для временных файлов обновлений
    - EXTRACTED_SUBDIR: Подкаталог для распакованных файлов
    - BACKUPS_SUBDIR: Подкаталог для резервных копий
    - LOG_DIR: Каталог для логов обновлений
    """
    
    # Конфигурация путей по умолчанию
    DEFAULT_CONFIG = {
        'BASE_TEMP_DIR': 'update_temp',          # Базовый каталог временных файлов
        'EXTRACTED_SUBDIR': 'extracted',         # Распакованные файлы
        'BACKUPS_SUBDIR': 'backups',             # Резервные копии
        'LOG_DIR': 'update_logs',                # Логи обновлений
        'CLEANUP_DAYS': 7,                       # Дней хранения временных файлов
        'MAX_RETRIES': 3,                        # Попыток скачивания
        'TIMEOUT': 30,                           # Таймаут соединения (сек)
        'STATE_FILE': 'update_state.json',       # Файл хранения состояния обновлений
        'MIN_CHECK_INTERVAL': 30,                # Минимальный интервал между проверками в секундах
        'HISTORY_FILE': 'update_history.json',   # Файл истории обновлений
        'LOGS_EXTRACT': True,                    # Логировать процесс распаковки архивов
        'LOGS_CHANGES': True,                    # Логировать детали сравнения файлов
        'LOGS_BACKUP': True                      # Логировать процесс создания резервных копий
    }
    
    # Словарь для хранения активных процессов обновления
    _active_updates = {}
    
    @staticmethod
    def start_updates_projects(
        projects_config: Dict,
        module_config: Dict = None,
        force_check: bool = False
    ) -> Tuple[str, Dict, Dict]:
        """
        Основной процесс обновления проектов с контролем интервалов
        :param projects_config: Конфигурация проектов
        :param module_config: Конфигурация модуля обновлений
        :param force_check: Принудительное выполнение проверки
        :return: (Метка времени, Данные обновлений, Пути к файлам)
        """
        # Объединяем конфиги с настройками по умолчанию
        config = {**UpdatesModule.DEFAULT_CONFIG, **(module_config or {})}
        
        # Инициализация системы логирования
        UpdatesModule._init_logging(config)
        
        # Создаем базовые каталоги
        base_temp_dir = Path(config['BASE_TEMP_DIR'])
        base_temp_dir.mkdir(parents=True, exist_ok=True)
        Path(config['LOG_DIR']).mkdir(parents=True, exist_ok=True)
        
        # Метка времени для уникальных путей
        launch_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        update_id = f"update_{launch_timestamp}"
        projects_updates = {}
        projects_folders = {}
        
        # Начинаем запись в лог
        UpdatesModule._log_update(update_id, "=== Начало процесса обновления ===")
        UpdatesModule._log_update(update_id, f"Время начала: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Обработка каждого проекта
        for project_name, project_config in projects_config.items():
            try:
                UpdatesModule._log_update(update_id, f"Обработка проекта: {project_name}")
                
                # Проверка необходимости обновления
                last_update_seconds = UpdatesModule.seconds_since_last_update(project_name, config)
                
                if not force_check and not UpdatesModule.should_check_updates(project_name, config):
                    message = (f"Проверка пропущена: {project_name} "
                              f"(обновлялся {last_update_seconds:.0f} сек назад, "
                              f"интервал: {config['MIN_CHECK_INTERVAL']} сек)")
                    UpdatesModule._log_update(update_id, message)
                    continue
                    
                message = (f"Начало проверки: {project_name} "
                          f"(последняя проверка: {last_update_seconds:.0f} сек назад)")
                UpdatesModule._log_update(update_id, message)
                
                # Формирование путей для проекта
                project_paths = {
                    'EXTRACTED_DIR': base_temp_dir / config['EXTRACTED_SUBDIR'] / project_name / launch_timestamp,
                    'BACKUPS_DIR': base_temp_dir / config['BACKUPS_SUBDIR'] / project_name / launch_timestamp,
                    'BASE_PATH': Path(project_config['BASE_PATH'])
                }
                
                # Создание необходимых каталогов
                project_paths['EXTRACTED_DIR'].mkdir(parents=True, exist_ok=True)
                project_paths['BACKUPS_DIR'].mkdir(parents=True, exist_ok=True)
                projects_folders[project_name] = project_paths

                # Скачивание и распаковка архива
                projects_updates[project_name] = {}
                UpdatesModule._log_update(update_id, f"Скачивание архива для проекта {project_name}")
                projects_updates[project_name]['EXTRACTED_HASHES'] = UpdatesModule._download_and_extract(
                    url=project_config['DOWNLOAD_URL'],
                    extract_dir=project_paths['EXTRACTED_DIR'],
                    config=config,
                    update_id=update_id
                )

                # Проверка новой установки
                if 'CRITICAL_FILES' in project_config and UpdatesModule._is_new_installation(project_config):
                    UpdatesModule._log_update(update_id, f"Обнаружена новая установка: {project_name}")
                    shutil.copytree(
                        project_paths['EXTRACTED_DIR'],
                        project_paths['BASE_PATH'],
                        dirs_exist_ok=True
                    )
                    # Обновляем состояние после установки
                    UpdatesModule._update_state_file(project_name, config)
                    UpdatesModule._add_to_history(project_name, "new_installation", "Новая установка проекта", config)
                    continue  # Переходим к следующему проекту

                # Получение текущих хешей
                UpdatesModule._log_update(update_id, f"Вычисление хешей текущих файлов проекта {project_name}")
                projects_updates[project_name]['CURRENT_HASHES'] = UpdatesModule._get_current_hashes(project_config)
                
                # Поиск изменений
                UpdatesModule._log_update(update_id, f"Поиск изменений в проекте {project_name}")
                projects_updates[project_name]['CHANGES'] = UpdatesModule._find_changes(
                    old_hashes=projects_updates[project_name]['CURRENT_HASHES'],
                    new_hashes=projects_updates[project_name]['EXTRACTED_HASHES'],
                    config=project_config,
                    update_id=update_id
                )

                # Применение изменений при их наличии
                if any(projects_updates[project_name]['CHANGES'].values()):
                    UpdatesModule._log_update(update_id, f"Обнаружены изменения в проекте {project_name}")
                    
                    # Создание резервных копий
                    UpdatesModule._create_backups(
                        project_name=project_name,
                        config=project_config,
                        backup_dir=project_paths['BACKUPS_DIR'],
                        updates=projects_updates[project_name],
                        update_id=update_id
                    )
                    
                    # Применение обновлений
                    UpdatesModule._apply_updates(
                        changes=projects_updates[project_name]['CHANGES'],
                        extracted_dir=project_paths['EXTRACTED_DIR'],
                        config=project_config,
                        update_id=update_id
                    )
                    
                    # Обработка специальных файлов
                    UpdatesModule._handle_special_files(
                        project_name=project_name,
                        config=project_config,
                        updates=projects_updates,
                        folders=projects_folders,
                        update_id=update_id
                    )

                    # Перезапуск при необходимости
                    if project_config.get('RESTART_AFTER_UPDATE', False):
                        UpdatesModule._log_update(update_id, f"Перезапуск приложения после обновления {project_name}")
                        UpdatesModule._restart_application()
                    
                    # Обновляем состояние после успешного обновления
                    UpdatesModule._update_state_file(project_name, config)
                    UpdatesModule._add_to_history(project_name, "success", "Проект успешно обновлен", config)
                else:
                    UpdatesModule._log_update(update_id, f"Изменений не обнаружено: {project_name}")
                    # Обновляем время проверки даже если изменений нет
                    UpdatesModule._update_state_file(project_name, config)
                    UpdatesModule._add_to_history(project_name, "no_changes", "Изменений не обнаружено", config)

            except Exception as e:
                error_msg = f"Ошибка обновления {project_name}: {str(e)}"
                UpdatesModule._log_update(update_id, error_msg, level="ERROR")
                UpdatesModule._add_to_history(project_name, "error", error_msg, config)
                continue

        # Очистка устаревших файлов
        UpdatesModule._cleanup_old_files(config)
        UpdatesModule._log_update(update_id, "=== Процесс обновления завершен ===")
        return launch_timestamp, projects_updates, projects_folders

    @staticmethod
    def _download_and_extract(
        url: str, 
        extract_dir: Path,
        config: Dict,
        update_id: str = None
    ) -> Dict[str, str]:
        """
        Скачивание и распаковка архива с проектом
        :param url: URL архива для скачивания
        :param extract_dir: Каталог для распаковки
        :param config: Конфигурация модуля
        :param update_id: ID процесса обновления для логирования
        :return: Словарь хешей файлов {относительный_путь: хеш}
        """
        archive_path = extract_dir / "temp.zip"
        file_hashes = {}
        
        # Попытки скачивания с повторами
        for attempt in range(config['MAX_RETRIES']):
            try:
                UpdatesModule._log_update(update_id, f"Скачивание архива (попытка {attempt+1}): {url}")
                
                # Загрузка файла
                with requests.get(
                    url, 
                    stream=True, 
                    timeout=config['TIMEOUT']
                ) as response:
                    response.raise_for_status()
                    total_size = int(response.headers.get('content-length', 0))
                    downloaded = 0
                    
                    with open(archive_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                progress = (downloaded / total_size) * 100
                                progress_msg = f"Прогресс скачивания: {progress:.1f}%"
                                UpdatesModule._log_update(update_id, progress_msg)
                
                # Распаковка архива
                UpdatesModule._log_update(update_id, f"Распаковка архива: {archive_path}")
                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
                
                break  # Успешное завершение
                    
            except Exception as e:
                if attempt == config['MAX_RETRIES'] - 1:
                    error_msg = f"Ошибка скачивания/распаковки: {str(e)}"
                    UpdatesModule._log_update(update_id, error_msg, level="ERROR")
                    raise
                warning_msg = f"Ошибка попытки {attempt+1}: {str(e)}"
                UpdatesModule._log_update(update_id, warning_msg, level="WARNING")
            finally:
                # Всегда удаляем временный архив
                if archive_path.exists():
                    archive_path.unlink()

        # Вычисление хешей распакованных файлов
        UpdatesModule._log_update(update_id, "Вычисление хешей файлов...")
        for root, _, files in os.walk(extract_dir):
            for file in files:
                file_path = Path(root) / file
                rel_path = file_path.relative_to(extract_dir)
                
                with open(file_path, 'rb') as f:
                    file_hash = hashlib.sha256(f.read()).hexdigest()
                    file_hashes[str(rel_path)] = file_hash
                    
                    # Детальное логирование распаковки
                    if config.get('LOGS_EXTRACT', True):
                        UpdatesModule._log_update(update_id, f"Файл: {rel_path}, хеш: {file_hash}")
        
        message = f"Распаковано файлов: {len(file_hashes)}"
        UpdatesModule._log_update(update_id, message)
        return file_hashes

    @staticmethod
    def _get_current_hashes(project_config: Dict) -> Dict[str, str]:
        """
        Получение хешей текущих файлов проекта
        :param project_config: Конфигурация проекта
        :return: Словарь хешей {относительный_путь: хеш}
        """
        base_path = Path(project_config['BASE_PATH'])
        current_hashes = {}
        
        # Обработка всех целевых шаблонов
        for pattern in project_config['TARGETS']:
            for path in base_path.rglob(pattern):
                if path.is_file() and not UpdatesModule._is_ignored(path, project_config):
                    rel_path = path.relative_to(base_path)
                    with open(path, 'rb') as f:
                        current_hashes[str(rel_path)] = hashlib.sha256(f.read()).hexdigest()
        
        return current_hashes

    @staticmethod
    def _find_changes(
        old_hashes: Dict, 
        new_hashes: Dict, 
        config: Dict,
        update_id: str = None
    ) -> Dict[str, List]:
        """
        Поиск изменений между версиями
        :param old_hashes: Хеши текущей версии
        :param new_hashes: Хеши новой версии
        :param config: Конфигурация проекта
        :param update_id: ID процесса обновления для логирования
        :return: Словарь изменений {'new': [], 'updated': [], 'removed': []}
        """
        changes = {'new': [], 'updated': [], 'removed': []}
        log_data = []
        
        # Поиск новых и измененных файлов
        for rel_path, new_hash in new_hashes.items():
            if (UpdatesModule._is_target(rel_path, config) and 
                not UpdatesModule._is_ignored(rel_path, config)):
                old_hash = old_hashes.get(rel_path)
                if not old_hash:
                    changes['new'].append(rel_path)
                    log_data.append(f"Новый файл: {rel_path}")
                elif old_hash != new_hash:
                    changes['updated'].append(rel_path)
                    log_data.append(f"Измененный файл: {rel_path} (старый хеш: {old_hash}, новый хеш: {new_hash})")
        
        # Поиск удаленных файлов
        for rel_path in old_hashes:
            if (rel_path not in new_hashes and 
                UpdatesModule._is_target(rel_path, config) and 
                not UpdatesModule._is_ignored(rel_path, config)):
                changes['removed'].append({'path': rel_path, 'reason': "Удален в новой версии"})
                log_data.append(f"Удаленный файл: {rel_path}")
                
        # Детальное логирование изменений
        if config.get('LOGS_CHANGES', True) and log_data:
            UpdatesModule._log_update(update_id, "Детали изменений:")
            for log_entry in log_data:
                UpdatesModule._log_update(update_id, f"  {log_entry}")
                
        return changes

    @staticmethod
    def _create_backups(
        project_name: str, 
        config: Dict, 
        backup_dir: Path, 
        updates: Dict,
        update_id: str = None
    ) -> None:
        """
        Создание резервных копий изменяемых файлов
        :param project_name: Имя проекта
        :param config: Конфигурация проекта
        :param backup_dir: Каталог для резервных копий
        :param updates: Данные обновлений
        :param update_id: ID процесса обновления для логирования
        """
        base_path = Path(config['BASE_PATH'])
        log_file = backup_dir / "backup.log"
        
        message = f"Создание резервных копий в: {backup_dir}"
        UpdatesModule._log_update(update_id, message)
        
        with open(log_file, 'w') as log:
            log.write(f"Резервное копирование начато: {datetime.now()}\n")
            
            # Копирование целевых файлов
            for rel_path in updates['CURRENT_HASHES']:
                src = base_path / rel_path
                if src.exists():
                    dst = backup_dir / rel_path
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)
                    log.write(f"Скопирован: {rel_path}\n")
                    
                    # Детальное логирование бэкапа
                    if config.get('LOGS_BACKUP', True):
                        UpdatesModule._log_update(update_id, f"Резервная копия: {rel_path}")
            
            # Дополнительные файлы для бэкапа
            for pattern in config.get('ADD_IN_BACKUPS', []):
                for path in base_path.glob(pattern):
                    if path.is_file():
                        rel_path = path.relative_to(base_path)
                        dst = backup_dir / rel_path
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(path, dst)
                        log.write(f"Доп. копия: {rel_path}\n")
                        
                        # Детальное логирование бэкапа
                        if config.get('LOGS_BACKUP', True):
                            UpdatesModule._log_update(update_id, f"Доп. резервная копия: {rel_path}")
        
        message = f"Резервные копии созданы: {len(updates['CURRENT_HASHES'])} файлов"
        UpdatesModule._log_update(update_id, message)

    @staticmethod
    def _apply_updates(
        changes: Dict, 
        extracted_dir: Path, 
        config: Dict,
        update_id: str = None
    ) -> None:
        """
        Применение обновлений к файлам проекта
        :param changes: Обнаруженные изменения
        :param extracted_dir: Каталог с новыми файлами
        :param config: Конфигурация проекта
        :param update_id: ID процесса обновления для логирования
        """
        base_path = Path(config['BASE_PATH'])
        
        # Копирование новых и измененных файлов
        for rel_path in changes['new'] + changes['updated']:
            src = extracted_dir / rel_path
            dst = base_path / rel_path
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            UpdatesModule._log_update(update_id, f"Обновлен: {rel_path}")
            
        # Удаление отсутствующих в новой версии файлов
        for entry in changes['removed']:
            target = base_path / entry['path']
            if target.exists():
                target.unlink()
                UpdatesModule._log_update(update_id, f"Удален: {entry['path']}")
        
        message = (f"Применено обновлений: "
                  f"+{len(changes['new'])} "
                  f"~{len(changes['updated'])} "
                  f"-{len(changes['removed'])}")
        UpdatesModule._log_update(update_id, message)

    @staticmethod
    def _handle_special_files(
        project_name: str, 
        config: Dict, 
        updates: Dict, 
        folders: Dict,
        update_id: str = None
    ) -> None:
        """
        Обработка файлов с особыми функции обновления
        :param project_name: Имя проекта
        :param config: Конфигурация проекта
        :param updates: Данные обновлений
        :param folders: Пути к файлам проекта
        :param update_id: ID процесса обновления для логирования
        """
        if 'FUNCTIONS_IF_UPDATE' not in config:
            return
            
        special_files = config['FUNCTIONS_IF_UPDATE']
        
        # Обработка только измененных файлов
        for rel_path in updates[project_name]['CHANGES']['updated']:
            if rel_path in special_files:
                try:
                    func_name = special_files[rel_path]
                    module = __import__('starter_files.variables_functions', fromlist=[func_name])
                    func = getattr(module, func_name)
                    
                    # Вызов функции с передачей контекста
                    func(
                        projects_updates=updates[project_name],
                        projects_folders=folders[project_name]
                    )
                    message = f"Выполнена спец.функция {func_name} для {rel_path}"
                    UpdatesModule._log_update(update_id, message)
                except Exception as e:
                    error_msg = f"Ошибка спец.функции {func_name} ({rel_path}): {str(e)}"
                    UpdatesModule._log_update(update_id, error_msg, level="ERROR")

    @staticmethod
    def _is_new_installation(config: Dict) -> bool:
        """
        Проверка новой установки проекта
        :param config: Конфигурация проекта
        :return: True если это новая установка
        """
        base_path = Path(config['BASE_PATH'])
        critical_files = config.get('CRITICAL_FILES', [])
        
        # Если критические файлы не указаны, берем первый из TARGETS
        if not critical_files and config['TARGETS']:
            critical_files = [config['TARGETS'][0]]
            
        # Проверка существования критических файлов
        return not all((base_path / Path(f)).exists() for f in critical_files)

    @staticmethod
    def _is_target(rel_path: str, config: Dict) -> bool:
        """
        Проверка соответствия файла целевым шаблонам
        :param rel_path: Относительный путь файла
        :param config: Конфигурация проекта
        :return: True если файл соответствует TARGETS
        """
        path = Path(rel_path)
        for pattern in config['TARGETS']:
            if path.match(pattern):
                return True
        return False

    @staticmethod
    def _is_ignored(rel_path: str, config: Dict) -> bool:
        """
        Проверка игнорирования файла
        :param rel_path: Относительный путь файла
        :param config: Конфигурация проекта
        :return: True если файл должен быть игнорирован
        """
        path = Path(rel_path)
        for pattern in config.get('IGNORED', []):
            if path.match(pattern):
                return True
        return False

    @staticmethod
    def _cleanup_old_files(config: Dict) -> None:
        """
        Очистка устаревших временных файлов
        :param config: Конфигурация модуля
        """
        base_temp_dir = Path(config['BASE_TEMP_DIR'])
        cutoff_date = datetime.now() - timedelta(days=config['CLEANUP_DAYS'])
        removed_count = 0
        
        # Обработка каталогов извлеченных файлов и бэкапов
        for dir_type in [config['EXTRACTED_SUBDIR'], config['BACKUPS_SUBDIR']]:
            type_dir = base_temp_dir / dir_type
            if not type_dir.exists():
                continue
                
            # Поиск устаревших проектов
            for project_dir in type_dir.iterdir():
                if not project_dir.is_dir():
                    continue
                    
                # Удаление старых версий
                for version_dir in project_dir.iterdir():
                    try:
                        # Извлечение даты из имени каталога
                        dir_date = datetime.strptime(version_dir.name, '%Y%m%d_%H%M%S')
                        if dir_date < cutoff_date:
                            shutil.rmtree(version_dir)
                            removed_count += 1
                    except ValueError:
                        continue
        
        if removed_count > 0:
            UpdatesModule._log_update(None, f"Очищено устаревших каталогов: {removed_count}")

    @staticmethod
    def _restart_application() -> None:
        """Перезапуск приложения после обновления"""
        python = sys.executable
        subprocess.Popen([python] + sys.argv + ['--after-update'])
        sys.exit()

    @staticmethod
    def check_and_update_project(
        project_name: str,
        projects_config: Dict,
        module_config: Dict = None,
        force: bool = False
    ) -> bool:
        """
        Проверка и обновление конкретного проекта
        :param project_name: Имя проекта для обновления
        :param projects_config: Полная конфигурация проектов
        :param module_config: Конфигурация модуля
        :param force: Принудительное обновление
        :return: True если обновление выполнено
        """
        if project_name not in projects_config:
            return False
            
        config = {**UpdatesModule.DEFAULT_CONFIG, **(module_config or {})}
        
        if not force and not UpdatesModule.should_check_updates(project_name, config):
            return False
            
        try:
            # Выделяем конфигурацию нужного проекта
            project_config = {project_name: projects_config[project_name]}
            
            # Запускаем процесс обновления
            UpdatesModule.start_updates_projects(
                projects_config=project_config,
                module_config=module_config,
                force_check=True
            )
            return True
        except Exception as e:
            return False

    @staticmethod
    def get_last_update_time(project_name: str, config: Dict) -> Optional[datetime]:
        """
        Получение времени последнего обновления проекта
        :param project_name: Имя проекта
        :param config: Конфигурация модуля
        :return: datetime объекта или None
        """
        state_file = Path(config['STATE_FILE'])
        if not state_file.exists():
            return None
        
        try:
            with open(state_file, 'r') as f:
                state = json.load(f)
            project_state = state.get(project_name, {})
            return datetime.fromisoformat(project_state.get('last_update'))
        except:
            return None

    @staticmethod
    def seconds_since_last_update(project_name: str, config: Dict) -> float:
        """
        Вычисление секунд, прошедших с последнего обновления
        :param project_name: Имя проекта
        :param config: Конфигурация модуля
        :return: Количество секунд (0 если обновлений не было)
        """
        last_update = UpdatesModule.get_last_update_time(project_name, config)
        if not last_update:
            return 0
        return (datetime.now() - last_update).total_seconds()

    @staticmethod
    def should_check_updates(project_name: str, config: Dict) -> bool:
        """
        Проверка необходимости проверки обновлений
        :param project_name: Имя проекта
        :param config: Конфигурация модуля
        :return: True если проверка требуется
        """
        seconds_passed = UpdatesModule.seconds_since_last_update(project_name, config)
        min_interval = config['MIN_CHECK_INTERVAL']
        return seconds_passed >= min_interval

    @staticmethod
    def _update_state_file(project_name: str, config: Dict) -> None:
        """
        Обновление файла состояния после успешной проверки
        :param project_name: Имя проекта
        :param config: Конфигурация модуля
        """
        state_file = Path(config['STATE_FILE'])
        state = {}
        
        if state_file.exists():
            try:
                with open(state_file, 'r') as f:
                    state = json.load(f)
            except:
                pass
        
        project_state = state.get(project_name, {})
        project_state['last_update'] = datetime.now().isoformat()
        state[project_name] = project_state
        
        state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)

    @staticmethod
    def _init_logging(config: Dict) -> None:
        """
        Инициализация системы логирования
        :param config: Конфигурация модуля
        """
        log_dir = Path(config['LOG_DIR'])
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Настройка базового логирования
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / 'updates.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )

    @staticmethod
    def _log_update(update_id: str, message: str, level: str = "INFO") -> None:
        """
        Запись сообщения в лог обновления
        :param update_id: ID процесса обновления
        :param message: Сообщение для записи
        :param level: Уровень логирования
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_message = f"[{timestamp}] [{level}] {message}"
        
        if update_id:
            log_message = f"[{update_id}] {log_message}"
        
        # Запись в лог
        logger = logging.getLogger('updates')
        if level == "ERROR":
            logger.error(log_message)
        elif level == "WARNING":
            logger.warning(log_message)
        else:
            logger.info(log_message)
            
        # Также записываем в отдельный файл для данного обновления
        if update_id:
            log_dir = Path(UpdatesModule.DEFAULT_CONFIG['LOG_DIR'])
            update_log_file = log_dir / f"{update_id}.log"
            with open(update_log_file, 'a') as f:
                f.write(f"{log_message}\n")

    @staticmethod
    def _add_to_history(project_name: str, status: str, message: str, config: Dict) -> None:
        """
        Добавление записи в историю обновлений
        :param project_name: Имя проекта
        :param status: Статус обновления
        :param message: Сообщение
        :param config: Конфигурация модуля
        """
        history_file = Path(config['HISTORY_FILE'])
        history = []
        
        if history_file.exists():
            try:
                with open(history_file, 'r') as f:
                    history = json.load(f)
            except:
                pass
        
        history.append({
            'project': project_name,
            'timestamp': datetime.now().isoformat(),
            'status': status,
            'message': message
        })
        
        # Ограничиваем историю последними 100 записями
        history = history[-100:]
        
        history_file.parent.mkdir(parents=True, exist_ok=True)
        with open(history_file, 'w') as f:
            json.dump(history, f, indent=2)

    @staticmethod
    def get_update_history(project_name: str = None, config: Dict = None) -> List[Dict]:
        """
        Получение истории обновлений
        :param project_name: Имя проекта для фильтрации (None для всех проектов)
        :param config: Конфигурация модуля
        :return: Список записей истории
        """
        if config is None:
            config = UpdatesModule.DEFAULT_CONFIG
            
        history_file = Path(config['HISTORY_FILE'])
        history = []
        
        if history_file.exists():
            try:
                with open(history_file, 'r') as f:
                    history = json.load(f)
            except:
                pass
        
        if project_name:
            history = [item for item in history if item['project'] == project_name]
        
        return history

    @staticmethod
    def get_update_log(update_id: str, config: Dict = None) -> str:
        """
        Получение лога конкретного обновления
        :param update_id: ID обновления
        :param config: Конфигурация модуля
        :return: Содержимое лог-файла
        """
        if config is None:
            config = UpdatesModule.DEFAULT_CONFIG
            
        log_file = Path(config['LOG_DIR']) / f"{update_id}.log"
        
        if not log_file.exists():
            return "Лог-файл не найден"
        
        try:
            with open(log_file, 'r') as f:
                return f.read()
        except Exception as e:
            return f"Ошибка чтения лог-файла: {str(e)}"

    @staticmethod
    def get_updates_config() -> Dict:
        """
        Получение конфигурации с правильным путем к файлу состояния
        :return: Конфигурация модуля обновлений
        """
        config = UpdatesModule.DEFAULT_CONFIG.copy()
        
        # Устанавливаем правильный путь к файлу состояния
        script_path = Path(__file__).resolve().parent.parent.parent.parent
        state_file_path = script_path / 'starter_files' / 'update_state.json'
        config['STATE_FILE'] = str(state_file_path)
        
        # Создаем директорию, если она не существует
        state_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Создаем файл состояния, если он не существует
        if not state_file_path.exists():
            with open(state_file_path, 'w') as f:
                json.dump({}, f)
        
        return config