# files/web/sections/servers.py
"""
Секция управления серверами
- Установка серверов из server_types.py
- Управление серверами через servers.json
"""

import os
import shutil
from pathlib import Path
from flask import render_template, jsonify, session

from files.core.utils.globalVars_utils import get_global
from files.core.utils.loader_utils import get
from files.core.utils.log_utils import LogManager

logger = LogManager.get_logger('web-servers')

this_section_in_control_panel = True
section_icon = "bi-hdd-rack"
section_name = "Servers"
section_order = 2


def t(key: str, **kwargs) -> str:
    i18n = get('i18n')
    if i18n and hasattr(i18n, 'translate'):
        return i18n.translate(key, **kwargs)
    return key


def _check_server_status(server_path, project_type):
    """Проверяет реальный статус сервера по Docker контейнерам"""
    docker_mod = get('docker')
    if not docker_mod:
        return 'unknown'

    # Проверяем установлен ли Docker
    try:
        docker_installed = docker_mod.check_docker_installed()
    except Exception:
        return 'no_docker'

    if not docker_installed:
        return 'no_docker'

    # Проверяем есть ли docker-compose.yml
    compose_path = Path(server_path) / 'docker' / 'docker-compose.yml'
    if not compose_path.exists():
        return 'no_compose'

    # Определяем имя контейнера по типу сервера
    container_name = project_type.replace('_', '-')

    # Проверяем статус контейнера
    try:
        status_info = docker_mod.get_container_status(container_name)
        if status_info:
            state = status_info.get('State', {})
            if state.get('Running', False):
                return 'running'
            elif state.get('Status') == 'created':
                return 'stopped'
            elif state.get('Status') == 'restarting':
                return 'restarting'
            else:
                return 'stopped'
    except Exception:
        pass

    # Контейнера нет — проверяем есть ли вообще контейнеры в compose
    try:
        # Проверяем через docker compose ps
        import subprocess
        result = subprocess.run(
            ['docker', 'compose', '-f', str(compose_path), 'ps', '-a', '--format', '{{.State}}'],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            states = result.stdout.strip().splitlines()
            if any(s == 'running' for s in states):
                return 'running'
            else:
                return 'stopped'
    except Exception:
        pass

    return 'not_deployed'


def _get_user_servers(session_obj):
    """Получает серверы установленные через стартер с реальным статусом Docker"""
    user = session_obj.get('user') or session_obj.get('user_info')

    if user:
        registry = get('registry')
        if registry:
            from files.configs.server_types import SERVER_TYPES
            data = registry.load_registry()
            projects = data.get('projects', [])
            servers = []
            for p in projects:
                # Показываем только проекты, установленные через стартер
                if not p.get('installed_by_starter', False):
                    continue

                path = p.get('path', '')
                project_type = p.get('project_type', 'unknown')

                # Проверяем реальный статус
                real_status = _check_server_status(path, project_type)

                # Обновляем статус в реестре если изменился
                registry_status = p.get('status', 'unknown')
                if real_status != registry_status and real_status != 'unknown':
                    registry.update_project_status(path, real_status)

                # Получаем info из server_types
                type_info = SERVER_TYPES.get(project_type, {})
                has_web_interface = type_info.get('has_web_interface', False)

                servers.append({
                    'id': path,
                    'name': path.split('\\')[-1] if '\\' in path else path.split('/')[-1] if '/' in path else path,
                    'path': path,
                    'type': project_type,
                    'status': real_status,
                    'port': p.get('port', 0),
                    'subnet_octet': p.get('subnet_octet', 0),
                    'has_web_interface': has_web_interface,
                })
            return servers

    return []


def index(data, session_obj):
    user = session_obj.get('user') or session_obj.get('user_info')
    if not user:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

    servers = _get_user_servers(session_obj)
    logger.info(f"index: user={user}, servers count={len(servers)}")

    # Получаем объединённый список серверов (локальные + API)
    merged_types = _get_merged_server_types(session_obj)

    logger.info(f"Merged keys: {list(merged_types.keys())}")

    # Серверы доступные без заявок
    base_keys = set()
    for key, info in merged_types.items():
        if not info.get('requires_auth', False):
            base_keys.add(key)

    # Если авторизован — добавляем одобренные заявки
    approved_keys = set()
    if user:
        approved_keys = _get_approved_server_keys(session_obj)

    allowed_keys = base_keys | approved_keys
    logger.info(f"base_keys={base_keys}, approved_keys={approved_keys}, allowed_keys={allowed_keys}")

    server_types = [(k, v) for k, v in sorted(merged_types.items(), key=lambda x: x[1].get('order', 999)) if k in allowed_keys]

    can_manage = True

    # Проверяем статус reverse-proxy
    reverse_proxy_status = None
    try:
        from files.core.software.default.reverse_proxy import ReverseProxyModule
        reverse_proxy_status = ReverseProxyModule.get_status()
    except Exception:
        pass

    return render_template(
        'sections/servers/index.html',
        servers=servers,
        server_types=server_types,
        user=user,
        can_manage=can_manage,
        reverse_proxy_status=reverse_proxy_status,
        t=t
    )


def list_servers(data, session_obj):
    user = session_obj.get('user') or session_obj.get('user_info')
    if not user:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
    servers = _get_user_servers(session_obj)
    return jsonify({'status': 'success', 'servers': servers})


def _get_approved_server_keys(session_obj):
    """Получает одобренные типы серверов из myidon.site по заявкам пользователя"""
    oauth_token = session_obj.get('oauth_token')
    if not oauth_token:
        return set()

    try:
        from files.core.software.default.serverapi import fetch_user_servers, fetch_available_servers
        user_servers = fetch_user_servers(oauth_token)
        available = fetch_available_servers(oauth_token)

        if not user_servers:
            return set()

        # Собираем slug из user_servers
        keys = set()
        for s in user_servers:
            st = s.get('server_type')
            slug = s.get('slug')
            server_name = s.get('server_name') or ''
            desc = s.get('description') or ''
            project = s.get('project') or ''

            if st:
                keys.add(st)
            elif slug:
                keys.add(slug)
            else:
                # Попробовать match по всем полям
                search_text = f"{server_name} {desc} {project}".lower().strip()
                for api_server in available:
                    api_slug = api_server.get('slug', '')
                    api_name = (api_server.get('name') or '').lower().strip()
                    if (search_text and api_name and api_name in search_text) or \
                       (search_text and api_slug and api_slug in search_text):
                        keys.add(api_slug)
                        logger.info(f"Matched user server to API slug '{api_slug}'")
                        break

        # Fallback: если есть заявки но ни одна не смэтчилась —
        # показываем все серверы требующие auth (раз уж заявка одобрена)
        if not keys and user_servers and available:
            logger.info(f"No match found, showing all auth-required servers (user has {len(user_servers)} approved)")
            for api_server in available:
                if api_server.get('requires_auth', False):
                    keys.add(api_server.get('slug', ''))

        logger.info(f"Approved server types from myidon.site: {keys}")
        return keys

    except Exception as e:
        logger.error(f"Error fetching approved servers from myidon.site: {e}")
        return set()


def _get_merged_server_types(session_obj):
    """Получает объединённый список серверов: локальный + API"""
    from files.configs.server_types import SERVER_TYPES, get_sorted_server_types

    oauth_token = session_obj.get('oauth_token')

    # Если нет токена — возвращаем только локальные
    if not oauth_token:
        return {k: v for k, v in get_sorted_server_types()}

    try:
        from files.core.software.default.serverapi import fetch_available_servers, fetch_user_servers, merge_server_types

        api_servers = fetch_available_servers(oauth_token)
        user_servers = fetch_user_servers(oauth_token)

        # Собираем approved_keys ИЗ USER-SERVERS (теперь там slug!)
        approved_keys = set()
        for s in user_servers:
            slug = s.get('slug')
            if slug:
                approved_keys.add(slug)

        if api_servers:
            # API доступен — merge с репозиториями
            merged = merge_server_types(SERVER_TYPES, api_servers, user_servers, approved_keys)
            logger.info(f"Merged with API: {len(merged)} total, approved={approved_keys}")
            return merged
        elif approved_keys:
            # API недоступен (500), но user-servers отдал slug'и с репозиториями
            logger.info(f"API unavailable, using user-servers slugs: {approved_keys}")
            merged = dict({k: v for k, v in get_sorted_server_types()})
            for s in user_servers:
                slug = s.get('slug')
                if slug and slug not in merged:
                    # Формируем repository из user-servers
                    repos = s.get('repositories', [])
                    repository = None
                    if repos:
                        repo = repos[0]
                        repository = {
                            'url': repo.get('url', ''),
                            'branch': repo.get('branch', 'main'),
                            'auth_type': repo.get('auth_type', 'token'),
                            'credentials': repo.get('credentials', ''),
                            'name': repo.get('name', 'Основной'),
                        }
                        logger.info(f"  Repository for {slug}: {repo.get('url')}, has_creds={bool(repo.get('credentials'))}")

                    merged[slug] = {
                        'name': s.get('name', slug),
                        'description': s.get('description', ''),
                        'requires_auth': s.get('requires_auth', True),
                        'requires_reverse_proxy': s.get('requires_reverse_proxy', False),
                        'has_web_interface': s.get('has_web_interface', False),
                        'default_port': s.get('default_port', 8000),
                        'order': s.get('order', 50),
                        'can_have_multiple': s.get('can_have_multiple', True),
                        'default_folder': slug,
                        'repository': repository,
                        'from_api': True,
                    }
                    logger.info(f"Added from user-servers: {slug} (repo={'YES' if repository else 'NO'})")
            return merged
        else:
            logger.info("No API servers, using local only")
            return {k: v for k, v in get_sorted_server_types()}

    except Exception as e:
        logger.error(f"Error merging server types: {e}")
        return {k: v for k, v in get_sorted_server_types()}


def list_server_types(data, session_obj):
    is_authorized = bool(session_obj.get('user') or session_obj.get('user_info'))

    # Получаем объединённый список серверов (локальные + API)
    merged_types = _get_merged_server_types(session_obj)

    # Серверы доступные без заявок
    base_keys = set()
    for key, info in merged_types.items():
        if not info.get('requires_auth', False):
            base_keys.add(key)

    # Если авторизован — добавляем одобренные заявки
    approved_keys = set()
    if is_authorized:
        approved_keys = _get_approved_server_keys(session_obj)

    allowed_keys = base_keys | approved_keys

    types = []
    for key, info in sorted(merged_types.items(), key=lambda x: x[1].get('order', 999)):
        if key not in allowed_keys:
            continue
        types.append({
            'key': key,
            'name': info['name'],
            'description': info.get('description', ''),
            'requires_reverse_proxy': info.get('requires_reverse_proxy', False),
            'requires_auth': info.get('requires_auth', False),
            'has_web_interface': info.get('has_web_interface', False),
            'can_have_multiple': info.get('can_have_multiple', True),
            'default_port': info.get('default_port'),
            'default_folder': info.get('default_folder', key),
            'from_application': key in approved_keys and key not in base_keys,
            'from_api': info.get('from_api', False),
            'repository': info.get('repository'),
        })
    return jsonify({'status': 'success', 'server_types': types})


def _clone_repository(repo_url: str, repository: dict, target_dir: Path, logger, log_file_path: str = None) -> dict:
    """
    Клонирует репозиторий с поддержкой авторизации и потоковым выводом
    """
    import subprocess
    import urllib.parse

    branch = repository.get('branch', 'main')
    auth_type = repository.get('auth_type', '')
    credentials = repository.get('credentials', '')

    # Формируем URL с авторизацией
    clone_url = repo_url
    if credentials and auth_type == 'token':
        parsed = urllib.parse.urlparse(repo_url)
        path_parts = parsed.path.strip('/').split('/')
        username = path_parts[1] if len(path_parts) >= 2 else 'oauth2'
        clone_url = f"https://{username}:{credentials}@{parsed.netloc}{parsed.path}"
    elif credentials and auth_type == 'basic':
        parsed = urllib.parse.urlparse(repo_url)
        clone_url = f"https://{credentials}@{parsed.netloc}{parsed.path}"

    logger.info(f"Cloning {repo_url} -> {target_dir}")

    try:
        import os
        from datetime import datetime
        env = os.environ.copy()
        env['GIT_TERMINAL_PROMPT'] = '0'
        env['GIT_ASKPASS'] = 'echo'
        env['GIT_EDITOR'] = 'echo'

        if log_file_path:
            log_file = open(log_file_path, 'w', encoding='utf-8')
            
            def log_msg(msg):
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                line = f"[{timestamp}] {msg}"
                log_file.write(line + '\n')
                log_file.flush()
                logger.info(msg)
            
            log_msg(f"Starting git clone...")
            log_msg(f"Repository: {repo_url}")
            log_msg(f"Branch: {branch}")
            log_msg(f"Target: {target_dir}")
            
            process = subprocess.Popen(
                ['git', 'clone', '--branch', branch, '--depth', '1', clone_url, str(target_dir)],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1, env=env
            )
            
            for line in iter(process.stdout.readline, ''):
                if line:
                    log_msg(line.strip())
            
            return_code = process.wait()
            log_file.close()
            
            if return_code == 0:
                log_msg("Clone completed successfully!")
                return {'success': True}
            else:
                log_msg(f"Clone failed with exit code {return_code}")
                return {'success': False, 'error': f'Exit code {return_code}'}
        else:
            result = subprocess.run(
                ['git', 'clone', '--branch', branch, '--depth', '1', clone_url, str(target_dir)],
                capture_output=True, text=True, timeout=120, env=env
            )
            if result.returncode == 0:
                logger.info(f"Successfully cloned {repo_url}")
                return {'success': True, 'output': result.stdout}
            else:
                logger.error(f"Git clone failed: {result.stderr}")
                return {'success': False, 'error': result.stderr}

    except subprocess.TimeoutExpired:
        return {'success': False, 'error': 'Clone timed out (120s)'}
    except FileNotFoundError:
        return {'success': False, 'error': 'Git not installed'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def install_server(data, session_obj):
    user = session_obj.get('user') or session_obj.get('user_info')
    if not user:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

    server_type = data.get('server_type', '').strip()
    install_path = data.get('path', '').strip()
    server_name = data.get('name', '').strip()
    force = data.get('force', 'false') == 'true'

    if not server_type or not install_path:
        return jsonify({'status': 'error', 'message': 'server_type and path required'})

    # Получаем объединённый список серверов (локальные + API)
    merged_types = _get_merged_server_types(session_obj)

    if server_type not in merged_types:
        return jsonify({'status': 'error', 'message': f'Unknown server type: {server_type}'})

    type_info = merged_types[server_type]
    server_path = Path(install_path)
    docker_path = server_path / 'docker'
    code_path = server_path / 'code'

    # Проверяем не пустая ли папка
    is_reinstall = False
    if server_path.exists() and list(server_path.iterdir()):
        if not force:
            return jsonify({
                'status': 'error',
                'message': f'Папка {install_path} не пустая. Включите переустановку.',
                'code': 'NOT_EMPTY',
                'need_force': True
            })
        is_reinstall = True

    try:
        if is_reinstall:
            # Останавливаем контейнеры если есть docker-compose
            compose_file = docker_path / 'docker-compose.yml'
            if compose_file.exists():
                import subprocess
                try:
                    subprocess.run(
                        ['docker', 'compose', '-f', str(compose_file), 'down'],
                        capture_output=True, timeout=30
                    )
                except Exception:
                    pass

        server_path.mkdir(parents=True, exist_ok=True)
        docker_path.mkdir(exist_ok=True)
        code_path.mkdir(exist_ok=True)

        # Клонируем из репозитория
        repository = type_info.get('repository', {})
        repo_url = repository.get('url', '') if isinstance(repository, dict) else ''
        if repo_url and not repo_url.startswith('https://github.com/your-org'):
            import subprocess
            clone_result = _clone_repository(repo_url, repository, code_path, logger)
            if not clone_result.get('success'):
                # В продакшене — ошибка если clone не удался
                return jsonify({
                    'status': 'error', 
                    'message': f'Ошибка клонирования репозитория: {clone_result.get("error", "unknown")}'
                })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Репозиторий не настроен для этого сервера'
            })

        # Выделяем подсеть если нужна (не для reverse-proxy)
        subnet_octet = 0
        if not type_info.get('is_reverse_proxy', False):
            from files.core.oss.default.registry import RegistryModule
            used_octets = RegistryModule.get_used_octets(str(server_path))
            for octet in range(1, 255):
                if octet not in used_octets:
                    subnet_octet = octet
                    break

        port = type_info.get('default_port', 8000)
        project_name = server_type.replace('_', '-')

        # docker-compose.example ДОЛЖЕН быть в репозитории
        # Ищем в разных местах: code/docker/, code/, просто docker/
        compose_example = None
        for candidate in [
            server_path / 'code' / 'docker' / 'docker-compose.example',
            server_path / 'code' / 'docker-compose.example',
            server_path / 'docker' / 'docker-compose.example',
        ]:
            if candidate.exists():
                compose_example = candidate
                break
        
        if compose_example:
            import shutil
            shutil.copy2(compose_example, docker_path / 'docker-compose.yml')

            # Копируем .env.example если есть рядом
            env_example_src = compose_example.parent / '.env.example'
            if env_example_src.exists():
                shutil.copy2(env_example_src, docker_path / '.env.example')

            # Подставляем переменные
            compose_path = docker_path / 'docker-compose.yml'
            content = compose_path.read_text(encoding='utf-8')
            content = content.replace('${PROJECTNAME}', project_name)
            content = content.replace('${DOCKER_NETWORK_PREFIX}', f"172.{subnet_octet}" if subnet_octet > 0 else "")
            compose_path.write_text(content, encoding='utf-8')

            logger.info(f"Copied docker-compose.example from {compose_example}")
        else:
            # НЕТ docker-compose.example — ошибка для продакшена
            return jsonify({
                'status': 'error',
                'message': 'docker-compose.example не найден в репозитории. Проверьте структуру проекта.'
            })
            (docker_path / 'docker-compose.yml').write_text(compose_content, encoding='utf-8')

        # Генерируем .env если не скопирован
        if not (docker_path / '.env.example').exists():
            env_example = _generate_env_example(server_type, type_info, server_name or type_info['name'], subnet_octet, port)
            (docker_path / '.env.example').write_text(env_example, encoding='utf-8')
        if not (docker_path / '.env').exists():
            env_example = _generate_env_example(server_type, type_info, server_name or type_info['name'], subnet_octet, port)
            (docker_path / '.env').write_text(env_example, encoding='utf-8')

        # Регистрируем через RegistryModule
        registry = get('registry')
        if registry:
            registry.register_initializing(str(server_path))
            from files.core.oss.default.registry import RegistryModule
            reg = RegistryModule.load_registry()
            norm = str(Path(str(server_path)).resolve())
            for p in reg.get('projects', []):
                if p.get('path') == norm:
                    p['project_type'] = server_type
                    p['port'] = port
                    p['subnet_octet'] = subnet_octet
                    p['docker_network_prefix'] = f"172.{subnet_octet}" if subnet_octet > 0 else ""
                    p['installed_by_starter'] = True
                    break
            RegistryModule.save_registry(reg)
            logger.info(f"Server {'reinstalled' if is_reinstall else 'registered'}: {server_type} at {install_path} (subnet: {subnet_octet})")

        action = 'Переустановлен' if is_reinstall else 'Установлен'
        return jsonify({'status': 'success', 'message': f'{type_info["name"]} {action} в {install_path}'})

    except Exception as e:
        logger.error(f"Install server error: {e}")
        return jsonify({'status': 'error', 'message': str(e)})


