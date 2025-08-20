from starter_files.core.oss.base_module import BaseModule
import subprocess
import logging
from pathlib import Path
from typing import Dict, List
from datetime import datetime, time
import re
from starter_files.core.oss.module_loader import get
from starter_files.core.utils.globalVars_utils import get_global, set_global

logger = logging.getLogger('git_oss')

class GitModule(BaseModule):
    """Реализация Git утилит для работы с закрытыми репозиториями"""

    @staticmethod
    def check_git_installed() -> bool:
        """Проверяет установлен ли Git и возвращает статус"""
        try:
            result = subprocess.run(
                ['git', '--version'],
                capture_output=True,
                text=True,
                check=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    @staticmethod
    def install_git(log_file_path: str) -> Dict[str, str]:
        """Устанавливает Git и записывает логи в указанный файл"""
        result = {'status': 'success', 'message': '', 'logs': []}
        
        try:
            log_dir = Path(log_file_path).parent
            log_dir.mkdir(parents=True, exist_ok=True)
            
            with open(log_file_path, 'w') as log_file:
                def log(message):
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    log_entry = f"[{timestamp}] {message}"
                    log_file.write(log_entry + '\n')
                    log_file.flush()
                    result['logs'].append(log_entry)
                    logger.info(log_entry)
                
                log("Starting Git installation...")

                commands = get("git", "return_commands_install_git")

                for cmd in commands:
                    log(f"Executing: {cmd}")
                    process = subprocess.Popen(
                        cmd,
                        shell=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        bufsize=1,
                        universal_newlines=True
                    )
                    
                    for line in iter(process.stdout.readline, ''):
                        if line:
                            log(line.strip())
                    
                    return_code = process.wait()
                    if return_code != 0:
                        log(f"Command failed with exit code {return_code}")
                        result['status'] = 'error'
                        result['message'] = f"Command failed: {cmd}"
                        return result
                
                time.sleep(2)
                if GitModule.check_git_installed():
                    log("Git installed successfully!")
                    result['message'] = "Git installed successfully!"
                else:
                    log("Installation completed but Git not detected.")
                    result['status'] = 'warning'
                    result['message'] = "Installation completed but Git not detected."
        
        except Exception as e:
            error_msg = f"Installation failed: {str(e)}"
            result['status'] = 'error'
            result['message'] = error_msg
            logger.exception("Git installation error")
        
        return result

    @staticmethod
    def check_git_authentication() -> bool:
        """Проверяет наличие настроенной аутентификации в Git"""
        try:
            # Проверка наличия сохраненных учетных данных
            result = subprocess.run(
                ['git', 'config', '--global', '--get', 'credential.helper'],
                capture_output=True,
                text=True,
                check=True
            )
            if result.stdout.strip():
                return True
        except subprocess.CalledProcessError:
            pass
        
        # Проверка существования SSH ключа
        ssh_path = Path.home() / '.ssh'
        if ssh_path.exists():
            for key_file in ssh_path.glob('id_*'):
                if not key_file.name.endswith('.pub'):
                    return True
        
        return False

    @staticmethod
    def authenticate_git(username: str, password: str) -> bool:
        """Настраивает аутентификацию в Git"""
        try:
            # Сохранение учетных данных в кэше
            subprocess.run(
                ['git', 'config', '--global', 'credential.helper', 'store'],
                check=True
            )
            
            # Запись учетных данных
            cred_file = Path.home() / '.git-credentials'
            with open(cred_file, 'a') as f:
                f.write(f"https://{username}:{password}@github.com\n")
            
            # Настройка пользователя
            subprocess.run(['git', 'config', '--global', 'user.name', username], check=True)
            subprocess.run(['git', 'config', '--global', 'user.email', f"{username}@users.noreply.github.com"], check=True)
            
            return True
        except Exception as e:
            logger.error(f"Git authentication failed: {str(e)}")
            return False

    @staticmethod
    def clone_repositories(repos: List[Dict], base_path: str) -> Dict[str, Dict]:
        """Клонирует список репозиториев в указанную директорию"""
        results = {}
        base_path = Path(base_path)
        
        for repo in repos:
            repo_url = repo['url']
            repo_name = re.search(r'/([^/]+)\.git$', repo_url).group(1)
            repo_path = base_path / repo_name
            
            try:
                if repo_path.exists():
                    results[repo_url] = {
                        'status': 'skipped',
                        'message': 'Repository already exists'
                    }
                    continue
                
                result = subprocess.run(
                    ['git', 'clone', repo_url, str(repo_path)],
                    capture_output=True,
                    text=True,
                    check=True
                )
                
                results[repo_url] = {
                    'status': 'success',
                    'message': result.stdout
                }
                
            except subprocess.CalledProcessError as e:
                results[repo_url] = {
                    'status': 'error',
                    'message': f"{e.stderr}\n{e.stdout}"
                }
            except Exception as e:
                results[repo_url] = {
                    'status': 'error',
                    'message': str(e)
                }
        
        return results

    @staticmethod
    def update_repositories(repos: List[str], base_path: str) -> Dict[str, Dict]:
        """Обновляет существующие репозитории"""
        results = {}
        base_path = Path(base_path)
        
        for repo_url in repos:
            repo_name = re.search(r'/([^/]+)\.git$', repo_url).group(1)
            repo_path = base_path / repo_name
            
            try:
                if not repo_path.exists():
                    results[repo_url] = {
                        'status': 'error',
                        'message': 'Repository not found'
                    }
                    continue
                
                # Fetch updates
                subprocess.run(
                    ['git', 'fetch', '--all'],
                    cwd=repo_path,
                    check=True,
                    capture_output=True
                )
                
                # Reset to latest
                result = subprocess.run(
                    ['git', 'reset', '--hard', 'origin/main'],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    check=True
                )
                
                results[repo_url] = {
                    'status': 'success',
                    'message': result.stdout
                }
                
            except subprocess.CalledProcessError as e:
                results[repo_url] = {
                    'status': 'error',
                    'message': f"{e.stderr}\n{e.stdout}"
                }
            except Exception as e:
                results[repo_url] = {
                    'status': 'error',
                    'message': str(e)
                }
        
        return results

    @staticmethod
    def set_globals():
        """Устанавливает глобальные переменные для Git"""
        git_installed = get('git','check_git_installed')
        # git_authentication = get('git','check_git_authentication')

        set_global('git_installed', git_installed)
        # set_global('git_authentication', git_authentication)