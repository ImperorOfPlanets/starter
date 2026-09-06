# files/web/sections/servers.py
"""
РЎРµРєС†РёСЏ СѓРїСЂР°РІР»РµРЅРёСЏ СЃРµСЂРІРµСЂР°РјРё
- РЈСЃС‚Р°РЅРѕРІРєР° СЃРµСЂРІРµСЂРѕРІ РёР· server_types.py
- РЈРїСЂР°РІР»РµРЅРёРµ СЃРµСЂРІРµСЂР°РјРё С‡РµСЂРµР· servers.json
"""

import os
import shutil
import subprocess
from pathlib import Path
from flask import render_template, jsonify, session

from files.core.utils.globalVars_utils import get_global
from files.core.utils.loader_utils import get
from files.core.utils.log_utils import LogManager

logger = LogManager.get_logger('web-servers')


def _subprocess_kwargs(timeout=10):
    """.kwargs РґР»СЏ subprocess вЂ” СЃРєСЂС‹С‚РёРµ РѕРєРѕРЅ РЅР° Windows"""
    kwargs = {'capture_output': True, 'text': True, 'timeout': timeout}
    if get_global('os') == 'Windows':
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = subprocess.SW_HIDE
        kwargs['startupinfo'] = si
    return kwargs

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
    """РџСЂРѕРІРµСЂСЏРµС‚ СЂРµР°Р»СЊРЅС‹Р№ СЃС‚Р°С‚СѓСЃ СЃРµСЂРІРµСЂР° РїРѕ Docker РєРѕРЅС‚РµР№РЅРµСЂР°Рј"""
    docker_mod = get('docker')
    if not docker_mod:
        return 'unknown'

    # РџСЂРѕРІРµСЂСЏРµРј СѓСЃС‚Р°РЅРѕРІР»РµРЅ Р»Рё Docker (РєРµС€РёСЂСѓРµС‚СЃСЏ С‡РµСЂРµР· set_global РІ РјРѕРґСѓР»Рµ)
    try:
        docker_installed = docker_mod.check_docker_installed()
    except Exception:
        return 'no_docker'

    if not docker_installed:
        return 'no_docker'

    # РџСЂРѕРІРµСЂСЏРµРј РµСЃС‚СЊ Р»Рё docker-compose.yml
    compose_path = Path(server_path) / 'docker' / 'docker-compose.yml'
    if not compose_path.exists():
        return 'no_compose'

    # РћРїСЂРµРґРµР»СЏРµРј РёРјСЏ РєРѕРЅС‚РµР№РЅРµСЂР° РїРѕ С‚РёРїСѓ СЃРµСЂРІРµСЂР°
    container_name = project_type.replace('_', '-')

    # РџСЂРѕРІРµСЂСЏРµРј СЃС‚Р°С‚СѓСЃ РєРѕРЅС‚РµР№РЅРµСЂР°
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

    # РљРѕРЅС‚РµР№РЅРµСЂР° РЅРµС‚ вЂ” РїСЂРѕРІРµСЂСЏРµРј РµСЃС‚СЊ Р»Рё РІРѕРѕР±С‰Рµ РєРѕРЅС‚РµР№РЅРµСЂС‹ РІ compose
    try:
        # РџСЂРѕРІРµСЂСЏРµРј С‡РµСЂРµР· docker compose ps
        import subprocess
        kw = _subprocess_kwargs(10)
        result = subprocess.run(
            ['docker', 'compose', '-f', str(compose_path), 'ps', '-a', '--format', '{{.State}}'],
            **kw
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
    """РџРѕР»СѓС‡Р°РµС‚ СЃРµСЂРІРµСЂС‹ СѓСЃС‚Р°РЅРѕРІР»РµРЅРЅС‹Рµ С‡РµСЂРµР· СЃС‚Р°СЂС‚РµСЂ СЃ СЂРµР°Р»СЊРЅС‹Рј СЃС‚Р°С‚СѓСЃРѕРј Docker"""
    user = session_obj.get('user') or session_obj.get('user_info')

    if user:
        registry = get('registry')
        if registry:
            from files.configs.server_types import SERVER_TYPES
            data = registry.load_registry()
            projects = data.get('projects', [])
            servers = []
            for p in projects:
                # РџРѕРєР°Р·С‹РІР°РµРј С‚РѕР»СЊРєРѕ РїСЂРѕРµРєС‚С‹, СѓСЃС‚Р°РЅРѕРІР»РµРЅРЅС‹Рµ С‡РµСЂРµР· СЃС‚Р°СЂС‚РµСЂ
                if not p.get('installed_by_starter', False):
                    continue

                path = p.get('path', '')
                project_type = p.get('project_type', 'unknown')

                # РџСЂРѕРІРµСЂСЏРµРј СЂРµР°Р»СЊРЅС‹Р№ СЃС‚Р°С‚СѓСЃ
                real_status = _check_server_status(path, project_type)

                # РћР±РЅРѕРІР»СЏРµРј СЃС‚Р°С‚СѓСЃ РІ СЂРµРµСЃС‚СЂРµ РµСЃР»Рё РёР·РјРµРЅРёР»СЃСЏ
                registry_status = p.get('status', 'unknown')
                if real_status != registry_status and real_status != 'unknown':
                    registry.update_project_status(path, real_status)

                # РџРѕР»СѓС‡Р°РµРј info РёР· server_types
                type_info = SERVER_TYPES.get(project_type, {})
                has_web_interface = type_info.get('has_web_interface', False)

                # РџСЂРѕРІРµСЂСЏРµРј git Рё РѕР±РЅРѕРІР»РµРЅРёСЏ
                has_git = False
                has_update = False
                code_path = Path(path) / 'code'
                if (code_path / '.git').exists():
                    has_git = True
                    try:
                        import subprocess
                        kw = _subprocess_kwargs(5)
                        # РџСЂРѕРІРµСЂСЏРµРј remote URL
                        remote_url = subprocess.run(
                            ['git', 'remote', 'get-url', 'origin'],
                            cwd=str(code_path), **kw
                        ).stdout.strip()
                        if remote_url:
                            # Fetch Рё СЃСЂР°РІРЅРёРІР°РµРј РєРѕРјРјРёС‚С‹
                            subprocess.run(
                                ['git', 'fetch', '--quiet'],
                                cwd=str(code_path), **_subprocess_kwargs(10)
                            )
                            local = subprocess.run(
                                ['git', 'rev-parse', 'HEAD'],
                                cwd=str(code_path), **kw
                            ).stdout.strip()
                            remote_hash = subprocess.run(
                                ['git', 'rev-parse', '@{u}'],
                                cwd=str(code_path), **kw
                            ).stdout.strip()
                            has_update = bool(remote_hash) and local != remote_hash
                    except Exception:
                        pass

                servers.append({
                    'id': path,
                    'name': path.split('\\')[-1] if '\\' in path else path.split('/')[-1] if '/' in path else path,
                    'path': path,
                    'type': project_type,
                    'status': real_status,
                    'port': p.get('port', 0),
                    'subnet_octet': p.get('subnet_octet', 0),
                    'has_web_interface': has_web_interface,
                    'has_git': has_git,
                    'has_update': has_update,
                })
            return servers

    return []


def index(data, session_obj):
    user = session_obj.get('user') or session_obj.get('user_info')
    if not user:
        return {'status': 'error', 'message': 'Unauthorized'}), 401

    servers = _get_user_servers(session_obj)
    logger.info(f"index: user={user}, servers count={len(servers)}")

    # РџРѕР»СѓС‡Р°РµРј РѕР±СЉРµРґРёРЅС‘РЅРЅС‹Р№ СЃРїРёСЃРѕРє СЃРµСЂРІРµСЂРѕРІ (Р»РѕРєР°Р»СЊРЅС‹Рµ + API)
    merged_types = _get_merged_server_types(session_obj)

    logger.info(f"Merged keys: {list(merged_types.keys())}")

    # РЎРµСЂРІРµСЂС‹ РґРѕСЃС‚СѓРїРЅС‹Рµ Р±РµР· Р·Р°СЏРІРѕРє
    base_keys = set()
    for key, info in merged_types.items():
        if not info.get('requires_auth', False):
            base_keys.add(key)

    # Р•СЃР»Рё Р°РІС‚РѕСЂРёР·РѕРІР°РЅ вЂ” РґРѕР±Р°РІР»СЏРµРј РѕРґРѕР±СЂРµРЅРЅС‹Рµ Р·Р°СЏРІРєРё
    approved_keys = set()
    if user:
        approved_keys = _get_approved_server_keys(session_obj)

    allowed_keys = base_keys | approved_keys
    logger.info(f"base_keys={base_keys}, approved_keys={approved_keys}, allowed_keys={allowed_keys}")

    server_types = [(k, v) for k, v in sorted(merged_types.items(), key=lambda x: x[1].get('order', 999)) if k in allowed_keys]

    can_manage = True

    # РџСЂРѕРІРµСЂСЏРµРј СЃС‚Р°С‚СѓСЃ reverse-proxy
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
        return {'status': 'error', 'message': 'Unauthorized'}), 401
    servers = _get_user_servers(session_obj)
    return 


