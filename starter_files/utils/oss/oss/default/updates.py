from starter_files.utils.oss.base_module import BaseModule
import os
import shutil
import zipfile
import requests
import hashlib
import json
import sys
import subprocess
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Tuple, List, Optional

class UpdatesModule(BaseModule):
    """Полноценная реализация системы обновлений для всех ОС"""
    
    @classmethod
    def check(cls) -> bool:
        """Проверяет доступность всех необходимых инструментов"""
        try:
            import shutil
            tools = ['curl', 'unzip'] if sys.platform != 'win32' else ['powershell']
            return all(shutil.which(tool) for tool in tools)
        except Exception as e:
            logging.error(f"Ошибка проверки инструментов: {str(e)}")
            return False

    @staticmethod
    def start_updates_projects(projects_config: Dict) -> Tuple[str, Dict, Dict]:
        """Основная функция обновления проектов"""
        launch_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        projects_updates = {}
        projects_folders = {}

        for project_name, project_config in projects_config.items():
            try:
                logging.info(f"Начало обработки проекта: {project_name}")
                
                # Инициализация структур данных
                projects_updates[project_name] = {}
                projects_folders[project_name] = {
                    'EXTRACTED_DIR': UpdatesModule._get_path_dir(launch_timestamp, project_name, 'extracted'),
                    'BACKUPS_DIR': UpdatesModule._get_path_dir(launch_timestamp, project_name, 'backups'),
                    'BASE_PATH': Path(project_config['BASE_PATH'])
                }

                # Скачивание и распаковка
                projects_updates[project_name]['EXTRACTED_HASHES'] = UpdatesModule.download_and_extract(
                    url=project_config['DOWNLOAD_URL'],
                    extract_dir=projects_folders[project_name]['EXTRACTED_DIR']
                )

                # Проверка новой установки
                if 'CRITICAL_FILES' in project_config and UpdatesModule._is_new_installation(project_config):
                    logging.info(f"Новая установка проекта {project_name}")
                    shutil.copytree(
                        projects_folders[project_name]['EXTRACTED_DIR'],
                        projects_folders[project_name]['BASE_PATH'],
                        dirs_exist_ok=True
                    )
                    continue

                # Поиск изменений
                projects_updates[project_name]['CURRENT_HASHES'] = UpdatesModule._get_current_hashes(project_config)
                projects_updates[project_name]['CHANGES'] = UpdatesModule._find_changes(
                    projects_updates[project_name]['CURRENT_HASHES'],
                    projects_updates[project_name]['EXTRACTED_HASHES'],
                    project_config
                )

                if any(projects_updates[project_name]['CHANGES'].values()):
                    logging.info(f"Обнаружены изменения в проекте {project_name}")
                    UpdatesModule._create_backups(
                        project_name,
                        project_config,
                        projects_folders[project_name]['BACKUPS_DIR'],
                        projects_updates[project_name]
                    )
                    UpdatesModule._apply_updates(
                        projects_updates[project_name]['CHANGES'],
                        projects_folders[project_name]['EXTRACTED_DIR'],
                        project_config
                    )
                    UpdatesModule._handle_special_files(project_name, project_config, projects_updates, projects_folders)

                    if project_config.get('RESTART_AFTER_UPDATE', False):
                        UpdatesModule._restart_application()

            except Exception as e:
                logging.error(f"Ошибка обновления проекта {project_name}: {str(e)}")
                continue

        return launch_timestamp, projects_updates, projects_folders

    @staticmethod
    def download_and_extract(url: str, extract_dir: str) -> Dict[str, str]:
        """Скачивание и распаковка архива"""
        try:
            os.makedirs(extract_dir, exist_ok=True)
            archive_path = os.path.join(extract_dir, "temp.zip")
            
            # Скачивание
            with requests.get(url, stream=True) as r:
                r.raise_for_status()
                with open(archive_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)

            # Распаковка
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

            # Удаление временного архива
            os.remove(archive_path)

            # Сбор хешей
            file_hashes = {}
            for root, _, files in os.walk(extract_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, extract_dir)
                    with open(file_path, 'rb') as f:
                        file_hashes[relative_path] = hashlib.sha256(f.read()).hexdigest()

            return file_hashes

        except Exception as e:
            logging.error(f"Ошибка скачивания/распаковки: {str(e)}")
            if 'archive_path' in locals() and os.path.exists(archive_path):
                os.remove(archive_path)
            raise

    @staticmethod
    def _get_path_dir(launch_timestamp: str, project_name: str, dir_type: str) -> Path:
        """Генерирует путь к директории"""
        return Path(dir_type) / project_name / launch_timestamp

    @staticmethod
    def _get_current_hashes(project_config: Dict) -> Dict[str, str]:
        """Получает хеши текущих файлов"""
        base_path = Path(project_config['BASE_PATH'])
        current_hashes = {}
        
        for pattern in project_config['TARGETS']:
            for path in base_path.glob(pattern):
                if path.is_file() and not UpdatesModule._is_ignored(path, project_config):
                    with open(path, 'rb') as f:
                        current_hashes[str(path.relative_to(base_path))] = hashlib.sha256(f.read()).hexdigest()
        
        return current_hashes

    @staticmethod
    def _find_changes(old_hashes: Dict, new_hashes: Dict, config: Dict) -> Dict[str, List]:
        """Находит различия между версиями"""
        changes = {'new': [], 'updated': [], 'removed': []}
        
        for rel_path, new_hash in new_hashes.items():
            if UpdatesModule._is_target(rel_path, config) and not UpdatesModule._is_ignored(rel_path, config):
                old_hash = old_hashes.get(rel_path)
                if not old_hash:
                    changes['new'].append(rel_path)
                elif old_hash != new_hash:
                    changes['updated'].append(rel_path)

        for rel_path in old_hashes:
            if UpdatesModule._is_target(rel_path, config) and not UpdatesModule._is_ignored(rel_path, config):
                if rel_path not in new_hashes:
                    changes['removed'].append({'path': rel_path, 'reason': "Удален в новой версии"})

        return changes

    @staticmethod
    def _create_backups(project_name: str, config: Dict, backup_dir: Path, updates: Dict) -> None:
        """Создает резервные копии"""
        backup_dir.mkdir(parents=True, exist_ok=True)
        base_path = Path(config['BASE_PATH'])
        
        # Копирование файлов из TARGETS
        for rel_path in updates['CURRENT_HASHES']:
            src = base_path / rel_path
            if UpdatesModule._is_target(rel_path, config) and not UpdatesModule._is_ignored(rel_path, config):
                dst = backup_dir / rel_path
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)

        # Копирование ADD_IN_BACKUPS
        for pattern in config.get('ADD_IN_BACKUPS', []):
            for path in base_path.glob(pattern):
                if path.is_file():
                    rel_path = path.relative_to(base_path)
                    dst = backup_dir / rel_path
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(path, dst)
                elif path.is_dir():
                    for file_path in path.rglob('*'):
                        if file_path.is_file():
                            rel_path = file_path.relative_to(base_path)
                            dst = backup_dir / rel_path
                            dst.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(file_path, dst)

    @staticmethod
    def _apply_updates(changes: Dict, extracted_dir: Path, config: Dict) -> None:
        """Применяет обновления"""
        base_path = Path(config['BASE_PATH'])
        
        # Новые и измененные файлы
        for rel_path in changes['new'] + changes['updated']:
            src = extracted_dir / rel_path
            dst = base_path / rel_path
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

        # Удаленные файлы
        for entry in changes['removed']:
            target = base_path / entry['path']
            if target.exists():
                target.unlink()

    @staticmethod
    def _handle_special_files(project_name: str, config: Dict, updates: Dict, folders: Dict) -> None:
        """Обрабатывает файлы с особыми функциями"""
        if 'FUNCTIONS_IF_UPDATE' in config:
            for rel_path in updates[project_name]['CHANGES']['updated']:
                if rel_path in config['FUNCTIONS_IF_UPDATE']:
                    try:
                        module = __import__('starter_files.variables_functions', 
                                          fromlist=[config['FUNCTIONS_IF_UPDATE'][rel_path]])
                        func = getattr(module, config['FUNCTIONS_IF_UPDATE'][rel_path])
                        func(projects_updates=updates[project_name], projects_folders=folders[project_name])
                    except Exception as e:
                        logging.error(f"Ошибка обработки специального файла {rel_path}: {str(e)}")

    @staticmethod
    def _is_new_installation(config: Dict) -> bool:
        """Проверяет, является ли установка новой"""
        base_path = Path(config['BASE_PATH'])
        critical_files = config.get('CRITICAL_FILES', config['TARGETS'][:1])
        return not all((base_path / Path(f)).exists() for f in critical_files)

    @staticmethod
    def _is_target(rel_path: str, config: Dict) -> bool:
        """Проверяет, соответствует ли файл целевому шаблону"""
        path = Path(rel_path).as_posix()
        return any(path.match(p.replace('\\', '/')) for p in config['TARGETS'])

    @staticmethod
    def _is_ignored(rel_path: str, config: Dict) -> bool:
        """Проверяет, должен ли файл быть проигнорирован"""
        path = Path(config['BASE_PATH']) / rel_path
        return any(path.match(p) for p in config.get('IGNORED', []))

    @staticmethod
    def _restart_application() -> None:
        """Перезапускает приложение"""
        python = sys.executable
        subprocess.Popen([python] + sys.argv + ['--after-update'])
        sys.exit()