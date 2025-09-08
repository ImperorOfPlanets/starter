from pathlib import Path

def check_vpn_config(env_vars, docker_dir):
    """Проверка конфигурации VPN"""
    vpn_required = env_vars.get("VPN_REQUIRED", "disabled").lower()
    if vpn_required in ["required", "optional"]:
        vpn_config = env_vars.get("VPN_CONFIG")
        if not vpn_config:
            raise Exception("VPN_CONFIG не указан в .env")
        
        vpn_path = Path(docker_dir) / vpn_config
        if not vpn_path.exists():
            raise Exception(f"Файл конфигурации VPN не найден: {vpn_path}")