def _get_approved_server_keys(session_obj):
    """РџРѕР»СѓС‡Р°РµС‚ РѕРґРѕР±СЂРµРЅРЅС‹Рµ С‚РёРїС‹ СЃРµСЂРІРµСЂРѕРІ РёР· myidon.site РїРѕ Р·Р°СЏРІРєР°Рј РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ"""
    oauth_token = session_obj.get('oauth_token')
    if not oauth_token:
        return set()

    try:
        from files.core.software.default.serverapi import fetch_user_servers, fetch_available_servers
        user_servers = fetch_user_servers(oauth_token)
        available = fetch_available_servers(oauth_token)

        if not user_servers:
            return set()

        # РЎРѕР±РёСЂР°РµРј slug РёР· user_servers
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
                # РџРѕРїСЂРѕР±РѕРІР°С‚СЊ match РїРѕ РІСЃРµРј РїРѕР»СЏРј
                search_text = f"{server_name} {desc} {project}".lower().strip()
                for api_server in available:
                    api_slug = api_server.get('slug', '')
                    api_name = (api_server.get('name') or '').lower().strip()
                    if (search_text and api_name and api_name in search_text) or \
                       (search_text and api_slug and api_slug in search_text):
                        keys.add(api_slug)
                        logger.info(f"Matched user server to API slug '{api_slug}'")
                        break

        # Fallback: РµСЃР»Рё РµСЃС‚СЊ Р·Р°СЏРІРєРё РЅРѕ РЅРё РѕРґРЅР° РЅРµ СЃРјСЌС‚С‡РёР»Р°СЃСЊ вЂ”
        # РїРѕРєР°Р·С‹РІР°РµРј РІСЃРµ СЃРµСЂРІРµСЂС‹ С‚СЂРµР±СѓСЋС‰РёРµ auth (СЂР°Р· СѓР¶ Р·Р°СЏРІРєР° РѕРґРѕР±СЂРµРЅР°)
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
    """РџРѕР»СѓС‡Р°РµС‚ РѕР±СЉРµРґРёРЅС‘РЅРЅС‹Р№ СЃРїРёСЃРѕРє СЃРµСЂРІРµСЂРѕРІ: Р»РѕРєР°Р»СЊРЅС‹Р№ + API"""
    from files.configs.server_types import SERVER_TYPES, get_sorted_server_types

    oauth_token = session_obj.get('oauth_token')

    # Р•СЃР»Рё РЅРµС‚ С‚РѕРєРµРЅР° вЂ” РІРѕР·РІСЂР°С‰Р°РµРј С‚РѕР»СЊРєРѕ Р»РѕРєР°Р»СЊРЅС‹Рµ
    if not oauth_token:
        return {k: v for k, v in get_sorted_server_types()}

    try:
        from files.core.software.default.serverapi import fetch_available_servers, fetch_user_servers, merge_server_types

        api_servers = fetch_available_servers(oauth_token)
        user_servers = fetch_user_servers(oauth_token)

        # РЎРѕР±РёСЂР°РµРј approved_keys РР— USER-SERVERS (С‚РµРїРµСЂСЊ С‚Р°Рј slug!)
        approved_keys = set()
        for s in user_servers:
            slug = s.get('slug')
            if slug:
                approved_keys.add(slug)

        if api_servers:
            # API РґРѕСЃС‚СѓРїРµРЅ вЂ” merge СЃ СЂРµРїРѕР·РёС‚РѕСЂРёСЏРјРё
            merged = merge_server_types(SERVER_TYPES, api_servers, user_servers, approved_keys)
            logger.info(f"Merged with API: {len(merged)} total, approved={approved_keys}")
            return merged
        elif approved_keys:
            # API РЅРµРґРѕСЃС‚СѓРїРµРЅ (500), РЅРѕ user-servers РѕС‚РґР°Р» slug'Рё СЃ СЂРµРїРѕР·РёС‚РѕСЂРёСЏРјРё
            logger.info(f"API unavailable, using user-servers slugs: {approved_keys}")
            merged = dict({k: v for k, v in get_sorted_server_types()})
            for s in user_servers:
                slug = s.get('slug')
                if slug and slug not in merged:
                    # Р¤РѕСЂРјРёСЂСѓРµРј repository РёР· user-servers
                    repos = s.get('repositories', [])
                    repository = None
                    if repos:
                        repo = repos[0]
                        repository = {
                            'url': repo.get('url', ''),
                            'branch': repo.get('branch', 'main'),
                            'auth_type': repo.get('auth_type', 'token'),
                            'credentials': repo.get('credentials', ''),
                            'name': repo.get('name', 'РћСЃРЅРѕРІРЅРѕР№'),
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

    # РџРѕР»СѓС‡Р°РµРј РѕР±СЉРµРґРёРЅС‘РЅРЅС‹Р№ СЃРїРёСЃРѕРє СЃРµСЂРІРµСЂРѕРІ (Р»РѕРєР°Р»СЊРЅС‹Рµ + API)
    merged_types = _get_merged_server_types(session_obj)

    # РЎРµСЂРІРµСЂС‹ РґРѕСЃС‚СѓРїРЅС‹Рµ Р±РµР· Р·Р°СЏРІРѕРє
    base_keys = set()
    for key, info in merged_types.items():
        if not info.get('requires_auth', False):
            base_keys.add(key)

    # Р•СЃР»Рё Р°РІС‚РѕСЂРёР·РѕРІР°РЅ вЂ” РґРѕР±Р°РІР»СЏРµРј РѕРґРѕР±СЂРµРЅРЅС‹Рµ Р·Р°СЏРІРєРё
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
    return 


def _clone_repository(repo_url: str, repository: dict, target_dir: Path, logger, log_file_path: str = None) -> dict:
    """
    РљР»РѕРЅРёСЂСѓРµС‚ СЂРµРїРѕР·РёС‚РѕСЂРёР№ СЃ РїРѕРґРґРµСЂР¶РєРѕР№ Р°РІС‚РѕСЂРёР·Р°С†РёРё Рё РїРѕС‚РѕРєРѕРІС‹Рј РІС‹РІРѕРґРѕРј
    """
    import subprocess
    import urllib.parse

    branch = repository.get('branch', 'main')
    auth_type = repository.get('auth_type', '')
    credentials = repository.get('credentials', '')

    # Р¤РѕСЂРјРёСЂСѓРµРј URL СЃ Р°РІС‚РѕСЂРёР·Р°С†РёРµР№
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
            kw = _subprocess_kwargs(120)
            kw['env'] = env
            result = subprocess.run(
                ['git', 'clone', '--branch', branch, '--depth', '1', clone_url, str(target_dir)],
                **kw
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
        return {'status': 'error', 'message': 'Unauthorized'}), 401

    server_type = data.get('server_type', '').strip()
    install_path = data.get('path', '').strip()
    server_name = data.get('name', '').strip()
    force = data.get('force', 'false') == 'true'

    if not server_type or not install_path:
        return 

    # РџРѕР»СѓС‡Р°РµРј РѕР±СЉРµРґРёРЅС‘РЅРЅС‹Р№ СЃРїРёСЃРѕРє СЃРµСЂРІРµСЂРѕРІ (Р»РѕРєР°Р»СЊРЅС‹Рµ + API)
    merged_types = _get_merged_server_types(session_obj)

    if server_type not in merged_types:
        return 

    type_info = merged_types[server_type]
    server_path = Path(install_path)
    docker_path = server_path / 'docker'
    code_path = server_path / 'code'

    # РџСЂРѕРІРµСЂСЏРµРј РЅРµ РїСѓСЃС‚Р°СЏ Р»Рё РїР°РїРєР°
    is_reinstall = False
    if server_path.exists() and list(server_path.iterdir()):
        if not force:
            return {
                'status': 'error',
                'message': f'РџР°РїРєР° {install_path} РЅРµ РїСѓСЃС‚Р°СЏ. Р’РєР»СЋС‡РёС‚Рµ РїРµСЂРµСѓСЃС‚Р°РЅРѕРІРєСѓ.',
                'code': 'NOT_EMPTY',
                'need_force': True
            })
        is_reinstall = True

    try:
        if is_reinstall:
            # РћСЃС‚Р°РЅР°РІР»РёРІР°РµРј РєРѕРЅС‚РµР№РЅРµСЂС‹ РµСЃР»Рё РµСЃС‚СЊ docker-compose
            compose_file = docker_path / 'docker-compose.yml'
            if compose_file.exists():
                import subprocess
                try:
                    kw = _subprocess_kwargs(30)
                    subprocess.run(
                        ['docker', 'compose', '-f', str(compose_file), 'down'],
                        **kw
                    )
                except Exception:
                    pass

        server_path.mkdir(parents=True, exist_ok=True)
        docker_path.mkdir(exist_ok=True)
        code_path.mkdir(exist_ok=True)

        # РљР»РѕРЅРёСЂСѓРµРј РёР· СЂРµРїРѕР·РёС‚РѕСЂРёСЏ
        repository = type_info.get('repository', {})
        repo_url = repository.get('url', '') if isinstance(repository, dict) else ''
        if repo_url and not repo_url.startswith('https://github.com/your-org'):
            import subprocess
            clone_result = _clone_repository(repo_url, repository, code_path, logger)
            if not clone_result.get('success'):
                # Р’ РїСЂРѕРґР°РєС€РµРЅРµ вЂ” РѕС€РёР±РєР° РµСЃР»Рё clone РЅРµ СѓРґР°Р»СЃСЏ
                return {
                    'status': 'error', 
                    'message': f'РћС€РёР±РєР° РєР»РѕРЅРёСЂРѕРІР°РЅРёСЏ СЂРµРїРѕР·РёС‚РѕСЂРёСЏ: {clone_result.get("error", "unknown")}'
                })
        else:
            return {
                'status': 'error',
                'message': 'Р РµРїРѕР·РёС‚РѕСЂРёР№ РЅРµ РЅР°СЃС‚СЂРѕРµРЅ РґР»СЏ СЌС‚РѕРіРѕ СЃРµСЂРІРµСЂР°'
            })

        # Р’С‹РґРµР»СЏРµРј РїРѕРґСЃРµС‚СЊ РµСЃР»Рё РЅСѓР¶РЅР° (РЅРµ РґР»СЏ reverse-proxy)
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

        # docker-compose.example Р”РћР›Р–Р•Рќ Р±С‹С‚СЊ РІ СЂРµРїРѕР·РёС‚РѕСЂРёРё
        # РС‰РµРј РІ СЂР°Р·РЅС‹С… РјРµСЃС‚Р°С…: code/docker/, code/, РїСЂРѕСЃС‚Рѕ docker/
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

            # РљРѕРїРёСЂСѓРµРј .env.example РµСЃР»Рё РµСЃС‚СЊ СЂСЏРґРѕРј
            env_example_src = compose_example.parent / '.env.example'
            if env_example_src.exists():
                shutil.copy2(env_example_src, docker_path / '.env.example')

            # РџРѕРґСЃС‚Р°РІР»СЏРµРј Р’РЎР• РїРµСЂРµРјРµРЅРЅС‹Рµ РёР· .env РІ docker-compose.yml
            compose_path = docker_path / 'docker-compose.yml'
            content = compose_path.read_text(encoding='utf-8')

            # РћР±СЏР·Р°С‚РµР»СЊРЅС‹Рµ РїРѕРґСЃС‚Р°РЅРѕРІРєРё
            content = content.replace('${PROJECTNAME}', project_name)
            content = content.replace('${DOCKER_NETWORK_PREFIX}', f"172.{subnet_octet}" if subnet_octet > 0 else "")

            # Р§РёС‚Р°РµРј .env Рё РїРѕРґСЃС‚Р°РІР»СЏРµРј РІСЃРµ РїРµСЂРµРјРµРЅРЅС‹Рµ
            env_path = docker_path / '.env'
            if env_path.exists():
                env_vars = {}
                for line in env_path.read_text(encoding='utf-8').splitlines():
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, _, value = line.partition('=')
                        env_vars[key.strip()] = value.strip()

                for key, value in env_vars.items():
                    placeholder = '${' + key + '}'
                    if placeholder in content:
                        content = content.replace(placeholder, value)
                        logger.info(f"Substituted {placeholder} = {value[:30]}...")

            compose_path.write_text(content, encoding='utf-8')
            logger.info(f"Copied docker-compose.example from {compose_example}")
        else:
            # РќР•Рў docker-compose.example вЂ” РѕС€РёР±РєР° РґР»СЏ РїСЂРѕРґР°РєС€РµРЅР°
            return {
                'status': 'error',
                'message': 'docker-compose.example РЅРµ РЅР°Р№РґРµРЅ РІ СЂРµРїРѕР·РёС‚РѕСЂРёРё. РџСЂРѕРІРµСЂСЊС‚Рµ СЃС‚СЂСѓРєС‚СѓСЂСѓ РїСЂРѕРµРєС‚Р°.'
            })
            (docker_path / 'docker-compose.yml').write_text(compose_content, encoding='utf-8')

        # Р“РµРЅРµСЂРёСЂСѓРµРј .env РµСЃР»Рё РЅРµ СЃРєРѕРїРёСЂРѕРІР°РЅ
        if not (docker_path / '.env.example').exists():
            env_example = _generate_env_example(server_type, type_info, server_name or type_info['name'], subnet_octet, port, str(server_path))
            (docker_path / '.env.example').write_text(env_example, encoding='utf-8')
        if not (docker_path / '.env').exists():
            env_example = _generate_env_example(server_type, type_info, server_name or type_info['name'], subnet_octet, port, str(server_path))
            (docker_path / '.env').write_text(env_example, encoding='utf-8')

        # РџРѕРґСЃС‚Р°РІР»СЏРµРј СЂРµР°Р»СЊРЅС‹Рµ РїСѓС‚Рё РёР· server_path РІ .env
        env_path = docker_path / '.env'
        if env_path.exists():
            env_content = env_path.read_text(encoding='utf-8')
            env_content = env_content.replace('${PATH_APP_CODE}', str(server_path / 'code'))
            env_content = env_content.replace('${PATH_APP_DOCKER}', str(server_path / 'docker'))
            env_content = env_content.replace('${PATH_APP_DOCKER_LOGS}', str(server_path / 'docker' / 'logs'))
            env_content = env_content.replace('${PATH_APP_PROJECT}', str(server_path / 'code'))
            env_path.write_text(env_content, encoding='utf-8')

        # Р РµРіРёСЃС‚СЂРёСЂСѓРµРј С‡РµСЂРµР· RegistryModule
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

        action = 'РџРµСЂРµСѓСЃС‚Р°РЅРѕРІР»РµРЅ' if is_reinstall else 'РЈСЃС‚Р°РЅРѕРІР»РµРЅ'
        return 

    except Exception as e:
        logger.error(f"Install server error: {e}")
        return 


