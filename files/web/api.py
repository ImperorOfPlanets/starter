# files/web/api.py
"""
REST API для удалённого управления серверами через стартер.

Используется AI-агентом клиента для:
- Получения списка серверов
- Установки/удаления серверов
- Запуска/остановки серверов
- Проверки статуса

Аутентификация: X-API-Key header
"""

import os
import hashlib
import secrets
from functools import wraps
from pathlib import Path

from flask import Blueprint, jsonify, request, current_app

from files.core.utils.globalVars_utils import get_global
from files.core.utils.loader_utils import get
from files.core.utils.log_utils import LogManager

logger = LogManager.get_logger('api')

api = Blueprint('api', __name__, url_prefix='/api/v1')

# ======================== API KEY ========================

API_KEY_FILE = Path(__file__).parent.parent.parent / 'files' / 'crypto' / '.api_key'


def _load_or_create_api_key() -> str:
    """Загружает или создаёт API ключ"""
    if API_KEY_FILE.exists():
        return API_KEY_FILE.read_text().strip()

    key = secrets.token_hex(32)
    API_KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    API_KEY_FILE.write_text(key)
    return key


def require_api_key(f):
    """Декоратор проверки API ключа"""
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key', '')

        if not api_key:
            return jsonify({'success': False, 'error': 'X-API-Key header required'}), 401

        expected = _load_or_create_api_key()
        if not secrets.compare_digest(api_key, expected):
            return jsonify({'success': False, 'error': 'Invalid API key'}), 403

        return f(*args, **kwargs)
    return decorated


# ======================== SERVERS API ========================

