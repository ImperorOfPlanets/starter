from pathlib import Path

def check_nginx_configs(env_vars, docker_dir):
    """Проверка конфигурации Nginx"""
    conf_dir = Path(docker_dir) / "configs/nginx/confs"
    cert_dir = Path(docker_dir) / "configs/nginx/certs"
    
    if not conf_dir.exists():
        raise Exception(f"Директория конфигов Nginx не найдена: {conf_dir}")
        
    template_path = conf_dir / "templates/default.conf.template"
    if not template_path.exists():
        raise Exception(f"Шаблон Nginx не найден: {template_path}")
    domain = env_vars.get("NGINX_DOMAIN")
    if domain:
        cert_files = ["fullchain.pem", "privkey.pem"]
        missing = [f for f in cert_files if not (cert_dir / f).exists()]
        if missing:
            raise Exception(f"Отсутствуют SSL-сертификаты: {', '.join(missing)}")