def list_drives(data, session_obj):
    """РЎРїРёСЃРѕРє РґРѕСЃС‚СѓРїРЅС‹С… РґРёСЃРєРѕРІ (Windows) РёР»Рё С‚РѕС‡РµРє РјРѕРЅС‚РёСЂРѕРІР°РЅРёСЏ (Linux/Mac)"""
    user = session_obj.get('user') or session_obj.get('user_info')
    if not user:
        return {'status': 'error', 'message': 'Unauthorized'}), 401

    import os
    import shutil

    drives = []

    if os.name == 'nt':
        # Windows - РїРµСЂРµС‡РёСЃР»СЏРµРј РґРёСЃРєРё
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
                        'label': f"{letter}: ({round(free / (1024**3), 1)} GB СЃРІРѕР±РѕРґРЅРѕ)"
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
        # Linux/Mac - РїРѕРєР°Р·С‹РІР°РµРј РєРѕСЂРµРЅСЊ Рё С‚РѕС‡РєРё РјРѕРЅС‚РёСЂРѕРІР°РЅРёСЏ
        try:
            total, free = shutil.disk_usage('/')
            drives.append({
                'letter': '/',
                'path': '/',
                'total_gb': round(total / (1024**3), 1),
                'free_gb': round(free / (1024**3), 1),
                'label': f"/ ({round(free / (1024**3), 1)} GB СЃРІРѕР±РѕРґРЅРѕ)"
            })
        except Exception:
            drives.append({
                'letter': '/',
                'path': '/',
                'total_gb': 0,
                'free_gb': 0,
                'label': '/'
            })

        # Р”РѕР±Р°РІР»СЏРµРј /home РµСЃР»Рё СЃСѓС‰РµСЃС‚РІСѓРµС‚
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

    return 