def list_drives(data, session_obj):
    """Список доступных дисков (Windows) или точек монтирования (Linux/Mac)"""
    user = session_obj.get('user') or session_obj.get('user_info')
    if not user:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

    import os
    import shutil

    drives = []

    if os.name == 'nt':
        # Windows - перечисляем диски
        import string
        import ctypes
        bitmask = ctypes.windll.kernel32.GetLogicalDrives()
        for letter in string.ascii_uppercase:
            if bitmask & 1:
                drive_path = f"{letter}:\\"
                try:
                    total, free = shutil.disk_usage(drive_path)
                    drives.append({
                        'letter': letter,
                        'path': drive_path,
                        'total_gb': round(total / (1024**3), 1),
                        'free_gb': round(free / (1024**3), 1),
                        'label': f"{letter}: ({round(free / (1024**3), 1)} GB свободно)"
                    })
                except Exception:
                    drives.append({
                        'letter': letter,
                        'path': drive_path,
                        'total_gb': 0,
                        'free_gb': 0,
                        'label': f"{letter}:"
                    })
            bitmask >>= 1
    else:
        # Linux/Mac - показываем корень и точки монтирования
        try:
            total, free = shutil.disk_usage('/')
            drives.append({
                'letter': '/',
                'path': '/',
                'total_gb': round(total / (1024**3), 1),
                'free_gb': round(free / (1024**3), 1),
                'label': f"/ ({round(free / (1024**3), 1)} GB свободно)"
            })
        except Exception:
            drives.append({
                'letter': '/',
                'path': '/',
                'total_gb': 0,
                'free_gb': 0,
                'label': '/'
            })

        # Добавляем /home если существует
        home = os.path.expanduser('~')
        if home and home != '/' and os.path.exists(home):
            try:
                total, free = shutil.disk_usage(home)
                drives.append({
                    'letter': 'home',
                    'path': home,
                    'total_gb': round(total / (1024**3), 1),
                    'free_gb': round(free / (1024**3), 1),
                    'label': f"home ({round(free / (1024**3), 1)} GB)"
                })
            except Exception:
                pass

    return jsonify({'status': 'success', 'drives': drives})


