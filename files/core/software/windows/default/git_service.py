"""
Модуль работы с git-сервисами (Windows — скрытие окон)
"""
import subprocess
import sys
import urllib.parse
from typing import Optional, Dict


def _si():
    if sys.platform != 'win32':
        return None
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = subprocess.SW_HIDE
    return si


class GitService:
    """Абстракция для работы с различными git-сервисами"""

    PROVIDERS = {
        'gitflic.ru': {
            'name': 'GitFlic',
            'clone_username': 'project',
            'token_url_format': 'https://{username}:{token}@{host}/{path}',
        },
        'github.com': {
            'name': 'GitHub',
            'clone_username': 'x-access-token',
            'token_url_format': 'https://{username}:{token}@{host}/{path}',
        },
        'gitlab.com': {
            'name': 'GitLab',
            'clone_username': 'oauth2',
            'token_url_format': 'https://{username}:{token}@{host}/{path}',
        },
        'gitflic.ru': {
            'name': 'GitFlic',
            'clone_username': 'project',
            'token_url_format': 'https://{username}:{token}@{host}/{path}',
        },
    }

    @staticmethod
    def detect_provider(url: str) -> Optional[Dict]:
        """Определяет git-провайдер по URL"""
        parsed = urllib.parse.urlparse(url)
        host = parsed.netloc.lower()
        for domain, config in GitService.PROVIDERS.items():
            if domain in host:
                return {**config, 'domain': domain}
        return None

    @staticmethod
    def get_auth_url(repo_url: str, token: str, auth_type: str = 'token') -> str:
        """Формирует URL с авторизацией"""
        parsed = urllib.parse.urlparse(repo_url)
        clean_path = parsed.path.strip('/')
        provider = GitService.detect_provider(repo_url)

        if auth_type == 'token' and token:
            username = provider['clone_username'] if provider else 'oauth2'
            return f"https://{username}:{token}@{parsed.netloc}/{clean_path}"
        elif auth_type == 'basic' and token:
            return f"https://{token}@{parsed.netloc}/{clean_path}"

        return repo_url

    @staticmethod
    def get_remote_commit(repo_url: str, branch: str = 'main',
                          token: str = '', auth_type: str = '') -> Optional[str]:
        """Получает последний commit hash из удалённого репозитория"""
        urls_to_try = [repo_url]
        if not repo_url.endswith('.git'):
            urls_to_try.append(repo_url + '.git')

        auth_urls = []
        for url in urls_to_try:
            if token and auth_type:
                auth_urls.append(GitService.get_auth_url(url, token, auth_type))
            auth_urls.append(url)

        for url in auth_urls:
            try:
                result = subprocess.run(
                    ['git', 'ls-remote', '--heads', url, f'refs/heads/{branch}'],
                    capture_output=True, text=True, timeout=15,
                    startupinfo=_si()
                )
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout.strip().split()[0]
            except subprocess.TimeoutExpired:
                pass
            except FileNotFoundError:
                pass
            except Exception:
                pass
        return None

    @staticmethod
    def get_local_commit(project_path: str) -> Optional[str]:
        """Получает последний commit hash из локального репозитория"""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                cwd=project_path,
                capture_output=True, text=True, timeout=5,
                startupinfo=_si()
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return None

    @staticmethod
    def set_remote_auth(remote_url: str, target_dir: str, token: str, auth_type: str = 'token') -> bool:
        """Устанавливает URL с авторизацией для remote origin"""
        auth_url = GitService.get_auth_url(remote_url, token, auth_type)
        try:
            result = subprocess.run(
                ['git', 'remote', 'set-url', 'origin', auth_url],
                cwd=target_dir,
                capture_output=True, text=True, timeout=10,
                startupinfo=_si()
            )
            return result.returncode == 0
        except Exception:
            return False

    @staticmethod
    def pull(target_dir: str, token: str = '', auth_type: str = '') -> Dict:
        """Выполняет git pull с опциональной авторизацией"""
        if token and auth_type:
            GitService.set_remote_auth('', target_dir, token, auth_type)
        try:
            result = subprocess.run(
                ['git', 'pull'],
                cwd=target_dir,
                capture_output=True, text=True, timeout=30,
                startupinfo=_si()
            )
            return {
                'success': result.returncode == 0,
                'output': result.stdout.strip(),
                'error': result.stderr.strip()
            }
        except subprocess.TimeoutExpired:
            return {'success': False, 'error': 'Timeout'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @staticmethod
    def has_updates(repo_url: str, branch: str, local_path: str,
                    token: str = '', auth_type: str = '') -> Dict:
        """Проверяет наличие обновлений"""
        remote = GitService.get_remote_commit(repo_url, branch, token, auth_type)
        local = GitService.get_local_commit(local_path)
        return {
            'has_update': bool(remote and local and remote != local),
            'remote_commit': remote[:12] if remote else None,
            'local_commit': local[:12] if local else None,
        }