def list_folders(data, session_obj):
    """РЎРїРёСЃРѕРє РїР°РїРѕРє РІ РґРёСЂРµРєС‚РѕСЂРёРё"""
    user = session_obj.get('user') or session_obj.get('user_info')
    if not user:
        return {'status': 'error', 'message': 'Unauthorized'}), 401

    path = data.get('path', '').strip()
    if not path:
        return 

    import os

    p = Path(path)
    if not p.exists():
        return 

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
        return 
    except OSError as e:
        return 

    # РћРїСЂРµРґРµР»СЏРµРј СЂРѕРґРёС‚РµР»СЊСЃРєСѓСЋ РґРёСЂРµРєС‚РѕСЂРёСЋ
    try:
        parent = str(p.parent) if str(p) != str(p.root) and str(p) != '/' else None
    except Exception:
        parent = None

    return 


def create_folder(data, session_obj):
    """РЎРѕР·РґР°С‚СЊ РЅРѕРІСѓСЋ РїР°РїРєСѓ"""
    user = session_obj.get('user') or session_obj.get('user_info')
    if not user:
        return {'status': 'error', 'message': 'Unauthorized'}), 401

    path = data.get('path', '').strip()
    if not path:
        return 

    p = Path(path)

    if p.exists():
        return 

    try:
        p.mkdir(parents=True, exist_ok=True)
        logger.info(f"Folder created: {path}")
        return 
    except PermissionError:
        return 
    except OSError as e:
        return 