def list_folders(data, session_obj):
    """Список папок в директории"""
    user = session_obj.get('user') or session_obj.get('user_info')
    if not user:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

    path = data.get('path', '').strip()
    if not path:
        return jsonify({'status': 'error', 'message': 'Path required'})

    import os

    p = Path(path)
    if not p.exists():
        return jsonify({'status': 'error', 'message': f'Path not found: {path}'})

    folders = []
    try:
        for item in sorted(p.iterdir()):
            if item.is_dir() and not item.name.startswith('.'):
                try:
                    folders.append({
                        'name': item.name,
                        'path': str(item),
                        'has_docker': (item / 'docker').exists(),
                        'has_code': (item / 'code').exists(),
                        'writable': os.access(str(item), os.W_OK),
                    })
                except (PermissionError, OSError):
                    folders.append({
                        'name': item.name,
                        'path': str(item),
                        'has_docker': False,
                        'has_code': False,
                        'writable': False,
                    })
    except PermissionError:
        return jsonify({'status': 'error', 'message': 'Permission denied', 'folders': [], 'current': str(p), 'parent': None})
    except OSError as e:
        return jsonify({'status': 'error', 'message': str(e), 'folders': [], 'current': str(p), 'parent': None})

    # Определяем родительскую директорию
    try:
        parent = str(p.parent) if str(p) != str(p.root) and str(p) != '/' else None
    except Exception:
        parent = None

    return jsonify({'status': 'success', 'folders': folders, 'current': str(p), 'parent': parent})


