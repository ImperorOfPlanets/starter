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
from typing import Dict, List, Optional, Any

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
    def update_project(project_name: str, project_config: Dict[str, Any]) -> str:
        config = UpdatesModule.get_updates_config()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        update_id = f"{project_name}_{timestamp}"
        log_dir = Path(config['LOG_DIR'])
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"{update_id}.log"

        logger = logging.getLogger(f'update_{update_id}')
        logger.setLevel(logging.DEBUG)
        # Remove old handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        # File handler - detailed format with timestamp, level, module
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(module)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)

        # Console handler - simpler and cleaner format
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

        # Remove handlers after operation to avoid duplicate logs if called again
        logger.handlers.clear()
        return update_id

    @staticmethod
    def _perform_update(project_name: str, project_config: Dict[str, Any], logger: logging.Logger):
        config = UpdatesModule.get_updates_config()
        launch_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base_temp_dir = Path(config['BASE_UPDATES_DIR'])

        extracted_dir = base_temp_dir / config['EXTRACTED_SUBDIR'] / project_name / launch_timestamp
        backups_dir = base_temp_dir / config['BACKUPS_SUBDIR'] / project_name / launch_timestamp

        extracted_dir.mkdir(parents=True, exist_ok=True)
        backups_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Созданы директории: EXTRACTED_DIR={extracted_dir}, BACKUPS_DIR={backups_dir}")

        project_base_path = Path(get_global(f"{project_name}_path"))
        logger.info(f"Используется текущая папка проекта: {project_base_path}")
        logger.info(f"URL для загрузки: {project_config['DOWNLOAD_URL']}")

        # Скачиваем и распаковываем архив с фильтрацией
        extracted_hashes = UpdatesModule._download_and_extract(
            url=project_config['DOWNLOAD_URL'],
            extract_dir=extracted_dir,
            config=config,
            project_config=project_config,
            logger=logger
        )

        if not project_base_path.exists():
            logger.info(f"Обнаружена новая установка проекта {project_name}")
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
            logger.info(f"Найдены изменения: +{len(changes['new'])} ~{len(changes['updated'])} -{len(changes['removed'])}")
            UpdatesModule._create_backups(project_name, project_config, backups_dir, current_hashes, logger)
            UpdatesModule._apply_updates(changes, extracted_dir, project_base_path, logger)
        else:
            logger.info("Изменений не обнаружено")

        UpdatesModule._cleanup_old_files(config, logger)

    @staticmethod
    def _download_and_extract(url: str, extract_dir: Path, config: Dict[str, Any], project_config: Dict[str, Any], logger: logging.Logger) -> Dict[str, str]:
        archive_path = extract_dir / "temp.zip"
        file_hashes = {}

        for attempt in range(config['MAX_RETRIES']):
            try:
                logger.info(f"Скачивание архива (попытка {attempt + 1}): {url}")
                with requests.get(url, stream=True, timeout=config['TIMEOUT']) as response:
                    response.raise_for_status()
                    with open(archive_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                logger.info(f"Архив скачан: {archive_path} ({archive_path.stat().st_size} bytes)")

                logger.info(f"Распаковка архива: {archive_path}")
                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                    for file_info in zip_ref.infolist():
                        logger.debug(f"  Файл архива: {file_info.filename}")
                    zip_ref.extractall(extract_dir)
                logger.info("Распаковка завершена успешно")
                break  # Выход из цикла при успешной загрузке
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

        # Вычисляем хеши по фильтру TARGETS и IGNORED
        logger.info("Вычисление хешей распакованных файлов с учетом фильтров TARGETS и IGNORED")
        included_files = set()

        for pattern in project_config.get("TARGETS", []):
            try:
                matched = [p for p in extract_dir.rglob(pattern) if p.is_file()]
                logger.info(f"Шаблон TARGETS '{pattern}' нашёл {len(matched)} файлов")
                for f in matched:
                    logger.debug(f"  Включённый файл: {f.relative_to(extract_dir)}")
                included_files.update(matched)
            except Exception as e:
                logger.error(f"Ошибка при обработке TARGETS '{pattern}': {str(e)}")

        ignored_files = set()
        for pattern in project_config.get("IGNORED", []):
            try:
                matched = [p for p in extract_dir.rglob(pattern) if p.is_file()]
                logger.info(f"Шаблон IGNORED '{pattern}' нашёл {len(matched)} файлов")
                for f in matched:
                    logger.debug(f"  Игнорируемый файл: {f.relative_to(extract_dir)}")
                ignored_files.update(matched)
            except Exception as e:
                logger.error(f"Ошибка при обработке IGNORED '{pattern}': {str(e)}")

        final_files = included_files - ignored_files
        logger.info(f"Всего файлов после фильтрации: {len(final_files)}")

        for file_path in sorted(final_files):
            try:
                content = file_path.read_bytes()
                file_hash = hashlib.sha256(content).hexdigest()
                rel_path = str(file_path.relative_to(extract_dir))
                file_hashes[rel_path] = file_hash
                logger.debug(f"Вычислен хеш: {rel_path} → {file_hash}")
            except Exception as e:
                logger.error(f"Ошибка вычисления хеша для {file_path}: {str(e)}")

        logger.info("Завершено вычисление хешей распакованных файлов")
        return file_hashes

    @staticmethod
    def _get_current_hashes(project_name: str, project_config: Dict[str, Any], logger: logging.Logger) -> Dict[str, str]:
        base_path = Path(get_global(f"{project_name}_path"))
        logger.info(f"Вычисление хешей текущих файлов проекта в '{base_path}' с фильтрацией TARGETS и IGNORED")
        included_files = set()

        for pattern in project_config.get("TARGETS", []):
            try:
                matched = [p for p in base_path.rglob(pattern) if p.is_file()]
                logger.info(f"Шаблон TARGETS '{pattern}' нашёл {len(matched)} файлов")
                for f in matched:
                    logger.debug(f"  Включённый файл: {f.relative_to(base_path)}")
                included_files.update(matched)
            except Exception as e:
                logger.error(f"Ошибка при обработке TARGETS '{pattern}': {str(e)}")

        ignored_files = set()
        for pattern in project_config.get("IGNORED", []):
            try:
                matched = [p for p in base_path.rglob(pattern) if p.is_file()]
                logger.info(f"Шаблон IGNORED '{pattern}' нашёл {len(matched)} файлов")
                for f in matched:
                    logger.debug(f"  Игнорируемый файл: {f.relative_to(base_path)}")
                ignored_files.update(matched)
            except Exception as e:
                logger.error(f"Ошибка при обработке IGNORED '{pattern}': {str(e)}")

        final_files = included_files - ignored_files
        logger.info(f"Всего файлов после фильтрации: {len(final_files)}")

        hashes = {}
        for file_path in sorted(final_files):
            try:
                content = file_path.read_bytes()
                file_hash = hashlib.sha256(content).hexdigest()
                rel_path = str(file_path.relative_to(base_path))
                hashes[rel_path] = file_hash
                logger.debug(f"Вычислен хеш: {rel_path} → {file_hash}")
            except Exception as e:
                logger.error(f"Ошибка вычисления хеша для {file_path}: {str(e)}")

        logger.info("Завершено вычисление хешей текущих файлов")
        return hashes

    @staticmethod
    def _find_changes(old_hashes: Dict[str, str], new_hashes: Dict[str, str], old_dir: Optional[Path] = None, new_dir: Optional[Path] = None, logger: Optional[logging.Logger] = None) -> Dict[str, List[str]]:
        changes = {'new': [], 'updated': [], 'removed': []}
        if logger:
            logger.info("Сравнение файлов текущей и новой версий:")
            logger.info(f"Текущая папка: {old_dir}")
            logger.info(f"Новая папка: {new_dir}")
            logger.info(f"Количество файлов текущей версии: {len(old_hashes)}")
            logger.info(f"Количество файлов новой версии: {len(new_hashes)}")

        for rel_path, new_hash in new_hashes.items():
            old_hash = old_hashes.get(rel_path)
            if not old_hash:
                changes['new'].append(rel_path)
                if logger:
                    logger.info(f"НОВЫЙ файл: {rel_path}")
            elif old_hash != new_hash:
                changes['updated'].append(rel_path)
                if logger:
                    logger.info(f"ИЗМЕНЕН файл: {rel_path}")
                    logger.info(f"  Старый хеш: {old_hash}")
                    logger.info(f"  Новый хеш: {new_hash}")

        for rel_path in old_hashes:
            if rel_path not in new_hashes:
                changes['removed'].append(rel_path)
                if logger:
                    logger.info(f"УДАЛЁН файл: {rel_path}")

        if logger:
            logger.info(f"Итоги сравнения: +{len(changes['new'])} ~{len(changes['updated'])} -{len(changes['removed'])}")
        return changes

    @staticmethod
    def _create_backups(project_name: str, project_config: Dict[str, Any], backup_dir: Path, current_hashes: Dict[str, str], logger: logging.Logger):
        base_path = Path(get_global(f"{project_name}_path"))
        logger.info(f"Создание резервных копий проекта в {backup_dir}")
        copied = 0

        backup_dir.mkdir(parents=True, exist_ok=True)

        for rel_path in current_hashes:
            src = base_path / rel_path
            if src.exists():
                dst = backup_dir / rel_path
                dst.parent.mkdir(parents=True, exist_ok=True)
                try:
                    shutil.copy2(src, dst)
                    copied += 1
                    logger.debug(f"  Скопирован файл: {rel_path}")
                except Exception as e:
                    logger.error(f"Ошибка копирования файла {rel_path}: {str(e)}")

        logger.info(f"Скопировано файлов для бэкапа: {copied}")

    @staticmethod
    def _apply_updates(changes: Dict[str, List[str]], extracted_dir: Path, base_path: Path, logger: logging.Logger):
        logger.info("Начало применения обновлений")
        for rel_path in changes['new']:
            src = extracted_dir / rel_path
            dst = base_path / rel_path
            try:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                logger.info(f"Добавлен файл: {rel_path}")
            except Exception as e:
                logger.error(f"Ошибка добавления файла {rel_path}: {str(e)}")

        for rel_path in changes['updated']:
            src = extracted_dir / rel_path
            dst = base_path / rel_path
            try:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                logger.info(f"Обновлен файл: {rel_path}")
            except Exception as e:
                logger.error(f"Ошибка обновления файла {rel_path}: {str(e)}")

        for rel_path in changes['removed']:
            target = base_path / rel_path
            try:
                if target.exists():
                    target.unlink()
                    logger.info(f"Удален файл: {rel_path}")
            except Exception as e:
                logger.error(f"Ошибка удаления файла {rel_path}: {str(e)}")
        logger.info(f"Обновления применены: +{len(changes['new'])} ~{len(changes['updated'])} -{len(changes['removed'])}")

    @staticmethod
    def _cleanup_old_files(config: Dict[str, Any], logger: logging.Logger):
        base_temp_dir = Path(config['BASE_UPDATES_DIR'])
        cutoff_date = datetime.now() - timedelta(days=config['CLEANUP_DAYS'])
        logger.info(f"Очистка старых данных за период более {config['CLEANUP_DAYS']} дней")
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
        logger.info("Очистка старых данных завершена")

    @staticmethod
    def get_update_history(project_name: str = None) -> Dict[str, Any]:
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
        if last_update:
            return (datetime.now() - last_update).total_seconds()
        return float('inf')

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


