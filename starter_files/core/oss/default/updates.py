import os
import shutil
import zipfile
import requests
import hashlib
import sys
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
    def get_update_history(project_name: Optional[str] = None) -> Dict:
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
    def update_project(project_name: str, project_config: Dict) -> Dict[str, Any]:
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

        need_restart = False
        changes_count = 0

        try:
            logger.info(f"Начало обновления проекта {project_name}")
            result = UpdatesModule._perform_update(project_name, project_config, logger)
            need_restart = result['need_restart']
            changes_count = result['changes_count']
            logger.info("Обновление завершено успешно")
        except Exception as e:
            logger.error(f"ОШИБКА при обновлении: {str(e)}", exc_info=True)

        logger.handlers.clear()
        
        return {
            'update_id': update_id,
            'need_restart': need_restart,
            'changes_count': changes_count
        }

    @staticmethod
    def _walk_files_with_ignore(base_path: Path, targets: List[str], ignored: List[str], logger: logging.Logger) -> List[Path]:
        """
        Обход папки base_path, выбирая файлы подходящие под паттерны targets,
        и исключая пути и папки которые подходят под patters в ignored.
        """

        ignored_norm = [pat.rstrip('/').replace('\\', '/') for pat in ignored]
        matched_files = []

        for root, dirs, files in os.walk(base_path):
            root_rel = Path(root).relative_to(base_path).as_posix() if root != str(base_path) else ''

            # Фильтрация папок из обхода по игнорируемым паттернам,
            # учитываем только директории в IGNORED (те что с ** или /**)
            new_dirs = []
            for d in dirs:
                dir_rel_path = os.path.join(root_rel, d).replace('\\', '/')
                ignore_dir = False
                for pat in ignored_norm:
                    if pat.endswith('**') or pat.endswith('/'):
                        if fnmatch(dir_rel_path + '/', pat):
                            ignore_dir = True
                            break
                if not ignore_dir:
                    new_dirs.append(d)
            dirs[:] = new_dirs

            for f in files:
                file_rel_path = os.path.join(root_rel, f).replace('\\', '/')

                # Проверка совпадения с TARGETS
                matched = any(fnmatch(file_rel_path, pattern) for pattern in targets)
                if not matched:
                    continue

                # Проверка на игнор
                ignored_file = False
                for pat in ignored_norm:
                    if fnmatch(file_rel_path, pat):
                        ignored_file = True
                        break
                if ignored_file:
                    continue

                matched_files.append(Path(root) / f)

        logger.info(f"Найдено файлов с учётом игнорирования: {len(matched_files)}")
        return matched_files

    @staticmethod
    def _perform_update(project_name: str, project_config: Dict, logger: logging.Logger) -> Dict[str, Any]:
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
            return {'need_restart': True, 'changes_count': -1}  # -1 означает новую установку

        current_hashes = UpdatesModule._get_current_hashes(project_name, project_config, logger)

        changes = UpdatesModule._find_changes(
            old_hashes=current_hashes,
            new_hashes=extracted_hashes,
            old_dir=project_base_path,
            new_dir=extracted_dir,
            logger=logger
        )

        changes_count = len(changes['new']) + len(changes['updated']) + len(changes['removed'])
        need_restart = changes_count > 0 and project_config.get('RESTART_AFTER_UPDATE', False)

        if changes_count > 0:
            logger.info(f"Обнаружены изменения: +{len(changes['new'])} ~{len(changes['updated'])} -{len(changes['removed'])}")

            ignored_patterns = project_config.get('IGNORED', [])
            def is_ignored(rel_path: str) -> bool:
                for ignore_pat in ignored_patterns:
                    if '**' in ignore_pat:
                        if fnmatch(rel_path, ignore_pat):
                            return True
                    else:
                        if rel_path == ignore_pat:
                            return True
                return False

            files_to_backup = [f for f in changes['updated'] + changes['removed'] if not is_ignored(f)]
            UpdatesModule._make_backup_files(project_base_path, backups_dir, files_to_backup, logger)

            UpdatesModule._apply_updates(changes, extracted_dir, project_base_path, logger)
            
            if need_restart:
                logger.info("Требуется перезапуск приложения после обновления")
        else:
            logger.info("Изменений не обнаружено")

        UpdatesModule._cleanup_old_files(config, logger)
        
        return {
            'need_restart': need_restart,
            'changes_count': changes_count
        }

    @staticmethod
    def _make_backup_files(base_path: Path, backup_dir: Path, files: List[str], logger: logging.Logger):
        logger.info(f"Создание резервных копий для {len(files)} файлов")
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
                    # УБИРАЕМ логирование каждого файла в архиве
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

        matched_files = UpdatesModule._walk_files_with_ignore(
                extract_dir,
                project_config.get('TARGETS', []),
                project_config.get('IGNORED', []),
                logger
            )

        file_hashes = {}
        for f in matched_files:
            rel_path_str = str(f.relative_to(extract_dir)).replace('\\', '/')
            file_hash = hashlib.sha256(f.read_bytes()).hexdigest()
            file_hashes[rel_path_str] = file_hash
        
        logger.info(f"Вычислено хешей новых файлов: {len(file_hashes)}")
        return file_hashes

    @staticmethod
    def _get_current_hashes(project_name: str, project_config: Dict, logger: logging.Logger) -> Dict[str, str]:
        base_path = Path(get_global(f"{project_name}_path"))
        logger.info(f"Вычисление хешей текущих файлов проекта в {base_path}")

        matched_files = UpdatesModule._walk_files_with_ignore(
            base_path,
            project_config.get('TARGETS', []),
            project_config.get('IGNORED', []),
            logger
        )

        file_hashes = {}
        for f in matched_files:
            rel_path_str = str(f.relative_to(base_path)).replace('\\', '/')
            file_hash = hashlib.sha256(f.read_bytes()).hexdigest()
            file_hashes[rel_path_str] = file_hash
        
        logger.info(f"Вычислено хешей текущих файлов: {len(file_hashes)}")
        return file_hashes

    @staticmethod
    def _find_changes(old_hashes: Dict[str, str], new_hashes: Dict[str, str], old_dir: Optional[Path] = None, new_dir: Optional[Path] = None, logger: Optional[logging.Logger] = None) -> Dict[str, List[str]]:
        changes = {'new': [], 'updated': [], 'removed': []}
        if logger:
            logger.info("=== СРАВНЕНИЕ ФАЙЛОВ ===")
            logger.info(f"Текущая версия: {old_dir}")
            logger.info(f"Новая версия: {new_dir}")
            logger.info(f"Файлов в текущей версии: {len(old_hashes)}")
            logger.info(f"Файлов в новой версии: {len(new_hashes)}")

        # Сравниваем файлы
        for rel_path, new_hash in new_hashes.items():
            old_hash = old_hashes.get(rel_path)
            if not old_hash:
                changes['new'].append(rel_path)
                if logger:
                    logger.info(f"НОВЫЙ: {rel_path}")
            elif old_hash != new_hash:
                changes['updated'].append(rel_path)
                if logger:
                    logger.info(f"ИЗМЕНЕН: {rel_path}")
                    logger.debug(f"  Старый хеш: {old_hash}")
                    logger.debug(f"  Новый хеш: {new_hash}")

        for rel_path, old_hash in old_hashes.items():
            if rel_path not in new_hashes:
                changes['removed'].append(rel_path)
                if logger:
                    logger.info(f"УДАЛЕН: {rel_path}")

        if logger:
            logger.info(f"ИТОГО: Новые: {len(changes['new'])}, Измененные: {len(changes['updated'])}, Удаленные: {len(changes['removed'])}")
            if not any(changes.values()):
                logger.info("ИЗМЕНЕНИЙ НЕТ")
            logger.info("=== ЗАВЕРШЕНО ===")
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
        logger.info(f"Очистка старых данных, оставляем 3 последние версии")
        
        for dir_type in [config['EXTRACTED_SUBDIR'], config['BACKUPS_SUBDIR']]:
            type_dir = base_temp_dir / dir_type
            if not type_dir.exists():
                continue
                
            for project_dir in type_dir.iterdir():
                if not project_dir.is_dir():
                    continue
                    
                # Получаем все версии и сортируем по дате (новые сначала)
                version_dirs = []
                for version_dir in project_dir.iterdir():
                    try:
                        dir_date = datetime.strptime(version_dir.name, '%Y%m%d_%H%M%S')
                        version_dirs.append((dir_date, version_dir))
                    except ValueError:
                        continue
                
                # Сортируем по дате (новые сначала)
                version_dirs.sort(key=lambda x: x[0], reverse=True)
                
                # Удаляем все, кроме 3 последних версий
                for dir_date, version_dir in version_dirs[3:]:
                    try:
                        shutil.rmtree(version_dir)
                        logger.info(f"Удалена устаревшая папка: {version_dir}")
                    except Exception as e:
                        logger.error(f"Ошибка удаления папки {version_dir}: {str(e)}")
        
        logger.info("Очистка завершена")

    @staticmethod
    def rollback_update(project_name: str, update_id: str) -> Dict[str, Any]:
        """
        Откатывает обновление до указанной версии
        """
        config = UpdatesModule.get_updates_config()
        backups_dir = Path(config['BASE_UPDATES_DIR']) / config['BACKUPS_SUBDIR'] / project_name / update_id
        
        if not backups_dir.exists():
            return {'status': 'error', 'message': 'Резервная копия для отката не найдена'}
        
        project_base_path = Path(get_global(f"{project_name}_path"))
        
        # Создаем логгер для отката
        log_dir = Path(config['LOG_DIR'])
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"rollback_{update_id}.log"
        
        logger = logging.getLogger(f'rollback_{update_id}')
        logger.setLevel(logging.INFO)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
        try:
            logger.info(f"Начало отката проекта {project_name} до версии {update_id}")
            
            # Восстанавливаем файлы из резервной копии
            for backup_file in backups_dir.rglob('*'):
                if backup_file.is_file():
                    rel_path = backup_file.relative_to(backups_dir)
                    target_path = project_base_path / rel_path
                    
                    # Создаем директорию, если нужно
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Копируем файл обратно
                    shutil.copy2(backup_file, target_path)
                    logger.info(f"Восстановлен файл: {rel_path}")
            
            logger.info("Откат завершен успешно")
            return {'status': 'success', 'message': 'Откат выполнен успешно'}
            
        except Exception as e:
            logger.error(f"Ошибка при откате: {str(e)}", exc_info=True)
            return {'status': 'error', 'message': f'Ошибка при откате: {str(e)}'}
        
        finally:
            logger.handlers.clear()

    @staticmethod
    def get_available_rollbacks(project_name: str) -> List[Dict[str, Any]]:
        """
        Возвращает список доступных версий для отката
        """
        config = UpdatesModule.get_updates_config()
        backups_dir = Path(config['BASE_UPDATES_DIR']) / config['BACKUPS_SUBDIR'] / project_name
        
        if not backups_dir.exists():
            return []
        
        available_versions = []
        
        for version_dir in backups_dir.iterdir():
            if version_dir.is_dir():
                try:
                    dir_date = datetime.strptime(version_dir.name, '%Y%m%d_%H%M%S')
                    available_versions.append({
                        'id': version_dir.name,
                        'timestamp': dir_date.isoformat(),
                        'date': dir_date.strftime('%Y-%m-%d %H:%M:%S')
                    })
                except ValueError:
                    continue
        
        # Сортируем по дате (новые сначала)
        available_versions.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return available_versions