"""
Модуль реестра проектов (ОС-независимый)
"""

import json
import os
import platform
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from files.core.base_module import BaseModule
from files.core.utils.globalVars_utils import get_global, set_global
from files.core.utils.log_utils import LogManager

logger = LogManager.get_logger('registry')


class RegistryModule(BaseModule):
    """Модуль управления реестром проектов"""
    
    @staticmethod
    def check() -> bool:
        return True
    
    @staticmethod
    def set_globals():
        """Устанавливает путь к реестру в зависимости от ОС"""
        if platform.system() == "Windows":
            registry_path = Path(os.environ.get("PROGRAMDATA", "C:\\ProgramData")) / "starter-registry.json"
        else:
            registry_path = Path("/var/lib/starter-registry.json")
        
        set_global('registry_path', registry_path)
        logger.info(f"Registry path: {registry_path}")
    
    @staticmethod
    def get_registry_path() -> Path:
        """Возвращает путь к файлу реестра"""
        registry_path = get_global('registry_path')
        if registry_path is None:
            RegistryModule.set_globals()
            registry_path = get_global('registry_path')
        return registry_path
    
    @staticmethod
    def ensure_registry_dir():
        """Гарантирует существование директории для реестра"""
        registry_path = RegistryModule.get_registry_path()
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        if platform.system() != "Windows":
            os.chmod(registry_path.parent, 0o755)
    
    @staticmethod
    def load_registry() -> Dict:
        """Загружает реестр из файла или возвращает пустую структуру"""
        registry_path = RegistryModule.get_registry_path()
        if not registry_path.exists():
            return {
                "version": "1.0", 
                "projects": [],
                "reverse_proxy": {
                    "enabled": False,
                    "started_at": None,
                    "network": "global_reverse_proxy_network",
                    "container_name": "global-nginx-proxy"
                }
            }
        try:
            with open(registry_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading registry: {e}")
            return {
                "version": "1.0", 
                "projects": [],
                "reverse_proxy": {
                    "enabled": False,
                    "started_at": None,
                    "network": "global_reverse_proxy_network",
                    "container_name": "global-nginx-proxy"
                }
            }
    
    @staticmethod
    def save_registry(data: Dict):
        """Сохраняет реестр в файл"""
        RegistryModule.ensure_registry_dir()
        registry_path = RegistryModule.get_registry_path()
        with open(registry_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    @staticmethod
    def _normalize_path(path) -> str:
        """Нормализует путь к абсолютному и каноническому виду"""
        if not path:
            raise ValueError("Путь не может быть пустым")
        return str(Path(path).resolve())
    
    @staticmethod
    def register_initializing(path: str):
        """Регистрирует проект как инициализирующийся (без октета)"""
        normalized_path = RegistryModule._normalize_path(path)
        registry = RegistryModule.load_registry()
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
                RegistryModule.save_registry(registry)
                return
        
        registry["projects"].append({
            "path": normalized_path,
            "subnet_octet": 0,
            "docker_network_prefix": "",
            "port": 0,
            "last_seen": now,
            "status": "initializing",
            "proxy_config": {
                "enabled": False,
                "mode": "auto",
                "domain": None
            }
        })
        RegistryModule.save_registry(registry)
    
    @staticmethod
    def register_project(path: str, subnet_octet: int, port: int, 
                        use_reverse_proxy: bool = False, 
                        domain: str = None,
                        proxy_mode: str = "auto",
                        project_type: str = "unknown"):
        """
        Регистрирует или обновляет проект с реальными сетевыми параметрами
        
        Args:
            path: Путь к проекту
            subnet_octet: Выделенный октет (0 если через reverse-proxy)
            port: Порт (80/443 для reverse-proxy, иначе уникальный)
            use_reverse_proxy: Использует ли проект reverse-proxy
            domain: Доменное имя проекта (для reverse-proxy)
            proxy_mode: Режим работы ("auto", "force", "disabled")
            project_type: Тип проекта (client, ai, vpn, monitoring, etc.)
        """
        normalized_path = RegistryModule._normalize_path(path)
        registry = RegistryModule.load_registry()
        now = datetime.utcnow().isoformat() + "Z"
        
        project_data = {
            "subnet_octet": subnet_octet,
            "docker_network_prefix": f"172.{subnet_octet}" if subnet_octet > 0 else "",
            "port": port,
            "last_seen": now,
            "status": "active",
            "project_type": project_type,
            "proxy_config": {
                "enabled": use_reverse_proxy,
                "mode": proxy_mode,
                "domain": domain,
                "registered_at": now
            }
        }
        
        for proj in registry["projects"]:
            if proj["path"] == normalized_path:
                proj.update(project_data)
                RegistryModule.save_registry(registry)
                logger.info(f"Updated project: {normalized_path} (reverse_proxy={use_reverse_proxy})")
                return
        
        project_data["path"] = normalized_path
        registry["projects"].append(project_data)
        RegistryModule.save_registry(registry)
        logger.info(f"Registered new project: {normalized_path} (reverse_proxy={use_reverse_proxy})")
    
    @staticmethod
    def get_used_octets(exclude_path: str) -> List[int]:
        """Возвращает список реально занятых октетов (subnet_octet > 0)"""
        normalized_exclude = RegistryModule._normalize_path(exclude_path)
        registry = RegistryModule.load_registry()
        used = set()
        
        for proj in registry["projects"]:
            if proj["path"] == normalized_exclude:
                continue
            # Только проекты с реальным октетом (не reverse-proxy)
            if proj.get("subnet_octet", 0) > 0:
                used.add(proj["subnet_octet"])
        
        return sorted(used)
    
    @staticmethod
    def get_proxy_projects() -> List[Dict]:
        """Возвращает все проекты, использующие reverse-proxy"""
        registry = RegistryModule.load_registry()
        proxy_projects = []
        
        for proj in registry["projects"]:
            proxy_config = proj.get("proxy_config", {})
            if proxy_config.get("enabled", False):
                # Добавляем информацию о проекте
                project_info = {
                    "path": proj["path"],
                    "name": Path(proj["path"]).name,
                    "project_type": proj.get("project_type", "unknown"),
                    "status": proj.get("status", "unknown"),
                    "last_seen": proj.get("last_seen"),
                    "subnet_octet": proj.get("subnet_octet", 0),
                    "port": proj.get("port", 0),
                    "proxy_config": proxy_config
                }
                proxy_projects.append(project_info)
        
        return proxy_projects
    
    @staticmethod
    def get_reverse_proxy_status() -> Dict:
        """Возвращает статус reverse-proxy и список проектов"""
        registry = RegistryModule.load_registry()
        proxy_projects = RegistryModule.get_proxy_projects()
        reverse_proxy_info = registry.get("reverse_proxy", {})
        
        return {
            "has_projects": len(proxy_projects) > 0,
            "projects_count": len(proxy_projects),
            "projects": proxy_projects,
            "global_enabled": reverse_proxy_info.get("enabled", False),
            "started_at": reverse_proxy_info.get("started_at"),
            "network": reverse_proxy_info.get("network", "global_reverse_proxy_network"),
            "container_name": reverse_proxy_info.get("container_name", "global-nginx-proxy"),
            "last_updated": datetime.utcnow().isoformat() + "Z"
        }
    
    @staticmethod
    def should_use_reverse_proxy(path: str, compose_analysis: Dict = None) -> bool:
        """
        Определяет, должен ли проект использовать reverse-proxy
        Приоритет: 1. Настройка в реестре > 2. FORCE_REVERSE_PROXY > 3. Анализ compose
        """
        normalized_path = RegistryModule._normalize_path(path)
        registry = RegistryModule.load_registry()
        
        # 1. Проверяем настройку в реестре
        for proj in registry["projects"]:
            if proj["path"] == normalized_path:
                if "proxy_config" in proj and "enabled" in proj["proxy_config"]:
                    return proj["proxy_config"]["enabled"]
                break
        
        # 2. Проверяем глобальную настройку FORCE_REVERSE_PROXY
        force_reverse = get_global('FORCE_REVERSE_PROXY')
        if force_reverse is not None:
            return force_reverse
        
        # 3. Анализируем docker-compose
        if compose_analysis:
            return compose_analysis.get('requires_reverse_proxy', False)
        
        return False
    
    @staticmethod
    def update_proxy_domain(path: str, domain: str) -> bool:
        """Обновляет домен для reverse-proxy"""
        normalized_path = RegistryModule._normalize_path(path)
        registry = RegistryModule.load_registry()
        
        for proj in registry["projects"]:
            if proj["path"] == normalized_path:
                if "proxy_config" not in proj:
                    proj["proxy_config"] = {}
                proj["proxy_config"]["domain"] = domain
                proj["proxy_config"]["updated_at"] = datetime.utcnow().isoformat() + "Z"
                RegistryModule.save_registry(registry)
                logger.info(f"Updated domain for {normalized_path} to {domain}")
                return True
        
        return False
    
    @staticmethod
    def set_reverse_proxy_global(enabled: bool, network: str = None, container_name: str = None) -> bool:
        """Устанавливает глобальный флаг reverse-proxy"""
        registry = RegistryModule.load_registry()
        
        if "reverse_proxy" not in registry:
            registry["reverse_proxy"] = {}
        
        registry["reverse_proxy"]["enabled"] = enabled
        if enabled:
            registry["reverse_proxy"]["started_at"] = datetime.utcnow().isoformat() + "Z"
        else:
            registry["reverse_proxy"]["stopped_at"] = datetime.utcnow().isoformat() + "Z"
        
        if network:
            registry["reverse_proxy"]["network"] = network
        if container_name:
            registry["reverse_proxy"]["container_name"] = container_name
        
        RegistryModule.save_registry(registry)
        logger.info(f"Global reverse-proxy flag set to {enabled}")
        return True
    
    @staticmethod
    def get_project_by_path(path: str) -> Optional[Dict]:
        """Возвращает проект по пути"""
        normalized_path = RegistryModule._normalize_path(path)
        registry = RegistryModule.load_registry()
        
        for proj in registry["projects"]:
            if proj["path"] == normalized_path:
                return proj
        
        return None
    
    @staticmethod
    def update_project_status(path: str, status: str) -> bool:
        """Обновляет статус проекта"""
        normalized_path = RegistryModule._normalize_path(path)
        registry = RegistryModule.load_registry()
        
        for proj in registry["projects"]:
            if proj["path"] == normalized_path:
                proj["status"] = status
                proj["last_seen"] = datetime.utcnow().isoformat() + "Z"
                RegistryModule.save_registry(registry)
                return True
        
        return False
    
    @staticmethod
    def remove_project(path: str) -> bool:
        """Удаляет проект из реестра"""
        normalized_path = RegistryModule._normalize_path(path)
        registry = RegistryModule.load_registry()
        
        original_length = len(registry["projects"])
        registry["projects"] = [p for p in registry["projects"] if p["path"] != normalized_path]
        
        if len(registry["projects"]) < original_length:
            RegistryModule.save_registry(registry)
            logger.info(f"Removed project {normalized_path} from registry")
            return True
        
        return False
    
    @staticmethod
    def get_all_projects() -> List[Dict]:
        """Возвращает все проекты в реестре"""
        registry = RegistryModule.load_registry()
        return registry.get("projects", [])
    
    @staticmethod
    def get_projects_count() -> int:
        """Возвращает количество проектов в реестре"""
        registry = RegistryModule.load_registry()
        return len(registry.get("projects", []))
    
    @staticmethod
    def cleanup_old_projects(max_age_days: int = 30):
        """Очищает старые проекты, не обновлявшиеся более max_age_days"""
        registry = RegistryModule.load_registry()
        now = datetime.utcnow()
        removed = 0
        
        for proj in registry["projects"][:]:  # Копия списка для безопасного удаления
            last_seen_str = proj.get("last_seen")
            if last_seen_str:
                try:
                    last_seen = datetime.fromisoformat(last_seen_str.replace('Z', '+00:00'))
                    age_days = (now - last_seen).days
                    
                    if age_days > max_age_days:
                        registry["projects"].remove(proj)
                        removed += 1
                        logger.info(f"Removed old project {proj['path']} (age: {age_days} days)")
                except Exception as e:
                    logger.warning(f"Error parsing date for {proj['path']}: {e}")
        
        if removed > 0:
            RegistryModule.save_registry(registry)
            logger.info(f"Cleaned up {removed} old projects")
        
        return removed