def _generate_compose(server_type, type_info, subnet_octet=0, port=None):
    """Р“РµРЅРµСЂРёСЂСѓРµС‚ docker-compose.yml СЃ СЃРµС‚СЊСЋ Рё РїРѕРґСЃРµС‚СЊСЋ"""
    name = server_type.replace('_', '-')
    port = port or type_info.get('default_port', 8000)
    network_prefix = f"172.{subnet_octet}" if subnet_octet > 0 else ""

    # Р‘Р°Р·РѕРІС‹Р№ СЃРµСЂРІРёСЃ
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

    # Р”РѕР±Р°РІР»СЏРµРј СЃРµС‚СЊ РµСЃР»Рё РІС‹РґРµР»РµРЅ РѕРєС‚РµС‚
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


def _generate_env_example(server_type, type_info, server_name, subnet_octet=0, port=None, server_path=''):
    """Р“РµРЅРµСЂРёСЂСѓРµС‚ .env.example СЃ РїРµСЂРµРјРµРЅРЅС‹РјРё РґР»СЏ docker-compose"""
    port = port or type_info.get('default_port', 8000)
    network_prefix = f"172.{subnet_octet}" if subnet_octet > 0 else ""
    project_name = server_type.replace('_', '-')

    env = f"""# {type_info['name']}
PROJECTNAME={project_name}
SERVER_TYPE={server_type}
SERVER_NAME={server_name}
SERVER_PORT={port}

# Docker Network
DOCKER_NETWORK_PREFIX={network_prefix}

# РџСѓС‚Рё (РїР»РµР№СЃС…РѕР»РґРµСЂС‹ вЂ” РїРѕРґСЃС‚Р°РІР»СЏСЋС‚СЃСЏ РїСЂРё СѓСЃС‚Р°РЅРѕРІРєРµ)
PATH_APP_DOCKER=${PATH_APP_DOCKER}
PATH_APP_DOCKER_LOGS=${PATH_APP_DOCKER_LOGS}
PATH_APP_CODE=${PATH_APP_CODE}
PATH_APP_PROJECT=${PATH_APP_PROJECT}

# Р”РѕРјРµРЅ
NGINX_DOMAIN=localhost
MAX_BODY_SIZE=100M

# VPN
VPN_REQUIRED=optional
VPN_USERNAME=
VPN_PASSWORD=

# PHP
PHP_UPLOAD_MAX_FILESIZE=50M
PHP_POST_MAX_SIZE=50M
PHP_FPM_PM=dynamic
PHP_FPM_MAX_CHILDREN=50
PHP_FPM_MEMORY_LIMIT=256M

# App
APP_ENV=local
APP_DEBUG=true
APP_URL=https://localhost
APP_LOCALE=ru
CACHE_STORE=database
QUEUE_CONNECTION=database

# Database
DB_CONNECTION=mariadb
DB_HOST=mariadb-{project_name}
DB_PORT=3306
DB_DATABASE=temp
DB_USERNAME=root
DB_PASSWORD=root
DB_DATA_PATH=./data/mysql

# Redis
REDIS_HOST=redis-{project_name}
REDIS_PORT=6379
REDIS_PASSWORD=null
REDIS_DATA_PATH=./db/redis

# Qdrant
QDRANT_HOST=http://qdrant-{project_name}:6333
QDRANT_COLLECTION=embeddings
QDRANT_TIMEOUT=30
QDRANT_DATA_PATH=./db/qdrant

# Reverb
REVERB_APP_ID=
REVERB_APP_KEY=
REVERB_APP_SECRET=
REVERB_HOST=
REVERB_PORT=443
REVERB_SCHEME=https
REVERB_DEBUG=true
REVERB_APP_MAX_MESSAGE_SIZE=1048576
PORT_REVERB=443

# OAuth
OAUTH_CLIENT_ID=
OAUTH_SECRET=
OAUTH_REDIRECT_URI=
"""

    # Р”РѕР±Р°РІР»СЏРµРј СЃРїРµС†РёС„РёС‡РЅС‹Рµ РїРµСЂРµРјРµРЅРЅС‹Рµ
    if server_type == 'wecom':
        env += """
# WeCom
WECOM_CORP_ID=your_corp_id
WECOM_CORP_SECRET=your_corp_secret
WECOM_AGENT_ID=your_agent_id
WECOM_TOKEN=your_webhook_token
WECOM_ENCODING_AES_KEY=your_encoding_aes_key
"""

    return env


