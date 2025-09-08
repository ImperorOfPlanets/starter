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
from typing import Dict, Any, List, Optional
from fnmatch import fnmatch

from starter_files.core.utils.globalVars_utils import get_global

class UpdatesModule:
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
    def get_updates_config() -> Dict[str, Any]:
        config = UpdatesModule.DEFAULT_CONFIG.copy()
        script_path = Path(get_global('script_path'))
        base_updates_dir = script_path / 'starter_files' / 'updates'
        logs_dir = script_path / 'starter_files' / 'logs' / 'updates'
        base_updates_dir.mkdir(parents=True, exist_ok=True)
        logs_dir.mkdir(parents=True, exist_ok=True)
        config['BASE_UPDATES_DIR'] = str(base_updates_dir)
        config['LOG_DIR'] = str(logs_dir)
        return config

    @staticmethod
    def get_update_history(project_name: str = None) -> Dict:
        config = UpdatesModule.get_updates_config()
        log_dir = Path(config['LOG_DIR'])
        history = []
        log_files = list(log_dir.glob("*.log")) if log_dir.exists() else []
        log_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        for log_file in log_files:
            filename = log_file.stem
            parts = filename.split('_')
            if len(parts) >= 3:
                log_project = parts[0]
                log_date = parts[1]
                log_time = parts[2]
                if project_name and project_name != 'all' and log_project != project_name:
                    continue
                try:
                    timestamp = datetime.strptime(f"{log_date}_{log_time}", "%Y%m%d_%H%M%S")
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
                    except Exception:
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
        history = UpdatesModule.get_update_history(project_name)["history"]
        if history:
            latest = max(history, key=lambda x: x["timestamp"])
            return datetime.fromisoformat(latest["timestamp"])
        return None

    @staticmethod
    def seconds_since_last_update(project_name: str, config: Dict) -> float:
        last_update = UpdatesModule.get_last_update_time(project_name, config)
        return (datetime.now() - last_update).total_seconds() if last_update else float('inf')

    @staticmethod
    def should_check_updates(project_name: str, config: Dict) -> bool:
        return UpdatesModule.seconds_since_last_update(project_name, config) >= config['MIN_CHECK_INTERVAL']

    @staticmethod
    def get_update_log(update_id: str) -> str:
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
    def update_project(project_name: str, project_config: Dict) -> str:
        config = UpdatesModule.get_updates_config()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        update_id = f"{project_name}_{timestamp}"

        log_dir = Path(config['LOG_DIR'])
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"{update_id}.log"

        logger = logging.getLogger(f'update_{update_id}')
        logger.setLevel(logging.DEBUG)
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)

        console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = logging.Formatter('%(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(logging.INFO)
        logger.addHandler(console_handler)

        try:
            logger.info(f"Начало обновления проекта {project_name}")
            UpdatesModule._perform_update(project_name, project_config, logger)
            logger.info("Обновление завершено успешно")
        except Exception as e:
            logger.error(f"ОШИБКА при обновлении: {str(e)}", exc_info=True)

        logger.handlers.clear()
        return update_id

    @staticmethod
    def _perform_update(project_name: str, project_config: Dict, logger: logging.Logger):
        config = UpdatesModule.get_updates_config()
        launch_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base_temp_dir = Path(config['BASE_UPDATES_DIR'])
        extracted_dir = base_temp_dir / config['EXTRACTED_SUBDIR'] / project_name / launch_timestamp
        backups_dir = base_temp_dir / config['BACKUPS_SUBDIR'] / project_name / launch_timestamp
        extracted_dir.mkdir(parents=True, exist_ok=True)
        backups_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Созданы временные директории: EXTRACTED_DIR={extracted_dir}, BACKUPS_DIR={backups_dir}")

        project_base_path = Path(get_global(f"{project_name}_path"))
        logger.info(f"Текущая папка проекта: {project_base_path}")
        logger.info(f"URL загрузки: {project_config['DOWNLOAD_URL']}")

        extracted_hashes = UpdatesModule._download_and_extract(
            url=project_config['DOWNLOAD_URL'],
            extract_dir=extracted_dir,
            config=config,
            project_config=project_config,
            logger=logger
        )

        if not project_base_path.exists():
            logger.info(f"Обнаружена новая установка: {project_name}")
            shutil.copytree(extracted_dir, project_base_path, dirs_exist_ok=True)
            return

        current_hashes = UpdatesModule._get_current_hashes(project_name, project_config, logger)

        changes = UpdatesModule._find_changes(
            old_hashes=current_hashes,
            new_hashes=extracted_hashes,
            old_dir=project_base_path,
            new_dir=extracted_dir,
            logger=logger
        )

        if changes['new'] or changes['updated'] or changes['removed']:
            logger.info(f"Обнаружены изменения: +{len(changes['new'])} ~{len(changes['updated'])} -{len(changes['removed'])}")

            # Создаем резервные копии всех файлов, которые будут заменены или удалены
            files_to_backup = changes['updated'] + changes['removed']
            UpdatesModule._make_backup_files(project_base_path, backups_dir, files_to_backup, logger)

            UpdatesModule._apply_updates(changes, extracted_dir, project_base_path, logger)
        else:
            logger.info("Изменений не обнаружено")

        UpdatesModule._cleanup_old_files(config, logger)

    @staticmethod
    def _make_backup_files(base_path: Path, backup_dir: Path, files: List[str], logger: logging.Logger):
        logger.info(f"Создание бэкапов для {len(files)} файлов")
        for rel_path in files:
            src = base_path / rel_path
            if src.exists():
                dst = backup_dir / rel_path
                dst.parent.mkdir(parents=True, exist_ok=True)
                try:
                    shutil.copy2(src, dst)
                    logger.debug(f"Создана резервная копия: {rel_path}")
                except Exception as e:
                    logger.error(f"Ошибка при создании бэкапа файла {rel_path}: {str(e)}")

    @staticmethod
    def _download_and_extract(url: str, extract_dir: Path, config: Dict, project_config: Dict, logger: logging.Logger) -> Dict[str, str]:
        archive_path = extract_dir / "temp.zip"
        for attempt in range(config['MAX_RETRIES']):
            try:
                logger.info(f"Скачивание архива (попытка {attempt + 1}): {url}")
                with requests.get(url, stream=True, timeout=config['TIMEOUT']) as response:
                    response.raise_for_status()
                    with open(archive_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                logger.info(f"Распаковка архива: {archive_path}")
                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                    for file_info in zip_ref.infolist():
                        logger.debug(f"  Файл архива: {file_info.filename}")
                    zip_ref.extractall(extract_dir)
                logger.info("Распаковка завершена успешно")
                break
            except Exception as e:
                logger.warning(f"Попытка {attempt + 1} не удалась: {str(e)}", exc_info=True)
                if attempt == config['MAX_RETRIES'] - 1:
                    raise
            finally:
                if archive_path.exists():
                    try:
                        archive_path.unlink()
                        logger.debug(f"Временный архив удалён: {archive_path}")
                    except Exception as e:
                        logger.error(f"Ошибка удаления временного архива: {str(e)}")

        file_hashes = {}
        matched_files = set()
        for pattern in project_config.get('TARGETS', []):
            logger.info(f"Поиск файлов по шаблону '{pattern}' в директории: {extract_dir}")
            if pattern.startswith('starter_files'):
                sub_dir = extract_dir / 'starter_files'
                matched = [p for p in sub_dir.rglob('*') if p.is_file()] if sub_dir.exists() else []
            else:
                matched = list(extract_dir.rglob(pattern))
            logger.info(f"Найдено по шаблону {pattern}: {len(matched)} файлов")
            matched_files.update(matched)

        ignored_patterns = project_config.get('IGNORED', [])

        def is_ignored(path: Path) -> bool:
            rel_path = str(path.relative_to(extract_dir)).replace(os.sep, '/')
            for ignore_pat in ignored_patterns:
                ignore_pat_norm = ignore_pat.replace(os.sep, '/')
                if fnmatch(rel_path, ignore_pat_norm):
                    return True
            return False

        filtered_files = [f for f in matched_files if not is_ignored(f)]
        logger.info(f"Файлов после фильтрации игнорируемых паттернов: {len(filtered_files)}")

        for f in filtered_files[:20]:
            logger.info(f"  - {f.relative_to(extract_dir)}")

        for f in filtered_files:
            file_hashes[str(f.relative_to(extract_dir))] = hashlib.sha256(f.read_bytes()).hexdigest()

        logger.info("=== Завершено вычисление хешей распакованных файлов ===")
        return file_hashes

    @staticmethod
    def _get_current_hashes(project_name: str, project_config: Dict, logger: logging.Logger) -> Dict[str, str]:
        base_path = Path(get_global(f"{project_name}_path"))
        logger.info(f"Вычисление хешей текущих файлов проекта в {base_path}")

        matched_files = set()
        file_hashes = {}

        for pattern in project_config.get('TARGETS', []):
            logger.info(f"Поиск файлов по шаблону '{pattern}' в директории: {base_path}")
            if pattern.startswith('starter_files'):
                sub_dir = base_path / 'starter_files'
                matched = [p for p in sub_dir.rglob('*') if p.is_file()] if sub_dir.exists() else []
            else:
                matched = list(base_path.rglob(pattern))
            logger.info(f"Найдено по шаблону {pattern}: {len(matched)} файлов")
            matched_files.update(matched)

        ignored_patterns = project_config.get('IGNORED', [])

        def is_ignored(path: Path) -> bool:
            rel_path = str(path.relative_to(base_path)).replace(os.sep, '/')
            for ignore_pat in ignored_patterns:
                ignore_pat_norm = ignore_pat.replace(os.sep, '/')
                if fnmatch(rel_path, ignore_pat_norm):
                    return True
            return False

        filtered_files = [f for f in matched_files if not is_ignored(f)]
        logger.info(f"Файлов после фильтрации игнорируемых паттернов: {len(filtered_files)}")

        for f in filtered_files[:20]:
            logger.info(f"  - {f.relative_to(base_path)}")

        for f in filtered_files:
            file_hashes[str(f.relative_to(base_path))] = hashlib.sha256(f.read_bytes()).hexdigest()

        logger.info("=== Завершено вычисление хешей текущих файлов ===")
        return file_hashes

    @staticmethod
    def _find_changes(old_hashes: Dict[str, str], new_hashes: Dict[str, str], old_dir: Optional[Path] = None, new_dir: Optional[Path] = None, logger: Optional[logging.Logger] = None) -> Dict[str, List[str]]:
        changes = {'new': [], 'updated': [], 'removed': []}
        if logger:
            logger.info("=== Сравнение хешей файлов ===")
            logger.info(f"Сравниваем папки:\n  Старая: {old_dir}\n  Новая: {new_dir}")
            logger.info(f"Файлов в текущей версии: {len(old_hashes)}")
            logger.info(f"Файлов в новой версии: {len(new_hashes)}")

        for rel_path, new_hash in new_hashes.items():
            old_hash = old_hashes.get(rel_path)
            if not old_hash:
                changes['new'].append(rel_path)
                if logger:
                    logger.info(f"Новый файл: {rel_path}")
            elif old_hash != new_hash:
                changes['updated'].append(rel_path)
                if logger:
                    logger.info(f"Изменён файл: {rel_path}")
                    logger.info(f"  Старый хеш: {old_hash}")
                    logger.info(f"  Новый хеш: {new_hash}")

        for rel_path, old_hash in old_hashes.items():
            if rel_path not in new_hashes:
                changes['removed'].append(rel_path)
                if logger:
                    logger.info(f"Удалён файл: {rel_path}")

        if logger:
            logger.info(f"Результаты сравнения: +{len(changes['new'])} ~{len(changes['updated'])} -{len(changes['removed'])}")
            logger.info("=== Конец сравнения ===")
        return changes

    @staticmethod
    def _apply_updates(changes: Dict[str, List[str]], extracted_dir: Path, base_path: Path, logger: logging.Logger) -> None:
        logger.info("=== Начало применения обновлений ===")
        logger.info(f"Копирование изменений из {extracted_dir} в {base_path}")

        for rel_path in changes['new']:
            try:
                src = extracted_dir / rel_path
                dst = base_path / rel_path
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                logger.info(f"Добавлен файл: {rel_path}")
            except Exception as e:
                logger.error(f"Ошибка добавления файла {rel_path}: {str(e)}")

        for rel_path in changes['updated']:
            try:
                src = extracted_dir / rel_path
                dst = base_path / rel_path
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                logger.info(f"Обновлён файл: {rel_path}")
            except Exception as e:
                logger.error(f"Ошибка обновления файла {rel_path}: {str(e)}")

        for rel_path in changes['removed']:
            try:
                target = base_path / rel_path
                if target.exists():
                    target.unlink()
                    logger.info(f"Удалён файл: {rel_path}")
            except Exception as e:
                logger.error(f"Ошибка удаления файла {rel_path}: {str(e)}")

        logger.info(f"Обновлений применено: +{len(changes['new'])} ~{len(changes['updated'])} -{len(changes['removed'])}")
        logger.info("=== Обновления применены ===")

    @staticmethod
    def _cleanup_old_files(config: Dict, logger: logging.Logger) -> None:
        base_temp_dir = Path(config['BASE_UPDATES_DIR'])
        cutoff_date = datetime.now() - timedelta(days=config['CLEANUP_DAYS'])
        logger.info(f"Очистка старых данных старше {config['CLEANUP_DAYS']} дней")
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
                            logger.info(f"Удалена устаревшая папка: {version_dir}")
                    except ValueError:
                        continue
        logger.info("Очистка завершена")