def create_folder(data, session_obj):
    """Создать новую папку"""
    user = session_obj.get('user') or session_obj.get('user_info')
    if not user:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

    path = data.get('path', '').strip()
    if not path:
        return jsonify({'status': 'error', 'message': 'Path required'})

    p = Path(path)

    if p.exists():
        return jsonify({'status': 'error', 'message': 'Папка уже существует'})

    try:
        p.mkdir(parents=True, exist_ok=True)
        logger.info(f"Folder created: {path}")
        return jsonify({'status': 'success', 'message': f'Папка создана: {p.name}'})
    except PermissionError:
        return jsonify({'status': 'error', 'message': 'Нет прав на создание папки'})
    except OSError as e:
        return jsonify({'status': 'error', 'message': f'Ошибка: {str(e)}'})


def _generate_compose(server_type, type_info, subnet_octet=0, port=None):
    """Генерирует docker-compose.yml с сетью и подсетью"""
    name = server_type.replace('_', '-')
    port = port or type_info.get('default_port', 8000)
    network_prefix = f"172.{subnet_octet}" if subnet_octet > 0 else ""

    # Базовый сервис
    services = f"""services:
  {name}:
    image: alpine:latest
    container_name: {name}
    restart: unless-stopped
    ports:
      - "{port}:{port}"
    volumes:
      - ../code:/app
    working_dir: /app
    command: sh -c "echo '{type_info['name']} is running' && sleep infinity"
"""

    # Добавляем сеть если выделен октет
    if subnet_octet > 0:
        services += f"""
    networks:
      {name}net:
        ipv4_address: {network_prefix}.0.2

networks:
  {name}net:
    driver: bridge
    ipam:
      config:
        - subnet: {network_prefix}.0.0/16
          gateway: {network_prefix}.0.1
"""

    return services


