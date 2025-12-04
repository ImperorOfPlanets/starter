"""
МОДУЛЬ ОБНОВЛЕНИЯ STARTER
Отвечает за обновление самого стартера (основного приложения)
"""
import logging
from typing import Dict, Any, List, Optional

from files.core.oss.default.updates import UpdatesModule
from files.configs.starter_repos import STARTER_REPOSITORIES, STARTER_CONFIG, UPDATE_CHECK_CONFIG
from files.core.utils.globalVars_utils import get_global
from files.core.utils.log_utils import LogManager

logger = LogManager.get_logger(__name__)

class StarterUpdates:
    """Класс для управления обновлениями стартера"""
    
    @staticmethod
    def get_starter_config() -> Dict[str, Any]:
        """Получает конфигурацию обновления для стартера"""
        config = STARTER_CONFIG.copy()
        
        # Получаем доступный URL из репозиториев
        available_url = StarterUpdates._get_available_repository_url()
        if available_url:
            config['DOWNLOAD_URL'] = available_url
        else:
            # Fallback на первый репозиторий
            config['DOWNLOAD_URL'] = STARTER_REPOSITORIES[0]['url']
            logger.warning("No available repository found, using fallback URL")
        
        return config
    
    @staticmethod
    def _get_available_repository_url() -> Optional[str]:
        """Получает URL первого доступного репозитория"""
        # Пока просто возвращаем основной репозиторий
        # В будущем можно добавить проверку доступности
        if STARTER_REPOSITORIES:
            # Сортируем по приоритету
            sorted_repos = sorted(STARTER_REPOSITORIES, key=lambda x: x.get('priority', 99))
            return sorted_repos[0]['url']
        return None
    
    @staticmethod
    def get_available_repositories() -> List[Dict[str, Any]]:
        """Возвращает список всех доступных репозиториев"""
        return STARTER_REPOSITORIES.copy()
    
    @staticmethod
    def get_current_repository() -> Dict[str, Any]:
        """Возвращает текущий используемый репозиторий"""
        config = StarterUpdates.get_starter_config()
        current_url = config.get('DOWNLOAD_URL')
        
        for repo in STARTER_REPOSITORIES:
            if repo['url'] == current_url:
                return repo.copy()
        
        # Если не нашли, возвращаем первый
        return STARTER_REPOSITORIES[0].copy() if STARTER_REPOSITORIES else {}
    
    @staticmethod
    def switch_repository(repo_name: str) -> bool:
        """Переключает на указанный репозиторий"""
        for repo in STARTER_REPOSITORIES:
            if repo['name'] == repo_name:
                # Здесь можно добавить логику смены репозитория
                logger.info(f"Switched to repository: {repo_name}")
                return True
        return False
    
    @staticmethod
    def check_for_updates() -> Dict[str, Any]:
        """Проверяет доступность обновлений для стартера"""
        try:
            config = UpdatesModule.get_updates_config()
            project_name = 'starter'
            
            last_update = UpdatesModule.get_last_update_time(project_name, config)
            seconds_passed = UpdatesModule.seconds_since_last_update(project_name, config)
            
            check_interval = UPDATE_CHECK_CONFIG.get('CHECK_INTERVAL_MINUTES', 60) * 60
            
            return {
                'has_update': seconds_passed > check_interval,
                'last_update': last_update,
                'seconds_since_update': seconds_passed,
                'update_available': seconds_passed > (check_interval * 24),  # Срочное обновление если прошло больше суток
                'auto_update': UPDATE_CHECK_CONFIG.get('AUTO_UPDATE', False),
                'notify_available': UPDATE_CHECK_CONFIG.get('NOTIFY_AVAILABLE', True)
            }
        except Exception as e:
            logger.error(f"Error checking starter updates: {str(e)}")
            return {
                'has_update': False,
                'last_update': None,
                'seconds_since_update': float('inf'),
                'update_available': False,
                'auto_update': False,
                'notify_available': True
            }
    
    @staticmethod
    def update_starter() -> Dict[str, Any]:
        """Выполняет обновление стартера"""
        try:
            starter_config = StarterUpdates.get_starter_config()
            result = UpdatesModule.update_project('starter', starter_config)
            
            logger.info(f"Starter update completed: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error updating starter: {str(e)}")
            return {
                'status': 'error',
                'message': str(e),
                'update_id': None
            }
    
    @staticmethod
    def get_update_history() -> List[Dict[str, Any]]:
        """Получает историю обновлений стартера"""
        try:
            history = UpdatesModule.get_update_history('starter')
            return history.get('history', [])
        except Exception as e:
            logger.error(f"Error getting starter update history: {str(e)}")
            return []
    
    @staticmethod
    def get_update_status() -> Dict[str, Any]:
        """Получает текущий статус обновления стартера"""
        update_info = StarterUpdates.check_for_updates()
        
        if update_info['last_update']:
            check_interval = UPDATE_CHECK_CONFIG.get('CHECK_INTERVAL_MINUTES', 60) * 60
            if update_info['seconds_since_update'] < check_interval:
                status = 'up_to_date'
                color = 'success'
            elif update_info['seconds_since_update'] < (check_interval * 24):
                status = 'recently_updated'
                color = 'warning'
            else:
                status = 'update_available'
                color = 'danger'
        else:
            status = 'never_updated'
            color = 'secondary'
        
        return {
            'status': status,
            'color': color,
            'last_update': update_info['last_update'],
            'has_update': update_info['has_update'],
            'update_available': update_info['update_available'],
            'auto_update': update_info['auto_update'],
            'current_repository': StarterUpdates.get_current_repository()
        }
    
    @staticmethod
    def get_update_settings() -> Dict[str, Any]:
        """Возвращает настройки обновлений"""
        return UPDATE_CHECK_CONFIG.copy()
    
    @staticmethod
    def update_settings(new_settings: Dict[str, Any]) -> bool:
        """Обновляет настройки обновлений"""
        try:
            # Здесь можно добавить логику сохранения настроек
            # Пока просто обновляем в памяти
            UPDATE_CHECK_CONFIG.update(new_settings)
            logger.info("Starter update settings updated")
            return True
        except Exception as e:
            logger.error(f"Error updating settings: {str(e)}")
            return False