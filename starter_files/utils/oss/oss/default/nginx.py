import logging
from pathlib import Path

from starter_files.utils.oss.base_module import BaseModule

class NginxModule(BaseModule):
    """Базовая реализация работы с Nginx для всех ОС"""
    
    @classmethod
    def check(cls) -> bool:
        """Проверяет доступность nginx в системе"""
        import shutil
        return bool(shutil.which('nginx'))
    
    @staticmethod
    def check_configs(env_vars: dict, docker_dir: str) -> bool:
        """Проверка конфигурации Nginx"""
        try:
            conf_dir = Path(docker_dir) / "configs/nginx/confs"
            cert_dir = Path(docker_dir) / "configs/nginx/certs"
            
            if not conf_dir.exists():
                logging.error(f"Директория конфигов Nginx не найдена: {conf_dir}")
                return False
                
            template_path = conf_dir / "templates/default.conf.template"
            if not template_path.exists():
                logging.error(f"Шаблон Nginx не найден: {template_path}")
                return False
                
            domain = env_vars.get("NGINX_DOMAIN")
            if domain:
                cert_files = ["fullchain.pem", "privkey.pem"]
                missing = [f for f in cert_files if not (cert_dir / f).exists()]
                if missing:
                    logging.error(f"Отсутствуют SSL-сертификаты: {', '.join(missing)}")
                    return False
            
            return True
            
        except Exception as e:
            logging.error(f"Ошибка проверки конфигурации Nginx: {str(e)}")
            return False
    
    @staticmethod
    def generate_config(env_vars: dict, template_path: str, output_path: str) -> bool:
        """Генерация конфига Nginx из шаблона"""
        try:
            from string import Template
            with open(template_path, 'r') as f:
                template = Template(f.read())
            
            config = template.safe_substitute(env_vars)
            
            with open(output_path, 'w') as f:
                f.write(config)
            
            return True
        except Exception as e:
            logging.error(f"Ошибка генерации конфига Nginx: {str(e)}")
            return False