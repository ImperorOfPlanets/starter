from starter_files.core.utils.globalVars_utils import set_global, get_global
from pathlib import Path
import requests
import socket
from urllib.parse import urlparse
import urllib3
import logging

logger = logging.getLogger("notification")


class NotificationModule:

    ENV_KEYS = ['SMTP_HOST', 'SMTP_PORT', 'SMTP_USER', 'SMTP_PASSWORD', 'SMTP_USE_TLS', 'SMTP_FROM_EMAIL']

    @staticmethod
    def _get_env_path() -> Path:
        script_path = Path(get_global("script_path")) if 'get_global' in globals() else Path('.')
        return script_path / ".env"

    @staticmethod
    def read_env_file(env_path: Path) -> dict:
        if not env_path.exists():
            return {}
        with open(env_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        vars_dict = {}
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, val = line.split('=', 1)
                vars_dict[key.strip()] = val.strip()
        return vars_dict

    @staticmethod
    def write_env_file(env_path: Path, vars_dict: dict):
        with open(env_path, 'w', encoding='utf-8') as f:
            for k, v in vars_dict.items():
                f.write(f"{k}={v}\n")

    @staticmethod
    def has_smtp_config(env_vars: dict) -> bool:
        return all(k in env_vars and env_vars[k] for k in NotificationModule.ENV_KEYS)

    @staticmethod
    def _is_server_available(host: str, port: int = 443, timeout: float = 2.0) -> bool:
        try:
            with socket.create_connection((host, port), timeout):
                return True
        except OSError:
            return False

    @staticmethod
    def fetch_smtp_config(core_url: str, project_id: str) -> dict:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        parsed_url = urlparse(core_url)
        host = parsed_url.hostname
        port = parsed_url.port or (443 if parsed_url.scheme == 'https' else 80)

        if not NotificationModule._is_server_available(host, port):
            logger.warning(f"Server {host}:{port} is unreachable, skipping config fetch")
            return {}

        try:
            ip = requests.get('https://api.ipify.org', timeout=5).text
        except Exception:
            ip = '0.0.0.0'

        try:
            response = requests.post(core_url, json={'project_id': project_id, 'ip': ip}, timeout=10, verify=False)
            response.raise_for_status()
            data = response.json()
            smtp = data.get('smtp', {})
            if all(k in smtp for k in NotificationModule.ENV_KEYS):
                logger.info("SMTP configuration fetched from core server")
                return smtp
            else:
                logger.warning("Response lacks full SMTP configuration")
        except Exception as e:
            logger.warning(f"Error fetching SMTP configuration: {e}")
        return {}

    @staticmethod
    def set_globals():
        env_path = NotificationModule._get_env_path()
        env_vars = NotificationModule.read_env_file(env_path)

        # Устанавливаем PROJECT_ID и CORE_SERVER_URL из env, если есть в env
        project_id = env_vars.get('PROJECT_ID') or ''
        core_url = env_vars.get('CORE_SERVER_URL') or ''

        # Сохраняем их в глобальные переменные (пользовательский код на это может опираться)
        set_global('PROJECT_ID', project_id)
        set_global('CORE_SERVER_URL', core_url)

        if not NotificationModule.has_smtp_config(env_vars) and project_id and core_url:
            # Если SMTP конфиг отсутствует, пытаемся получить с сервера CORE
            smtp_conf = NotificationModule.fetch_smtp_config(core_url, project_id)
            if smtp_conf:
                env_vars.update(smtp_conf)
                NotificationModule.write_env_file(env_path, env_vars)
                for key in NotificationModule.ENV_KEYS:
                    set_global(key, smtp_conf.get(key))
                set_global('SMTP_CONFIG_AVAILABLE', True)
                logger.info("Global variables set from SMTP config fetched from core server")
                return
            else:
                logger.warning("SMTP config missing and could not be fetched")
                for key in NotificationModule.ENV_KEYS:
                    set_global(key, None)
                set_global('SMTP_CONFIG_AVAILABLE', False)
                return
        else:
            # Если конфиг уже есть в env
            for key in NotificationModule.ENV_KEYS:
                set_global(key, env_vars.get(key))
            set_global('SMTP_CONFIG_AVAILABLE', True)
            logger.info("Global variables set from existing .env SMTP config")
