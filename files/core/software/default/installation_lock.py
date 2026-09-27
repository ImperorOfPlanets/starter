"""
Модуль фиксации установок через API myidon.site.
При первой установке сохраняет данные.
При переустановке проверяет что данные совпадают.
"""

import hashlib
import socket
import uuid
from typing import Dict, Optional

from files.core.base_module import BaseModule
from files.core.utils.log_utils import LogManager
from files.core.utils.globalVars_utils import get_global

logger = LogManager.get_logger('installation_lock')


class InstallationLockModule(BaseModule):
    """Фиксация установок серверов/клиентов через API myidon.site"""
    
    @staticmethod
    def get_device_fingerprint() -> str:
        """Получить отпечаток устройства (v2: hardware ID)"""
        from files.core.utils.hardware_id import get_device_fingerprint as hw_fp
        return hw_fp()
    
    @staticmethod
    def check_installation(
        oauth_token: str,
        server_type: str,
        server_path: str,
        application_id: int
    ) -> Dict:
        """
        Проверить можно ли устанавливать/переустанавливать сервер.
        """
        import requests
        
        try:
            response = requests.post(
                f"{get_myidon_url()}/api/installation/check",
                headers={
                    'Authorization': f'Bearer {oauth_token}',
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                },
                json={
                    'server_type': server_type,
                    'server_path': server_path,
                    'application_id': application_id,
                    'device_fingerprint': InstallationLockModule.get_device_fingerprint(),
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Installation check: {result.get('reason')}")
                return result
            else:
                logger.error(f"Installation check failed: {response.status_code}")
                return {'allowed': False, 'reason': f'HTTP {response.status_code}'}
                
        except Exception as e:
            logger.error(f"Installation check error: {e}")
            return {'allowed': False, 'reason': str(e)}
    
    @staticmethod
    def record_installation(
        oauth_token: str,
        server_type: str,
        server_path: str,
        application_id: int,
        additional_data: Dict = None
    ) -> bool:
        """
        Зафиксировать установку на myidon.site.
        """
        import requests
        
        try:
            payload = {
                'server_type': server_type,
                'server_path': server_path,
                'application_id': application_id,
                'device_fingerprint': InstallationLockModule.get_device_fingerprint(),
                'hostname': socket.gethostname(),
            }
            
            if additional_data:
                payload['additional_data'] = additional_data
            
            response = requests.post(
                f"{get_myidon_url()}/api/installation/record",
                headers={
                    'Authorization': f'Bearer {oauth_token}',
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                },
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Installation recorded: {result.get('message')}")
                return result.get('success', False)
            else:
                logger.error(f"Installation record failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Installation record error: {e}")
            return False
    
    @staticmethod
    def update_installation(
        oauth_token: str,
        server_type: str,
        server_path: str,
        additional_data: Dict = None
    ) -> bool:
        """
        Обновить запись установки на myidon.site.
        """
        import requests
        
        try:
            payload = {
                'server_type': server_type,
                'server_path': server_path,
            }
            
            if additional_data:
                payload['additional_data'] = additional_data
            
            response = requests.put(
                f"{get_myidon_url()}/api/installation/record",
                headers={
                    'Authorization': f'Bearer {oauth_token}',
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                },
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Installation updated: {result.get('message')}")
                return result.get('success', False)
            else:
                logger.error(f"Installation update failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Installation update error: {e}")
            return False
    
    @staticmethod
    def remove_installation(
        oauth_token: str,
        server_type: str,
        server_path: str
    ) -> bool:
        """
        Удалить запись установки с myidon.site.
        """
        import requests
        
        try:
            response = requests.delete(
                f"{get_myidon_url()}/api/installation/record",
                headers={
                    'Authorization': f'Bearer {oauth_token}',
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                },
                json={
                    'server_type': server_type,
                    'server_path': server_path,
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Installation removed: {result.get('message')}")
                return result.get('success', False)
            else:
                logger.error(f"Installation remove failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Installation remove error: {e}")
            return False
    
    @staticmethod
    def get_user_installations(oauth_token: str) -> list:
        """
        Получить все установки пользователя с myidon.site.
        """
        import requests
        
        try:
            response = requests.get(
                f"{get_myidon_url()}/api/installation/list",
                headers={
                    'Authorization': f'Bearer {oauth_token}',
                    'Accept': 'application/json',
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('records', [])
            else:
                logger.error(f"Get installations failed: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Get installations error: {e}")
            return []

    @staticmethod
    def request_hardware_change(
        oauth_token: str,
        reason: str,
        new_device_info: str = None
    ) -> Dict:
        """
        Подать заявку на смену железа.
        """
        import requests
        
        try:
            payload = {
                'reason': reason,
            }
            if new_device_info:
                payload['new_device_info'] = new_device_info
            
            response = requests.post(
                f"{get_myidon_url()}/api/hardware-change/request",
                headers={
                    'Authorization': f'Bearer {oauth_token}',
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                },
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Hardware change request submitted: {result.get('message')}")
                return result
            else:
                logger.error(f"Hardware change request failed: {response.status_code}")
                return {'success': False, 'error': f'HTTP {response.status_code}'}
                
        except Exception as e:
            logger.error(f"Hardware change request error: {e}")
            return {'success': False, 'error': str(e)}

    @staticmethod
    def get_hardware_change_status(oauth_token: str) -> Dict:
        """
        Проверить статус заявки на смену железа.
        """
        import requests
        
        try:
            response = requests.get(
                f"{get_myidon_url()}/api/hardware-change/status",
                headers={
                    'Authorization': f'Bearer {oauth_token}',
                    'Accept': 'application/json',
                },
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Hardware change status failed: {response.status_code}")
                return {'has_pending': False}
                
        except Exception as e:
            logger.error(f"Hardware change status error: {e}")
            return {'has_pending': False}


def get_myidon_url() -> str:
    """Получить URL myidon.site"""
    try:
        from files.core.software.default.oauth import OauthModule
        return OauthModule.MYIDON_URL
    except Exception:
        return 'https://myidon.site'