def _generate_env_example(server_type, type_info, server_name, subnet_octet=0, port=None):
    """Генерирует .env.example с переменными для docker-compose"""
    port = port or type_info.get('default_port', 8000)
    network_prefix = f"172.{subnet_octet}" if subnet_octet > 0 else ""

    env = f"""# {type_info['name']}
PROJECTNAME={server_type.replace('_', '-')}
SERVER_TYPE={server_type}
SERVER_NAME={server_name}
SERVER_PORT={port}

# Docker Network
DOCKER_NETWORK_PREFIX={network_prefix}
"""

    # Добавляем специфичные переменные для WeCom
    if server_type == 'wecom':
        env += """
# WeCom Configuration
# Получи данные в WeCom Admin Console:
# https://work.weixin.qq.com/wework_admin/frame
WECOM_CORP_ID=your_corp_id
WECOM_CORP_SECRET=your_corp_secret
WECOM_AGENT_ID=your_agent_id
WECOM_TOKEN=your_webhook_token
WECOM_ENCODING_AES_KEY=your_encoding_aes_key
"""

    return env


def _get_server_env_path(server_path):
    """Возвращает путь к .env файлу сервера"""
    return Path(server_path) / 'docker' / '.env'


def _read_server_env(server_path):
    """Читает env переменные сервера"""
    env_path = _get_server_env_path(server_path)
    if not env_path.exists():
        return {}
    env_vars = {}
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, _, value = line.partition('=')
                env_vars[key.strip()] = value.strip()
    return env_vars


