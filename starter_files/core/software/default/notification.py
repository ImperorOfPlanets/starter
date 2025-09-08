# starter_files/core/software/default/notification.py
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional
import requests
from email.message import EmailMessage
import smtplib
import socket
from urllib.parse import urlparse
import urllib3

from starter_files.core.utils.globalVars_utils import get_global  # если нужно
from starter_files.core.utils.log_utils import LogManager

logger = LogManager.get_logger("notification")

class NotificationModule:
    ENV_KEYS = ['SMTP_HOST', 'SMTP_PORT', 'SMTP_USER', 'SMTP_PASSWORD', 'SMTP_USE_TLS', 'SMTP_FROM_EMAIL']

    @staticmethod
    def _get_env_path() -> Path:
        """
        Возвращает путь к .env файлу (можно изменить при необходимости)
        """
        script_path = Path(get_global("script_path")) if 'get_global' in globals() else Path('.')
        return script_path / ".env"

    @staticmethod
    def read_env_file(env_path: Path) -> Dict[str, str]:
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
    def write_env_file(env_path: Path, vars_dict: Dict[str, str]):
        with open(env_path, 'w', encoding='utf-8') as f:
            for k, v in vars_dict.items():
                f.write(f"{k}={v}\n")

    @staticmethod
    def has_smtp_config(env_vars: Dict[str, str]) -> bool:
        return all(k in env_vars and env_vars[k] for k in NotificationModule.ENV_KEYS)

    @staticmethod
    def _is_server_available(host: str, port: int = 443, timeout: float = 2.0) -> bool:
        try:
            with socket.create_connection((host, port), timeout):
                return True
        except OSError:
            return False

    @staticmethod
    def fetch_smtp_config(core_url: str, project_id: str) -> Optional[Dict[str, str]]:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)  # Отключаем SSL предупреждения

        parsed_url = urlparse(core_url)
        host = parsed_url.hostname
        port = parsed_url.port or (443 if parsed_url.scheme == 'https' else 80)

        if not NotificationModule._is_server_available(host, port):
            logger.warning(f"Сервер {host}:{port} недоступен, пропуск запроса конфигурации")
            return None

        try:
            ip = requests.get('https://api.ipify.org', timeout=5).text
        except Exception:
            ip = '0.0.0.0'

        try:
            response = requests.post(
                core_url,
                json={'project_id': project_id, 'ip': ip},
                timeout=10,
                verify=False  # игнорируем SSL ошибки
            )
            response.raise_for_status()
            data = response.json()
            smtp = data.get('smtp')
            if smtp and all(k in smtp for k in NotificationModule.ENV_KEYS):
                logger.info("Получена SMTP конфигурация с core сервера")
                return smtp
            else:
                logger.warning("Ответ не содержит корректных SMTP данных")
        except Exception as e:
            logger.warning(f"Ошибка запроса SMTP конфигурации: {e}")
        return None

    @staticmethod
    def update_smtp_config(core_url: str, project_id: str):
        env_path = NotificationModule._get_env_path()
        env_vars = NotificationModule.read_env_file(env_path)

        if not NotificationModule.has_smtp_config(env_vars):
            smtp_conf = NotificationModule.fetch_smtp_config(core_url, project_id)
            if smtp_conf:
                env_vars.update(smtp_conf)
                NotificationModule.write_env_file(env_path, env_vars)

    @staticmethod
    def periodic_check(core_url: str, project_id: str, interval_sec: int = 600):
        while True:
            NotificationModule.update_smtp_config(core_url, project_id)
            time.sleep(interval_sec)

    @staticmethod
    def start_periodic_check(core_url: str, project_id: str, interval_sec: int = 600):
        thread = threading.Thread(
            target=NotificationModule.periodic_check,
            args=(core_url, project_id, interval_sec),
            daemon=True
        )
        thread.start()
        logger.info(f"Стартован периодический опрос core сервера каждые {interval_sec} секунд")

    @staticmethod
    def send_email(
        to_email: str,
        subject: str,
        body: str,
        attachments: Optional[List[str]] = None
    ) -> bool:
        env_path = NotificationModule._get_env_path()
        env_vars = NotificationModule.read_env_file(env_path)
        if not NotificationModule.has_smtp_config(env_vars):
            logger.error("SMTP конфигурация отсутствует, письмо не отправлено")
            return False

        msg = EmailMessage()
        msg['From'] = env_vars['SMTP_FROM_EMAIL']
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.set_content(body)

        if attachments:
            for filepath in attachments:
                path = Path(filepath)
                if path.exists():
                    with open(path, 'rb') as f:
                        data = f.read()
                    msg.add_attachment(data, maintype='application', subtype='octet-stream', filename=path.name)

        try:
            smtp_host = env_vars['SMTP_HOST']
            smtp_port = int(env_vars['SMTP_PORT'])
            use_tls = env_vars.get('SMTP_USE_TLS', 'true').lower() == 'true'
            smtp_user = env_vars.get('SMTP_USER')
            smtp_password = env_vars.get('SMTP_PASSWORD')

            with smtplib.SMTP(smtp_host, smtp_port) as smtp:
                if use_tls:
                    smtp.starttls()
                if smtp_user and smtp_password:
                    smtp.login(smtp_user, smtp_password)
                smtp.send_message(msg)

            logger.info(f"Письмо успешно отправлено на {to_email}")
            return True
        except Exception as e:
            logger.error(f"Ошибка отправки письма: {e}")
            return False
