# files/core/utils/registry_manager.py

import json
import os
import platform
from datetime import datetime
from pathlib import Path
from typing import Dict, List

class RegistryManager:
    @staticmethod
    def get_registry_path() -> Path:
        """Возвращает путь к файлу реестра в зависимости от ОС."""
        if platform.system() == "Windows":
            return Path(os.environ.get("PROGRAMDATA", "C:\\ProgramData")) / "starter-registry.json"
        else:
            return Path("/var/lib/starter-registry.json")

    @staticmethod
    def ensure_registry_dir():
        """Гарантирует существование директории для реестра."""
        registry_path = RegistryManager.get_registry_path()
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        if platform.system() != "Windows":
            os.chmod(registry_path.parent, 0o755)

    @staticmethod
    def load_registry() -> Dict:
        """Загружает реестр из файла или возвращает пустую структуру."""
        registry_path = RegistryManager.get_registry_path()
        if not registry_path.exists():
            return {"version": "1.0", "projects": []}
        try:
            with open(registry_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {"version": "1.0", "projects": []}

    @staticmethod
    def save_registry(data: Dict):
        """Сохраняет реестр в файл."""
        RegistryManager.ensure_registry_dir()
        registry_path = RegistryManager.get_registry_path()
        with open(registry_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @staticmethod
    def _normalize_path(path) -> str:
        """Нормализует путь к абсолютному и каноническому виду."""
        if not path:
            raise ValueError("Путь не может быть пустым")
        # Path() принимает str, Path, bytes — безопасно для любого входа
        return str(Path(path).resolve())

    @staticmethod
    def register_initializing(path: str):
        """Регистрирует проект как инициализирующийся (без октета)."""
        normalized_path = RegistryManager._normalize_path(path)
        registry = RegistryManager.load_registry()
        now = datetime.utcnow().isoformat() + "Z"

        for proj in registry["projects"]:
            if proj["path"] == normalized_path:
                proj.update({
                    "subnet_octet": 0,
                    "docker_network_prefix": "",
                    "port": 0,
                    "last_seen": now,
                    "status": "initializing"
                })
                RegistryManager.save_registry(registry)
                return

        registry["projects"].append({
            "path": normalized_path,
            "subnet_octet": 0,
            "docker_network_prefix": "",
            "port": 0,
            "last_seen": now,
            "status": "initializing"
        })
        RegistryManager.save_registry(registry)

    @staticmethod
    def register_project(path: str, subnet_octet: int, port: int):
        """Регистрирует или обновляет проект с реальными сетевыми параметрами."""
        normalized_path = RegistryManager._normalize_path(path)
        registry = RegistryManager.load_registry()
        now = datetime.utcnow().isoformat() + "Z"

        for proj in registry["projects"]:
            if proj["path"] == normalized_path:
                proj.update({
                    "subnet_octet": subnet_octet,
                    "docker_network_prefix": f"172.{subnet_octet}",
                    "port": port,
                    "last_seen": now,
                    "status": "active"
                })
                RegistryManager.save_registry(registry)
                return

        registry["projects"].append({
            "path": normalized_path,
            "subnet_octet": subnet_octet,
            "docker_network_prefix": f"172.{subnet_octet}",
            "port": port,
            "last_seen": now,
            "status": "active"
        })
        RegistryManager.save_registry(registry)

    @staticmethod
    def get_used_octets(exclude_path: str) -> List[int]:
        """
        Возвращает список реально занятых октетов (subnet_octet > 0),
        исключая проект по указанному пути.
        """
        normalized_exclude = RegistryManager._normalize_path(exclude_path)
        registry = RegistryManager.load_registry()
        used = set()

        for proj in registry["projects"]:
            if proj["path"] == normalized_exclude:
                continue  # Пропускаем текущий проект
            if proj["subnet_octet"] > 0:  # Игнорируем "initializing" (октет = 0)
                used.add(proj["subnet_octet"])

        return sorted(used)