def _write_server_env(server_path, env_vars):
    """Записывает env переменные сервера"""
    env_path = _get_server_env_path(server_path)
    with open(env_path, 'w', encoding='utf-8') as f:
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")


def get_server_config(data, session_obj):
    """Получить конфигурацию (env переменные) сервера"""
    user = session_obj.get('user') or session_obj.get('user_info')
    if not user:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

    server_path = data.get('server_id')
    if not server_path:
        return jsonify({'status': 'error', 'message': 'Server ID required'})

    env_vars = _read_server_env(server_path)
    return jsonify({'status': 'success', 'env': env_vars})


def save_server_config(data, session_obj):
    """Сохранить конфигурацию (env переменные) сервера"""
    user = session_obj.get('user') or session_obj.get('user_info')
    if not user:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

    server_path = data.get('server_id')
    if not server_path:
        return jsonify({'status': 'error', 'message': 'Server ID required'})

    # Собираем env переменные из данных
    env_vars = {}
    for key, value in data.items():
        if key not in ('server_id', 'action', 'section') and not key.startswith('_'):
            env_vars[key] = value

    if env_vars:
        _write_server_env(server_path, env_vars)
        return jsonify({'status': 'success', 'message': 'Конфигурация сохранена'})
    return jsonify({'status': 'error', 'message': 'Нет данных для сохранения'})


