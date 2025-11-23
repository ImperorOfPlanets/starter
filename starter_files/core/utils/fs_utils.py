import os
import shutil
import hashlib
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

class FSUtils:
    """Утилиты для работы с файловой системой"""

    @staticmethod
    def check_folders(folders_to_check: List[str]) -> None:
        """
        Проверяет наличие папок и создает их при необходимости.
        
        Args:
            folders_to_check: Список папок для проверки (относительно рабочей директории)
        """
        folders_to_check = [
            'docker', 'laravel'
        ]
        for folder in folders_to_check:
            path = Path(folder)
            if not path.exists():
                path.mkdir(parents=True)
                logger.info(f'Папка "{folder}" создана')
            else:
                logger.info(f'Папка "{folder}" уже существует')

    @staticmethod
    def validate_env_file(env_path: str, allowed_empty: List[str] = None) -> List[str]:
        """
        Проверяет .env файл на незаполненные переменные.
        
        Args:
            env_path: Путь к .env файлу
            allowed_empty: Список переменных, которые могут быть пустыми
            
        Returns:
            Список незаполненных переменных
        """
        if allowed_empty is None:
            allowed_empty = ['ENABLED_SERVICES']
            
        empty_vars = []
        env_pattern = re.compile(
            r'^\s*(?!#)(?P<key>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?P<value>\s*("")?(\'\')?[^#\n]*)(?=\n|$)',
            re.MULTILINE
        )

        with open(env_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
            for match in env_pattern.finditer(content):
                key = match.group('key')
                value = match.group('value').strip()
                
                if key not in allowed_empty:
                    is_empty = (
                        not value 
                        or value in ('""', "''", "' '", '" "')
                        or (len(value.strip('"\'')) == 0)
                    )
                    
                    if is_empty:
                        empty_vars.append(key)
                        
        return empty_vars

    @staticmethod
    def copy_environment_variables(env_example_path: str, env_path: str) -> None:
        """
        Копирует переменные из старого .env в новый .env.example.
        
        Args:
            env_example_path: Путь к новому .env.example
            env_path: Путь к текущему .env
        """
        # Чтение старых переменных
        old_vars = {}
        if Path(env_path).exists():
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if '=' in line and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        old_vars[key] = value

        # Копирование с сохранением старых значений
        if Path(env_example_path).exists():
            with open(env_example_path, 'r', encoding='utf-8') as f_in:
                with open(env_path, 'w', encoding='utf-8') as f_out:
                    for line in f_in:
                        if '=' in line and not line.startswith('#'):
                            key, _ = line.split('=', 1)
                            if key in old_vars:
                                line = f"{key}={old_vars[key]}\n"
                        f_out.write(line)

    @staticmethod
    def get_file_hash(file_path: str) -> str:
        """
        Вычисляет SHA-256 хеш файла.
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            Хеш-сумма файла в hex-формате
        """
        with open(file_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()

    @staticmethod
    def create_backup(source_dir: str, backup_dir: str, exclude: List[str] = None) -> None:
        """
        Создает резервную копию директории.
        
        Args:
            source_dir: Директория для бэкапа
            backup_dir: Целевая директория
            exclude: Список шаблонов для исключения
        """
        if exclude is None:
            exclude = []
            
        source = Path(source_dir)
        backup = Path(backup_dir)
        
        for item in source.glob('**/*'):
            if any(item.match(pattern) for pattern in exclude):
                continue
                
            if item.is_file():
                relative = item.relative_to(source)
                target = backup / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, target)

    @staticmethod
    def sync_dirs(source_dir: str, target_dir: str, patterns: List[str], ignore: List[str] = None) -> Dict:
        """
        Синхронизирует файлы между директориями по шаблонам.
        
        Args:
            source_dir: Источник
            target_dir: Цель
            patterns: Шаблоны файлов для включения
            ignore: Шаблоны файлов для исключения
            
        Returns:
            Словарь с информацией о синхронизированных файлах
        """
        if ignore is None:
            ignore = []
            
        changes = {'new': [], 'updated': [], 'removed': []}
        source = Path(source_dir)
        target = Path(target_dir)
        
        # Обработка новых/измененных файлов
        for pattern in patterns:
            for src_path in source.glob(pattern):
                if src_path.is_file():
                    rel_path = src_path.relative_to(source)
                    
                    if any(rel_path.match(ignore_pattern) for ignore_pattern in ignore):
                        continue
                        
                    dst_path = target / rel_path
                    dst_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    if not dst_path.exists():
                        changes['new'].append(str(rel_path))
                    elif FSUtils.get_file_hash(src_path) != FSUtils.get_file_hash(dst_path):
                        changes['updated'].append(str(rel_path))
                        
                    shutil.copy2(src_path, dst_path)
        
        return changes

    @staticmethod
    def create_shortcut(target: str, shortcut: str, args: str = "", workdir: str = "") -> None:
        """
        Создает ярлык в Windows.
        
        Args:
            target: Целевой файл
            shortcut: Путь к ярлыку
            args: Аргументы командной строки
            workdir: Рабочая директория
        """
        try:
            import winshell
            from win32com.client import Dispatch
            
            shell = Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(shortcut)
            shortcut.TargetPath = target
            shortcut.Arguments = args
            shortcut.WorkingDirectory = workdir
            shortcut.save()
        except ImportError:
            raise Exception("Для создания ярлыков требуется pywin32 и winshell")

    @staticmethod
    def get_ip_addresses() -> List[str]:
        """Возвращает список IP-адресов устройства"""
        import socket
        try:
            hostnames = socket.gethostbyname_ex(socket.gethostname())
            return hostnames[2]
        except Exception:
            return []

    @staticmethod
    def is_valid_network(ip_address: str) -> bool:
        """
        Проверяет, соответствует ли IP адресу диапазону '10.8.*'.
        
        Args:
            ip_address: IP-адрес для проверки
            
        Returns:
            bool: True если адрес валидный
        """
        import re
        return bool(re.match(r'^10\.8\.\d+\.\d+$', ip_address))