"""
Менеджер серверов: CRUD, сканирование путей, выделение ресурсов
"""

import json
import os
import platform
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from files.core.base_module import BaseModule
from files.core.utils.globalVars_utils import get_global, set_global
from files.core.utils.log_utils import LogManager

logger = LogManager.get_logger('servers')


class ServersModule(BaseModule):
    """Управление серверами: добавление, удаление, сканирование"""

    _servers_path: Optional[Path] = None

    @staticmethod
    def check() -> bool:
        return True

    @staticmethod
    def set_globals():
        starter_path = get_global('starter_path')
        if starter_path:
            ServersModule._servers_path = starter_path / 'servers.json'
            set_global('servers_path', ServersModule._servers_path)

    @staticmethod
    def _get_path() -> Path:
        if ServersModule._servers_path is None:
            ServersModule.set_globals()
        return ServersModule._servers_path

    @staticmethod
    def load() -> Dict:
        path = ServersModule._get_path()
        if not path.exists():
            return {"version": "2.0", "servers": []}
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading servers: {e}")
            return {"version": "2.0", "servers": []}

    @staticmethod
    def save(data: Dict):
        path = ServersModule._get_path()
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @staticmethod
    def scan_directory(project_path: str) -> Dict:
        """Сканирует директорию проекта, находит docker/ и code/"""
        p = Path(project_path)
        result = {
            "valid": False,
            "has_docker": False,
            "has_code": False,
            "docker_compose": None,
            "env_file": None,
            "starter_json": None,
            "name": p.name,
        }

        if not p.exists() or not p.is_dir():
            return result

        docker_dir = p / 'docker'
        code_dir = p / 'code'

        result["has_docker"] = docker_dir.exists() and docker_dir.is_dir()
        result["has_code"] = code_dir.exists() and code_dir.is_dir()

        if result["has_docker"]:
            compose = docker_dir / 'docker-compose.yml'
            if not compose.exists():
                compose = docker_dir / 'docker-compose.yaml'
            result["docker_compose"] = str(compose) if compose.exists() else None

        env_file = p / '.env'
        result["env_file"] = str(env_file) if env_file.exists() else None

        sj = p / 'starter.json'
        result["starter_json"] = str(sj) if sj.exists() else None

        result["valid"] = result["has_docker"] or result["has_code"]
        return result

    @staticmethod
    def add_server(project_path: str, name: str = None, user_id: str = None) -> Dict:
        """Добавляет сервер из указанного пути"""
        scan = ServersModule.scan_directory(project_path)
        if not scan["valid"]:
            return {"status": "error", "message": "Invalid directory: no docker/ or code/ found"}

        resolved = str(Path(project_path).resolve())
        data = ServersModule.load()

        for s in data["servers"]:
            if s["path"] == resolved:
                return {"status": "error", "message": "Server already registered"}

        server_id = str(uuid.uuid4())[:8]
        now = datetime.utcnow().isoformat() + "Z"

        server = {
            "id": server_id,
            "name": name or scan["name"],
            "path": resolved,
            "docker_path": str(Path(resolved) / 'docker'),
            "code_path": str(Path(resolved) / 'code'),
            "has_docker": scan["has_docker"],
            "has_code": scan["has_code"],
            "docker_compose": scan["docker_compose"],
            "env_file": scan["env_file"],
            "subnet_octet": 0,
            "base_port": 0,
            "status": "registered",
            "created_at": now,
            "updated_at": now,
            "created_by": user_id,
        }

        data["servers"].append(server)
        ServersModule.save(data)

        logger.info(f"Server added: {server_id} -> {resolved}")
        return {"status": "success", "server": server}

    @staticmethod
    def remove_server(server_id: str) -> Dict:
        data = ServersModule.load()
        original = len(data["servers"])
        data["servers"] = [s for s in data["servers"] if s["id"] != server_id]

        if len(data["servers"]) < original:
            ServersModule.save(data)
            logger.info(f"Server removed: {server_id}")
            return {"status": "success"}
        return {"status": "error", "message": "Server not found"}

    @staticmethod
    def switch_to_server(server_id: str) -> Dict:
        """Переключает глобальные пути на указанный сервер"""
        server = ServersModule.get_server(server_id)
        if not server:
            return {"status": "error", "message": "Server not found"}

        from pathlib import Path as P
        server_root = P(server['path'])
        docker_path = P(server.get('docker_path') or str(server_root / 'docker'))
        code_path = P(server.get('code_path') or str(server_root / 'code'))

        set_global('project_path', server_root)
        set_global('docker_path', docker_path)
        set_global('code_path', code_path)
        set_global('docker_compose_path', docker_path / 'docker-compose.yml')
        set_global('docker_compose_example_path', docker_path / 'docker-compose.example')
        set_global('docker_env_path', docker_path / '.env')
        set_global('docker_env_example_path', docker_path / '.env.example')
        set_global('active_server_id', server_id)

        logger.info(f"Switched to server: {server_id} ({server['name']}) -> {server_root}")
        return {"status": "success", "server": server}

    @staticmethod
    def get_server(server_id: str) -> Optional[Dict]:
        data = ServersModule.load()
        for s in data["servers"]:
            if s["id"] == server_id:
                return s
        return None

    @staticmethod
    def get_all() -> List[Dict]:
        data = ServersModule.load()
        return data.get("servers", [])

    @staticmethod
    def update_server(server_id: str, updates: Dict) -> Dict:
        data = ServersModule.load()
        for s in data["servers"]:
            if s["id"] == server_id:
                s.update(updates)
                s["updated_at"] = datetime.utcnow().isoformat() + "Z"
                ServersModule.save(data)
                return {"status": "success", "server": s}
        return {"status": "error", "message": "Server not found"}

    @staticmethod
    def set_resources(server_id: str, subnet_octet: int, base_port: int) -> Dict:
        """Устанавливает выделенные ресурсы для сервера"""
        return ServersModule.update_server(server_id, {
            "subnet_octet": subnet_octet,
            "base_port": base_port,
        })

    @staticmethod
    def get_used_octets() -> List[int]:
        """Список занятых октетов"""
        servers = ServersModule.get_all()
        return sorted([s["subnet_octet"] for s in servers if s.get("subnet_octet", 0) > 0])

    @staticmethod
    def get_used_ports() -> List[int]:
        """Список занятых базовых портов"""
        servers = ServersModule.get_all()
        return sorted([s["base_port"] for s in servers if s.get("base_port", 0) > 0])

    @staticmethod
    def next_octet() -> int:
        """Находит следующий свободный октет (10-250)"""
        used = ServersModule.get_used_octets()
        for octet in range(10, 251):
            if octet not in used:
                return octet
        raise RuntimeError("No free subnet octets available")

    @staticmethod
    def next_port(start: int = 3000) -> int:
        """Находит следующий свободный порт"""
        used = ServersModule.get_used_ports()
        port = start
        while port in used:
            port += 1
        return port
