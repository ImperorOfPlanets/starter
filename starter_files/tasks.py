from starter_files.interactive.docker import check_docker_installed, run_docker_compose
from starter_files.untils.updates import start_updates_projects
from starter_files.untils.logger import logger

def check_docker_containers():
    """Проверяет состояние контейнеров и перезапускает при необходимости"""
    logger.log("Проверка состояния Docker контейнеров...", "TASK")
    if not check_docker_installed():
        logger.log("Docker не установлен", "ERROR")
        return
        
    # Здесь можно добавить более сложную логику проверки
    run_docker_compose(push_to_registry=False, pull_from_registry=False)

def check_for_updates():
    """Проверяет наличие обновлений"""
    logger.log("Проверка обновлений...", "TASK")
    start_updates_projects()

def cleanup_old_logs():
    """Очищает старые логи"""
    logger.log("Очистка старых логов...", "TASK")
    # Реализация очистки логов