def start_server(data, session_obj):
    """Запустить сервер через Docker Compose"""
    import subprocess
    user = session_obj.get('user') or session_obj.get('user_info')
    if not user:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

    server_id = data.get('server_id')
    if not server_id:
        return jsonify({'status': 'error', 'message': 'Server ID required'})

    # Ищем сервер в реестре
    registry = get('registry')
    if not registry:
        return jsonify({'status': 'error', 'message': 'Registry not found'})

    reg_data = registry.load_registry()
    server = next((s for s in reg_data.get('projects', []) if s.get('path') == server_id), None)
    if not server:
        return jsonify({'status': 'error', 'message': 'Server not found'})

    server_path = server.get('path')
    docker_path = os.path.join(server_path, 'docker')
    if not os.path.exists(docker_path):
        return jsonify({'status': 'error', 'message': 'Docker directory not found'})

    compose_file = os.path.join(docker_path, 'docker-compose.yml')
    if not os.path.exists(compose_file):
        return jsonify({'status': 'error', 'message': 'docker-compose.yml not found'})

    try:
        result = subprocess.run(
            ['docker-compose', 'up', '-d'],
            cwd=docker_path,
            capture_output=True,
            text=True,
            timeout=120
        )
        if result.returncode == 0:
            # Обновляем статус в реестре
            server['status'] = 'running'
            registry.save_registry(reg_data)
            return jsonify({'status': 'success', 'message': 'Сервер запущен'})
        else:
            return jsonify({'status': 'error', 'message': f'Ошибка: {result.stderr[:500]}'})
    except Exception as e:
        logger.error(f"Error starting server: {e}")
        return jsonify({'status': 'error', 'message': f'Ошибка запуска: {str(e)}'})