@api.route('/servers', methods=['GET'])
@require_api_key
def list_servers():
    """Получить список установленных серверов"""
    try:
        registry = get('registry')
        if not registry:
            return jsonify({'success': False, 'error': 'Registry not available'}), 500

        from files.configs.server_types import SERVER_TYPES
        data = registry.load_registry()
        projects = data.get('projects', [])

        servers = []
        for p in projects:
            if not p.get('installed_by_starter', False):
                continue

            path = p.get('path', '')
            project_type = p.get('project_type', 'unknown')
            type_info = SERVER_TYPES.get(project_type, {})

            servers.append({
                'id': path,
                'name': path.split('\\')[-1] if '\\' in path else path.split('/')[-1],
                'path': path,
                'type': project_type,
                'type_name': type_info.get('name', project_type),
                'status': p.get('status', 'unknown'),
                'port': p.get('port', 0),
                'has_web_interface': type_info.get('has_web_interface', False),
                'description': type_info.get('description', ''),
            })

        return jsonify({'success': True, 'servers': servers, 'count': len(servers)})

    except Exception as e:
        logger.error(f"API list_servers error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@api.route('/servers/types', methods=['GET'])
@require_api_key
def list_server_types():
    """Получить список доступных типов серверов"""
    try:
        from files.configs.server_types import SERVER_TYPES, get_sorted_server_types

        types = []
        for key, info in get_sorted_server_types():
            types.append({
                'key': key,
                'name': info['name'],
                'description': info.get('description', ''),
                'requires_auth': info.get('requires_auth', False),
                'requires_reverse_proxy': info.get('requires_reverse_proxy', False),
                'has_web_interface': info.get('has_web_interface', False),
                'can_have_multiple': info.get('can_have_multiple', True),
                'default_port': info.get('default_port'),
                'default_folder': info.get('default_folder', key),
                'repository': info.get('repository'),
            })

        return jsonify({'success': True, 'server_types': types, 'count': len(types)})

    except Exception as e:
        logger.error(f"API list_server_types error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@api.route('/servers/install', methods=['POST'])
@require_api_key
def install_server():
    """Установить новый сервер"""
    try:
        data = request.get_json(force=True, silent=True) or {}
        server_type = data.get('server_type', '').strip()
        install_path = data.get('path', '').strip()
        server_name = data.get('name', '').strip()
        force = data.get('force', False)

        if not server_type or not install_path:
            return jsonify({'success': False, 'error': 'server_type and path required'}), 400

        # Используем существующую функцию из servers.py
        from files.web.sections.servers import install_server as do_install

        # Формируем данные как в form
        form_data = {
            'server_type': server_type,
            'path': install_path,
            'name': server_name,
            'force': 'true' if force else 'false',
        }

        # Вызываем с пустой сессией (API авторизован через ключ)
        result = do_install(form_data, {})

        if isinstance(result, tuple):
            result, status = result
            return result, status

        return result

    except Exception as e:
        logger.error(f"API install_server error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@api.route('/servers/<path:server_id>/start', methods=['POST'])
@require_api_key
def start_server(server_id):
    """Запустить сервер"""
    try:
        from files.web.sections.servers import start_server as do_start

        result = do_start({'server_id': server_id}, {})

        if isinstance(result, tuple):
            result, status = result
            return result, status

        return result

    except Exception as e:
        logger.error(f"API start_server error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@api.route('/servers/<path:server_id>/stop', methods=['POST'])
@require_api_key
def stop_server(server_id):
    """Остановить сервер"""
    try:
        from files.web.sections.servers import stop_server as do_stop

        result = do_stop({'server_id': server_id}, {})

        if isinstance(result, tuple):
            result, status = result
            return result, status

        return result

    except Exception as e:
        logger.error(f"API stop_server error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@api.route('/servers/<path:server_id>/remove', methods=['DELETE'])
@require_api_key
def remove_server(server_id):
    """Удалить сервер"""
    try:
        from files.web.sections.servers import remove_server as do_remove

        result = do_remove({'server_id': server_id}, {})

        if isinstance(result, tuple):
            result, status = result
            return result, status

        return result

    except Exception as e:
        logger.error(f"API remove_server error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@api.route('/servers/<path:server_id>', methods=['GET'])
@require_api_key
def server_details(server_id):
    """Получить детали сервера"""
    try:
        from files.web.sections.servers import _get_user_servers, _check_server_status
        from files.configs.server_types import SERVER_TYPES

        registry = get('registry')
        if not registry:
            return jsonify({'success': False, 'error': 'Registry not available'}), 500

        data = registry.load_registry()
        server = next((s for s in data.get('projects', []) if s.get('path') == server_id), None)

        if not server:
            return jsonify({'success': False, 'error': 'Server not found'}), 404

        project_type = server.get('project_type', 'unknown')
        type_info = SERVER_TYPES.get(project_type, {})

        # Проверяем реальный статус
        real_status = _check_server_status(server_id, project_type)

        # Читаем env
        env_path = Path(server_id) / 'docker' / '.env'
        env_vars = {}
        if env_path.exists():
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, _, value = line.partition('=')
                        env_vars[key.strip()] = value.strip()

        return jsonify({
            'success': True,
            'server': {
                'id': server_id,
                'name': server_id.split('\\')[-1] if '\\' in server_id else server_id.split('/')[-1],
                'path': server_id,
                'type': project_type,
                'type_name': type_info.get('name', project_type),
                'status': real_status,
                'port': server.get('port', 0),
                'has_web_interface': type_info.get('has_web_interface', False),
                'description': type_info.get('description', ''),
                'env': env_vars,
            }
        })

    except Exception as e:
        logger.error(f"API server_details error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@api.route('/servers/<path:server_id>/config', methods=['GET'])
@require_api_key
def get_server_config(server_id):
    """Получить конфигурацию сервера (env)"""
    try:
        from files.web.sections.servers import _read_server_env
        env = _read_server_env(server_id)
        return jsonify({'success': True, 'env': env})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api.route('/servers/<path:server_id>/config', methods=['PUT'])
@require_api_key
def save_server_config(server_id):
    """Сохранить конфигурацию сервера"""
    try:
        from files.web.sections.servers import _write_server_env
        data = request.get_json(force=True, silent=True) or {}
        env_vars = data.get('env', {})

        if env_vars:
            _write_server_env(server_id, env_vars)
            return jsonify({'success': True, 'message': 'Config saved'})
        else:
            return jsonify({'success': False, 'error': 'No env data'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ======================== SYSTEM API ========================

@api.route('/status', methods=['GET'])
@require_api_key
def system_status():
    """Общий статус системы"""
    try:
        docker_mod = get('docker')
        docker_installed = False
        if docker_mod:
            try:
                docker_installed = docker_mod.check_docker_installed()
            except Exception:
                pass

        registry = get('registry')
        servers_count = 0
        if registry:
            data = registry.load_registry()
            servers_count = len([p for p in data.get('projects', []) if p.get('installed_by_starter', False)])

        return jsonify({
            'success': True,
            'docker_installed': docker_installed,
            'servers_count': servers_count,
            'api_version': '1.0.0',
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api.route('/drives', methods=['GET'])
@require_api_key
def list_drives():
    """Список доступных дисков"""
    try:
        from files.web.sections.servers import list_drives as do_list_drives
        result = do_list_drives({}, {})
        if isinstance(result, tuple):
            result, status = result
            return result, status
        return result
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api.route('/folders', methods=['GET'])
@require_api_key
def list_folders():
    """Список папок"""
    try:
        path = request.args.get('path', '')
        from files.web.sections.servers import list_folders as do_list_folders
        result = do_list_folders({'path': path}, {})
        if isinstance(result, tuple):
            result, status = result
            return result, status
        return result
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
