import json
import os
import shutil
import zipfile
import requests
import hashlib
import sys
import subprocess
import logging
import uuid
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple, List, Optional

from starter_files.core.utils.globalVars_utils import get_global

class UpdatesModule:
    """
    Модуль для управления обновлениями проектов
    Все файлы хранятся в папке /starter_files/updates/
    Для каждого проекта создается отдельная папка
    Логи сохраняются с датой в названии
    """
    
    # Конфигурация путей
    DEFAULT_CONFIG = {
        'BASE_UPDATES_DIR': 'starter_files/updates',
        'EXTRACTED_SUBDIR': 'extracted',
        'BACKUPS_SUBDIR': 'backups',
        'LOG_DIR': 'starter_files/logs/updates',
        'CLEANUP_DAYS': 7,
        'MAX_RETRIES': 3,
        'TIMEOUT': 30,
        'MIN_CHECK_INTERVAL': 30
    }
    
    @staticmethod
    def get_updates_config() -> Dict:
        """
        Получение конфигурации с правильными путями
        """
        config = UpdatesModule.DEFAULT_CONFIG.copy()
        
        # Устанавливаем правильные пути
        script_path = get_global('script_path')
        base_updates_dir = script_path / 'starter_files' / 'updates'
        logs_dir = script_path / 'starter_files' / 'logs' / 'updates'
        
        config['BASE_UPDATES_DIR'] = str(base_updates_dir)
        config['LOG_DIR'] = str(logs_dir)
        
        # Создаем директории если не существуют
        base_updates_dir.mkdir(parents=True, exist_ok=True)
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        return config

    @staticmethod
    def get_update_history(project_name: str = None) -> Dict:
        """
        Получение истории обновлений из лог-файлов
        """
        config = UpdatesModule.get_updates_config()
        log_dir = Path(config['LOG_DIR'])
        
        history = []
        
        # Получаем все лог-файлы
        log_files = []
        if log_dir.exists():
            log_files = list(log_dir.glob("*.log"))
        
        # Сортируем по дате изменения (новые сначала)
        log_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        for log_file in log_files:
            # Извлекаем информацию из имени файла
            filename = log_file.stem
            parts = filename.split('_')
            
            if len(parts) >= 3:  # Формат: {project}_{date}_{time}
                log_project = parts[0]
                log_date = parts[1]
                log_time = parts[2]
                
                # Если указан конкретный проект, пропускаем другие
                if project_name and project_name != 'all' and log_project != project_name:
                    continue
                
                # Парсим дату и время из имени файла
                try:
                    timestamp = datetime.strptime(f"{log_date}_{log_time}", "%Y%m%d_%H%M%S")
                    
                    # Читаем статус из лог-файла
                    status = "unknown"
                    try:
                        with open(log_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if "Обновление завершено успешно" in content:
                                status = "completed"
                            elif "ОШИБКА" in content:
                                status = "error"
                            elif "Начало обновления" in content:
                                status = "in_progress"
                    except:
                        pass
                    
                    history.append({
                        "project": log_project,
                        "update_id": filename,
                        "status": status,
                        "timestamp": timestamp.isoformat(),
                        "log_file": log_file.name
                    })
                except ValueError:
                    continue
        
        return {"history": history}

    @staticmethod
    def get_last_update_time(project_name: str, config: Dict) -> Optional[datetime]:
        """
        Получение времени последнего обновления проекта из логов
        """
        history = UpdatesModule.get_update_history(project_name)["history"]
        
        if history:
            # Берем самую свежую запись
            latest = max(history, key=lambda x: x["timestamp"])
            return datetime.fromisoformat(latest["timestamp"])
        
        return None

    @staticmethod
    def seconds_since_last_update(project_name: str, config: Dict) -> float:
        """
        Вычисление секунд, прошедших с последнего обновления
        """
        last_update = UpdatesModule.get_last_update_time(project_name, config)
        if not last_update:
            return float('inf')  # Никогда не обновлялся
        return (datetime.now() - last_update).total_seconds()

    @staticmethod
    def should_check_updates(project_name: str, config: Dict) -> bool:
        """
        Проверка необходимости проверки обновлений
        """
        seconds_passed = UpdatesModule.seconds_since_last_update(project_name, config)
        min_interval = config['MIN_CHECK_INTERVAL']
        return seconds_passed >= min_interval

    @staticmethod
    def update_project(project_name: str, project_config: Dict) -> str:
        """
        Обновление конкретного проекта
        Возвращает ID обновления (имя лог-файла)
        """
        config = UpdatesModule.get_updates_config()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        update_id = f"{project_name}_{timestamp}"
        
        # Создаем директории для логов
        log_dir = Path(config['LOG_DIR'])
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Настройка логирования для этого обновления
        logger = logging.getLogger(f'update_{update_id}')
        logger.setLevel(logging.INFO)
        
        # Удаляем существующие обработчики
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        log_file = log_dir / f"{update_id}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(file_handler)
        
        # Также добавляем вывод в консоль
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(console_handler)
        
        try:
            logger.info(f"Начало обновления проекта {project_name}")
            
            # Запускаем процесс обновления
            UpdatesModule._perform_update(project_name, project_config, logger)
            
            logger.info("Обновление завершено успешно")
            return update_id
            
        except Exception as e:
            logger.error(f"Ошибка при обновлении: {str(e)}")
            return update_id

    @staticmethod
    def _perform_update(project_name: str, project_config: Dict, logger: logging.Logger):
        """
        Выполнение процесса обновления с детальным логированием
        """
        config = UpdatesModule.get_updates_config()
        
        logger.info(f"Базовая директория: {project_config['BASE_PATH']}")
        logger.info(f"URL загрузки: {project_config['DOWNLOAD_URL']}")
        
        # Формирование путей для проекта
        base_temp_dir = Path(config['BASE_UPDATES_DIR'])
        launch_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        project_paths = {
            'EXTRACTED_DIR': base_temp_dir / config['EXTRACTED_SUBDIR'] / project_name / launch_timestamp,
            'BACKUPS_DIR': base_temp_dir / config['BACKUPS_SUBDIR'] / project_name / launch_timestamp,
            'BASE_PATH': Path(project_config['BASE_PATH'])
        }
        
        # Создание необходимых каталогов
        project_paths['EXTRACTED_DIR'].mkdir(parents=True, exist_ok=True)
        project_paths['BACKUPS_DIR'].mkdir(parents=True, exist_ok=True)

        logger.info(f"Созданы временные директории:")
        logger.info(f"  - Для распаковки: {project_paths['EXTRACTED_DIR']}")
        logger.info(f"  - Для резервных копий: {project_paths['BACKUPS_DIR']}")

        # Скачивание и распаковка архива
        logger.info(f"Скачивание архива для проекта {project_name}")
        extracted_hashes = UpdatesModule._download_and_extract(
            url=project_config['DOWNLOAD_URL'],
            extract_dir=project_paths['EXTRACTED_DIR'],
            config=config,
            logger=logger
        )

        # Проверка новой установки
        if not project_paths['BASE_PATH'].exists():
            logger.info(f"Обнаружена новая установка: {project_name}")
            logger.info(f"Копирование файлов в: {project_paths['BASE_PATH']}")
            shutil.copytree(
                project_paths['EXTRACTED_DIR'],
                project_paths['BASE_PATH'],
                dirs_exist_ok=True
            )
            return

        # Получение текущих хешей
        logger.info(f"Вычисление хешей текущих файлов проекта {project_name}")
        current_hashes = UpdatesModule._get_current_hashes(project_config, logger)
        
        # Поиск изменений
        logger.info(f"Поиск изменений в проекте {project_name}")
        changes = UpdatesModule._find_changes(
            old_hashes=current_hashes,
            new_hashes=extracted_hashes,
            old_dir=project_paths['BASE_PATH'],
            new_dir=project_paths['EXTRACTED_DIR'],
            logger=logger
        )

        # Применение изменений при их наличии
        if any(changes.values()):
            logger.info(f"Обнаружены изменения в проекте {project_name}")
            
            # Создание резервных копий
            UpdatesModule._create_backups(
                project_config=project_config,
                backup_dir=project_paths['BACKUPS_DIR'],
                current_hashes=current_hashes,
                logger=logger
            )
            
            # Применение обновлений
            UpdatesModule._apply_updates(
                changes=changes,
                extracted_dir=project_paths['EXTRACTED_DIR'],
                base_path=project_paths['BASE_PATH'],
                logger=logger
            )
        else:
            logger.info("Изменений не обнаружено")

        # Очистка устаревших файлов
        UpdatesModule._cleanup_old_files(config)

    @staticmethod
    def _download_and_extract(
        url: str, 
        extract_dir: Path,
        config: Dict,
        logger: logging.Logger
    ) -> Dict[str, str]:
        """
        Скачивание и распаковка архива с проектом с детальным логированием
        """
        archive_path = extract_dir / "temp.zip"
        file_hashes = {}
        
        # Попытки скачивания с повторами
        for attempt in range(config['MAX_RETRIES']):
            try:
                logger.info(f"Скачивание архива (попытка {attempt+1}): {url}")
                
                # Загрузка файла
                with requests.get(url, stream=True, timeout=config['TIMEOUT']) as response:
                    response.raise_for_status()
                    with open(archive_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                
                # Распаковка архива
                logger.info(f"Распаковка архива: {archive_path}")
                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
                
                break
                    
            except Exception as e:
                if attempt == config['MAX_RETRIES'] - 1:
                    raise
                logger.warning(f"Попытка {attempt+1} не удалась: {str(e)}")
            finally:
                if archive_path.exists():
                    archive_path.unlink()

        # Вычисление хешей распакованных файлов
        logger.info("=== ВЫЧИСЛЕНИЕ ХЕШЕЙ СКАЧАННЫХ ФАЙЛОВ ===")
        logger.info(f"Директория распаковки: {extract_dir}")
        
        file_count = 0
        for root, _, files in os.walk(extract_dir):
            for file in files:
                file_path = Path(root) / file
                rel_path = file_path.relative_to(extract_dir)
                
                with open(file_path, 'rb') as f:
                    file_hash = hashlib.sha256(f.read()).hexdigest()
                    file_hashes[str(rel_path)] = file_hash
                
                logger.debug(f"Вычислен хеш для: {rel_path} -> {file_hash}")
                file_count += 1
                    
        logger.info(f"Всего распаковано файлов: {file_count}")
        logger.info("=== ЗАВЕРШЕНО ВЫЧИСЛЕНИЕ ХЕШЕЙ СКАЧАННЫХ ФАЙЛОВ ===")
        return file_hashes

    @staticmethod
    def _create_backups(
        project_config: Dict, 
        backup_dir: Path, 
        current_hashes: Dict,
        logger: logging.Logger
    ) -> None:
        """
        Создание резервных копии изменяемых файлов с детальным логированием
        """
        base_path = Path(project_config['BASE_PATH'])
        
        logger.info(f"Создание резервных копий в: {backup_dir}")
        
        # Копирование целевых файлов
        for rel_path in current_hashes:
            src = base_path / rel_path
            if src.exists():
                dst = backup_dir / rel_path
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                logger.debug(f"Создана резервная копия: {rel_path}")
        
        logger.info(f"Резервные копии созданы: {len(current_hashes)} файлов")

    @staticmethod
    def _cleanup_old_files(config: Dict) -> None:
        """
        Очистка устаревших временных файлов
        """
        base_temp_dir = Path(config['BASE_UPDATES_DIR'])
        cutoff_date = datetime.now() - timedelta(days=config['CLEANUP_DAYS'])
        
        for dir_type in [config['EXTRACTED_SUBDIR'], config['BACKUPS_SUBDIR']]:
            type_dir = base_temp_dir / dir_type
            if not type_dir.exists():
                continue
                
            for project_dir in type_dir.iterdir():
                if not project_dir.is_dir():
                    continue
                    
                for version_dir in project_dir.iterdir():
                    try:
                        dir_date = datetime.strptime(version_dir.name, '%Y%m%d_%H%M%S')
                        if dir_date < cutoff_date:
                            shutil.rmtree(version_dir)
                    except ValueError:
                        continue

    @staticmethod
    def _get_current_hashes(project_config: Dict, logger: logging.Logger = None) -> Dict[str, str]:
        """
        Получение хешей текущих файлов проекта с детальным логированием
        """
        base_path = Path(project_config['BASE_PATH'])
        current_hashes = {}
        
        if logger:
            logger.info("=== ВЫЧИСЛЕНИЕ ХЕШЕЙ ТЕКУЩИХ ФАЙЛОВ ===")
            logger.info(f"Директория: {base_path}")
            logger.info(f"Шаблоны поиска: {project_config['TARGETS']}")
        
        for pattern in project_config['TARGETS']:
            if logger:
                logger.info(f"Поиск файлов по шаблону: {pattern}")
            
            file_count = 0
            for path in base_path.rglob(pattern):
                if path.is_file():
                    rel_path = path.relative_to(base_path)
                    with open(path, 'rb') as f:
                        file_hash = hashlib.sha256(f.read()).hexdigest()
                        current_hashes[str(rel_path)] = file_hash
                    
                    if logger:
                        logger.debug(f"Вычислен хеш для: {rel_path} -> {file_hash}")
                    file_count += 1
            
            if logger:
                logger.info(f"Найдено файлов по шаблону '{pattern}': {file_count}")
        
        if logger:
            logger.info(f"Всего найдено файлов: {len(current_hashes)}")
            logger.info("=== ЗАВЕРШЕНО ВЫЧИСЛЕНИЕ ХЕШЕЙ ===")
        
        return current_hashes

    @staticmethod
    def _find_changes(
        old_hashes: Dict,
        new_hashes: Dict,
        old_dir: Path = None,
        new_dir: Path = None,
        logger: logging.Logger = None
    ) -> Dict[str, List]:
        changes = {'new': [], 'updated': [], 'removed': []}

        if logger:
            logger.info("=== СРАВНЕНИЕ ХЕШЕЙ ФАЙЛОВ ===")
            if old_dir and new_dir:
                logger.info(f"Сравниваются папки:\n  Старая: {old_dir}\n  Новая: {new_dir}")
            logger.info(f"Файлов в текущей версии: {len(old_hashes)}")
            logger.info(f"Файлов в новой версии: {len(new_hashes)}")

        # Поиск новых и измененных файлов
        for rel_path, new_hash in new_hashes.items():
            old_hash = old_hashes.get(rel_path)
            if not old_hash:
                changes['new'].append(rel_path)
                if logger:
                    logger.info(f"НОВЫЙ ФАЙЛ: {rel_path}")
                    logger.info(f"  Хеш новой версии: {new_hash}")
            elif old_hash != new_hash:
                changes['updated'].append(rel_path)
                if logger:
                    logger.info(f"ИЗМЕНЕН ФАЙЛ: {rel_path}")
                    logger.info(f"  Хеш текущей версии: {old_hash}")
                    logger.info(f"  Хеш новой версии: {new_hash}")
                    logger.info(f"  Файл будет заменен")

        # Поиск удаленных файлов
        for rel_path, old_hash in old_hashes.items():
            if rel_path not in new_hashes:
                changes['removed'].append(rel_path)
                if logger:
                    logger.info(f"УДАЛЕН ФАЙЛ: {rel_path}")
                    logger.info(f"  Хеш удаляемого файла: {old_hash}")

        if logger:
            logger.info("=== РЕЗУЛЬТАТЫ СРАВНЕНИЯ ===")
            logger.info(f"Новых файлов: {len(changes['new'])}")
            for new_file in changes['new']:
                logger.info(f"  + {new_file}")

            logger.info(f"Измененных файлов: {len(changes['updated'])}")
            for updated_file in changes['updated']:
                logger.info(f"  ~ {updated_file}")

            logger.info(f"Удаленных файлов: {len(changes['removed'])}")
            for removed_file in changes['removed']:
                logger.info(f"  - {removed_file}")

            logger.info("=== КОНЕЦ СРАВНЕНИЯ ===")

        return changes

    @staticmethod
    def _apply_updates(
        changes: Dict, 
        extracted_dir: Path, 
        base_path: Path,
        logger: logging.Logger
    ) -> None:
        """
        Применение обновлений к файлам проекта с детальным логированием
        """
        logger.info("=== НАЧАЛО ПРИМЕНЕНИЯ ОБНОВЛЕНИЙ ===")
        logger.info(f"Применяются изменения из папки:\n  {extracted_dir}\nв папку:\n  {base_path}")
        # Копирование новых файлов
        if changes['new']:
            logger.info(f"Добавление новых файлов ({len(changes['new'])}):")
            for rel_path in changes['new']:
                src = extracted_dir / rel_path
                dst = base_path / rel_path
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                logger.info(f"  + {rel_path}")
        
        # Копирование измененных файлов
        if changes['updated']:
            logger.info(f"Обновление измененных файлов ({len(changes['updated'])}):")
            for rel_path in changes['updated']:
                src = extracted_dir / rel_path
                dst = base_path / rel_path
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                logger.info(f"  ~ {rel_path}")
                
        # Удаление отсутствующих в новой версии файлов
        if changes['removed']:
            logger.info(f"Удаление файлов ({len(changes['removed'])}):")
            for rel_path in changes['removed']:
                target = base_path / rel_path
                if target.exists():
                    target.unlink()
                    logger.info(f"  - {rel_path}")
        
        message = (f"Применено обновлений: "
                f"+{len(changes['new'])} "
                f"~{len(changes['updated'])} "
                f"-{len(changes['removed'])}")
        
        logger.info(message)
        logger.info("=== ОБНОВЛЕНИЯ ПРИМЕНЕНЫ ===")

    @staticmethod
    def get_update_log(update_id: str) -> str:
        """
        Получение лога конкретного обновления
        """
        config = UpdatesModule.get_updates_config()
        log_file = Path(config['LOG_DIR']) / f"{update_id}.log"
        
        if not log_file.exists():
            return "Лог-файл не найден"
        
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            return f"Ошибка чтения лог-файла: {str(e)}"