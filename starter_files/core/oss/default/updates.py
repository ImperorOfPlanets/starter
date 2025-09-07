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
from starter_files.core.utils.log_utils import LogManager

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
        'TIMEOUT': 30 ,                          # Таймаут соединения (сек)
        'STATE_FILE': 'update_state.json',       # Файл хранения состояния обновлений
        'MIN_CHECK_INTERVAL': 30                 # Минимальный интервал между проверками в секундах 
    }
    
    @classmethod
    def start_updates_projects(
        cls, 
        projects_config: Dict,
        module_config: Dict = None,
        force_check: bool = False  # Принудительная проверка
    ) -> Tuple[str, Dict, Dict]:
        """
        Основной процесс обновления проектов с контролем интервалов
        :param projects_config: Конфигурация проектов
        :param module_config: Конфигурация модуля обновлений
        :param force_check: Принудительное выполнение проверки
        :return: (Метка времени, Данные обновлений, Пути к файлам)
        """
        # Объединяем конфиги с настройками по умолчанию
        config = {**cls.DEFAULT_CONFIG, **(module_config or {})}
        
        # Инициализация системы логирования
        LogManager.register_log_dir('updates', config['LOG_DIR'])
        logger = LogManager.get_logger('updates')
        logger.info("=== Начало процесса обновления ===")
        
        # Создаем базовые каталоги
        base_temp_dir = Path(config['BASE_TEMP_DIR'])
        base_temp_dir.mkdir(parents=True, exist_ok=True)
        Path(config['LOG_DIR']).mkdir(parents=True, exist_ok=True)
        
        # Метка времени для уникальных путей
        launch_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        projects_updates = {}
        projects_folders = {}

        # Обработка каждого проекта
        for project_name, project_config in projects_config.items():
            try:
                logger.info(f"Обработка проекта: {project_name}")
                
                # Проверка необходимости обновления
                last_update_seconds = cls.seconds_since_last_update(project_name, config)
                
                if not force_check and not cls.should_check_updates(project_name, config):
                    logger.info(f"Проверка пропущена: {project_name} "
                                f"(обновлялся {last_update_seconds:.0f} сек назад, "
                                f"интервал: {config['MIN_CHECK_INTERVAL']} сек)")
                    continue
                    
                logger.info(f"Начало проверки: {project_name} "
                            f"(последняя проверка: {last_update_seconds:.0f} сек назад)")
                
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
                projects_updates[project_name]['EXTRACTED_HASHES'] = cls._download_and_extract(
                    url=project_config['DOWNLOAD_URL'],
                    extract_dir=project_paths['EXTRACTED_DIR'],
                    config=config
                )

                # Проверка новой установки
                if 'CRITICAL_FILES' in project_config and cls._is_new_installation(project_config):
                    logger.info(f"Обнаружена новая установка: {project_name}")
                    shutil.copytree(
                        project_paths['EXTRACTED_DIR'],
                        project_paths['BASE_PATH'],
                        dirs_exist_ok=True
                    )
                    # Обновляем состояние после установки
                    cls._update_state_file(project_name, config)
                    continue  # Переходим к следующему проекту

                # Получение текущих хешей
                projects_updates[project_name]['CURRENT_HASHES'] = cls._get_current_hashes(project_config)
                
                # Поиск изменений
                projects_updates[project_name]['CHANGES'] = cls._find_changes(
                    old_hashes=projects_updates[project_name]['CURRENT_HASHES'],
                    new_hashes=projects_updates[project_name]['EXTRACTED_HASHES'],
                    config=project_config
                )

                # Применение изменений при их наличии
                if any(projects_updates[project_name]['CHANGES'].values()):
                    logger.info(f"Обнаружены изменения в проекте {project_name}")
                    
                    # Создание резервных копий
                    cls._create_backups(
                        project_name=project_name,
                        config=project_config,
                        backup_dir=project_paths['BACKUPS_DIR'],
                        updates=projects_updates[project_name]
                    )
                    
                    # Применение обновлений
                    cls._apply_updates(
                        changes=projects_updates[project_name]['CHANGES'],
                        extracted_dir=project_paths['EXTRACTED_DIR'],
                        config=project_config
                    )
                    
                    # Обработка специальных файлов
                    cls._handle_special_files(
                        project_name=project_name,
                        config=project_config,
                        updates=projects_updates,
                        folders=projects_folders
                    )

                    # Перезапуск при необходимости
                    if project_config.get('RESTART_AFTER_UPDATE', False):
                        cls._restart_application()
                    
                    # Обновляем состояние после успешного обновления
                    cls._update_state_file(project_name, config)
                else:
                    logger.info(f"Изменений не обнаружено: {project_name}")
                    # Обновляем время проверки даже если изменений нет
                    cls._update_state_file(project_name, config)

            except Exception as e:
                logger.error(f"Ошибка обновления {project_name}: {str(e)}")
                continue

        # Очистка устаревших файлов
        cls._cleanup_old_files(config)
        logger.info("=== Процесс обновления завершен ===")
        return launch_timestamp, projects_updates, projects_folders

    @classmethod
    def _download_and_extract(
        cls,
        url: str, 
        extract_dir: Path,
        config: Dict
    ) -> Dict[str, str]:
        """
        Скачивание и распаковка архива с проектом
        :param url: URL архива для скачивания
        :param extract_dir: Каталог для распаковки
        :param config: Конфигурация модуля
        :return: Словарь хешей файлов {относительный_путь: хеш}
        """
        logger = LogManager.get_logger('updates')
        archive_path = extract_dir / "temp.zip"
        file_hashes = {}
        
        # Попытки скачивания с повторами
        for attempt in range(config['MAX_RETRIES']):
            try:
                logger.info(f"Скачивание архива (попытка {attempt+1}): {url}")
                
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
                                logger.debug(f"Прогресс: {progress:.1f}%")
                
                # Распаковка архива
                logger.info(f"Распаковка архива: {archive_path}")
                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
                
                break  # Успешное завершение
                    
            except Exception as e:
                if attempt == config['MAX_RETRIES'] - 1:
                    logger.error(f"Ошибка скачивания/распаковки: {str(e)}")
                    raise
                logger.warning(f"Ошибка попытки {attempt+1}: {str(e)}")
            finally:
                # Всегда удаляем временный архив
                if archive_path.exists():
                    archive_path.unlink()

        # Вычисление хешей распакованных файлов
        logger.info("Вычисление хешей файлов...")
        for root, _, files in os.walk(extract_dir):
            for file in files:
                file_path = Path(root) / file
                rel_path = file_path.relative_to(extract_dir)
                
                with open(file_path, 'rb') as f:
                    file_hashes[str(rel_path)] = hashlib.sha256(f.read()).hexdigest()
        
        logger.info(f"Распаковано файлов: {len(file_hashes)}")
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
        config: Dict
    ) -> Dict[str, List]:
        """
        Поиск изменений между версиями
        :param old_hashes: Хеши текущей версии
        :param new_hashes: Хеши новой версии
        :param config: Конфигурация проекта
        :return: Словарь изменений {'new': [], 'updated': [], 'removed': []}
        """
        changes = {'new': [], 'updated': [], 'removed': []}
        
        # Поиск новых и измененных файлов
        for rel_path, new_hash in new_hashes.items():
            if (UpdatesModule._is_target(rel_path, config) and 
                not UpdatesModule._is_ignored(rel_path, config)):
                old_hash = old_hashes.get(rel_path)
                if not old_hash:
                    changes['new'].append(rel_path)
                elif old_hash != new_hash:
                    changes['updated'].append(rel_path)
        
        # Поиск удаленных файлов
        for rel_path in old_hashes:
            if (rel_path not in new_hashes and 
                UpdatesModule._is_target(rel_path, config) and 
                not UpdatesModule._is_ignored(rel_path, config)):
                changes['removed'].append({'path': rel_path, 'reason': "Удален в новой версии"})
                
        return changes

    @staticmethod
    def _create_backups(
        project_name: str, 
        config: Dict, 
        backup_dir: Path, 
        updates: Dict
    ) -> None:
        """
        Создание резервных копий изменяемых файлов
        :param project_name: Имя проекта
        :param config: Конфигурация проекта
        :param backup_dir: Каталог для резервных копий
        :param updates: Данные обновлений
        """
        logger = LogManager.get_logger('updates')
        base_path = Path(config['BASE_PATH'])
        log_file = backup_dir / "backup.log"
        
        logger.info(f"Создание резервных копий в: {backup_dir}")
        
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
            
            # Дополнительные файлы для бэкапа
            for pattern in config.get('ADD_IN_BACKUPS', []):
                for path in base_path.glob(pattern):
                    if path.is_file():
                        rel_path = path.relative_to(base_path)
                        dst = backup_dir / rel_path
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(path, dst)
                        log.write(f"Доп. копия: {rel_path}\n")
        
        logger.info(f"Резервные копии созданы: {len(updates['CURRENT_HASHES'])} файлов")

    @staticmethod
    def _apply_updates(
        changes: Dict, 
        extracted_dir: Path, 
        config: Dict
    ) -> None:
        """
        Применение обновлений к файлам проекта
        :param changes: Обнаруженные изменения
        :param extracted_dir: Каталог с новыми файлами
        :param config: Конфигурация проекта
        """
        logger = LogManager.get_logger('updates')
        base_path = Path(config['BASE_PATH'])
        
        # Копирование новых и измененных файлов
        for rel_path in changes['new'] + changes['updated']:
            src = extracted_dir / rel_path
            dst = base_path / rel_path
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            logger.debug(f"Обновлен: {rel_path}")
            
        # Удаление отсутствующих в новой версии файлов
        for entry in changes['removed']:
            target = base_path / entry['path']
            if target.exists():
                target.unlink()
                logger.debug(f"Удален: {entry['path']}")
        
        logger.info(f"Применено обновлений: "
                    f"+{len(changes['new'])} "
                    f"~{len(changes['updated'])} "
                    f"-{len(changes['removed'])}")

    @staticmethod
    def _handle_special_files(
        project_name: str, 
        config: Dict, 
        updates: Dict, 
        folders: Dict
    ) -> None:
        """
        Обработка файлов с особыми функциями обновления
        :param project_name: Имя проекта
        :param config: Конфигурация проекта
        :param updates: Данные обновлений
        :param folders: Пути к файлам проекта
        """
        if 'FUNCTIONS_IF_UPDATE' not in config:
            return
            
        logger = LogManager.get_logger('updates')
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
                    logger.info(f"Выполнена спец.функция {func_name} для {rel_path}")
                except Exception as e:
                    logger.error(f"Ошибка спец.функции {func_name} ({rel_path}): {str(e)}")

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
        logger = LogManager.get_logger('updates')
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
                            logger.debug(f"Удален устаревший каталог: {version_dir}")
                    except ValueError:
                        continue
        
        if removed_count > 0:
            logger.info(f"Очищено устаревших каталогов: {removed_count}")

    @staticmethod
    def _restart_application() -> None:
        """Перезапуск приложения после обновления"""
        logger = LogManager.get_logger('updates')
        logger.info("Инициирован перезапуск приложения...")
        python = sys.executable
        subprocess.Popen([python] + sys.argv + ['--after-update'])
        sys.exit()

    @classmethod
    def check_and_update_project(
        cls,
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
            
        config = {**cls.DEFAULT_CONFIG, **(module_config or {})}
        logger = LogManager.get_logger('updates')
        
        if not force and not cls.should_check_updates(project_name, config):
            time_passed = cls.time_since_last_update(project_name, config)
            logger.info(f"Проверка не требуется: {project_name}. Последнее обновление: {time_passed}")
            return False
            
        try:
            # Выделяем конфигурацию нужного проекта
            project_config = {project_name: projects_config[project_name]}
            
            # Запускаем процесс обновления
            cls.start_updates_projects(
                projects_config=project_config,
                module_config=module_config,
                force_check=True
            )
            return True
        except Exception as e:
            logger.error(f"Ошибка при обновлении {project_name}: {str(e)}")
            return False

    @classmethod
    def get_last_update_time(cls, project_name: str, config: Dict) -> Optional[datetime]:
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

    @classmethod
    def seconds_since_last_update(cls, project_name: str, config: Dict) -> float:
        """
        Вычисление секунд, прошедших с последнего обновления
        :param project_name: Имя проекта
        :param config: Конфигурация модуля
        :return: Количество секунд (0 если обновлений не было)
        """
        last_update = cls.get_last_update_time(project_name, config)
        if not last_update:
            return 0
        return (datetime.now() - last_update).total_seconds()

    @classmethod
    def should_check_updates(cls, project_name: str, config: Dict) -> bool:
        """
        Проверка необходимости проверки обновлений
        :param project_name: Имя проекта
        :param config: Конфигурация модуля
        :return: True если проверка требуется
        """
        seconds_passed = cls.seconds_since_last_update(project_name, config)
        min_interval = config['MIN_CHECK_INTERVAL']
        return seconds_passed >= min_interval

    @classmethod
    def _update_state_file(cls, project_name: str, config: Dict) -> None:
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