def _get_server_env_path(server_path):
    """Р’РѕР·РІСЂР°С‰Р°РµС‚ РїСѓС‚СЊ Рє .env С„Р°Р№Р»Сѓ СЃРµСЂРІРµСЂР°"""
    return Path(server_path) / 'docker' / '.env'


def _read_server_env(server_path):
    """Р§РёС‚Р°РµС‚ env РїРµСЂРµРјРµРЅРЅС‹Рµ СЃРµСЂРІРµСЂР°"""
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
    """Р—Р°РїРёСЃС‹РІР°РµС‚ env РїРµСЂРµРјРµРЅРЅС‹Рµ СЃРµСЂРІРµСЂР°"""
    env_path = _get_server_env_path(server_path)
    with open(env_path, 'w', encoding='utf-8') as f:
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")


def get_server_config(data, session_obj):
    """РџРѕР»СѓС‡РёС‚СЊ РєРѕРЅС„РёРіСѓСЂР°С†РёСЋ (env РїРµСЂРµРјРµРЅРЅС‹Рµ) СЃРµСЂРІРµСЂР°"""
    user = session_obj.get('user') or session_obj.get('user_info')
    if not user:
        return {'status': 'error', 'message': 'Unauthorized'}), 401

    server_path = data.get('server_id')
    if not server_path:
        return 

    env_vars = _read_server_env(server_path)
    return 


def save_server_config(data, session_obj):
    """РЎРѕС…СЂР°РЅРёС‚СЊ РєРѕРЅС„РёРіСѓСЂР°С†РёСЋ (env РїРµСЂРµРјРµРЅРЅС‹Рµ) СЃРµСЂРІРµСЂР°"""
    user = session_obj.get('user') or session_obj.get('user_info')
    if not user:
        return {'status': 'error', 'message': 'Unauthorized'}), 401

    server_path = data.get('server_id')
    if not server_path:
        return 

    # РЎРѕР±РёСЂР°РµРј env РїРµСЂРµРјРµРЅРЅС‹Рµ РёР· РґР°РЅРЅС‹С…
    env_vars = {}
    for key, value in data.items():
        if key not in ('server_id', 'action', 'section') and not key.startswith('_'):
            env_vars[key] = value

    if env_vars:
        _write_server_env(server_path, env_vars)
        return 
    return 


