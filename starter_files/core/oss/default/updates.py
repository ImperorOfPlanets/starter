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

from starter_files.core.utils.globalVars_utils import get_global

class UpdatesModule:
    """
    Модуль для управления обновлениями проектов
    Все файлы хранятся в папке /starter_files/updates/
    """
    
    # Конфигурация путей
    DEFAULT_CONFIG = {
        'BASE_TEMP_DIR': 'starter_files/updates',
        'EXTRACTED_SUBDIR': 'extracted',
        'BACKUPS_SUBDIR': 'backups',
        'LOG_DIR': 'starter_files/logs/updates',
        'CLEANUP_DAYS': 7,
        'MAX_RETRIES': 3,
        'TIMEOUT': 30,
        'STATE_FILE': 'update_state.json',
        'MIN_CHECK_INTERVAL': 30,
        'HISTORY_FILE': 'update_history.json'
    }
    
    @staticmethod
    def get_updates_config() -> Dict:
        """
        Получение конфигурации с правильными путями
        """
        config = UpdatesModule.DEFAULT_CONFIG.copy()
        
        # Устанавливаем правильные пути
        script_path = get_global('script_path')
        base_dir = script_path / 'starter_files' / 'updates'
        logs_dir = script_path / 'starter_files' / 'logs' / 'updates'
        
        config['BASE_TEMP_DIR'] = str(base_dir)
        config['STATE_FILE'] = str(base_dir / 'update_state.json')
        config['HISTORY_FILE'] = str(base_dir / 'update_history.json')
        config['LOG_DIR'] = str(script_path / 'starter_files' / 'logs' / 'updates')
        
        # Создаем директории если не существуют
        base_dir.mkdir(parents=True, exist_ok=True)
        (base_dir / 'logs').mkdir(exist_ok=True)
        (base_dir / 'extracted').mkdir(exist_ok=True)
        (base_dir / 'backups').mkdir(exist_ok=True)
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        return config

    @staticmethod
    def start_updates_projects(
        projects_config: Dict,
        module_config: Dict = None,
        force_check: bool = False
    ) -> Tuple[str, Dict, Dict]:
        """
        Основной процесс обновления проектов
        """
        config = {**UpdatesModule.get_updates_config(), **(module_config or {})}
        
        # Инициализация логирования
        UpdatesModule._init_logging(config)
        
        # Создаем базовые каталоги
        base_temp_dir = Path(config['BASE_TEMP_DIR'])
        base_temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Метка времени для уникальных путей
        launch_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        update_id = f"update_{launch_timestamp}"
        
        # Начинаем запись в лог
        logger = UpdatesModule._init_update_logging(update_id, config)
        logger.info("=== Начало процесса обновления ===")
        logger.info(f"Время начала: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Обработка каждого проекта
        for project_name, project_config in projects_config.items():
            try:
                logger.info(f"Обработка проекта: {project_name}")
                
                # Проверка необходимости обновления
                last_update_seconds = UpdatesModule.seconds_since_last_update(project_name, config)
                
                if not force_check and not UpdatesModule.should_check_updates(project_name, config):
                    logger.info(f"Проверка пропущена: {project_name}")
                    continue
                    
                logger.info(f"Начало проверки: {project_name}")
                
                # Формирование путей для проекта
                project_paths = {
                    'EXTRACTED_DIR': base_temp_dir / config['EXTRACTED_SUBDIR'] / project_name / launch_timestamp,
                    'BACKUPS_DIR': base_temp_dir / config['BACKUPS_SUBDIR'] / project_name / launch_timestamp,
                    'BASE_PATH': Path(project_config['BASE_PATH'])
                }
                
                # Создание необходимых каталогов
                project_paths['EXTRACTED_DIR'].mkdir(parents=True, exist_ok=True)
                project_paths['BACKUPS_DIR'].mkdir(parents=True, exist_ok=True)

                # Скачивание и распаковка архива
                logger.info(f"Скачивание архива для проекта {project_name}")
                extracted_hashes = UpdatesModule._download_and_extract(
                    url=project_config['DOWNLOAD_URL'],
                    extract_dir=project_paths['EXTRACTED_DIR'],
                    config=config,
                    logger=logger
                )

                # Проверка новой установки
                if UpdatesModule._is_new_installation(project_config):
                    logger.info(f"Обнаружена новая установка: {project_name}")
                    shutil.copytree(
                        project_paths['EXTRACTED_DIR'],
                        project_paths['BASE_PATH'],
                        dirs_exist_ok=True
                    )
                    UpdatesModule._update_state_file(project_name, config)
                    continue

                # Получение текущих хешей
                logger.info(f"Вычисление хешей текущих файлов проекта {project_name}")
                current_hashes = UpdatesModule._get_current_hashes(project_config)
                
                # Поиск изменений
                logger.info(f"Поиск изменений в проекте {project_name}")
                changes = UpdatesModule._find_changes(
                    old_hashes=current_hashes,
                    new_hashes=extracted_hashes,
                    config=project_config
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
                    
                    # Обновляем состояние после успешного обновления
                    UpdatesModule._update_state_file(project_name, config)

            except Exception as e:
                logger.error(f"Ошибка обновления {project_name}: {str(e)}")
                continue

        # Очистка устаревших файлов
        UpdatesModule._cleanup_old_files(config)
        logger.info("=== Процесс обновления завершен ===")
        return launch_timestamp, {}, {}

    @staticmethod
    def _download_and_extract(
        url: str, 
        extract_dir: Path,
        config: Dict,
        logger: logging.Logger
    ) -> Dict[str, str]:
        """
        Скачивание и распаковка архива с проектом
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
            finally:
                if archive_path.exists():
                    archive_path.unlink()

        # Вычисление хешей распакованных файлов
        logger.info("Вычисление хешей файлов...")
        for root, _, files in os.walk(extract_dir):
            for file in files:
                file_path = Path(root) / file
                rel_path = file_path.relative_to(extract_dir)
                
                with open(file_path, 'rb') as f:
                    file_hash = hashlib.sha256(f.read()).hexdigest()
                    file_hashes[str(rel_path)] = file_hash
                    
        logger.info(f"Распаковано файлов: {len(file_hashes)}")
        return file_hashes

    @staticmethod
    def _get_current_hashes(project_config: Dict) -> Dict[str, str]:
        """
        Получение хешей текущих файлов проекта
        """
        base_path = Path(project_config['BASE_PATH'])
        current_hashes = {}
        
        for pattern in project_config['TARGETS']:
            for path in base_path.rglob(pattern):
                if path.is_file():
                    rel_path = path.relative_to(base_path)
                    with open(path, 'rb') as f:
                        current_hashes[str(rel_path)] = hashlib.sha256(f.read()).hexdigest()
        
        return current_hashes

    @staticmethod
    def _find_changes(old_hashes: Dict, new_hashes: Dict, config: Dict) -> Dict[str, List]:
        """
        Поиск изменений между версиями
        """
        changes = {'new': [], 'updated': [], 'removed': []}
        
        # Поиск новых и измененных файлов
        for rel_path, new_hash in new_hashes.items():
            old_hash = old_hashes.get(rel_path)
            if not old_hash:
                changes['new'].append(rel_path)
            elif old_hash != new_hash:
                changes['updated'].append(rel_path)
        
        # Поиск удаленных файлов
        for rel_path in old_hashes:
            if rel_path not in new_hashes:
                changes['removed'].append(rel_path)
                
        return changes

    @staticmethod
    def _create_backups(
        project_config: Dict, 
        backup_dir: Path, 
        current_hashes: Dict,
        logger: logging.Logger
    ) -> None:
        """
        Создание резервных копий изменяемых файлов
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
        
        logger.info(f"Резервные копии созданы: {len(current_hashes)} файлов")

    @staticmethod
    def _apply_updates(
        changes: Dict, 
        extracted_dir: Path, 
        base_path: Path,
        logger: logging.Logger
    ) -> None:
        """
        Применение обновлений к файлам проекта
        """
        # Копирование новых и измененных файлов
        for rel_path in changes['new'] + changes['updated']:
            src = extracted_dir / rel_path
            dst = base_path / rel_path
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            logger.info(f"Обновлен: {rel_path}")
            
        # Удаление отсутствующих в новой версии файлов
        for rel_path in changes['removed']:
            target = base_path / rel_path
            if target.exists():
                target.unlink()
                logger.info(f"Удален: {rel_path}")
        
        message = (f"Применено обновлений: "
                  f"+{len(changes['new'])} "
                  f"~{len(changes['updated'])} "
                  f"-{len(changes['removed'])}")
        logger.info(message)

    @staticmethod
    def _is_new_installation(config: Dict) -> bool:
        """
        Проверка новой установки проекта
        """
        base_path = Path(config['BASE_PATH'])
        return not base_path.exists()

    @staticmethod
    def _cleanup_old_files(config: Dict) -> None:
        """
        Очистка устаревших временных файлов
        """
        base_temp_dir = Path(config['BASE_TEMP_DIR'])
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
    def get_last_update_time(project_name: str, config: Dict) -> Optional[datetime]:
        """
        Получение времени последнего обновления проекта
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
        """
        last_update = UpdatesModule.get_last_update_time(project_name, config)
        if not last_update:
            return 0
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
    def _update_state_file(project_name: str, config: Dict) -> None:
        """
        Обновление файла состояния после успешной проверки
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
        
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)

    @staticmethod
    def _init_logging(config: Dict) -> None:
        """
        Инициализация системы логирования
        """
        log_dir = Path(config['LOG_DIR'])
        log_dir.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / 'updates.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )

    @staticmethod
    def _init_update_logging(update_id: str, config: Dict) -> logging.Logger:
        """
        Инициализация системы логирования для конкретного обновления
        """
        log_dir = Path(config['LOG_DIR'])
        log_dir.mkdir(parents=True, exist_ok=True)
        
        logger = logging.getLogger(f'updates_{update_id}')
        logger.setLevel(logging.INFO)
        
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        log_file = log_dir / f"{update_id}.log"
        fh = logging.FileHandler(log_file, encoding='utf-8')
        fh.setLevel(logging.INFO)
        fh.setFormatter(formatter)
        logger.addHandler(fh)
        
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.INFO)
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        
        return logger

    @staticmethod
    def get_update_log(update_id: str, config: Dict = None) -> str:
        """
        Получение лога конкретного обновления
        """
        if config is None:
            config = UpdatesModule.get_updates_config()
            
        log_file = Path(config['LOG_DIR']) / f"{update_id}.log"
        
        if not log_file.exists():
            return "Лог-файл не найден"
        
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            return f"Ошибка чтения лог-файла: {str(e)}"