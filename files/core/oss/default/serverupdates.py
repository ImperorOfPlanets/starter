"""
МОДУЛЬ ОБНОВЛЕНИЯ СЕРВЕРНЫХ ПРОЕКТОВ
Отвечает за обновление серверов на основе их типа с использованием targets.json
"""
import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from files.core.oss.default.updates import UpdatesModule
from files.configs.server_types import SERVER_TYPES, DEFAULT_TARGETS_CONFIG
from files.core.utils.globalVars_utils import get_global
from files.core.utils.log_utils import LogManager

logger = LogManager.get_logger(__name__)

class ServerUpdates:
    """Класс для управления обновлениями серверных проектов"""
    
    @staticmethod
    def get_server_config(server_type: str) -> Dict[str, Any]:
        """Генерирует конфигурацию обновления для сервера с использованием targets.json"""
        if server_type not in SERVER_TYPES:
            raise ValueError(f"Unknown server type: {server_type}")
        
        server_info = SERVER_TYPES[server_type]
        
        # Получаем доступный репозиторий
        repo = ServerUpdates._get_available_repository(server_type)
        
        if not repo:
            raise ValueError(f"No available repository for server type: {server_type}")
        
        # Базовая конфигурация
        config = {
            'DOWNLOAD_URL': repo['url'],
            'SERVER_TYPE': server_type,
            'SERVER_NAME': server_info['name'],
            'TARGETS_CONFIG': repo.get('targets_config', 'targets.json')
        }
        
        # Загружаем конфигурацию целей из targets.json
        targets_config = ServerUpdates._load_targets_config(config['TARGETS_CONFIG'])
        config.update(targets_config)
        
        return config
    
    @staticmethod
    def _load_targets_config(config_name: str) -> Dict[str, Any]:
        """Загружает конфигурацию целей обновления"""
        # В будущем можно загружать из удаленного источника
        # Пока используем дефолтную конфигурацию
        return DEFAULT_TARGETS_CONFIG.copy()
    
    @staticmethod
    def _get_available_repository(server_type: str) -> Optional[Dict[str, str]]:
        """Получает доступный репозиторий для сервера"""
        server_info = SERVER_TYPES[server_type]
        
        # Пока используем первый доступный репозиторий
        # В будущем можно добавить проверку доступности
        if server_info['repositories']:
            return server_info['repositories'][0]
        
        return None
    
    @staticmethod
    def get_current_server_type() -> Optional[str]:
        """Получает текущий тип сервера"""
        return get_global('server_type')
    
    @staticmethod
    def check_server_updates(server_type: str = None) -> Dict[str, Any]:
        """Проверяет обновления для сервера"""
        if not server_type:
            server_type = ServerUpdates.get_current_server_type()
            if not server_type:
                return {'error': 'Server type not configured'}
        
        try:
            config = UpdatesModule.get_updates_config()
            project_name = f"server_{server_type}"
            
            last_update = UpdatesModule.get_last_update_time(project_name, config)
            seconds_passed = UpdatesModule.seconds_since_last_update(project_name, config)
            
            return {
                'server_type': server_type,
                'has_update': seconds_passed > 3600,
                'last_update': last_update,
                'seconds_since_update': seconds_passed,
                'update_available': seconds_passed > 86400
            }
        except Exception as e:
            logger.error(f"Error checking server updates for {server_type}: {str(e)}")
            return {
                'server_type': server_type,
                'has_update': False,
                'last_update': None,
                'seconds_since_update': float('inf'),
                'update_available': False,
                'error': str(e)
            }
    
    @staticmethod
    def update_server(server_type: str = None) -> Dict[str, Any]:
        """Выполняет обновление сервера"""
        if not server_type:
            server_type = ServerUpdates.get_current_server_type()
            if not server_type:
                return {'status': 'error', 'message': 'Server type not configured'}
        
        try:
            server_config = ServerUpdates.get_server_config(server_type)
            project_name = f"server_{server_type}"
            
            result = UpdatesModule.update_project(project_name, server_config)
            result['server_type'] = server_type
            result['server_name'] = SERVER_TYPES[server_type]['name']
            
            logger.info(f"Server {server_type} update completed: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error updating server {server_type}: {str(e)}")
            return {
                'status': 'error',
                'message': str(e),
                'server_type': server_type,
                'update_id': None
            }
    
    @staticmethod
    def get_all_server_updates_status() -> List[Dict[str, Any]]:
        """Получает статус обновлений для всех типов серверов"""
        status_list = []
        
        for server_type in SERVER_TYPES.keys():
            status = ServerUpdates.check_server_updates(server_type)
            server_info = SERVER_TYPES[server_type]
            
            if status.get('last_update'):
                if status['seconds_since_update'] < 3600:
                    status_text = 'up_to_date'
                    color = 'success'
                elif status['seconds_since_update'] < 86400:
                    status_text = 'recently_updated'
                    color = 'warning'
                else:
                    status_text = 'update_available'
                    color = 'danger'
            else:
                status_text = 'never_updated'
                color = 'secondary'
            
            status_list.append({
                'type': server_type,
                'name': server_info['name'],
                'description': server_info['description'],
                'status': status_text,
                'color': color,
                'last_update': status.get('last_update'),
                'has_update': status.get('has_update', False),
                'is_current': server_type == ServerUpdates.get_current_server_type()
            })
        
        return status_list
    
    @staticmethod
    def get_server_update_history(server_type: str = None) -> List[Dict[str, Any]]:
        """Получает историю обновлений сервера"""
        try:
            if server_type:
                history = UpdatesModule.get_update_history(f"server_{server_type}")
            else:
                history = UpdatesModule.get_update_history("all")
            
            return history.get('history', [])
        except Exception as e:
            logger.error(f"Error getting server update history: {str(e)}")
            return []