def start_server(data, session_obj):
    """Р—Р°РїСѓСЃС‚РёС‚СЊ СЃРµСЂРІРµСЂ С‡РµСЂРµР· Docker Compose"""
    import subprocess
    user = session_obj.get('user') or session_obj.get('user_info')
    if not user:
        return {'status': 'error', 'message': 'Unauthorized'}), 401

    server_id = data.get('server_id')
    if not server_id:
        return 

    registry = get('registry')
    if not registry:
        return 

    reg_data = registry.load_registry()
    server = next((s for s in reg_data.get('projects', []) if s.get('path') == server_id), None)
    if not server:
        return 

    server_path = server.get('path')
    docker_path = os.path.join(server_path, 'docker')
    if not os.path.exists(docker_path):
        return 

    compose_file = os.path.join(docker_path, 'docker-compose.yml')
    if not os.path.exists(compose_file):
        return 

    try:
        kw = _subprocess_kwargs(120)
        result = subprocess.run(
            ['docker', 'compose', 'up', '-d'],
            cwd=docker_path, **kw
        )
        if result.returncode == 0:
            server['status'] = 'running'
            registry.save_registry(reg_data)
            return 
        else:
            return 
    except Exception as e:
        logger.error(f"Error starting server: {e}")
        return 


def stop_server(data, session_obj):
    """РћСЃС‚Р°РЅРѕРІРёС‚СЊ СЃРµСЂРІРµСЂ С‡РµСЂРµР· Docker Compose"""
    import subprocess
    user = session_obj.get('user') or session_obj.get('user_info')
    if not user:
        return {'status': 'error', 'message': 'Unauthorized'}), 401

    server_id = data.get('server_id')
    if not server_id:
        return 

    # РС‰РµРј СЃРµСЂРІРµСЂ РІ СЂРµРµСЃС‚СЂРµ
    registry = get('registry')
    if not registry:
        return 

    reg_data = registry.load_registry()
    server = next((s for s in reg_data.get('projects', []) if s.get('path') == server_id), None)
    if not server:
        return 

    server_path = server.get('path')
    docker_path = os.path.join(server_path, 'docker')
    if not os.path.exists(docker_path):
        return 

    try:
        kw = _subprocess_kwargs(60)
        result = subprocess.run(
            ['docker', 'compose', 'down'],
            cwd=docker_path, **kw
        )
        if result.returncode == 0:
            # РћР±РЅРѕРІР»СЏРµРј СЃС‚Р°С‚СѓСЃ РІ СЂРµРµСЃС‚СЂРµ
            server['status'] = 'stopped'
            registry.save_registry(reg_data)
            return 
        else:
            return 
    except Exception as e:
        logger.error(f"Error stopping server: {e}")
        return 


def remove_server(data, session_obj):
    user = session_obj.get('user') or session_obj.get('user_info')
    if not user:
        return {'status': 'error', 'message': 'Unauthorized'}), 401

    server_id = data.get('server_id')
    if not server_id:
        return 

    # РћСЃС‚Р°РЅР°РІР»РёРІР°РµРј РєРѕРЅС‚РµР№РЅРµСЂС‹ РµСЃР»Рё РµСЃС‚СЊ docker-compose
    server_path = Path(server_id)
    compose_file = server_path / 'docker' / 'docker-compose.yml'
    if compose_file.exists():
        try:
            kw = _subprocess_kwargs(30)
            subprocess.run(
                ['docker', 'compose', '-f', str(compose_file), 'down', '-v'],
                **kw
            )
        except Exception:
            pass

    # РЈРґР°Р»СЏРµРј РёР· СЂРµРµСЃС‚СЂР°
    registry = get('registry')
    if registry:
        reg_data = registry.load_registry()
        reg_data['projects'] = [p for p in reg_data['projects'] if p.get('path') != server_id]
        registry.save_registry(reg_data)

    # РЈРґР°Р»СЏРµРј РїР°РїРєСѓ СЃРµСЂРІРµСЂР°
    import shutil
    if server_path.exists():
        try:
            shutil.rmtree(server_path)
            return 
        except Exception as e:
            return 

    return 


def scan_path(data, session_obj):
    user = session_obj.get('user') or session_obj.get('user_info')
    if not user:
        return {'status': 'error', 'message': 'Unauthorized'}), 401

    path = data.get('path', '').strip()
    if not path:
        return 

    servers_mod = get('servers')
    if not servers_mod:
        return 

    scan = servers_mod.scan_directory(path)
    return 


def server_details(data, session_obj):
    user = session_obj.get('user') or session_obj.get('user_info')
    if not user:
        return {'status': 'error', 'message': 'Unauthorized'}), 401

    server_id = data.get('server_id')
    if not server_id:
        return 

    servers = _get_user_servers(session_obj)
    server = next((s for s in servers if str(s.get('id')) == str(server_id)), None)

    if not server:
        return 

    return 


def server_repo_info(data, session_obj):
    """РџРѕР»СѓС‡РёС‚СЊ РёРЅС„РѕСЂРјР°С†РёСЋ Рѕ СЂРµРїРѕР·РёС‚РѕСЂРёРё СЃРµСЂРІРµСЂР°"""
    user = session_obj.get('user') or session_obj.get('user_info')
    if not user:
        return {'status': 'error', 'message': 'Unauthorized'}

    server_id = data.get('server_id')
    if not server_id:
        return {'status': 'error', 'message': 'Server ID required'}

    import subprocess

    server_path = Path(server_id)
    code_path = server_path / 'code'

    if not (code_path / '.git').exists():
        return {'status': 'success', 'repo': None, 'message': 'Not a git repository'}

    try:
        kw = _subprocess_kwargs(5)
        url = subprocess.run(
            ['git', 'remote', 'get-url', 'origin'],
            cwd=str(code_path), **kw
        ).stdout.strip()

        branch = subprocess.run(
            ['git', 'branch', '--show-current'],
            cwd=str(code_path), **kw
        ).stdout.strip()

        commit = subprocess.run(
            ['git', 'log', '-1', '--format=%H'],
            cwd=str(code_path), **kw
        ).stdout.strip()

        commit_msg = subprocess.run(
            ['git', 'log', '-1', '--format=%s'],
            cwd=str(code_path), **kw
        ).stdout.strip()

        commit_date = subprocess.run(
            ['git', 'log', '-1', '--format=%ci'],
            cwd=str(code_path), **kw
        ).stdout.strip()

        return {
            'status': 'success',
            'repo': {
                'url': url,
                'branch': branch,
                'commit': commit[:12],
                'commit_full': commit,
                'commit_message': commit_msg,
                'commit_date': commit_date,
            }
        }
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


