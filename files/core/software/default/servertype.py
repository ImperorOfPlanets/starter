from files.core.base_module import BaseModule
import requests
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from files.configs.server_types import SERVER_TYPES
from files.core.utils.globalVars_utils import get_global
from files.core.utils.log_utils import LogManager

logger = LogManager.get_logger('server_type')

class ServertypeModule(BaseModule):
    """Менеджер для работы с типами серверов и их репозиториями"""
    
    @staticmethod
    def get_current_server_type() -> str:
        """Возвращает текущий тип сервера из .env"""
        script_path = get_global('script_path')
        env_file = script_path / '.env'
        
        if env_file.exists():
            with open(env_file, 'r') as f:
                for line in f:
                    if line.startswith('TYPE_SERVER='):
                        return line.strip().split('=', 1)[1].strip()
        return ''
    
    @staticmethod
    def set_server_type(server_type: str) -> bool:
        """Устанавливает тип сервера в .env"""
        if server_type not in SERVER_TYPES:
            logger.error(f"Unknown server type: {server_type}")
            return False
            
        script_path = get_global('script_path')
        env_file = script_path / '.env'
        
        # Читаем текущий .env
        lines = []
        type_found = False
        
        if env_file.exists():
            with open(env_file, 'r') as f:
                for line in f:
                    if line.startswith('TYPE_SERVER='):
                        lines.append(f'TYPE_SERVER={server_type}\n')
                        type_found = True
                    else:
                        lines.append(line)
        
        # Если не нашли, добавляем в конец
        if not type_found:
            lines.append(f'\n# Server Type\nTYPE_SERVER={server_type}\n')
        
        # Записываем обратно
        with open(env_file, 'w') as f:
            f.writelines(lines)
        
        logger.info(f"Server type set to: {server_type}")
        return True
    
    @staticmethod
    def get_available_repositories(server_type: str) -> List[Dict]:
        """Возвращает доступные репозитории для типа сервера"""
        if server_type not in SERVER_TYPES:
            return []
        return SERVER_TYPES[server_type].get('repositories', [])
    
    @staticmethod
    def test_repository_access(repo_url: str) -> Tuple[bool, str]:
        """Проверяет доступность репозитория"""
        try:
            # Для Git репозиториев
            if repo_url.endswith('.git'):
                # Пробуем получить информацию через Git
                import subprocess
                result = subprocess.run(
                    ['git', 'ls-remote', repo_url],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                return result.returncode == 0, result.stderr if result.returncode != 0 else "Repository accessible"
            
            # Для HTTP/HTTPS URL (архивы)
            response = requests.head(repo_url, timeout=10)
            return response.status_code == 200, f"HTTP {response.status_code}"
            
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def get_best_available_repository(server_type: str) -> Optional[Dict]:
        """Возвращает первый доступный репозиторий для типа сервера"""
        repositories = ServertypeModule.get_available_repositories(server_type)
        
        for repo in repositories:
            is_accessible, message = ServertypeModule.test_repository_access(repo['url'])
            if is_accessible:
                logger.info(f"Repository {repo['name']} is accessible: {message}")
                return repo
            else:
                logger.warning(f"Repository {repo['name']} not accessible: {message}")
        
        return None
    
    @staticmethod
    def get_server_paths() -> Dict[str, Path]:
        """Возвращает пути для папок code и docker текущего сервера"""
        script_path = get_global('script_path')
        server_type = ServertypeModule.get_current_server_type()
        
        if not server_type:
            return {}
        
        return {
            'code': script_path / 'code',
            'docker': script_path / 'docker',
            'type': server_type
        }
    
    @staticmethod
    def get_server_info() -> Dict:
        """Возвращает полную информацию о текущем сервере"""
        server_type = ServertypeModule.get_current_server_type()
        
        if not server_type or server_type not in SERVER_TYPES:
            return {
                'type': '',
                'name': 'Not configured',
                'description': 'Server type not configured',
                'configured': False
            }
        
        info = SERVER_TYPES[server_type].copy()
        info['type'] = server_type
        info['configured'] = True
        info['paths'] = ServertypeModule.get_server_paths()
        
        # Проверяем доступность репозиториев
        info['repositories_status'] = []
        for repo in info['repositories']:
            accessible, message = ServertypeModule.test_repository_access(repo['url'])
            info['repositories_status'].append({
                'name': repo['name'],
                'url': repo['url'],
                'accessible': accessible,
                'message': message
            })
        
        return info