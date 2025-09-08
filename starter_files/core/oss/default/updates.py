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
        config['LOG_DIR'] = str(logs_dir)
        
        # Создаем директории если не существуют
        base_dir.mkdir(parents=True, exist_ok=True)
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        return config

    @staticmethod
    def get_update_history(project_name: str = None) -> Dict:
        """
        Получение истории обновлений для проекта или всех проектов
        """
        config = UpdatesModule.get_updates_config()
        history_file = Path(config['HISTORY_FILE'])
        
        if not history_file.exists():
            return {"history": []}

        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
            
            if project_name and project_name != 'all':
                project_history = [item for item in history if item.get('project') == project_name]
                return {"history": project_history}
            else:
                return {"history": history}
                
        except Exception as e:
            return {"error": str(e), "history": []}

    @staticmethod
    def update_project(project_name: str, project_config: Dict) -> Dict:
        """
        Обновление конкретного проекта
        """
        config = UpdatesModule.get_updates_config()
        update_id = str(uuid.uuid4())
        
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
            timestamp, _, _ = UpdatesModule.start_updates_projects(
                {project_name: project_config},
                force_check=True
            )
            
            # Добавляем запись в историю
            UpdatesModule._add_to_history(project_name, timestamp, "completed", config)
            
            logger.info("Обновление завершено успешно")
            return {
                "success": True,
                "update_id": update_id,
                "project": project_name,
                "message": "Обновление завершено успешно"
            }
            
        except Exception as e:
            logger.error(f"Ошибка при обновлении: {str(e)}")
            # Добавляем запись об ошибке в историю
            UpdatesModule._add_to_history(project_name, update_id, f"error: {str(e)}", config)
            return {
                "success": False,
                "update_id": update_id,
                "project": project_name,
                "message": str(e)
            }

    @staticmethod
    def _add_to_history(project_name: str, update_id: str, status: str, config: Dict):
        """
        Добавление записи в историю обновлений
        """
        history_file = Path(config['HISTORY_FILE'])
        history = []
        
        if history_file.exists():
            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            except:
                pass
        
        history.append({
            "project": project_name,
            "update_id": update_id,
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "log_file": f"{update_id}.log"
        })
        
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)

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
                logger.warning(f"Попытка {attempt+1} не удалась: {str(e)}")
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
    def _create_backups(
        project_config: Dict, 
        backup_dir: Path, 
        current_hashes: Dict,
        logger: logging.Logger
    ) -> None:
        """
        Создание резервных копии изменяемых файлов
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
            with open(state_file, 'r', encoding='utf-8') as f:
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
                with open(state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
            except:
                pass
        
        project_state = state.get(project_name, {})
        project_state['last_update'] = datetime.now().isoformat()
        state[project_name] = project_state
        
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)

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
                logging.FileHandler(log_dir / 'updates.log', encoding='utf-8'),
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

    @staticmethod
    def start_updates_projects(
        projects_config: Dict,
        module_config: Dict = None,
        force_check: bool = False,
        custom_logger: logging.Logger = None  # Добавляем параметр для кастомного логгера
    ) -> Tuple[str, Dict, Dict]:
        """
        Основной процесс обновления проектов
        """
        config = {**UpdatesModule.get_updates_config(), **(module_config or {})}
        
        # Используем кастомный логгер или инициализируем стандартный
        if custom_logger:
            logger = custom_logger
        else:
            # Метка времени для уникальных путей
            launch_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            update_id = f"update_{launch_timestamp}"
            logger = UpdatesModule._init_update_logging(update_id, config)
        
        logger.info("=== Начало процесса обновления ===")
        logger.info(f"Время начала: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        base_temp_dir = Path(config['BASE_TEMP_DIR'])
        base_temp_dir.mkdir(parents=True, exist_ok=True)

        # Обработка каждого проекта
        for project_name, project_config in projects_config.items():
            try:
                logger.info(f"Обработка проекта: {project_name}")
                logger.info(f"Базовая директория: {project_config['BASE_PATH']}")
                
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
                if UpdatesModule._is_new_installation(project_config):
                    logger.info(f"Обнаружена новая установка: {project_name}")
                    logger.info(f"Копирование файлов в: {project_paths['BASE_PATH']}")
                    shutil.copytree(
                        project_paths['EXTRACTED_DIR'],
                        project_paths['BASE_PATH'],
                        dirs_exist_ok=True
                    )
                    UpdatesModule._update_state_file(project_name, config)
                    continue

                # Получение текущих хешей
                logger.info(f"Вычисление хешей текущих файлов проекта {project_name}")
                current_hashes = UpdatesModule._get_current_hashes(project_config, logger)
                
                # Поиск изменений
                logger.info(f"Поиск изменений в проекте {project_name}")
                changes = UpdatesModule._find_changes(
                    old_hashes=current_hashes,
                    new_hashes=extracted_hashes,
                    config=project_config,
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
    def _get_current_hashes(project_config: Dict, logger: logging.Logger = None) -> Dict[str, str]:
        """
        Получение хешей текущих файлов проекта с логированием
        """
        base_path = Path(project_config['BASE_PATH'])
        current_hashes = {}
        
        for pattern in project_config['TARGETS']:
            if logger:
                logger.info(f"Поиск файлов по шаблону: {pattern}")
            
            for path in base_path.rglob(pattern):
                if path.is_file():
                    rel_path = path.relative_to(base_path)
                    with open(path, 'rb') as f:
                        current_hashes[str(rel_path)] = hashlib.sha256(f.read()).hexdigest()
                    
                    if logger:
                        logger.debug(f"Вычислен хеш для: {path}")
        
        if logger:
            logger.info(f"Найдено файлов: {len(current_hashes)}")
        
        return current_hashes

    @staticmethod
    def _find_changes(old_hashes: Dict, new_hashes: Dict, config: Dict, logger: logging.Logger = None) -> Dict[str, List]:
        """
        Поиск изменений между версиями с логированием
        """
        changes = {'new': [], 'updated': [], 'removed': []}
        
        # Поиск новых и измененных файлов
        for rel_path, new_hash in new_hashes.items():
            old_hash = old_hashes.get(rel_path)
            if not old_hash:
                changes['new'].append(rel_path)
                if logger:
                    logger.info(f"Новый файл: {rel_path}")
            elif old_hash != new_hash:
                changes['updated'].append(rel_path)
                if logger:
                    logger.info(f"Изменен файл: {rel_path}")
        
        # Поиск удаленных файлов
        for rel_path in old_hashes:
            if rel_path not in new_hashes:
                changes['removed'].append(rel_path)
                if logger:
                    logger.info(f"Удален файл: {rel_path}")
        
        if logger:
            logger.info(f"Обнаружено изменений: +{len(changes['new'])}, ~{len(changes['updated'])}, -{len(changes['removed'])}")
                
        return changes

    @staticmethod
    def _apply_updates(
        changes: Dict, 
        extracted_dir: Path, 
        base_path: Path,
        logger: logging.Logger = None
    ) -> None:
        """
        Применение обновлений к файлам проекта с логированием
        """
        # Копирование новых и измененных файлов
        for rel_path in changes['new'] + changes['updated']:
            src = extracted_dir / rel_path
            dst = base_path / rel_path
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            
            if logger:
                logger.info(f"Скопирован: {src} -> {dst}")
                
        # Удаление отсутствующих в новой версии файлов
        for rel_path in changes['removed']:
            target = base_path / rel_path
            if target.exists():
                target.unlink()
                if logger:
                    logger.info(f"Удален: {target}")
        
        message = (f"Применено обновлений: "
                f"+{len(changes['new'])} "
                f"~{len(changes['updated'])} "
                f"-{len(changes['removed'])}")
        
        if logger:
            logger.info(message)