def stop_server(data, session_obj):
    """Остановить сервер через Docker Compose"""
    import subprocess
    user = session_obj.get('user') or session_obj.get('user_info')
    if not user:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

    server_id = data.get('server_id')
    if not server_id:
        return jsonify({'status': 'error', 'message': 'Server ID required'})

    # Ищем сервер в реестре
    registry = get('registry')
    if not registry:
        return jsonify({'status': 'error', 'message': 'Registry not found'})

    reg_data = registry.load_registry()
    server = next((s for s in reg_data.get('projects', []) if s.get('path') == server_id), None)
    if not server:
        return jsonify({'status': 'error', 'message': 'Server not found'})

    server_path = server.get('path')
    docker_path = os.path.join(server_path, 'docker')
    if not os.path.exists(docker_path):
        return jsonify({'status': 'error', 'message': 'Docker directory not found'})

    try:
        result = subprocess.run(
            ['docker-compose', 'down'],
            cwd=docker_path,
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode == 0:
            # Обновляем статус в реестре
            server['status'] = 'stopped'
            registry.save_registry(reg_data)
            return jsonify({'status': 'success', 'message': 'Сервер остановлен'})
        else:
            return jsonify({'status': 'error', 'message': f'Ошибка: {result.stderr[:500]}'})
    except Exception as e:
        logger.error(f"Error stopping server: {e}")
        return jsonify({'status': 'error', 'message': f'Ошибка остановки: {str(e)}'})


def remove_server(data, session_obj):
    user = session_obj.get('user') or session_obj.get('user_info')
    if not user:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

    server_id = data.get('server_id')
    if not server_id:
        return jsonify({'status': 'error', 'message': 'Server ID required'})

    # Удаляем из реестра
    registry = get('registry')
    if registry:
        reg_data = registry.load_registry()
        reg_data['projects'] = [p for p in reg_data['projects'] if p.get('path') != server_id]
        registry.save_registry(reg_data)
        return jsonify({'status': 'success', 'message': 'Сервер удалён'})

    return jsonify({'status': 'error', 'message': 'Registry not found'})


def scan_path(data, session_obj):
    user = session_obj.get('user') or session_obj.get('user_info')
    if not user:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

    path = data.get('path', '').strip()
    if not path:
        return jsonify({'status': 'error', 'message': 'Path is required'})

    servers_mod = get('servers')
    if not servers_mod:
        return jsonify({'status': 'error', 'message': 'Servers module not found'})

    scan = servers_mod.scan_directory(path)
    return jsonify({'status': 'success', 'scan': scan})


def server_details(data, session_obj):
    user = session_obj.get('user') or session_obj.get('user_info')
    if not user:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

    server_id = data.get('server_id')
    if not server_id:
        return jsonify({'status': 'error', 'message': 'Server ID required'})

    servers = _get_user_servers(session_obj)
    server = next((s for s in servers if str(s.get('id')) == str(server_id)), None)

    if not server:
        return jsonify({'status': 'error', 'message': 'Server not found or access denied'})

    return jsonify({'status': 'success', 'server': server})
