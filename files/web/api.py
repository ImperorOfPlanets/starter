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


API_SESSION = {'logged_in': True, 'user': {'id': 'api', 'name': 'API'}}


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
    """Получить список установленных серверов.

    По возможности читает SQLite-кеш фонового монитора (мгновенно);
    при пустом кеше выполняет синхронную проверку.
    """
    try:
        registry = get('registry')
        if not registry:
            return jsonify({'success': False, 'error': 'Registry not available'}), 500

        from files.configs.server_types import SERVER_TYPES

        # Быстрый путь: кеш монитора
        cached = None
        cache_info = None
        try:
            from files.core.oss.default.server_monitor import ServerMonitorModule
            cached = ServerMonitorModule.get_cached_servers()
            cache_info = ServerMonitorModule.get_status()
            if cached is None:
                ServerMonitorModule.refresh_all(background=True)
        except Exception as e:
            logger.warning(f"server_monitor недоступен для API: {e}")

        if cached is not None:
            servers = []
            for s in cached:
                type_info = SERVER_TYPES.get(s['type'], {})
                servers.append({
                    **s,
                    'type_name': type_info.get('name', s['type']),
                    'description': type_info.get('description', ''),
                })
            return jsonify({'success': True, 'servers': servers, 'count': len(servers),
                            'cache': {'updated_at': cache_info.get('updated_at') if cache_info else None}})

        # Фолбэк: синхронная проверка
        from files.web.sections.servers import _check_server_status, _project_files_exist
        data = registry.load_registry()
        projects = data.get('projects', [])

        servers = []
        for p in projects:
            if not p.get('installed_by_starter', False):
                continue

            path = p.get('path', '')
            project_type = p.get('project_type', 'unknown')
            type_info = SERVER_TYPES.get(project_type, {})

            if not _project_files_exist(path):
                real_status = 'missing_files'
            else:
                real_status = _check_server_status(path, project_type)

            servers.append({
                'id': path,
                'name': path.split('\\')[-1] if '\\' in path else path.split('/')[-1],
                'path': path,
                'type': project_type,
                'type_name': type_info.get('name', project_type),
                'status': real_status,
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

                # Природа типа. Без этих полей потребитель не может
                # отличить клиент от модуля и понять, что ставится
                # внутрь клиента через composer, а что клонируется
                # как отдельный сервер.
                'is_client': bool(info.get('is_client')),
                'is_module': bool(info.get('is_module')),

                # Данные модуля (при is_module = true)
                'composer_package': info.get('composer_package'),
                'module_path': info.get('module_path'),
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

        result = do_install(form_data, API_SESSION)

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

        result = do_start({'server_id': server_id}, API_SESSION)

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

        result = do_stop({'server_id': server_id}, API_SESSION)

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

        result = do_remove({'server_id': server_id}, API_SESSION)

        if isinstance(result, tuple):
            result, status = result
            return result, status

        return result

    except Exception as e:
        logger.error(f"API remove_server error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@api.route('/servers/<path:server_id>/update', methods=['POST'])
@require_api_key
def update_server(server_id):
    """Обновить сервер по стратегии его типа из SERVER_TYPES.

    Фазы: preflight -> backup -> pull -> deps -> docker-конфиг -> migrate
          -> restart -> verify, с откатом при провале проверки.

    Тело запроса (JSON или form):
        dry_run       1 — только проверка, ничего не применяется
        project_type  подсказка, если записи нет в реестре
    """
    try:
        from files.web.sections.servers import update_server as do_update

        payload = request.get_json(force=True, silent=True) or {}
        if not payload:
            payload = {k: v for k, v in request.form.items()}
        payload['server_id'] = server_id

        result = do_update(payload, API_SESSION)

        if isinstance(result, tuple):
            result, status = result
            return result, status

        status = 200 if result.get('status') == 'success' else 400
        return jsonify(result), status

    except Exception as e:
        logger.error(f"API update_server error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@api.route('/servers/<path:server_id>/update/plan', methods=['GET'])
@require_api_key
def update_server_plan(server_id):
    """План обновления: какая стратегия и какие фазы выполнятся."""
    try:
        from files.web.sections.servers import update_plan

        result = update_plan({'server_id': server_id}, API_SESSION)
        status = 200 if result.get('status') == 'success' else 400
        return jsonify(result), status

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api.route('/servers/<path:server_id>/update/preflight', methods=['GET'])
@require_api_key
def update_server_preflight(server_id):
    """Фаза 0 без изменений: коммиты, ветка, грязное дерево, что приедет."""
    try:
        from files.web.sections.servers import update_preflight

        result = update_preflight({'server_id': server_id}, API_SESSION)
        status = 200 if result.get('status') == 'success' else 400
        return jsonify(result), status

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api.route('/servers/update-clients', methods=['POST'])
@require_api_key
def update_all_clients():
    """Обновить все клиенты из реестра — по стратегии каждого типа.

    По умолчанию dry_run по всем: показываем, что изменится, ничего не трогая.
    Тело: {"apply": 1, "project_type": "clientv2"} — применить (опционально фильтр).
    """
    try:
        from files.web.sections.servers import update_all_clients as do_update_all

        payload = request.get_json(force=True, silent=True) or {}
        if not payload:
            payload = {k: v for k, v in request.form.items()}

        result = do_update_all(payload, API_SESSION)
        status = 200 if result.get('status') == 'success' else 409
        return jsonify(result), status

    except Exception as e:
        logger.error(f"API update_all_clients error: {e}")
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
        result = do_list_drives({}, API_SESSION)
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
        result = do_list_folders({'path': path}, API_SESSION)
        if isinstance(result, tuple):
            result, status = result
            return result, status
        return result
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ======================== МОДУЛИ ========================
# Модуль ставится внутрь клиента через composer require на хосте.
# Отдельный префикс /servers/modules, чтобы путь модуля не путался
# с путём сервера: /servers/<path>/update относится к серверу,
# а /servers/modules/install - к модулю.


@api.route('/servers/modules', methods=['GET'])
@require_api_key
def list_modules():
    """Типы модулей, которые можно поставить внутрь клиента"""
    try:
        from files.configs.server_types import SERVER_TYPES, get_sorted_server_types

        modules = []
        for key, info in get_sorted_server_types():
            if not info.get('is_module'):
                continue
            modules.append({
                'key': key,
                'name': info.get('name', key),
                'description': info.get('description', ''),
                'composer_package': info.get('composer_package'),
                'module_path': info.get('module_path'),
                'default_folder': info.get('default_folder', key),
            })

        return jsonify({'success': True, 'modules': modules, 'count': len(modules)})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api.route('/servers/modules/hosts', methods=['GET'])
@require_api_key
def module_hosts():
    """Клиенты, в которые можно поставить модуль"""
    try:
        server_type = request.args.get('server_type', '').strip()

        if not server_type:
            return jsonify({'success': False, 'error': 'server_type required'}), 400

        from files.web.sections.servers import list_module_hosts as do_hosts

        result = do_hosts({'server_type': server_type}, API_SESSION)

        if isinstance(result, tuple):
            result, status = result
            return result, status

        return result

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api.route('/servers/modules/install', methods=['POST'])
@require_api_key
def install_module_api():
    """Поставить модуль внутрь клиента"""
    try:
        data = request.get_json(force=True, silent=True) or {}
        server_type = data.get('server_type', '').strip()
        host_path = data.get('host_path', '').strip()

        if not server_type or not host_path:
            return jsonify({'success': False,
                            'error': 'server_type and host_path required'}), 400

        from files.web.sections.servers import install_module as do_install

        result = do_install({'server_type': server_type, 'host_path': host_path},
                            API_SESSION)

        if isinstance(result, tuple):
            result, status = result
            return result, status

        return result

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api.route('/servers/modules/update', methods=['POST'])
@require_api_key
def update_module_api():
    """Обновить модуль (в т.ч. перенести его в другого клиента)"""
    try:
        data = request.get_json(force=True, silent=True) or {}
        server_type = data.get('server_type', '').strip()
        host_path = data.get('host_path', '').strip()
        dry_run = data.get('dry_run', False)

        if not server_type:
            return jsonify({'success': False, 'error': 'server_type required'}), 400

        payload = {'server_type': server_type, 'dry_run': 'true' if dry_run else 'false'}

        if host_path:
            payload['host_path'] = host_path

        from files.web.sections.servers import update_module as do_update

        result = do_update(payload, API_SESSION)

        if isinstance(result, tuple):
            result, status = result
            return result, status

        return result

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
