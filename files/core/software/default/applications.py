# files/core/software/default/applications.py
"""
Модуль для работы с заявками пользователя на MyIDon.Site
Позволяет получать, обновлять и управлять заявками через API
"""

import requests
from typing import List, Dict, Optional
from datetime import datetime

from files.core.base_module import BaseModule
from files.core.utils.log_utils import LogManager
from files.core.utils.globalVars_utils import get_global, set_global

logger = LogManager.get_logger('applications')


class ApplicationsModule(BaseModule):
    """Модуль для работы с заявками пользователя на MyIDon.Site"""
    
    MYIDON_URL = "https://myidon.site"
    _access_token = None
    _applications_cache = None
    _cache_timestamp = None
    _cache_ttl = 60  # Кэш на 60 секунд
    
    @staticmethod
    def check() -> bool:
        """Проверка доступности модуля"""
        try:
            import requests
            return True
        except ImportError:
            return False
    
    @staticmethod
    def set_globals():
        """Инициализация модуля"""
        myidon_url = get_global('myidon_url', 'https://myidon.site')
        ApplicationsModule.MYIDON_URL = myidon_url
        logger.info(f"Applications module initialized with MYIDON_URL: {myidon_url}")
    
    @staticmethod
    def get_myidon_url() -> str:
        """Возвращает URL MyIDon.Site"""
        return ApplicationsModule.MYIDON_URL
    
    @staticmethod
    def set_access_token(token: str):
        """Устанавливает OAuth токен для API запросов"""
        ApplicationsModule._access_token = token
        logger.debug("Access token set for applications module")
    
    @staticmethod
    def get_access_token() -> Optional[str]:
        """Получает OAuth токен из модуля или из глобальных переменных"""
        if ApplicationsModule._access_token:
            return ApplicationsModule._access_token
        
        # Пытаемся получить из OAuth модуля
        try:
            from files.core.utils.loader_utils import get
            oauth_module = get('oauth')
            if oauth_module and hasattr(oauth_module, 'get_access_token'):
                token = oauth_module.get_access_token()
                if token:
                    ApplicationsModule._access_token = token
                    return token
        except Exception as e:
            logger.error(f"Error getting access token from oauth module: {e}")
        
        return None
    
    @staticmethod
    def is_authenticated() -> bool:
        """Проверяет есть ли токен доступа"""
        return ApplicationsModule.get_access_token() is not None
    
    @staticmethod
    def _make_request(method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        """Выполняет запрос к API MyIDon.Site"""
        token = ApplicationsModule.get_access_token()
        if not token:
            logger.warning("No access token available for API request")
            return None
        
        url = f"{ApplicationsModule.MYIDON_URL}{endpoint}"
        headers = {
            'Authorization': f'Bearer {token}',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                timeout=10,
                **kwargs
            )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                logger.error("Unauthorized - token may be expired")
                ApplicationsModule._access_token = None
                return None
            else:
                logger.error(f"API request failed: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error(f"API request timeout: {endpoint}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"API request error: {e}")
            return None
    
    @staticmethod
    def get_user_applications(force_refresh: bool = False) -> List[Dict]:
        """
        Получает одобренные заявки пользователя
        
        Args:
            force_refresh: Принудительное обновление кэша
            
        Returns:
            Список заявок пользователя
        """
        # Проверяем кэш
        if not force_refresh and ApplicationsModule._applications_cache is not None:
            if ApplicationsModule._cache_timestamp:
                elapsed = (datetime.now() - ApplicationsModule._cache_timestamp).total_seconds()
                if elapsed < ApplicationsModule._cache_ttl:
                    logger.debug(f"Returning cached applications (age: {elapsed:.1f}s)")
                    return ApplicationsModule._applications_cache
        
        # Проверяем авторизацию
        if not ApplicationsModule.is_authenticated():
            logger.warning("User not authenticated, cannot fetch applications")
            return []
        
        # Запрашиваем заявки
        data = ApplicationsModule._make_request('GET', '/api/user/applications')
        
        if data is None:
            return []
        
        applications = data.get('applications', [])
        
        # Обновляем кэш
        ApplicationsModule._applications_cache = applications
        ApplicationsModule._cache_timestamp = datetime.now()
        
        logger.info(f"Fetched {len(applications)} applications from API")
        return applications
    
    @staticmethod
    def get_application(application_id: int) -> Optional[Dict]:
        """
        Получает конкретную заявку по ID
        
        Args:
            application_id: ID заявки
            
        Returns:
            Данные заявки или None
        """
        if not ApplicationsModule.is_authenticated():
            logger.warning("User not authenticated, cannot fetch application")
            return None
        
        data = ApplicationsModule._make_request('GET', f'/api/user/applications/{application_id}')
        
        if data and 'application' in data:
            return data['application']
        
        return None
    
    @staticmethod
    def refresh_applications() -> List[Dict]:
        """
        Принудительно обновляет список заявок
        
        Returns:
            Свежий список заявок
        """
        return ApplicationsModule.get_user_applications(force_refresh=True)
    
    @staticmethod
    def clear_cache():
        """Очищает кэш заявок"""
        ApplicationsModule._applications_cache = None
        ApplicationsModule._cache_timestamp = None
        logger.debug("Applications cache cleared")
    
    @staticmethod
    def get_applications_count() -> int:
        """Возвращает количество заявок"""
        applications = ApplicationsModule.get_user_applications()
        return len(applications)
    
    @staticmethod
    def get_applications_by_type(app_type: str) -> List[Dict]:
        """
        Фильтрует заявки по типу
        
        Args:
            app_type: Тип заявки (server_type, tailscale, starter и т.д.)
            
        Returns:
            Отфильтрованный список заявок
        """
        applications = ApplicationsModule.get_user_applications()
        return [app for app in applications if app.get('type') == app_type]
    
    @staticmethod
    def get_applications_by_status(status: str) -> List[Dict]:
        """
        Фильтрует заявки по статусу
        
        Args:
            status: Статус заявки (approved, pending, rejected и т.д.)
            
        Returns:
            Отфильтрованный список заявок
        """
        applications = ApplicationsModule.get_user_applications()
        return [app for app in applications if app.get('status') == status]
