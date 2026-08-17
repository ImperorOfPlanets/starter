# files/core/software/default/oauth.py
"""
Модуль OAuth2 авторизации через MyIDon.Site
Автоматически создает заявку при первом запуске Starter
"""

import requests
import secrets
import urllib.parse
import json
import hashlib
import socket
import platform
from flask import session, redirect, url_for, request
from typing import Dict, Optional, List
from pathlib import Path
from datetime import datetime

from files.core.base_module import BaseModule
from files.core.utils.log_utils import LogManager
from files.core.utils.globalVars_utils import get_global, set_global

logger = LogManager.get_logger('oauth')


class OauthModule(BaseModule):
    """OAuth2 авторизация через MyIDon.Site с автоматическим созданием заявки"""
    
    MYIDON_URL = "https://myidon.site"
    CLIENT_ID = None
    CLIENT_SECRET = None
    REDIRECT_URI = None
    _application_id = None
    _server_id = None
    
    @staticmethod
    def check() -> bool:
        try:
            import requests
            return True
        except ImportError:
            return False
    
    @staticmethod
    def set_globals():
        """Инициализация OAuth - проверяет наличие приложения, создает заявку если нет"""
        from files.core.software.default.env import EnvModule
        
        env_path = get_global('starter_env_path')
        if not env_path or not env_path.exists():
            logger.warning("ENV file not found, OAuth will be configured later")
            return
        
        env_vars = EnvModule.read_env_file(env_path)
        
        # Проверяем наличие OAuth клиента
        client_id = env_vars.get('OAUTH_CLIENT_ID') or env_vars.get('OAUTH_STARTER_ID')
        client_secret = env_vars.get('OAUTH_CLIENT_SECRET') or env_vars.get('OAUTH_STARTER_SECRET')
        application_id = env_vars.get('APPLICATION_ID')
        
        if client_id and client_secret:
            # Уже есть клиент - используем его
            OauthModule.CLIENT_ID = client_id
            OauthModule.CLIENT_SECRET = client_secret
            if application_id:
                OauthModule._application_id = application_id

            # Определяем redirect_uri
            port = get_global('port', 2000)
            host = 'localhost'
            OauthModule.REDIRECT_URI = f"https://{host}:{port}/oauth/callback"

            logger.info(f"OAuth using existing credentials, redirect_uri={OauthModule.REDIRECT_URI}")
            return  # <-- ВАЖНО: выход, если уже есть клиент
        
        # Нет клиента - создаем заявку
        logger.info("No OAuth client found. Creating application request...")
        try:
            # Убеждаемся, что env_vars обновлены
            success = OauthModule.create_application(env_path, env_vars)
            if success:
                logger.info("Application created successfully! Waiting for admin approval...")
            else:
                logger.warning("Application creation failed, will retry")
        except Exception as e:
            logger.error(f"Application creation error: {e}")
        
        # Определяем redirect_uri
        port = get_global('port', 2000)
        protocol = 'https' if get_global('ssl_context') else 'http'
        host = 'localhost'
        OauthModule.REDIRECT_URI = f"{protocol}://{host}:{port}/oauth/callback"
        
        logger.info(f"OAuth configured with MYIDON_URL: {OauthModule.MYIDON_URL}")
        logger.info(f"Redirect URI: {OauthModule.REDIRECT_URI}")
    
    @staticmethod
    def create_application(env_path: Path, env_vars: Dict) -> bool:
        """
        Создает заявку на myidon.site для получения OAuth клиента
        """
        try:
            # Собираем информацию о сервере
            server_name = env_vars.get('SERVER_NAME', 'Starter Server')
            server_type = env_vars.get('TYPE_SERVER', 'unknown')
            starter_path = str(get_global('starter_path'))
            
            # Уникальный идентификатор
            path_hash = hashlib.sha256(starter_path.encode()).hexdigest()[:16]
            hostname = socket.gethostname()
            
            # IP адреса
            ips = []
            try:
                hostname_ip = socket.gethostbyname(hostname)
                ips.append(hostname_ip)
            except:
                pass
            
            # Получаем MAC адрес
            mac_address = "unknown"
            try:
                import uuid
                mac_address = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) 
                                       for elements in range(0, 2*6, 2)][::-1])
            except:
                pass
            
            # Данные для заявки (тип business - для серверного приложения)
            application_data = {
                'type': 'business',
                'country_id': 1,  # Россия
                'location': 'Moscow',
                'contact_email': env_vars.get('ADMIN_EMAIL', 'admin@localhost'),
                'contact_phone': env_vars.get('ADMIN_PHONE', ''),
                
                # Бизнес данные
                'company_name': f"Starter: {server_name}",
                'company_registration_number': path_hash,
                'business_type': server_type,
                'business_description': f'Starter server for management\nPath: {starter_path}\nHost: {hostname}',
                'representative_name': env_vars.get('ADMIN_NAME', 'Admin'),
                'representative_position': 'Administrator',
                
                # Дополнительная информация
                'additional_info': json.dumps({
                    'server_path': starter_path,
                    'hostname': hostname,
                    'ips': ips,
                    'mac_address': mac_address,
                    'public_key': path_hash,
                    'version': get_global('version', '1.0.0'),
                    'server_type': server_type,
                    'os': platform.system(),
                    'python_version': platform.python_version(),
                    'starter_port': get_global('port', 2000)
                })
            }
            
            logger.info(f"Creating application for: {server_name}")
            logger.info(f"Application data: {json.dumps(application_data, indent=2)}")
            
            # Отправляем заявку
            response = requests.post(
                f"{OauthModule.MYIDON_URL}/api/applications",
                json=application_data,
                timeout=15,
                headers={
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                }
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                application_id = data.get('id')
                
                if application_id:
                    # Сохраняем ID заявки в .env
                    env_vars['APPLICATION_ID'] = str(application_id)
                    from files.core.software.default.env import EnvModule
                    EnvModule.write_env_file(env_path, env_vars)
                    
                    OauthModule._application_id = application_id
                    
                    logger.info(f"✅ Application created! ID: {application_id}")
                    logger.info("📋 Waiting for admin approval on myidon.site")
                    return True
                else:
                    logger.error(f"Application creation failed: {data.get('message')}")
            else:
                logger.error(f"Application HTTP error: {response.status_code}")
                logger.debug(f"Response: {response.text[:200]}")
            
            return False
            
        except Exception as e:
            logger.error(f"Application creation error: {e}")
            return False
    
    @staticmethod
    def check_application_status() -> Dict:
        """Проверяет статус заявки и получает OAuth клиента если одобрена"""
        # Если нет ID заявки, но есть клиент - значит уже одобрено
        if OauthModule.CLIENT_ID and OauthModule.CLIENT_SECRET:
            return {'status': 'approved', 'client_id': OauthModule.CLIENT_ID}
        
        if not OauthModule._application_id:
            # Пробуем прочитать из .env
            env_path = get_global('starter_env_path')
            if env_path and env_path.exists():
                from files.core.software.default.env import EnvModule
                env_vars = EnvModule.read_env_file(env_path)
                app_id = env_vars.get('APPLICATION_ID')
                if app_id:
                    OauthModule._application_id = app_id
                else:
                    return {'status': 'no_application', 'message': 'No application found'}
        
        try:
            response = requests.get(
                f"{OauthModule.MYIDON_URL}/api/applications/{OauthModule._application_id}",
                timeout=10,
                headers={'Accept': 'application/json'}
            )
            
            if response.status_code == 200:
                data = response.json()
                status = data.get('status')
                
                logger.info(f"Application status: {status}")
                
                # Если заявка одобрена и есть OAuth клиент
                if status == 'approved':
                    client = data.get('oauth_client')
                    if client and client.get('id') and client.get('secret'):
                        client_id = client.get('id')
                        client_secret = client.get('secret')
                        
                        # Сохраняем в .env
                        env_path = get_global('starter_env_path')
                        if env_path and env_path.exists():
                            env_vars = {}
                            with open(env_path, 'r', encoding='utf-8') as f:
                                for line in f:
                                    if '=' in line and not line.startswith('#'):
                                        key, value = line.strip().split('=', 1)
                                        env_vars[key] = value
                            
                            env_vars['OAUTH_STARTER_ID'] = str(client_id)
                            env_vars['OAUTH_STARTER_SECRET'] = client_secret
                            
                            from files.core.software.default.env import EnvModule
                            EnvModule.write_env_file(env_path, env_vars)
                            
                            OauthModule.CLIENT_ID = client_id
                            OauthModule.CLIENT_SECRET = client_secret
                            
                            logger.info(f"✅ OAuth credentials obtained! Client ID: {client_id}")
                            return {'status': 'approved', 'client_id': client_id}
                
                elif status == 'rejected':
                    logger.warning(f"Application rejected: {data.get('notes', 'No reason provided')}")
                    return {'status': 'rejected', 'message': data.get('notes', 'Rejected')}
                
                elif status == 'pending':
                    logger.info("Application is pending admin approval")
                    return {'status': 'pending'}
                
                elif status == 'in_review':
                    logger.info("Application is under review")
                    return {'status': 'in_review'}
                
            else:
                logger.error(f"Failed to check application: {response.status_code}")
                return {'status': 'error', 'message': f'HTTP {response.status_code}'}
                
        except Exception as e:
            logger.error(f"Error checking application: {e}")
            return {'status': 'error', 'message': str(e)}
    
    @staticmethod
    def is_configured() -> bool:
        """Проверяет, настроен ли OAuth"""
        return bool(OauthModule.CLIENT_ID and OauthModule.CLIENT_SECRET)
    
    @staticmethod
    def get_authorization_url(state: str = None, scope: str = None) -> Optional[str]:
        """Генерирует URL для авторизации"""
        if not OauthModule.is_configured():
            logger.error("OAuth not configured — cannot generate auth URL")
            return None

        if state is None:
            state = secrets.token_urlsafe(32)

        session['oauth_state'] = state

        params = {
            'client_id': OauthModule.CLIENT_ID,
            'redirect_uri': OauthModule.REDIRECT_URI,
            'response_type': 'code',
            'state': state,
            'scope': ''
        }

        auth_url = f"{OauthModule.MYIDON_URL}/oauth/authorize?{urllib.parse.urlencode(params)}"
        logger.info(f"Generated OAuth URL")
        return auth_url
    
    @staticmethod
    def exchange_code_for_token(code: str, state: str) -> Optional[Dict]:
        """Обменивает код на токен"""
        if state != session.get('oauth_state'):
            logger.error("OAuth state mismatch")
            return None
        
        import base64
        credentials = f"{OauthModule.CLIENT_ID}:{OauthModule.CLIENT_SECRET}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        headers = {
            'Accept': 'application/json',
            'Authorization': f'Basic {encoded_credentials}'
        }
        
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': OauthModule.REDIRECT_URI
        }
        
        try:
            response = requests.post(
                f"{OauthModule.MYIDON_URL}/oauth/token",
                data=data,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                token_data = response.json()
                logger.info("Successfully exchanged code for token")
                return token_data
            else:
                logger.error(f"Token exchange failed: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Token exchange error: {e}")
            return None
    
    @staticmethod
    def get_user_info(access_token: str) -> Optional[Dict]:
        """Получает информацию о пользователе"""
        try:
            response = requests.get(
                f"{OauthModule.MYIDON_URL}/api/user",
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Accept': 'application/json'
                },
                timeout=10
            )
            
            if response.status_code == 200:
                user_data = response.json()
                logger.info(f"Retrieved user info")
                return user_data
            else:
                logger.error(f"Failed to get user info: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"User info error: {e}")
            return None
    
    @staticmethod
    def oauth_callback(data, session_obj) -> Dict:
        """Callback после OAuth авторизации"""
        code = data.get('code')
        state = data.get('state')
        error = data.get('error')
        
        if error:
            logger.error(f"OAuth error: {error}")
            return {
                'status': 'error',
                'message': f'Authorization failed: {error}'
            }
        
        if not code:
            logger.error("No code in OAuth callback")
            return {
                'status': 'error',
                'message': 'Invalid authorization response'
            }
        
        token_data = OauthModule.exchange_code_for_token(code, state)
        if not token_data:
            return {
                'status': 'error',
                'message': 'Failed to obtain access token'
            }
        
        access_token = token_data.get('access_token')
        if not access_token:
            return {
                'status': 'error',
                'message': 'No access token received'
            }
        
        user_info = OauthModule.get_user_info(access_token)
        if not user_info:
            return {
                'status': 'error',
                'message': 'Failed to get user information'
            }
        
        # Авторизуем пользователя
        session_obj['logged_in'] = True
        session_obj['username'] = user_info.get('email') or user_info.get('name')
        session_obj['user_id'] = user_info.get('id')
        session_obj['oauth_token'] = access_token
        session_obj['user_info'] = user_info
        session_obj['auth_method'] = 'myidon_oauth'
        session_obj.permanent = True

        logger.info(f"User {session_obj['username']} logged in via MyIDon OAuth")

        # Получаем список серверов пользователя из myidon.site
        user_servers = OauthModule.get_user_servers(access_token)
        if user_servers is not None:
            session_obj['user_servers'] = user_servers
            logger.info(f"User has access to {len(user_servers)} servers")
        else:
            session_obj['user_servers'] = []
            logger.warning("Failed to fetch user servers from myidon.site")

        # После входа — создаём заявку если нет
        if not OauthModule._application_id:
            env_path = get_global('starter_env_path')
            if env_path and env_path.exists():
                from files.core.software.default.env import EnvModule
                env_vars = EnvModule.read_env_file(env_path)
                OauthModule.create_application(env_path, env_vars)

        return {
            'status': 'success',
            'redirect': url_for('routes.index')
        }
    
    @staticmethod
    def get_application_status_message() -> Dict:
        """
        Возвращает сообщение о статусе заявки для отображения в интерфейсе
        """
        # Сначала пробуем проверить статус (это также обновит CLIENT_ID если одобрено)
        status = OauthModule.check_application_status()
        
        # Если статус 'no_application' - пытаемся создать заявку
        if status.get('status') == 'no_application':
            logger.info("No application found, trying to create one...")
            env_path = get_global('starter_env_path')
            if env_path and env_path.exists():
                from files.core.software.default.env import EnvModule
                env_vars = EnvModule.read_env_file(env_path)
                success = OauthModule.create_application(env_path, env_vars)
                if success:
                    # После создания заявки проверяем статус еще раз
                    status = OauthModule.check_application_status()
                else:
                    return {
                        'status': 'error',
                        'message': 'Failed to create application. Check logs.',
                        'can_login': False
                    }
            else:
                return {
                    'status': 'error',
                    'message': 'ENV file not found. Please run setup first.',
                    'can_login': False
                }
        
        if status.get('status') == 'approved':
            return {
                'status': 'approved',
                'message': 'Application approved! You can login.',
                'can_login': True
            }
        elif status.get('status') == 'pending':
            return {
                'status': 'pending',
                'message': 'Application is pending admin approval. Please wait.',
                'can_login': False,
                'application_id': OauthModule._application_id
            }
        elif status.get('status') == 'in_review':
            return {
                'status': 'in_review',
                'message': 'Application is under review by admin.',
                'can_login': False,
                'application_id': OauthModule._application_id
            }
        elif status.get('status') == 'rejected':
            return {
                'status': 'rejected',
                'message': f"Application rejected: {status.get('message', 'No reason provided')}",
                'can_login': False
            }
        else:
            return {
                'status': 'error',
                'message': f"Error checking application: {status.get('message', 'Unknown error')}",
                'can_login': False
            }
    
    @staticmethod
    def get_application_id() -> Optional[str]:
        """Возвращает ID заявки"""
        return OauthModule._application_id

    @staticmethod
    def get_user_servers(access_token: str) -> Optional[List[Dict]]:
        """Получает список серверов (заявок), доступных текущему пользователю"""
        try:
            response = requests.get(
                f"{OauthModule.MYIDON_URL}/api/user/servers",
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Accept': 'application/json'
                },
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                servers = data.get('servers', [])
                logger.info(f"Retrieved {len(servers)} servers for user")
                return servers
            else:
                logger.error(f"Failed to get user servers: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Error getting user servers: {e}")
            return None