def update_server(data, session_obj):
    """РћР±РЅРѕРІРёС‚СЊ СЃРµСЂРІРµСЂ С‡РµСЂРµР· git pull"""
    user = session_obj.get('user') or session_obj.get('user_info')
    if not user:
        return {'status': 'error', 'message': 'Unauthorized'}

    server_id = data.get('server_id')
    if not server_id:
        return {'status': 'error', 'message': 'Server ID required'}

    import subprocess

    server_path = Path(server_id)
    code_path = server_path / 'code'

    if not (code_path / '.git').exists():
        return {'status': 'error', 'message': 'Not a git repository'}

    try:
        kw = _subprocess_kwargs(60)
        result = subprocess.run(
            ['git', 'pull'],
            cwd=str(code_path), **kw
        )

        if result.returncode == 0:
            compose_file = server_path / 'docker' / 'docker-compose.yml'
            if compose_file.exists():
                kw2 = _subprocess_kwargs(120)
                docker_result = subprocess.run(
                    ['docker', 'compose', 'up', '-d'],
                    cwd=str(server_path / 'docker'), **kw2
                )
                if docker_result.returncode == 0:
                    return {'status': 'success', 'message': 'РЎРµСЂРІРµСЂ РѕР±РЅРѕРІР»С‘РЅ Рё РїРµСЂРµР·Р°РїСѓС‰РµРЅ'}
                else:
                    return {'status': 'success', 'message': 'РљРѕРґ РѕР±РЅРѕРІР»С‘РЅ, РЅРѕ РѕС€РёР±РєР° РїРµСЂРµР·Р°РїСѓСЃРєР°: ' + docker_result.stderr[:300]}
            else:
                return {'status': 'success', 'message': 'РљРѕРґ РѕР±РЅРѕРІР»С‘РЅ: ' + result.stdout[:200]}
        else:
            return {'status': 'error', 'message': 'РћС€РёР±РєР° git pull: ' + result.stderr[:300]}

    except Exception as e:
        return {'status': 'error', 'message': str(e)}


def server_git_log(data, session_obj):
    """РџРѕР»СѓС‡РёС‚СЊ РїРѕСЃР»РµРґРЅРёРµ РєРѕРјРјРёС‚С‹ + СЃС‚Р°С‚СѓСЃ РѕР±РЅРѕРІР»РµРЅРёСЏ РёР· server_types"""
    user = session_obj.get('user') or session_obj.get('user_info')
    if not user:
        return {'status': 'error', 'message': 'Unauthorized'}

    server_id = data.get('server_id')
    if not server_id:
        return {'status': 'error', 'message': 'Server ID required'}

    import subprocess

    server_path = Path(server_id)
    code_path = server_path / 'code'

    if not (code_path / '.git').exists():
        return {'status': 'success', 'log': [], 'has_update': False, 'message': 'Not a git repository'}

    try:
        kw = _subprocess_kwargs(10)

        # РџРѕР»СѓС‡Р°РµРј URL remote
        remote_url = (subprocess.run(
            ['git', 'remote', 'get-url', 'origin'],
            cwd=str(code_path), **kw
        ).stdout or b'').decode().strip()

        # РџРѕР»СѓС‡Р°РµРј С‚РµРєСѓС‰РёР№ РєРѕРјРјРёС‚
        local_commit = (subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            cwd=str(code_path), **kw
        ).stdout or b'').decode().strip()

        # РџРѕР»СѓС‡Р°РµРј РІРµС‚РєСѓ
        branch = (subprocess.run(
            ['git', 'branch', '--show-current'],
            cwd=str(code_path), **kw
        ).stdout or b'').decode().strip()

        # Fetch remote Рё РїРѕР»СѓС‡Р°РµРј СѓРґР°Р»С‘РЅРЅС‹Р№ РєРѕРјРјРёС‚
        has_update = False
        remote_commit = ''
        if remote_url:
            subprocess.run(
                ['git', 'fetch', '--quiet'],
                cwd=str(code_path), **_subprocess_kwargs(15)
            )
            remote_commit = (subprocess.run(
                ['git', 'rev-parse', '@{u}'],
                cwd=str(code_path), **kw
            ).stdout or b'').decode().strip()
            has_update = bool(remote_commit) and local_commit != remote_commit

        # РџРѕР»СѓС‡Р°РµРј РїРѕСЃР»РµРґРЅРёРµ РєРѕРјРјРёС‚С‹
        result = subprocess.run(
            ['git', 'log', '-10', '--format=%H|%h|%s|%ci|%an'],
            cwd=str(code_path), **kw
        )

        log = []
        if result.returncode == 0 and result.stdout.strip():
            for line in result.stdout.strip().splitlines():
                parts = line.split('|', 4)
                if len(parts) >= 5:
                    log.append({
                        'hash': parts[0][:12],
                        'short': parts[1],
                        'message': parts[2],
                        'date': parts[3],
                        'author': parts[4],
                    })

        return {
            'status': 'success',
            'log': log,
            'has_update': has_update,
            'remote_url': remote_url,
            'local_commit': local_commit[:12],
            'remote_commit': remote_commit[:12] if remote_commit else '',
            'branch': branch,
        }
    except Exception as e:
        return {'status': 'error', 'message': str(e), 'log': [], 'has_update': False}


