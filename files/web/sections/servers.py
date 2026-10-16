# files/web/sections/servers.py
"""
Секция управления серверами
- Установка серверов из server_types.py
- Управление серверами через servers.json
"""

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Dict
from flask import render_template, jsonify, session

from files.core.utils.globalVars_utils import get_global
from files.core.utils.loader_utils import get
from files.core.utils.log_utils import LogManager

logger = LogManager.get_logger('web-servers')


def _subprocess_kwargs(timeout=10):
    """.kwargs для subprocess — скрытие окон на Windows, UTF-8 кодировка"""
    kwargs = {'capture_output': True, 'text': True, 'timeout': timeout, 'encoding': 'utf-8', 'errors': 'replace'}
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


def _compose_project_name(server_path, server_type: str) -> str:
    """Имя docker-compose проекта — из папки установки.

    Должно быть уникальным на каждый сервер, иначе контейнеры
    получат одинаковые container_name (php-<PROJECTNAME> и т.д.).
    Допустимы только [a-z0-9-], как того требует Docker.
    """
    raw = os.path.basename(str(server_path).rstrip('\\/'))
    name = re.sub(r'[^a-z0-9-]+', '-', raw.lower()).strip('-')
    if not name:
        name = re.sub(r'[^a-z0-9-]+', '-', str(server_type).lower()).strip('-')
    return name or 'server'


def _ensure_fingerprint(docker_path: Path, logger=None) -> str:
    """Стабильный идентификатор экземпляра сервера (клиента).

    Записывается в docker/.env как CLIENT_FINGERPRINT и дублируется в
    реестр. Нужен, чтобы отличать экземпляры клиентов независимо от пути:
    путь меняется при переезде, fingerprint — нет.

    force-переустановка пересоздаёт только code/, поэтому docker/.env с
    fingerprint переживает её — клиент предъявляет тот же идентификатор.
    Повторный вызов идемпотентен: если значение уже есть — возвращается оно.
    """
    import uuid

    env_path = Path(docker_path) / '.env'
    try:
        content = env_path.read_text(encoding='utf-8') if env_path.exists() else ''
    except Exception as e:
        if logger:
            logger.warning('Fingerprint: cannot read %s: %s', env_path, e)
        content = ''

    m = re.search(r'^CLIENT_FINGERPRINT=([A-Za-z0-9-]+)\s*$', content, flags=re.MULTILINE)
    if m and m.group(1).strip():
        return m.group(1).strip()

    fingerprint = uuid.uuid4().hex

    if env_path.exists():
        try:
            if content and not content.endswith('\n'):
                content += '\n'
            content += f'\n# Стабильный идентификатор экземпляра (starter). Не менять вручную.\nCLIENT_FINGERPRINT={fingerprint}\n'
            env_path.write_text(content, encoding='utf-8')
        except Exception as e:
            if logger:
                logger.warning('Fingerprint: cannot write %s: %s', env_path, e)

    if logger:
        logger.info('Fingerprint generated for %s: %s', docker_path, fingerprint)
    return fingerprint


def _compose_cmd(server_path, *args):
    """Команда docker compose с явным -p <имя папки>.

    Без -p compose берёт проект из имени папки с docker-compose.yml,
    а у всех серверов эта папка называется 'docker' — они начинают
    управлять одними и теми же контейнерами и затирают друг друга.
    """
    project = _compose_project_name(server_path, '')
    return ['docker', 'compose', '-p', project, *args]


def _compose_env(docker_path):
    """Окружение для docker compose — без «чужих» переменных стартера.

    Стартер пишет свой веб-порт в os.environ (starter.py: PORT=2000).
    У docker compose переменная окружения имеет приоритет над .env
    проекта, поэтому ${PORT:-80} в compose-resolved в порт панели (2000),
    а не в выделенный проекту (9000). Источник истины — docker/.env
    проекта: убираем из наследуемого окружения всё, что там задано,
    плюс служебные переменные compose.
    """
    env = os.environ.copy()
    for key in ('COMPOSE_FILE', 'COMPOSE_PROJECT_NAME', 'COMPOSE_PROFILES',
                'COMPOSE_CONVERT_WINDOWS_PATHS', 'COMPOSE_IGNORE_ORPHANS'):
        env.pop(key, None)
    try:
        env_path = Path(docker_path) / '.env'
        if env_path.exists():
            for line in env_path.read_text(encoding='utf-8', errors='replace').splitlines():
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    env.pop(line.partition('=')[0].strip(), None)
    except Exception:
        pass
    return env


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

    # Проверяем установлен ли Docker (кешируется через set_global в модуле)
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

    # Проверяем статус через docker compose ps (надёжнее чем искать по имени)
    try:
        import subprocess
        kw = _subprocess_kwargs(15)
        result = subprocess.run(
            ['docker', 'compose', '-p', _compose_project_name(compose_path.parent.parent, ''),
             '-f', str(compose_path), 'ps', '-a', '--format', '{{.State}}'],
            env=_compose_env(compose_path.parent),
            **kw
        )
        if result.returncode == 0 and result.stdout.strip():
            states = result.stdout.strip().splitlines()
            if any(s == 'running' for s in states):
                return 'running'
            elif any(s in ('created', 'exited') for s in states):
                return 'stopped'
            elif any(s == 'restarting' for s in states):
                return 'restarting'
            else:
                return 'stopped'
    except Exception:
        pass

    # Фолбэк — проверяем по имени контейнера
    container_name = project_type.replace('_', '-')
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

    return 'not_deployed'


def _project_files_exist(path: str) -> bool:
    """Проверяет, что папка проекта и её docker/код реально на месте.

    Реестр мог устареть (проект удалён/перенесён вручную) — тогда файлов
    нет, и сервер не должен считаться корректно установленным.
    """
    try:
        from pathlib import Path
        pp = Path(path)
        if not pp.is_dir():
            return False
        return ((pp / 'docker' / 'docker-compose.yml').exists()
                or (pp / 'src').is_dir())
    except Exception:
        return False


def _get_user_servers(session_obj):
    """Получает серверы установленные через стартер с реальным статусом Docker.

    Статусы опрашиваются фоновым ServerMonitorModule и кешируются в
    SQLite — здесь только быстрое чтение. Если кеш ещё не наполнен
    (первый запуск до фонового прохода), выполняется старый
    синхронный расчёт, а монитор параллельно наполняет кеш.
    """
    user = session_obj.get('user') or session_obj.get('user_info')
    if not user:
        return []

    # Быстрый путь: кеш фонового монитора (мгновенно)
    try:
        from files.core.oss.default.server_monitor import ServerMonitorModule
        cached = ServerMonitorModule.get_cached_servers()
        if cached is not None:
            return cached
        # Кеш пуст — будим монитор и считаем синхронно (один раз за жизнь)
        ServerMonitorModule.refresh_all(background=True)
    except Exception as e:
        logger.warning(f"server_monitor недоступен, синхронный расчёт: {e}")

    return _scan_user_servers_now(session_obj)


def _monitor_refresh_path(path):
    """Быстро перепроверяет один сервер в кеше монитора (после действия)"""
    try:
        import threading
        from files.core.oss.default.server_monitor import ServerMonitorModule
        threading.Thread(target=ServerMonitorModule.refresh_path,
                         args=(path,), daemon=True).start()
    except Exception as e:
        logger.warning(f"monitor refresh_path({path}) failed: {e}")


def _scan_user_servers_now(session_obj):
    """Синхронный полный расчёт статусов (фолбэк, когда кеша ещё нет)"""
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

                # Реестр мог устареть — если файлов проекта нет, помечаем ошибкой
                if not _project_files_exist(path):
                    real_status = 'missing_files'
                else:
                    # Проверяем реальный статус
                    real_status = _check_server_status(path, project_type)

                # Обновляем статус в реестре если изменился
                registry_status = p.get('status', 'unknown')
                if real_status != registry_status and real_status != 'unknown':
                    registry.update_project_status(path, real_status)

                # Получаем info из server_types
                type_info = SERVER_TYPES.get(project_type, {})
                has_web_interface = type_info.get('has_web_interface', False)

                # Проверяем git и обновления
                has_git = False
                has_update = False
                git_path = Path(path) / 'src'
                if not (git_path / '.git').exists() and (Path(path) / '.git').exists():
                    git_path = Path(path)
                if (git_path / '.git').exists():
                    has_git = True
                    try:
                        import subprocess
                        kw = _subprocess_kwargs(5)
                        # Проверяем remote URL
                        remote_url = subprocess.run(
                            ['git', 'remote', 'get-url', 'origin'],
                            cwd=str(git_path), **kw
                        ).stdout.strip()
                        if remote_url:
                            # Fetch и сравниваем коммиты
                            subprocess.run(
                                ['git', 'fetch', '--quiet'],
                                cwd=str(git_path), **_subprocess_kwargs(10)
                            )
                            local = subprocess.run(
                                ['git', 'rev-parse', 'HEAD'],
                                cwd=str(git_path), **kw
                            ).stdout.strip()
                            remote_hash = subprocess.run(
                                ['git', 'rev-parse', '@{u}'],
                                cwd=str(git_path), **kw
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
                    'port': _server_port(p.get('path', ''), p.get('port', 0)),
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

    # Получаем application_id из заявок пользователя
    user_applications = session_obj.get('user_applications', [])
    application_id = None
    for app in user_applications:
        if app.get('type') == 'server_type' and app.get('status') == 'approved':
            application_id = app.get('id')
            break
    
    # Если нет server_type заявки, берём первую одобренную
    if not application_id and user_applications:
        for app in user_applications:
            if app.get('status') == 'approved':
                application_id = app.get('id')
                break

    return render_template(
        'sections/servers/index.html',
        servers=servers,
        server_types=server_types,
        user=user,
        can_manage=can_manage,
        reverse_proxy_status=reverse_proxy_status,
        application_id=application_id,
        tailscale_domains=session_obj.get('tailscale_domains', []),
        t=t
    )


def list_servers(data, session_obj):
    user = session_obj.get('user') or session_obj.get('user_info')
    if not user:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

    force = data.get('force', False) in ('true', '1', True)

    # force — лишь сигнал «будь свежим»: будим фоновый монитор,
    # а сами читаем SQLite-кеш (мгновенно вместо docker/git на запросе)
    if force:
        try:
            from files.core.oss.default.server_monitor import ServerMonitorModule
            ServerMonitorModule.refresh_all(background=True)
        except Exception:
            pass

    servers = _get_user_servers(session_obj)
    resp = {'status': 'success', 'servers': servers}

    # Шапка панели: кеш на какое время и когда обновится
    try:
        from files.core.oss.default.server_monitor import ServerMonitorModule
        info = ServerMonitorModule.get_status()
        resp['cache'] = {
            'updated_at': info['updated_at'],
            'git_checked_at': info['git_checked_at'],
            'status_interval': info['status_interval'],
            'git_interval': info['git_interval'],
            'monitor_running': info['monitor_running'],
        }
    except Exception as e:
        logger.warning(f"monitor status unavailable: {e}")
        resp['cache'] = None

    return jsonify(resp)


def get_monitor_settings(data, session_obj):
    """Настройки мониторинга серверов.

    Интервал статусов живёт в расписании задачи планировщика
    server_status_refresh (управается из интерфейса); git_interval —
    в конфиге server_monitor.json.
    """
    user = session_obj.get('user') or session_obj.get('user_info')
    if not user:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

    try:
        from files.core.oss.default.server_monitor import ServerMonitorModule
        from files.core.oss.default.scheduler import SchedulerModule

        settings = ServerMonitorModule.get_settings()

        # эффективный интервал — из расписания задачи планировщика
        interval = settings.get('status_interval', 30)
        try:
            for t in SchedulerModule.get_tasks().get('tasks', []):
                if t['name'] == 'server_status_refresh':
                    interval = SchedulerModule.interval_seconds(t)
                    break
        except Exception:
            pass

        info = ServerMonitorModule.get_status()
        return jsonify({'status': 'success',
                        'settings': {'status_interval': interval,
                                     'git_interval': settings.get('git_interval', 600)},
                        'monitor_running': info['monitor_running']})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})


def save_monitor_settings(data, session_obj):
    """Сохраняет интервалы мониторинга (без рестарта).

    status_interval -> расписание задачи server_status_refresh в
    планировщике; git_interval -> server_monitor.json.
    """
    user = session_obj.get('user') or session_obj.get('user_info')
    if not user:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

    try:
        from files.core.oss.default.server_monitor import ServerMonitorModule
        from files.core.oss.default.scheduler import SchedulerModule

        # валидация/сохранение обоих значений (status_interval — фолбэк)
        settings = ServerMonitorModule.save_settings({
            'status_interval': data.get('status_interval'),
            'git_interval': data.get('git_interval'),
        })

        # интервал статусов -> расписание задачи планировщика
        seconds = settings['status_interval']
        task_data = {
            'name': 'server_status_refresh',
            'schedule': 'custom',
            'custom_schedule': str(seconds),
            'enabled': True,
        }
        res = SchedulerModule.update_task(task_data)
        if res.get('status') != 'success':
            # задачи ещё нет в конфиге — создаём с нужным расписанием
            SchedulerModule.add_task({
                'name': 'server_status_refresh',
                'enabled': True,
                'schedule': 'custom',
                'custom_schedule': str(seconds),
                'category': 'monitoring',
                'events': ['on_schedule'],
            })

        return jsonify({'status': 'success', 'settings': settings})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})


def _get_approved_server_keys(session_obj):
    """Получает одобренные типы серверов из заявок пользователя в сессии"""
    from files.configs.server_types import SERVER_TYPES

    # Сначала пробуем из заявок в сессии (быстрее)
    user_applications = session_obj.get('user_applications', [])
    if user_applications:
        keys = set()
        for app in user_applications:
            if app.get('status') != 'approved':
                continue

            data = app.get('data', {}) or {}
            app_type = app.get('type')

            # Собираем все возможные ключи серверного типа из заявки.
            # Одобренная заявка = доступ к этому типу сервера.
            candidates = []
            for field in ('server_type_keys', 'server_type_key',
                          'repository_type_key', 'server_type', 'slug', 'type_key'):
                value = data.get(field)
                if isinstance(value, list):
                    candidates.extend(value)
                elif value:
                    candidates.append(value)

            # Ключ может лежать и на верхнем уровне заявки
            for field in ('server_type_key', 'server_type'):
                value = app.get(field)
                if value:
                    candidates.append(value)

            for key in candidates:
                if key and key in SERVER_TYPES:
                    keys.add(key)

        # Валидируем по реально существующим типам — мусор вроде
        # 'server_type'/'business' в allowed_keys попадать не должен
        if keys:
            logger.info(f"Approved server types from applications: {keys}")
            return keys

        logger.info(f"No valid server types in applications (candidates: {candidates}), trying API")

    # Fallback: если нет заявок в сессии — пробуем API
    oauth_token = session_obj.get('oauth_token')
    if not oauth_token:
        return _all_auth_required_types(SERVER_TYPES)

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
        if not keys and user_servers:
            logger.info(f"No match found, showing all auth-required servers (user has {len(user_servers)} approved)")
            keys |= _all_auth_required_types(SERVER_TYPES)

        logger.info(f"Approved server types from myidon.site: {keys}")
        return keys

    except Exception as e:
        logger.error(f"Error fetching approved servers from myidon.site: {e}")
        return _all_auth_required_types(SERVER_TYPES)


def _all_auth_required_types(server_types: Dict) -> set:
    """Аварийный fallback: все типы серверов, требующие заявки.

    Используется, когда myidon.site не отдаёт user-servers (404)
    и в заявках нет явного server_type_key — чтобы раздел серверов
    оставался рабочим, а админ выдавал доступ вручную.
    """
    keys = {k for k, v in server_types.items() if v.get('requires_auth', False)}
    if keys:
        logger.info(f"Fallback: showing all {len(keys)} auth-required server types")
    return keys


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
        # Get current language for localized name/description
        current_lang = 'ru'
        try:
            i18n_mod = get('i18n')
            if i18n_mod:
                current_lang = i18n_mod.get_current_language()
        except Exception:
            pass

        lang_name = info.get(f'name_{current_lang}', info['name'])
        lang_desc = info.get(f'description_{current_lang}', info.get('description', ''))

        types.append({
            'key': key,
            'name': lang_name,
            'description': lang_desc,
            'requires_reverse_proxy': info.get('requires_reverse_proxy', False),
            'requires_auth': info.get('requires_auth', False),
            'has_web_interface': info.get('has_web_interface', False),
            'can_have_multiple': info.get('can_have_multiple', True),
            'default_port': info.get('default_port'),
            'default_folder': info.get('default_folder', key),
            'from_application': key in approved_keys and key not in base_keys,
            'from_api': info.get('from_api', False),
            'repository': info.get('repository'),
            'is_module': info.get('is_module', False),
            'composer_package': info.get('composer_package'),
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
            kw = _subprocess_kwargs(600)
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
        return {'success': False, 'error': 'Clone timed out (600s)'}
    except FileNotFoundError:
        return {'success': False, 'error': 'Git not installed'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def _find_composer():
    """Ищет composer на хосте — в PATH и в типовых местах.

    Composer не входит в PATH системного Python, поэтому ищем явно.
    """
    # 1. shutil.which по PATH
    found = shutil.which('composer')
    if found:
        return found

    # 2. php-composer.phar
    for base in (Path.home(), Path('C:/'), Path('C:/tools'), Path('C:/xampp')):
        for rel in ('composer.phar', 'composer/composer.phar',
                    'tools/composer/composer.phar', 'composer.phar'):
            p = base / rel
            if p.is_file():
                return str(p)

    # 3. .bat/.exe в PATH-подобных каталогах
    for d in os.environ.get('PATH', '').split(os.pathsep):
        if not d:
            continue
        for name in ('composer.bat', 'composer.exe', 'composer'):
            p = Path(d) / name
            if p.is_file():
                return str(p)
    return None


def _composer_cmd():
    """Команда запуска composer: .bat -> cmd /c, .phar -> php, иначе как есть."""
    exe = _find_composer()
    if not exe:
        return None
    if exe.lower().endswith('.phar'):
        return ['php', exe]
    if exe.lower().endswith('.bat'):
        return ['cmd', '/c', exe]
    return [exe]


def _module_hosts(session_obj, type_info):
    """Клиенты, в которые можно поставить модуль.

    Берём из реестра проекты, установленные стартером, у которых:
      - тип помечен is_client в server_types.py, либо
      - тип входит в installs_into модуля

    Так новый тип клиента подхватывается автоматически, без правок
    в каждом модуле.
    """
    from files.configs.server_types import SERVER_TYPES

    allowed = type_info.get('installs_into') or []
    registry = get('registry')
    hosts = []
    if not registry:
        return hosts

    try:
        projects = registry.load_registry().get('projects', [])
    except Exception:
        return hosts

    for p in projects:
        if not p.get('installed_by_starter'):
            continue
        ptype = p.get('project_type', '')
        path = p.get('path', '')
        if not path:
            continue

        is_client = SERVER_TYPES.get(ptype, {}).get('is_client', False)
        if not (is_client or ptype in allowed):
            continue

        # модуль ставится только туда, где есть src/composer.json
        if not (Path(path) / 'src' / 'composer.json').exists():
            continue

        hosts.append({
            'path': path,
            'name': Path(path).name,
            'project_type': ptype,
            'status': p.get('status', 'unknown'),
        })

    return hosts


def _module_installed_hosts(server_type, type_info):
    """Куда модуль уже установлен (папка vendor/imperor/<pkg>)."""
    package = type_info.get('composer_package', '')
    if not package:
        return []
    vendor_dir = package.replace('/', os.sep)
    registry = get('registry')
    if not registry:
        return []
    out = []
    try:
        projects = registry.load_registry().get('projects', [])
    except Exception:
        return out
    for p in projects:
        path = p.get('path', '')
        if path and (Path(path) / 'src' / 'vendor' / vendor_dir).exists():
            out.append(path)
    return out


def list_module_hosts(data, session_obj):
    """Клиенты, доступные для установки модуля + где модуль уже стоит."""
    user = session_obj.get('user') or session_obj.get('user_info')
    if not user:
        return {'status': 'error', 'message': 'Unauthorized'}

    server_type = (data.get('server_type') or '').strip()
    merged_types = _get_merged_server_types(session_obj)
    if server_type not in merged_types:
        return {'status': 'error', 'message': f'Unknown server type: {server_type}'}

    type_info = merged_types[server_type]
    if not type_info.get('is_module'):
        return {'status': 'error', 'message': f'{server_type} не является модулем'}

    return {
        'status': 'success',
        'package': type_info.get('composer_package'),
        'module_path': type_info.get('module_path'),
        'hosts': _module_hosts(session_obj, type_info),
        'installed_in': _module_installed_hosts(server_type, type_info),
    }


def install_module(data, session_obj):
    """Установка модуля внутрь клиента: composer require на хосте + перезапуск."""
    user = session_obj.get('user') or session_obj.get('user_info')
    if not user:
        return {'status': 'error', 'message': 'Unauthorized'}

    server_type = data.get('server_type', '').strip()
    host_path = data.get('host_path', '').strip()

    merged_types = _get_merged_server_types(session_obj)
    if server_type not in merged_types:
        return {'status': 'error', 'message': f'Unknown server type: {server_type}'}

    type_info = merged_types[server_type]
    package = type_info.get('composer_package')
    module_path = type_info.get('module_path')

    if not package:
        return {'status': 'error', 'message': f'{server_type}: composer_package не задан'}

    if not host_path:
        hosts = _module_hosts(session_obj, type_info)
        return {
            'status': 'select_host',
            'message': 'Выберите клиент для установки модуля',
            'server_type': server_type,
            'package': package,
            'hosts': hosts,
        }

    host = Path(host_path)
    code_dir = host / 'src'
    if not (code_dir / 'composer.json').exists():
        return {'status': 'error', 'message': f'В {host} нет src/composer.json'}

    # уже стоит в этом клиенте?
    vendor_dir = code_dir / 'vendor' / package.replace('/', os.sep)
    if vendor_dir.exists():
        return {
            'status': 'error',
            'message': f'{package} уже установлен в {host.name}',
            'code': 'ALREADY_INSTALLED',
        }

    # уже стоит в другом клиенте? — нужен перенос (заявка)
    others = [h for h in _module_installed_hosts(server_type, type_info)
              if str(h).lower() != str(host).lower()]
    if others:
        names = ', '.join(Path(h).name for h in others)
        return {
            'status': 'error',
            'message': f'{package} уже установлен в: {names}. '
                       f'Для переноса нужна заявка.',
            'code': 'TRANSFER_REQUIRES_APPLICATION',
            'installed_in': others,
        }

    # регистрируем path-репозиторий модуля, если его ещё нет
    cj_path = code_dir / 'composer.json'
    try:
        cj = json.loads(cj_path.read_text(encoding='utf-8'))
    except Exception as e:
        return {'status': 'error', 'message': f'Не читается composer.json: {e}'}

    repos = cj.setdefault('repositories', [])
    url = module_path or f'C:/control/{server_type.upper()}'
    if not any(r.get('url') == url for r in repos):
        repos.append({'type': 'path', 'url': url, 'options': {'symlink': False}})
        cj_path.write_text(json.dumps(cj, indent=4, ensure_ascii=False) + '\n', encoding='utf-8')
        logger.info(f"Added path repository {url} for {package}")

    if not Path(url).exists():
        return {'status': 'error', 'message': f'Каталог модуля не найден: {url}'}

    # composer на хосте — в контейнере распаковка занимает минуты
    composer = _composer_cmd()
    if not composer:
        return {'status': 'error', 'message': 'Composer не найден на хосте (PATH/composer.phar)'}

    logger.info(f"Installing {package} into {code_dir} via host composer: {composer}")
    try:
        kw = _subprocess_kwargs(900)
        proc = subprocess.run(
            composer + ['require', f'{package}:@dev', '--no-interaction',
                        '--working-dir=' + str(code_dir)],
            **kw
        )
    except FileNotFoundError:
        return {'status': 'error', 'message': f'Не удалось запустить: {composer[0]}'}
    except subprocess.TimeoutExpired:
        return {'status': 'error', 'message': 'composer require превысил 15 минут'}

    if proc.returncode != 0:
        tail = (proc.stdout or '')[-1500:]
        return {
            'status': 'error',
            'message': f'composer require завершился с кодом {proc.returncode}',
            'output': tail,
        }

    # Миграции модуля. На хосте PHP нет, поэтому artisan выполняется
    # внутри контейнера php-<project>. Ошибку не глотаем: без таблиц
    # модуль формально установлен, но не работает.
    project = _compose_project_name(host, '')
    container = 'php-' + project
    migrate_error = None

    try:
        mig = subprocess.run(
            ['docker', 'exec', container, 'php', 'artisan', 'migrate', '--force'],
            **_subprocess_kwargs(600)
        )
        if mig.returncode != 0:
            migrate_error = (mig.stderr or mig.stdout or '')[-1500:]
            logger.warning('artisan migrate failed in %s: %s', container, migrate_error)
    except Exception as e:
        migrate_error = str(e)
        logger.warning('artisan migrate could not run: %s', e)

    # перезапуск клиента, чтобы новые сервис-провайдеры и виды подхватились
    docker_path = host / 'docker'
    compose = docker_path / 'docker-compose.yml'
    if compose.exists():
        try:
            subprocess.run(
                _compose_cmd(host, 'up', '-d', '--force-recreate', 'php-' + project),
                cwd=str(docker_path), env=_compose_env(docker_path),
                **_subprocess_kwargs(300))
        except Exception as e:
            logger.warning('restart failed: %s', e)

    # отмечаем в реестре
    registry = get('registry')
    if registry:
        try:
            registry.add_module_install(server_type, str(host), package)
        except Exception as e:
            logger.warning(f'registry module install failed: {e}')

    if migrate_error:
        return {
            'status': 'error',
            'message': (f'{package} установлен в {host.name}, но миграции не прошли. '
                        f'Без таблиц модуль не работает — выполните вручную: '
                        f'docker exec {container} php artisan migrate --force'),
            'code': 'MIGRATE_FAILED',
            'package': package,
            'host': str(host),
            'output': migrate_error,
        }

    return {
        'status': 'success',
        'message': f'{package} установлен в {host.name}',
        'package': package,
        'host': str(host),
    }


def _apply_storage_settings(server_type: str, type_info: dict, docker_path: Path,
                            server_name: str = None) -> dict:
    """Применяет настройки хранилища (тип local/ftp, квота) в docker/.env.

    Приоритет источников:
      1. type_info['config']['storage'] — из myidon.site (новое)
      2. type_info['storage_settings']  — из server_types.py (локальный дефолт)
    Возвращает применённые значения {КЛЮЧ: значение} или {} если нечего применять.
    """
    applied = {}

    storage_cfg = (type_info.get('config') or {}).get('storage') or {}
    ftp_cfg = (type_info.get('config') or {}).get('ftp') or {}
    defaults = type_info.get('storage_settings') or {}

    if storage_cfg or defaults:
        stype = storage_cfg.get('type') or defaults.get('STORAGE_TYPE') or 'local'
        quota = storage_cfg.get('quota_gb')
        if quota is None:
            quota = defaults.get('STORAGE_QUOTA_GB', '50')
        applied['STORAGE_TYPE'] = str(stype)
        applied['STORAGE_QUOTA_GB'] = str(quota)

        path = storage_cfg.get('path') or defaults.get('STORAGE_PATH')
        if path:
            applied['STORAGE_PATH'] = str(path)
        max_size = storage_cfg.get('max_file_size')
        if max_size:
            applied['MAX_FILE_SIZE'] = str(max_size)

    # FTP-настройки применяем только когда выбран ftp
    if applied.get('STORAGE_TYPE') == 'ftp' or ftp_cfg.get('host'):
        applied['FTP_HOST'] = str(ftp_cfg.get('host') or defaults.get('FTP_HOST') or '')
        applied['FTP_PORT'] = str(ftp_cfg.get('port') or defaults.get('FTP_PORT') or '21')
        applied['FTP_USER'] = str(ftp_cfg.get('user') or defaults.get('FTP_USER') or '')
        applied['FTP_PASSWORD'] = str(ftp_cfg.get('password') or defaults.get('FTP_PASSWORD') or '')
        applied['FTP_PATH'] = str(ftp_cfg.get('path') or defaults.get('FTP_PATH') or '/upload')
        if ftp_cfg.get('tls') is not None:
            applied['FTP_TLS'] = 'true' if ftp_cfg['tls'] else 'false'

    if not applied:
        return {}

    # Пишем в .env (перезаписывая значения из .env.example) и в .env.example
    env_file = docker_path / '.env'
    if env_file.exists():
        content = env_file.read_text(encoding='utf-8')
        for key, value in applied.items():
            if re.search(rf'^{re.escape(key)}=', content, flags=re.MULTILINE):
                content = re.sub(rf'^{re.escape(key)}=.*$', f'{key}={value}',
                                 content, flags=re.MULTILINE)
            else:
                content += f'\n{key}={value}'
        env_file.write_text(content, encoding='utf-8')

    return applied


def install_server(data, session_obj):
    user = session_obj.get('user') or session_obj.get('user_info')
    if not user:
        return {'status': 'error', 'message': 'Unauthorized'}

    server_type = data.get('server_type', '').strip()
    install_path = data.get('path', '').strip()
    server_name = data.get('name', '').strip()
    force = data.get('force', 'false') == 'true'

    if not server_type or not install_path:
        return {'status': 'error', 'message': 'server_type and path required'}

    # Получаем объединённый список серверов (локальные + API)
    merged_types = _get_merged_server_types(session_obj)

    if server_type not in merged_types:
        return {'status': 'error', 'message': f'Unknown server type: {server_type}'}

    type_info = merged_types[server_type]

    # Модуль клиента — ставится внутрь (composer require), не как проект
    if type_info.get('is_module'):
        return install_module(data, session_obj)

    server_path = Path(install_path)
    docker_path = server_path / 'docker'
    code_path = server_path / 'src'

    # =================== ПРОВЕРКА УСТАНОВКИ ЧЕРЕЗ MYIDON.SITE =================
    oauth_token = session_obj.get('oauth_token')
    application_id = data.get('application_id')
    
    if oauth_token and application_id:
        from files.core.software.default.installation_lock import InstallationLockModule
        
        check_result = InstallationLockModule.check_installation(
            oauth_token=oauth_token,
            server_type=server_type,
            server_path=install_path,
            application_id=int(application_id)
        )
        
        if not check_result.get('allowed', False):
            reason = check_result.get('reason', 'unknown')
            existing = check_result.get('existing', {})
            
            # Если это не первая установка и данные не совпадают — блокируем
            if reason != 'first_installation':
                return {
                    'status': 'error',
                    'message': f'Установка заблокирована: {reason}',
                    'code': 'INSTALLATION_LOCKED',
                    'existing': existing,
                    'checks': check_result.get('checks', {}),
                }
        
        logger.info(f"Installation check passed: {check_result.get('reason')}")
    # =================== КОНЕЦ ПРОВЕРКИ =================

    # Проверяем не пустая ли папка
    is_reinstall = False
    if server_path.exists() and list(server_path.iterdir()):
        if not force:
            return {
                'status': 'error',
                'message': f'Папка {install_path} не пустая. Включите переустановку.',
                'code': 'NOT_EMPTY',
                'need_force': True
            }
        is_reinstall = True

    # Корневой репозиторий (python-сервисы: core, stt, streams, carto-v2):
    # git-репо содержит code/ и docker/ в корне, клонируется в сам проект,
    # а не в code/ (как Laravel-проекты).
    repo_root = bool(type_info.get('repo_root'))

    def _remove_path(p: Path, logger=None):
        import shutil
        try:
            if p.is_dir() and not p.is_symlink():
                shutil.rmtree(p)
            else:
                p.unlink()
        except Exception as e:
            if logger:
                logger.warning("Could not remove %s: %s", p, e)

    try:
        if is_reinstall:
            # Останавливаем контейнеры если есть docker-compose
            compose_file = docker_path / 'docker-compose.yml'
            if compose_file.exists():
                import subprocess
                try:
                    kw = _subprocess_kwargs(30)
                    subprocess.run(
                        ['docker', 'compose', '-p',
                         _compose_project_name(server_path, server_type),
                         '-f', str(compose_file), 'down'],
                        env=_compose_env(compose_file.parent),
                        **kw
                    )
                except Exception:
                    pass

            if repo_root:
                # Корневой репозиторий: git-репо занимает весь проект.
                # docker/.env — настройки этого экземпляра, их сохраняем,
                # остальное чистим для переклонирования.
                import shutil
                for entry in server_path.iterdir():
                    if entry.name == 'docker':
                        for sub in entry.iterdir():
                            if sub.name == '.env':
                                continue
                            _remove_path(sub, logger)
                        continue
                    _remove_path(entry, logger)
            else:
                # Очищаем code/ для переклонирования
                if code_path.exists():
                    import shutil
                    try:
                        shutil.rmtree(code_path)
                        logger.info(f"Cleaned code directory: {code_path}")
                    except Exception as e:
                        logger.warning(f"Could not clean code dir: {e}")

        server_path.mkdir(parents=True, exist_ok=True)

        # Клонируем из репозитория (только если код отсутствует локально)
        repository = type_info.get('repository', {})
        repo_url = repository.get('url', '') if isinstance(repository, dict) else ''

        if repo_root:
            # Корневой репозиторий: code/ и docker/ приходят из репо.
            # docker/.env мог сохраниться при переустановке, а git clone
            # требует пустую папку — клонируем во временную и переносим.
            has_local_code = (server_path / '.git').exists()
            if has_local_code:
                logger.info(f"Git repo already exists at {server_path}, skipping clone")
            elif repo_url and not repo_url.startswith('https://github.com/your-org'):
                import shutil
                tmp_clone = server_path / '.clone_tmp'
                _remove_path(tmp_clone, logger)
                clone_result = _clone_repository(repo_url, repository, tmp_clone, logger)
                if not clone_result.get('success'):
                    _remove_path(tmp_clone, logger)
                    return {
                        'status': 'error',
                        'message': f'Ошибка клонирования репозитория: {clone_result.get("error", "unknown")}'
                    }
                for entry in tmp_clone.iterdir():
                    dest = server_path / entry.name
                    if entry.is_dir() and dest.is_dir() and entry.name != '.git':
                        # merge: например, сохранённый docker/ из репо
                        shutil.copytree(entry, dest, dirs_exist_ok=True)
                        _remove_path(entry, logger)
                        continue
                    # На Windows move падает с WinError 32, если за файлом
                    # закрепился дескриптор (антивирус, индексатор) —
                    # тогда копируем и удаляем исходник.
                    try:
                        shutil.move(str(entry), str(dest))
                    except OSError:
                        if entry.is_dir():
                            shutil.copytree(entry, dest, dirs_exist_ok=True)
                        else:
                            dest.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(entry, dest)
                        _remove_path(entry, logger)
                _remove_path(tmp_clone, logger)
            else:
                return {
                    'status': 'error',
                    'message': 'Репозиторий не настроен для этого сервера'
                }
            code_path.mkdir(exist_ok=True)
            docker_path.mkdir(exist_ok=True)
        else:
            code_path.mkdir(exist_ok=True)
            has_local_code = code_path.exists() and any(code_path.iterdir())

            if has_local_code:
                logger.info(f"Code already exists locally at {code_path}, skipping clone")
            elif repo_url and not repo_url.startswith('https://github.com/your-org'):
                clone_result = _clone_repository(repo_url, repository, code_path, logger)
                if not clone_result.get('success'):
                    # В продакшене — ошибка если clone не удался
                    return {
                        'status': 'error', 
                        'message': f'Ошибка клонирования репозитория: {clone_result.get("error", "unknown")}'
                    }
            else:
                return {
                    'status': 'error',
                    'message': 'Репозиторий не настроен для этого сервера'
                }

        # Зависимости PHP. Без них контейнеры стартуют, но artisan
        # падает на отсутствии vendor/autoload.php, поэтому ставим
        # сразу после клонирования. Composer работает на хосте.
        deps = None
        if (code_path / 'composer.json').exists():
            deps = _ensure_php_dependencies(code_path, server_path, logger=logger)
            if deps.get('status') == 'error':
                # не молчим: сервер без зависимостей не рабочий
                logger.warning('PHP dependencies not installed for %s: %s',
                               server_path, deps.get('message'))

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
        # PROJECTNAME берётся из имени папки установки, а не из server_type:
        # иначе все клиенты (clientv2/client-core/client-city/...) получают
        # одинаковые container_name php-clientv2 и не могут сосуществовать.
        project_name = _compose_project_name(server_path, server_type)

        # docker-compose.example ДОЛЖЕН быть в репозитории
        # Ищем в разных местах: src/docker/, src/, code/docker/, code/, docker/
        compose_example = None
        for candidate in [
            server_path / 'src' / 'docker' / 'docker-compose.example',
            server_path / 'src' / 'docker-compose.example',
            server_path / 'docker' / 'docker-compose.example',
        ]:
            if candidate.exists():
                compose_example = candidate
                break
        
        if compose_example:
            import shutil

            # Каталог docker/ для Laravel-проектов (не repo_root) может
            # отсутствовать: репозиторий клонируется в code/, а его docker/
            # переносится на шаге 3c. Без mkdir копирование .env.example
            # падает с WinError 3 (путь не найден).
            docker_path.mkdir(parents=True, exist_ok=True)

            # 1. Копируем .env.example если есть рядом.
            #     При корневой раскладке (repo_root) compose_example уже лежит
            #     в docker/ проекта, и копировать сам на себя нельзя —
            #     Windows отдаёт WinError 32.
            env_example_src = compose_example.parent / '.env.example'
            if env_example_src.exists():
                src_r = env_example_src.resolve()
                dst_r = (docker_path / '.env.example').resolve()
                if src_r != dst_r:
                    shutil.copy2(env_example_src, docker_path / '.env.example')

            # 2. Создаём .env из .env.example если нет
            if not (docker_path / '.env').exists():
                if env_example_src.exists():
                    shutil.copy2(env_example_src, docker_path / '.env')
                else:
                    env_example = _generate_env_example(server_type, type_info, server_name or type_info['name'], subnet_octet, port, str(server_path))
                    (docker_path / '.env').write_text(env_example, encoding='utf-8')

            # 3. Подставляем реальные пути из server_path в .env
            env_path = docker_path / '.env'
            if env_path.exists():
                env_content = env_path.read_text(encoding='utf-8')
                env_content = env_content.replace('${PATH_APP_CODE}', str(code_path))
                env_content = env_content.replace('${PATH_APP_DOCKER}', str(server_path / 'docker'))
                env_content = env_content.replace('${PATH_APP_DOCKER_LOGS}', str(server_path / 'docker' / 'logs'))
                env_content = env_content.replace('${PATH_APP_PROJECT}', str(code_path))
                env_path.write_text(env_content, encoding='utf-8')

            # 3b. Приводим .env к этому экземпляру.
            #     Обязательно до шага 5: переменные из .env подставляются
            #     в docker-compose.yml, поэтому пути, хосты БД/Redis/Qdrant
            #     и порты должны быть уже окончательными.
            #     Без этого шага второй клиент получает те же порты и
            #     те же хосты, что и первый (в шаблоне клиента они жёстко
            #     зашиты на первый экземпляр).
            reserved_ports = _collect_reserved_ports()

            instance_env = {}
            try:
                instance_env = _apply_instance_env(
                    docker_path,
                    Path(str(server_path)),
                    project_name,
                    reserved_ports=reserved_ports,
                    logger=logger,
                )
            except Exception as e:
                logger.warning('Failed to apply instance env for %s: %s', project_name, e)

            # 3c. Переносим конфиги из репозитория в docker/.
            #     compose монтирует их по ${PATH_APP_DOCKER}, а каталога
            #     с файлами после клонирования там нет — compose создаст
            #     на месте файлов каталоги и контейнеры не запустятся.
            try:
                _copy_docker_payload(code_path, docker_path, logger=logger)
            except Exception as e:
                logger.warning('Failed to copy docker payload for %s: %s',
                               server_path, e)

            # 4. Копируем docker-compose.example.
            #     Шаблон нужен в двух местах: .yml - то, с чем compose
            #     работает сейчас, .example - то, из чего .yml
            #     пересобирается при каждом start и откуда берётся
            #     откат. Без .example в папке docker условие регенерации
            #     в start_server не выполнялось, и изменения шаблона из
            #     репозитория после git pull не применялись.
            #     При корневой раскладке источник уже в docker/ — копировать
            #     сам на себя нельзя (WinError 32).
            compose_src_r = compose_example.resolve()
            if compose_src_r != (docker_path / 'docker-compose.example').resolve():
                shutil.copy2(compose_example, docker_path / 'docker-compose.example')
            if compose_src_r != (docker_path / 'docker-compose.yml').resolve():
                shutil.copy2(compose_example, docker_path / 'docker-compose.yml')

            # 5. Подставляем ВСЕ переменные из .env в docker-compose.yml
            compose_path = docker_path / 'docker-compose.yml'
            content = compose_path.read_text(encoding='utf-8')

            import re

            # Сначала читаем .env и подставляем все переменные
            env_path = docker_path / '.env'
            env_vars = {}
            if env_path.exists():
                for line in env_path.read_text(encoding='utf-8').splitlines():
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, _, value = line.partition('=')
                        env_vars[key.strip()] = value.strip()

            # Обязательные подстановки — перезаписываем .env значения для PROJECTNAME и NETWORK_PREFIX
            network_prefix = f"172.{subnet_octet}" if subnet_octet > 0 else ""
            env_vars['PROJECTNAME'] = project_name
            if network_prefix:
                env_vars['DOCKER_NETWORK_PREFIX'] = network_prefix

            # 5a. Настройки хранилища из myidon.site (тип сервера: local/ftp, квота)
            #     Значения приходят в type_info['config'] / ['services'] из API.
            storage_applied = _apply_storage_settings(server_type, type_info, docker_path, server_name)
            if storage_applied:
                logger.info(f"Applied storage settings for {server_type}: {storage_applied}")
                for k, v in storage_applied.items():
                    env_vars[k] = str(v)

            # Подставляем все переменные из .env (включая ${VAR:-default} синтаксис)
            for key, value in env_vars.items():
                pattern = r'\$\{' + re.escape(key) + r'(:-[^}]*)?\}'
                if value:
                    content = re.sub(pattern, lambda m, v=value: v, content)
                else:
                    content = re.sub(pattern, '', content)

            compose_path.write_text(content, encoding='utf-8')
            logger.info(f"Copied docker-compose.example from {compose_example}")

            # 6. Обновляем .env с правильными значениями
            if env_path.exists():
                env_content = env_path.read_text(encoding='utf-8')
                if network_prefix:
                    env_content = re.sub(r'^DOCKER_NETWORK_PREFIX=.*$', f'DOCKER_NETWORK_PREFIX={network_prefix}', env_content, flags=re.MULTILINE)
                env_content = re.sub(r'^PROJECTNAME=.*$', f'PROJECTNAME={project_name}', env_content, flags=re.MULTILINE)
                env_path.write_text(env_content, encoding='utf-8')

            # 7. Стабильный идентификатор экземпляра (CLIENT_FINGERPRINT).
            #    Пишется в docker/.env, который переживает force-переустановку
            #    (пересоздаётся только code/), поэтому клиент сохраняет свой
            #    идентификатор. Дублируется в реестр ниже.
            fingerprint = _ensure_fingerprint(docker_path, logger=logger)
        else:
            return {
                'status': 'error',
                'message': 'docker-compose.example не найден в репозитории. Проверьте структуру проекта.'
            }

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
                    # Реальный порт экземпляра, а не default_port типа:
                    # проверка после обновления идёт по этому значению
                    p['port'] = int(instance_env.get('PORT_SSL')
                                      or instance_env.get('PORT')
                                      or port or 0)
                    p['subnet_octet'] = subnet_octet
                    p['docker_network_prefix'] = f"172.{subnet_octet}" if subnet_octet > 0 else ""
                    p['installed_by_starter'] = True
                    if fingerprint:
                        p['fingerprint'] = fingerprint
                    break
            RegistryModule.save_registry(reg)
            logger.info(f"Server {'reinstalled' if is_reinstall else 'registered'}: {server_type} at {install_path} (subnet: {subnet_octet})")

        # =================== ФИКСАЦИЯ УСТАНОВКИ НА MYIDON.SITE =================
        oauth_token = session_obj.get('oauth_token')
        application_id = data.get('application_id')
        
        if oauth_token and application_id:
            try:
                from files.core.software.default.installation_lock import InstallationLockModule
                
                InstallationLockModule.record_installation(
                    oauth_token=oauth_token,
                    server_type=server_type,
                    server_path=install_path,
                    application_id=int(application_id),
                    additional_data={
                        'server_name': server_name,
                        'subnet_octet': subnet_octet,
                        'port': port,
                        'is_reinstall': is_reinstall,
                    }
                )
                logger.info(f"Installation recorded on myidon.site: {server_type} at {install_path}")
            except Exception as e:
                logger.warning(f"Failed to record installation on myidon.site: {e}")
        # =================== КОНЕЦ ФИКСАЦИИ =================

        action = 'Переустановлен' if is_reinstall else 'Установлен'
        result = {'status': 'success',
                  'message': f'{type_info["name"]} {action} в {install_path}'}

        # Сразу вносим новый сервер в кеш монитора
        _monitor_refresh_path(install_path)

        # Установка без vendor/ формально успешна, но artisan в контейнерах
        # не запустится, поэтому предупреждение возвращаем явно
        if deps and deps.get('status') == 'error':
            result['warnings'] = [f"PHP-зависимости не установлены: {deps.get('message')}"]
        if deps and deps.get('status') == 'skipped':
            result['php_dependencies'] = deps.get('reason', '')

        return result

    except Exception as e:
        import traceback
        logger.error("Install server error: %s\n%s", e, traceback.format_exc())
        return {'status': 'error', 'message': str(e)}


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
                        'has_code': (item / 'src').exists(),
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


def _collect_reserved_ports():
    """Порты, уже занятые установленными серверами.

    Берётся из docker/.env каждого проекта в реестре (PORT, PORT_SSL и
    производные *_PLUS). Без этого второй клиент получил бы тот же порт,
    что и первый, и compose упал бы с "port is already allocated".
    """
    reserved = set()

    try:
        from files.core.oss.default.registry import RegistryModule
        reg = RegistryModule.load_registry()
    except Exception:
        return reserved

    for project in reg.get('projects', []):
        env_path = Path(project.get('path', '')) / 'docker' / '.env'

        if not env_path.exists():
            continue

        try:
            content = env_path.read_text(encoding='utf-8', errors='replace')
        except Exception:
            continue

        base_http = None
        base_ssl = None

        for line in content.replace('\r\n', '\n').split('\n'):
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue

            key, _, value = line.partition('=')
            key = key.strip()
            value = value.strip()

            if not value.isdigit():
                continue

            port = int(value)

            if key == 'PORT':
                base_http = port
                reserved.add(port)
            elif key == 'PORT_SSL':
                base_ssl = port
                reserved.add(port)
            elif key.endswith('_PLUS') and base_http:
                # смещение от базового порта
                try:
                    reserved.add(base_http + port)
                except Exception:
                    pass

    return reserved


def _port_is_free(port: int) -> bool:
    """Занят ли TCP-порт на хосте."""
    import socket

    for family, socktype, proto, _canon, sa in socket.getaddrinfo(
            socket.gethostname(), port, 0, socket.SOCK_STREAM):
        try:
            s = socket.socket(family, socktype, proto)
            s.settimeout(0.3)
            s.connect(sa)
            s.close()
            return False
        except Exception:
            continue

    return True


def _allocate_client_ports(reserved, http_range=(9000, 9199), ssl_range=(9400, 9599)):
    """Подобрать свободные порты HTTP и SSL для клиента.

    reserved — множество занятых портов (уже выделенные в этой установке).
    Возвращает (http_port, ssl_port). Если свободного порта в диапазоне
    нет — поднимаемся выше диапазона, но всё равно проверяем занятость.
    """
    used = set(reserved or ())

    def pick(rng):
        lo, hi = rng
        for port in range(lo, hi):
            if port in used:
                continue
            if _port_is_free(port):
                used.add(port)
                return port
        # диапазон исчерпан — идём дальше подряд
        port = hi
        while port in used or not _port_is_free(port):
            port += 1
        used.add(port)
        return port

    return pick(http_range), pick(ssl_range)


def _read_env_file(path):
    """Разбор .env в OrderedDict-подобный dict + сохраняет порядок."""
    lines = path.read_text(encoding='utf-8', errors='replace').replace('\r\n', '\n').split('\n')
    values, order, comments = {}, [], {}

    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith('#') and '=' in stripped:
            key, _, value = stripped.partition('=')
            key = key.strip()
            values[key] = value.strip()
            order.append(key)

    return lines, values, order


def _apply_instance_env(docker_path: Path, server_path: Path, project_name: str,
                        reserved_ports=None, logger=None):
    """Привести docker/.env к конкретному экземпляру.

    Что делает:
      - пути -> в папку этого экземпляра
      - PROJECTNAME / COMPOSE_PROJECT_NAME -> имя папки
      - DB_HOST / REDIS_HOST / QDRANT_HOST -> сервисы этого compose-проекта
        (в compose ключи сервисов имеют вид <svc>-${PROJECTNAME})
      - PORT / PORT_SSL -> свободные порты хоста
      - добирает отсутствующие переменные, нужные compose
      - генерирует пустые секреты, если их нет

    Возвращает dict с применёнными значениями (для лога и отчёта).
    """
    env_path = docker_path / '.env'
    if not env_path.exists():
        return {}

    lines, values, order = _read_env_file(env_path)
    applied = {}

    def put(key, value):
        if key not in order:
            order.append(key)
        values[key] = str(value)
        applied[key] = str(value)

    code_dir = server_path / 'src'
    docker_dir = server_path / 'docker'

    # --- пути: в шаблоне могут быть как ${PATH_APP_*}, так и готовые пути
    put('PATH_APP_CODE', code_dir)
    put('PATH_APP_PROJECT', code_dir)
    put('PATH_APP_DOCKER', docker_dir)
    put('PATH_APP_DOCKER_LOGS', docker_dir / 'logs')
    put('PATH_APP_STARTER', docker_dir / 'starter')

    # --- имя проекта
    put('PROJECTNAME', project_name)
    put('COMPOSE_PROJECT_NAME', project_name)

    # --- сервисы своего compose-проекта.
    # Ключи сервисов в docker-compose: <svc>-${PROJECTNAME}, поэтому
    # второй экземпляр обязан смотреть в свои контейнеры, а не в чужие.
    put('DB_HOST', f'mariadb-{project_name}')
    put('REDIS_HOST', f'redis-{project_name}')
    put('QDRANT_HOST', f'http://qdrant-{project_name}:6333')

    # --- порты
    http_port, ssl_port = _allocate_client_ports(reserved_ports)
    put('PORT', http_port)
    put('PORT_SSL', ssl_port)

    # смещения для второстепенных сервисов (redis, reverb, vite, ...)
    for key, offset in (('PORT_REDIS_PLUS', 1), ('PORT_REVERB_PLUS', 2),
                        ('PORT_VITE_PLUS', 3), ('PORT_MAIL_PLUS', 4),
                        ('PORT_PGADMIN_PLUS', 5), ('PORT_QDRANT_HTTP_PLUS', 6),
                        ('PORT_QDRANT_GRPC_PLUS', 7)):
        if key in values or key not in order:
            if not values.get(key):
                put(key, offset)

    # --- переменные, которых нет вовсе, но compose их использует
    put('DIR_COPY', values.get('DIR_COPY') or '.')
    put('PHP_CONTAINER', values.get('PHP_CONTAINER') or f'php-{project_name}')

    # --- секреты: генерируем, если пусто
    import secrets as _secrets

    def ensure_secret(key, length=48):
        if not values.get(key):
            put(key, _secrets.token_urlsafe(length)[:length])
        else:
            applied.setdefault(key, values[key])

    ensure_secret('DB_PASSWORD', 24)
    ensure_secret('REVERB_APP_ID', 24)
    ensure_secret('REVERB_APP_KEY', 48)
    ensure_secret('REVERB_APP_SECRET', 48)
    ensure_secret('OAUTH_SECRET', 48)

    # APP_KEY Laravel — ключ шифрования сессий и cookie. На свежей
    # установке src/.env нет (compose передаёт настройки через
    # environment), поэтому artisan key:generate не срабатывает и
    # приложение падает с MissingAppKeyException. Генерируем ключ
    # здесь, в docker/.env, откуда compose прокидывает его в контейнер.
    if not values.get('APP_KEY'):
        import base64 as _b64
        put('APP_KEY', 'base64:' + _b64.b64encode(_secrets.token_bytes(32)).decode())
    else:
        applied.setdefault('APP_KEY', values['APP_KEY'])

    if not values.get('OAUTH_CLIENT_ID'):
        # id клиента выдаёт myidon.site; пока пусто, но ключ должен существовать,
        # иначе подстановка в compose убирает всю строку
        put('OAUTH_CLIENT_ID', '')
    else:
        applied.setdefault('OAUTH_CLIENT_ID', values['OAUTH_CLIENT_ID'])

    if not values.get('OAUTH_REDIRECT_URI'):
        put('OAUTH_REDIRECT_URI', values.get('APP_URL', 'https://localhost') + '/oauth/callback')
    else:
        applied.setdefault('OAUTH_REDIRECT_URI', values['OAUTH_REDIRECT_URI'])

    if not values.get('REVERB_HOST'):
        put('REVERB_HOST', f'0.0.0.0')
    else:
        applied.setdefault('REVERB_HOST', values['REVERB_HOST'])

    # REVERB_PORT — внутренний порт контейнера, хост не публикуется,
    # поэтому конфликта между экземплярами нет
    if not values.get('REVERB_PORT'):
        put('REVERB_PORT', 8080)

    if 'PORT_REVERB' not in values:
        put('PORT_REVERB', 8080)

    # --- сохраняем, сохраняя комментарии и порядок файла
    out = []
    written = set()
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith('#') and '=' in stripped:
            key = stripped.partition('=')[0].strip()
            if key in values:
                out.append(f'{key}={values[key]}')
                written.add(key)
                continue
        out.append(line)

    for key in order:
        if key not in written and key in values:
            out.append(f'{key}={values[key]}')

    env_path.write_text('\n'.join(out) + '\n', encoding='utf-8')

    if logger:
        logger.info('Instance env applied for %s: ports=%s/%s db=%s redis=%s',
                    project_name, http_port, ssl_port,
                    applied.get('DB_HOST'), applied.get('REDIS_HOST'))

    return applied


def _generate_env_example(server_type, type_info, server_name, subnet_octet=0, port=None, server_path=''):
    """Генерирует .env.example с переменными для docker-compose"""
    port = port or type_info.get('default_port', 8000)
    network_prefix = f"172.{subnet_octet}" if subnet_octet > 0 else ""
    # Имя проекта — из папки установки, иначе все серверы одного типа
    # получат одинаковые container_name
    project_name = _compose_project_name(server_path or server_type, server_type)

    env = f"""# {type_info['name']}
PROJECTNAME={project_name}
SERVER_TYPE={server_type}
SERVER_NAME={server_name}
SERVER_PORT={port}

# Docker Network
DOCKER_NETWORK_PREFIX={network_prefix}

# Пути (плейсхолдеры — подставляются при установке)
PATH_APP_DOCKER=${PATH_APP_DOCKER}
PATH_APP_DOCKER_LOGS=${PATH_APP_DOCKER_LOGS}
PATH_APP_CODE=${PATH_APP_CODE}
PATH_APP_PROJECT=${PATH_APP_PROJECT}

# Домен
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

    # Добавляем специфичные переменные
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
    """Запустить сервер через Docker Compose с предварительными проверками"""
    import subprocess
    import json
    user = session_obj.get('user') or session_obj.get('user_info')
    if not user:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

    server_id = data.get('server_id')
    if not server_id:
        return jsonify({'status': 'error', 'message': 'Server ID required'})

    registry = get('registry')
    if not registry:
        return jsonify({'status': 'error', 'message': 'Registry not found'})

    reg_data = registry.load_registry()
    server = _find_server(reg_data, server_id)
    if not server:
        return jsonify({'status': 'error',
                    'message': f'Server not found: {server_id}',
                    'server_id': server_id,
                    'hint': 'Путь сверяется с реестром; проверьте значение server_id'}), 404

    server_path = server.get('path')
    docker_path = os.path.join(server_path, 'docker')
    if not os.path.exists(docker_path):
        return jsonify({'status': 'error', 'message': 'Docker directory not found'})

    compose_file = os.path.join(docker_path, 'docker-compose.yml')
    compose_example = os.path.join(docker_path, 'docker-compose.example')

    # Regenerate docker-compose.yml from example on every start
    if os.path.exists(compose_example):
        import shutil
        shutil.copy2(compose_example, compose_file)
        # Substitute ${VAR} from .env
        env_file = os.path.join(docker_path, '.env')
        if os.path.exists(env_file):
            env_vars = {}
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        k, v = line.split('=', 1)
                        env_vars[k.strip()] = v.strip()
            with open(compose_file, 'r', encoding='utf-8') as f:
                content = f.read()
            # Поддерживаем и ${VAR}, и ${VAR:-default} — иначе шаблон
            # с дефолтом не заменяется, и порт решает сам compose
            # при запуске (из окружения стартера, а не из .env проекта).
            import re as _re
            for k, v in env_vars.items():
                if not v:
                    continue
                pattern = r'\$\{' + _re.escape(k) + r'(:-[^}]*)?\}'
                content = _re.sub(pattern, lambda m, val=v: val, content)
            with open(compose_file, 'w', encoding='utf-8') as f:
                f.write(content)

    if not os.path.exists(compose_file):
        return jsonify({'status': 'error', 'message': 'docker-compose.yml not found'})

    checks = []
    has_errors = False

    # Check 1: Docker running
    try:
        kw = _subprocess_kwargs(15)
        r = subprocess.run(['docker', 'info'], **kw)
        if r.returncode == 0:
            checks.append({'step': 'docker', 'status': 'ok', 'message': 'Docker works'})
        else:
            checks.append({'step': 'docker', 'status': 'error', 'message': 'Docker is not running'})
            has_errors = True
    except Exception as e:
        checks.append({'step': 'docker', 'status': 'error', 'message': f'Docker check failed: {e}'})
        has_errors = True

    # Check 2: docker-compose.yml valid
    if not has_errors:
        try:
            kw = _subprocess_kwargs(30)
            r = subprocess.run(_compose_cmd(server_path, 'config', '--quiet'), cwd=docker_path, env=_compose_env(docker_path), **kw)
            if r.returncode == 0:
                checks.append({'step': 'compose', 'status': 'ok', 'message': 'docker-compose.yml is valid'})
            else:
                err_msg = (r.stderr or '').strip()[:200]
                checks.append({'step': 'compose', 'status': 'error', 'message': f'Invalid docker-compose.yml: {err_msg}'})
                has_errors = True
        except Exception as e:
            checks.append({'step': 'compose', 'status': 'error', 'message': f'Compose check failed: {e}'})
            has_errors = True

    # Check 3: .env non-empty critical vars
    if not has_errors:
        env_path = os.path.join(docker_path, '.env')
        if os.path.exists(env_path):
            try:
                with open(env_path, 'r', encoding='utf-8') as f:
                    env_content = f.read()
                empty_vars = []
                for line in env_content.splitlines():
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, val = line.split('=', 1)
                        if key.strip() in ('DB_DATABASE', 'DB_USERNAME', 'DB_PASSWORD') and not val.strip():
                            empty_vars.append(key.strip())
                if empty_vars:
                    checks.append({'step': 'env', 'status': 'warn', 'message': f'Empty values: {", ".join(empty_vars)}'})
                else:
                    checks.append({'step': 'env', 'status': 'ok', 'message': '.env is configured'})
            except Exception:
                checks.append({'step': 'env', 'status': 'ok', 'message': '.env exists'})
        else:
            checks.append({'step': 'env', 'status': 'warn', 'message': '.env file not found'})

    # Check 4: Images built
    if not has_errors:
        try:
            kw = _subprocess_kwargs(60)
            r = subprocess.run(_compose_cmd(server_path, 'images', '--format', 'json'), cwd=docker_path, env=_compose_env(docker_path), capture_output=True, text=True, timeout=60, encoding='utf-8', errors='replace')
            if r.returncode == 0 and r.stdout.strip():
                checks.append({'step': 'images', 'status': 'ok', 'message': 'Images are available'})
            else:
                # Need to build
                checks.append({'step': 'images', 'status': 'info', 'message': 'Building images...'})
                build_kw = _subprocess_kwargs(600)
                build_r = subprocess.run(_compose_cmd(server_path, 'build'), cwd=docker_path, env=_compose_env(docker_path), **build_kw)
                if build_r.returncode == 0:
                    checks.append({'step': 'images', 'status': 'ok', 'message': 'Images built successfully'})
                else:
                    err_msg = (build_r.stderr or '').strip()[:300]
                    checks.append({'step': 'images', 'status': 'error', 'message': f'Build failed: {err_msg}'})
                    has_errors = True
        except Exception as e:
            checks.append({'step': 'images', 'status': 'warn', 'message': f'Image check skipped: {e}'})

    if has_errors:
        return jsonify({'status': 'error', 'message': 'Pre-flight checks failed', 'checks': checks})

    # All checks passed — start server
    try:
        # compose тянет образы и пересоздаёт контейнеры; 120 с не хватало,
        # и обрыв по таймауту выдавался за ошибку запуска при работающих
        # контейнерах
        kw = _subprocess_kwargs(900)
        result = subprocess.run(
            _compose_cmd(server_path, 'up', '-d'),
            cwd=docker_path, env=_compose_env(docker_path), **kw
        )
        if result.returncode == 0:
            server['status'] = 'running'
            # Идемпотентно: при старте сервера его docker/.env получает
            # CLIENT_FINGERPRINT, если его там ещё нет (старые установки),
            # и значение фиксируется в реестре.
            try:
                server['fingerprint'] = _ensure_fingerprint(docker_path, logger=logger)
            except Exception as e:
                logger.warning('Fingerprint skipped for %s: %s', server_path, e)
            registry.save_registry(reg_data)
            checks.append({'step': 'start', 'status': 'ok', 'message': 'Server started'})

            # Первый запуск: контейнеры поднялись, но Laravel ещё не
            # инициализирован (APP_KEY пуст, миграции не выполнялись),
            # поэтому сайт отдаёт 502. Делаем это только для PHP-серверов
            # и только если в code/ есть artisan.
            provision = None
            try:
                if _path_state(Path(server_path) / 'src' / 'artisan') == 'file':
                    provision = _provision_laravel(Path(server_path), logger=logger)
                    checks.append({
                        'step': 'laravel',
                        'status': 'ok' if provision.get('ok') else 'warn',
                        'message': ('Laravel инициализирован' if provision.get('ok')
                                    else f"Laravel: {provision.get('error') or 'миграции не прошли'}"),
                        'details': provision.get('steps'),
                    })
            except Exception as e:
                checks.append({'step': 'laravel', 'status': 'warn',
                               'message': f'Laravel init failed: {e}'})

            _monitor_refresh_path(server_path)
            return jsonify({'status': 'success', 'message': 'Сервер запущен', 'checks': checks})
        else:
            err_msg = (result.stderr or '').strip()[:500]
            checks.append({'step': 'start', 'status': 'error', 'message': err_msg})
            return jsonify({'status': 'error', 'message': f'Ошибка: {err_msg}', 'checks': checks})
    except subprocess.TimeoutExpired:
        # контейнеры к этому моменту обычно уже пересозданы, поэтому это не
        # ошибка запуска: сообщаем как warn и всё равно инициализируем Laravel
        logger.warning('docker compose up timed out for %s, '
                       'containers are probably already up', server_path)
        checks.append({
            'step': 'start',
            'status': 'warn',
            'message': 'compose не уложился в отведённое время; '
                       'состояние контейнеров: docker compose ps',
        })

        provision = None
        try:
            if _path_state(Path(server_path) / 'src' / 'artisan') == 'file':
                provision = _provision_laravel(Path(server_path), logger=logger)
                checks.append({
                    'step': 'laravel',
                    'status': 'ok' if provision.get('ok') else 'warn',
                    'message': ('Laravel инициализирован' if provision.get('ok')
                                else f"Laravel: {provision.get('error') or 'миграции не прошли'}"),
                    'details': provision.get('steps'),
                })
        except Exception as e:
            checks.append({'step': 'laravel', 'status': 'warn',
                           'message': f'Laravel init failed: {e}'})

        return jsonify({'status': 'success',
                        'message': 'Сервер запущен (compose не успел завершиться, '
                                   'состояние проверьте через docker compose ps)',
                        'checks': checks})

    except Exception as e:
        logger.error(f"Error starting server: {e}")
        return jsonify({'status': 'error', 'message': f'Ошибка запуска: {str(e)}', 'checks': checks})


def get_server_logs(data, session_obj):
    """Получить логи контейнеров сервера"""
    user = session_obj.get('user') or session_obj.get('user_info')
    if not user:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

    server_id = data.get('server_id')
    if not server_id:
        return jsonify({'status': 'error', 'message': 'Server ID required'})

    registry = get('registry')
    if not registry:
        return jsonify({'status': 'error', 'message': 'Registry not found'})

    reg_data = registry.load_registry()
    server = _find_server(reg_data, server_id)
    if not server:
        return jsonify({'status': 'error',
                    'message': f'Server not found: {server_id}',
                    'server_id': server_id,
                    'hint': 'Путь сверяется с реестром; проверьте значение server_id'}), 404

    server_path = server.get('path')
    docker_path = os.path.join(server_path, 'docker')
    lines = int(data.get('lines', 50))

    logs = {}
    try:
        # Get container names for this project
        project_name = _compose_project_name(server_path, '')
        kw = _subprocess_kwargs(30)
        r = subprocess.run(
            _compose_cmd(server_path, 'ps', '-a', '--format', 'json'),
            cwd=docker_path, env=_compose_env(docker_path), capture_output=True, text=True, timeout=30, encoding='utf-8', errors='replace'
        )
        if r.returncode == 0 and r.stdout.strip():
            for line in r.stdout.strip().split('\n'):
                try:
                    container = json.loads(line)
                    name = container.get('Name', container.get('name', ''))
                    state = container.get('State', container.get('state', ''))
                    if name:
                        # Get logs for each container
                        log_kw = _subprocess_kwargs(10)
                        log_r = subprocess.run(
                            ['docker', 'logs', '--tail', str(lines), name],
                            capture_output=True, text=True, timeout=10, encoding='utf-8', errors='replace'
                        )
                        log_output = (log_r.stdout or '') + (log_r.stderr or '')
                        logs[name] = {
                            'state': state,
                            'logs': log_output.strip()[-2000:] if log_output else '(no logs)'
                        }
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        logger.error(f"Error getting server logs: {e}")

    return jsonify({'status': 'success', 'logs': logs})


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
    server = _find_server(reg_data, server_id)
    if not server:
        return jsonify({'status': 'error',
                    'message': f'Server not found: {server_id}',
                    'server_id': server_id,
                    'hint': 'Путь сверяется с реестром; проверьте значение server_id'}), 404

    server_path = server.get('path')
    docker_path = os.path.join(server_path, 'docker')
    if not os.path.exists(docker_path):
        return jsonify({'status': 'error', 'message': 'Docker directory not found'})

    try:
        kw = _subprocess_kwargs(60)
        result = subprocess.run(
            _compose_cmd(server_path, 'down'),
            cwd=docker_path, env=_compose_env(docker_path), **kw
        )
        if result.returncode == 0:
            # Обновляем статус в реестре
            server['status'] = 'stopped'
            registry.save_registry(reg_data)
            _monitor_refresh_path(server_path)
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

    # Останавливаем контейнеры если есть docker-compose
    server_path = Path(server_id)
    compose_file = server_path / 'docker' / 'docker-compose.yml'
    if compose_file.exists():
        try:
            kw = _subprocess_kwargs(30)
            subprocess.run(
                ['docker', 'compose', '-p', _compose_project_name(server_path, ''),
                 '-f', str(compose_file), 'down', '-v'],
                env=_compose_env(compose_file.parent),
                **kw
            )
        except Exception:
            pass

    # Удаляем из реестра
    registry = get('registry')
    if registry:
        reg_data = registry.load_registry()
        reg_data['projects'] = [p for p in reg_data['projects'] if not _paths_equal(p.get('path'), server_id)]
        registry.save_registry(reg_data)

    # Чистим запись в кеше монитора
    try:
        from files.core.oss.default.server_monitor import ServerMonitorModule
        ServerMonitorModule.forget_path(server_id)
    except Exception as e:
        logger.warning(f"monitor forget_path failed: {e}")

    # Удаляем папку сервера.
    #
    # Файлы .git создаются read-only, и на Windows shutil.rmtree на них
    # падает с WinError 5, оставляя папку на месте. Раньше исключение
    # глоталось, а вызывающий получал 200 и думал, что сервер удалён,
    # из-за чего следующая установка шла поверх недоудалённой папки.
    import shutil
    import stat as _stat

    def _remove_readonly(func, path, exc_info):
        """Снять «только чтение» и повторить удаление."""
        try:
            os.chmod(path, _stat.S_IWRITE | _stat.S_IREAD)
            func(path)
        except Exception:
            # файл уже мог исчезнуть — тогда это не ошибка
            if not os.path.exists(path):
                return
            raise exc_info[1]

    if server_path.exists():
        try:
            shutil.rmtree(server_path, onerror=_remove_readonly)

            if server_path.exists():
                return jsonify({
                    'status': 'error',
                    'message': f'Сервер убран из реестра, но папка {server_id} осталась на месте',
                    'path': str(server_path),
                }), 500

            return jsonify({
                'status': 'success',
                'success': True,
                'message': f'Сервер и папка {server_id} удалены',
            })

        except Exception as e:
            return jsonify({
                'status': 'error',
                'success': False,
                'message': f'Сервер убран из реестра, но папка не удалена: {str(e)}',
                'path': str(server_path),
                'error': str(e),
            }), 500

    return jsonify({'status': 'success', 'message': 'Сервер удалён'})


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


def server_repo_info(data, session_obj):
    """Получить информацию о репозитории сервера"""
    user = session_obj.get('user') or session_obj.get('user_info')
    if not user:
        return {'status': 'error', 'message': 'Unauthorized'}

    server_id = data.get('server_id')
    if not server_id:
        return {'status': 'error', 'message': 'Server ID required'}

    import subprocess

    server_path = Path(server_id)
    code_path = server_path / 'src'
    if not (code_path / '.git').exists() and (server_path / '.git').exists():
        code_path = server_path

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


def _json_get(path, dotted_key):
    """Безопасное чтеение вложенного ключа из JSON — None вместо исключения."""
    import json as _json
    try:
        data = _json.loads(Path(path).read_text(encoding='utf-8'))
    except Exception:
        return None
    node = data
    for part in (dotted_key or '').split('.'):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def _ensure_php_dependencies(code_dir: Path, server_path: Path = None, logger=None,
                            timeout=1800, force=False):
    """Поставить зависимости PHP через composer на хосте.

    Без этого контейнеры стартуют, но artisan не работает: нет
    vendor/autoload.php. Composer запускается на хосте, а не в контейнере —
    так быстрее, и vendor сразу виден в примонтированном code/.

    Возвращает dict: {'status': 'ok'|'skipped'|'error', ...}
    """
    import subprocess

    code_dir = Path(code_dir)

    if not (code_dir / 'composer.json').exists():
        return {'status': 'skipped', 'reason': 'нет composer.json'}

    autoload = code_dir / 'vendor' / 'autoload.php'
    if autoload.exists() and not force:
        return {'status': 'skipped', 'reason': 'vendor/ уже есть'}

    composer = _composer_cmd()
    if not composer:
        return {'status': 'error',
                'message': 'composer не найден (PATH или composer.phar в проекте)'}

    args = composer + ['install', '--no-interaction', '--prefer-dist',
                       '--optimize-autoloader']

    # Пост-скрипты composer (package:discover) загружают приложение, а на
    # чистом хосте .env в code/ ещё нет: Laravel берёт дефолты из конфига
    # (CACHE_STORE=database, SESSION_DRIVER=database, sqlite) и падает,
    # не найдя файл БД. Делаем окружение подпроцесса нейтральным — эти
    # значения видит только composer, в .env проекта они не попадают,
    # а в контейнере приложение получает реальные настройки из compose.
    env = os.environ.copy()
    env.setdefault('CACHE_STORE', 'array')
    env.setdefault('SESSION_DRIVER', 'array')
    env.setdefault('QUEUE_CONNECTION', 'sync')
    env.setdefault('BROADCAST_CONNECTION', 'log')
    env.setdefault('DB_CONNECTION', 'sqlite')

    if logger:
        logger.info('composer install in %s via %s', code_dir, composer[0])

    try:
        # _subprocess_kwargs уже содержит timeout, поэтому отдельно
        # его не передаём — иначе subprocess.run получит его дважды
        proc = subprocess.run(
            args, cwd=str(code_dir), env=env, **_subprocess_kwargs(timeout),
        )
    except subprocess.TimeoutExpired:
        return {'status': 'error', 'message': f'composer install не уложился в {timeout} с'}
    except Exception as e:
        return {'status': 'error', 'message': f'composer install: {str(e)}'}

    output = ((proc.stdout or '') + (proc.stderr or '')).strip()

    if proc.returncode != 0 or not autoload.exists():
        if logger:
            logger.warning('composer install failed in %s (rc=%s)', code_dir, proc.returncode)
        return {'status': 'error',
                'returncode': proc.returncode,
                'message': f'composer install завершился с кодом {proc.returncode}',
                'output': output[-2000:]}

    if logger:
        logger.info('composer install OK in %s', code_dir)

    return {'status': 'ok', 'output': output[-500:]}


def _server_port(server_path, fallback=0):
    """Порт, на котором сервер реально отвечает.

    Приоритет: PORT_SSL из docker/.env, затем PORT, затем значение из
    реестра. Порт из типа (default_port) не годится: он не учитывает
    выделенный экземпляру порт, и проверка обновления после этого
    уходит на незанятый порт и приводит к откату.
    """
    env_path = Path(server_path) / 'docker' / '.env'

    try:
        if env_path.exists():
            values = {}
            for line in env_path.read_text(encoding='utf-8', errors='replace').split('\n'):
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, _, v = line.partition('=')
                    values[k.strip()] = v.strip()

            for key in ('PORT_SSL', 'PORT'):
                value = values.get(key, '')
                if value.isdigit() and int(value) > 0:
                    return int(value)
    except Exception:
        pass

    try:
        return int(fallback or 0)
    except Exception:
        return 0


def _path_state(path):
    """Состояние пути без исключений: 'file' | 'dir' | 'other' | 'missing'.

    Обычный Path.exists() бросает OSError на путях, которые Windows не
    может опросить, - например на Linux-ссылках внутри примонтированного
    каталога (code/public/storage после storage:link). Для наших целей
    важно лишь различать «есть» и «нет», поэтому все проверки состояния
    идут через эту функцию.
    """
    try:
        import os as _os
        _os.stat(path)
    except FileNotFoundError:
        return 'missing'
    except NotADirectoryError:
        # часть пути - файл, а не каталог: для нас это тоже «нет»
        return 'missing'
    except OSError:
        # путь есть, но Windows не может его опросить (например,
        # Linux-ссылка в примонтированном каталоге). Считаем, что он
        # существует: иначе попытаемся создать его повторно.
        return 'other'

    try:
        return 'dir' if path.is_dir() else 'file'
    except OSError:
        return 'other'


def _provision_laravel(server_path: Path, logger=None, timeout=1800,
                       wait_container=120):
    """Инициализировать Laravel после первого запуска контейнеров.

    Выполняется внутри контейнера php-<project>: только там есть
    PHP и доступ к сети compose, где лежит БД. На хосте PHP может быть
    другим, а БД всё равно недоступна.

    Возвращает {'ok': bool, 'steps': [{'step':..,'ok':..,'output':..}]}
    """
    import subprocess
    import time

    code_path = Path(server_path) / 'src'
    project = _compose_project_name(server_path, '')
    container = f'php-{project}'

    steps = []

    def art(*args, wait=timeout):
        cmd = ['docker', 'exec', container, 'php', 'artisan', *args]
        try:
            proc = subprocess.run(
                cmd, **_subprocess_kwargs(min(wait, timeout)),
            )
        except Exception as e:
            steps.append({'step': ' '.join(args), 'ok': False, 'output': str(e)[:300]})
            return False

        out = ((proc.stdout or '') + (proc.stderr or '')).strip()
        ok = proc.returncode == 0
        steps.append({'step': ' '.join(args), 'ok': ok,
                      'output': out[-400:] if not ok else out[-160:]})

        return ok

    if _path_state(code_path / 'artisan') != 'file':
        return {'ok': True, 'skipped': 'нет artisan', 'steps': []}

    # ждём готовности контейнера: сразу после up он ещё поднимается
    deadline = time.time() + wait_container
    while time.time() < deadline:
        try:
            r = subprocess.run(['docker', 'exec', container, 'php', '-v'],
                               **_subprocess_kwargs(20))
            if r.returncode == 0:
                break
        except Exception:
            pass
        time.sleep(3)
    else:
        return {'ok': False, 'error': f'контейнер {container} не отвечает',
                'steps': steps}

    art('config:clear')

    # APP_KEY пустой -> генерируем. Непустой не трогаем: смена ключа
    # делает нечитаемыми сессии, cookie и зашифрованные значения.
    env_path = code_path / '.env'
    key_empty = True

    if _path_state(env_path) == 'file':
        try:
            for line in env_path.read_text(encoding='utf-8', errors='replace').splitlines():
                if line.strip().startswith('APP_KEY='):
                    key_empty = len(line.split('=', 1)[1].strip().strip('"')) < 10
                    break
        except Exception:
            pass

    if key_empty:
        art('key:generate', '--force')
    else:
        steps.append({'step': 'key:generate', 'ok': True, 'output': 'ключ уже задан'})

    # storage:link создаёт Linux-ссылку, которую Windows не опрашивает,
    # поэтому exists() здесь бросает WinError 1920. Состояние спрашиваем
    # через _path_state().
    link = code_path / 'public' / 'storage'
    if _path_state(link) == 'missing':
        art('storage:link')
    else:
        steps.append({'step': 'storage:link', 'ok': True, 'output': 'ссылка уже есть'})

    # Ждём БД: сразу после compose up mariadb ещё инициализируется,
    # и migrate падает с Connection refused. Проверяем TCP-порт БД
    # изнутри php-контейнера (в compose-сети он виден по имени сервиса).
    db_host = f'mariadb-{project}'
    db_port = 3306
    try:
        docker_env = server_path / 'docker' / '.env'
        if docker_env.exists():
            for line in docker_env.read_text(encoding='utf-8', errors='replace').splitlines():
                line = line.strip()
                if line.startswith('DB_HOST='):
                    db_host = line.split('=', 1)[1].strip() or db_host
                elif line.startswith('DB_PORT=') and line.split('=', 1)[1].strip().isdigit():
                    db_port = int(line.split('=', 1)[1].strip())
    except Exception:
        pass

    db_deadline = time.time() + 120
    db_ready = False
    while time.time() < db_deadline:
        try:
            r = subprocess.run(
                ['docker', 'exec', container, 'php', '-r',
                 'exit(@fsockopen(getenv("DB_HOST") ?: "%s", %d) ? 0 : 1);' % (db_host, db_port)],
                **_subprocess_kwargs(15))
            if r.returncode == 0:
                db_ready = True
                break
        except Exception:
            pass
        time.sleep(3)
    steps.append({'step': 'wait-db', 'ok': db_ready,
                  'output': f'{db_host}:{db_port} ' + ('готова' if db_ready else 'не отвечает')})

    ok = False
    for _attempt in range(3):
        ok = art('migrate', '--force')
        if ok:
            break
        time.sleep(5)

    if logger:
        logger.info('Laravel provisioned for %s: %s', project,
                    'ok' if ok else 'migrate failed')

    return {'ok': ok, 'container': container, 'steps': steps}


def _copy_docker_payload(code_path: Path, docker_path: Path, logger=None):
    """Перенести из репозитория в docker/ то, что монтируется в контейнеры.

    docker-compose.yml монтирует ${PATH_APP_DOCKER}/configs/... и
    ${PATH_APP_DOCKER}/dockerfiles/... . Если эти файлы на хосте
    отсутствуют, docker compose создаёт на их месте каталоги, и внутри
    контейнера exec падает с "Permission denied".

    Каталоги времени выполнения (data, logs, nginx-runtime) только
    создаются: там лежат база и логи, их перезаписывать нельзя.
    """
    import shutil

    result = {'copied': {}, 'created': [], 'removed_stub_dirs': []}

    src_docker = Path(code_path) / 'docker'
    if not src_docker.is_dir():
        return result

    def copy_file(src, dst):
        # compose мог создать каталог на месте файла — убираем, иначе
        # копирование не пройдёт, а файл останется недоступным
        if dst.is_dir():
            try:
                shutil.rmtree(dst)
                result['removed_stub_dirs'].append(str(dst))
            except Exception:
                return
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    # каталоги конфигурации: переносим всё, включая вложенные
    for name in ('configs', 'dockerfiles', 'db'):
        src = src_docker / name

        if not src.is_dir():
            continue

        count = 0

        for f in src.rglob('*'):
            if f.is_file():
                rel = f.relative_to(src)
                copy_file(f, Path(docker_path) / name / rel)
                count += 1

        result['copied'][name] = count

    # каталоги времени выполнения: создаём, если нет
    for name in ('data', 'data/mysql', 'logs', 'nginx-runtime', 'nginx-runtime/conf.d'):
        p = Path(docker_path) / name
        if not p.exists():
            p.mkdir(parents=True, exist_ok=True)
            result['created'].append(name)

    if logger:
        logger.info('Docker payload for %s: copied=%s created=%s stub_dirs_removed=%d',
                    docker_path, result['copied'], result['created'],
                    len(result['removed_stub_dirs']))

    return result


def _norm_path(value):
    """Привести путь к сравнимому виду: слэши, регистр, хвостовые разделители."""
    if value is None:
        return ''
    s = str(value).strip().strip('"').strip("'")
    if not s:
        return ''
    s = s.replace('/', os.sep).replace('\\', os.sep)
    try:
        s = os.path.normpath(s)
    except Exception:
        pass
    return os.path.normcase(s)


def _paths_equal(a, b):
    """Один и тот же путь, записанный по-разному (слэши, регистр)."""
    na, nb = _norm_path(a), _norm_path(b)
    if na and nb:
        return na == nb
    return str(a) == str(b)


def _find_server(reg_data, server_id):
    """Запись реестра по пути установки.

    server_id может прийти из URL с прямыми слэшами, а в реестре путь
    записан с обратными, поэтому сравниваем нормализованно.
    """
    projects = (reg_data or {}).get('projects', [])
    for s in projects:
        if _paths_equal(s.get('path'), server_id):
            return s
    # запасной вариант: совпадение по имени папки установки
    name = os.path.basename(_norm_path(server_id))
    if name:
        for s in projects:
            if os.path.basename(_norm_path(s.get('path'))) == name:
                return s
    return None


def _registry_entry(server_id):
    """Запись реестра по пути установки."""
    registry = get('registry')
    if not registry:
        return {}
    try:
        norm = str(Path(server_id).resolve())
        for p in registry.load_registry().get('projects', []):
            if p.get('path') == norm:
                return p
    except Exception as e:
        logger.warning('registry read failed: %s', e)
    return {}


def update_plan(data, session_obj):
    """Что именно будет сделано при обновлении этого сервера. Ничего не меняет."""
    user = session_obj.get('user') or session_obj.get('user_info')
    if not user:
        return {'status': 'error', 'message': 'Unauthorized'}

    server_id = data.get('server_id')
    if not server_id:
        return {'status': 'error', 'message': 'Server ID required'}

    from files.core.software.default.serverstrategy import ServerstrategyModule

    entry = _registry_entry(server_id)
    server_type = entry.get('project_type') or data.get('project_type') or ''
    merged = _get_merged_server_types(session_obj)
    type_info = merged.get(server_type) or SERVER_TYPES.get(server_type) or {}

    return {
        'status': 'success',
        'server_id': server_id,
        'server_type': server_type,
        # порт из docker/.env, а не default_port типа из реестра
        'port': _server_port(server_id, entry.get('port', 0)),
        'plan': ServerstrategyModule.describe(server_type, type_info),
    }


def update_preflight(data, session_obj):
    """Фаза 0 без изменений: коммиты, ветка, грязное дерево, что изменится."""
    user = session_obj.get('user') or session_obj.get('user_info')
    if not user:
        return {'status': 'error', 'message': 'Unauthorized'}

    server_id = data.get('server_id')
    if not server_id:
        return {'status': 'error', 'message': 'Server ID required'}

    from files.core.software.default.serverstrategy import ServerstrategyModule

    entry = _registry_entry(server_id)
    server_type = entry.get('project_type') or data.get('project_type') or ''
    merged = _get_merged_server_types(session_obj)
    type_info = merged.get(server_type) or SERVER_TYPES.get(server_type) or {}

    pre = ServerstrategyModule.preflight(
        server_id, server_type, type_info,
        port=_server_port(server_id, entry.get('port', 0)))

    status = 'success' if pre.get('ok') else 'error'
    return {'status': status, 'preflight': pre}


def update_server(data, session_obj):
    """Обновить сервер — по стратегии типа из SERVER_TYPES.

    Фазы: preflight -> backup -> pull -> deps -> docker-конфиг -> migrate
          -> restart -> verify, с откатом при провале проверки.
    dry_run=1 выполняет только preflight.
    """
    user = session_obj.get('user') or session_obj.get('user_info')
    if not user:
        return {'status': 'error', 'message': 'Unauthorized'}

    server_id = data.get('server_id')
    if not server_id:
        return {'status': 'error', 'message': 'Server ID required'}

    from files.core.software.default.serverstrategy import ServerstrategyModule

    dry_run = str(data.get('dry_run', '')).lower() in ('1', 'true', 'yes')
    server_path = Path(server_id)

    # модуль ставится внутрь клиента — у него другой путь обновления
    entry = _registry_entry(server_id)
    server_type = entry.get('project_type') or data.get('project_type') or ''
    merged = _get_merged_server_types(session_obj)
    type_info = merged.get(server_type) or SERVER_TYPES.get(server_type) or {}

    if type_info.get('is_module'):
        return update_module({**data, 'dry_run': '1' if dry_run else '0'}, session_obj)

    if not type_info:
        return {'status': 'error',
                'message': f'Тип {server_type!r} не найден в SERVER_TYPES — обновление невозможно'}

    plan = ServerstrategyModule.get_update_plan(server_type, type_info)
    if not plan.get('enabled', True):
        return {'status': 'error',
                'message': f'Обновление для типа {server_type} отключено в конфигурации'}

    port = _server_port(server_path, entry.get('port', 0))

    # ---------- ФАЗА 0: PREFLIGHT ----------
    pre = ServerstrategyModule.preflight(server_id, server_type, type_info, port=port)
    if not pre.get('ok'):
        return {'status': 'error', 'message': pre.get('error', 'preflight failed'),
                'code': pre.get('code'), 'preflight': pre}

    if dry_run:
        return {'status': 'success', 'dry_run': True,
                'message': 'Проверка завершена, изменения не применялись',
                'preflight': pre, 'plan': ServerstrategyModule.describe(server_type, type_info)}

    if pre.get('no_changes'):
        return {'status': 'success', 'message': 'Обновлений нет — сервер на последнем коммите',
                'preflight': pre}

    report = {'phases': {}, 'server_type': server_type,
              'strategy': plan['strategy'], 'path': str(server_path)}

    # ---------- БЭКАП ----------
    bk = ServerstrategyModule.backup(server_path, pre, plan)
    report['backup'] = bk
    if not bk.get('ok'):
        return {'status': 'error',
                'message': 'Не удалось создать резервную копию — обновление остановлено',
                **report}

    def rollback(reason):
        if not plan.get('rollback_on_failure'):
            return
        report['rollback'] = ServerstrategyModule.rollback(server_path, pre, bk)
        report['rollback_reason'] = reason

    # ---------- ФАЗА 1: PULL ----------
    res = ServerstrategyModule.pull(server_path, pre, plan)
    report['phases']['pull'] = res
    if not res.get('ok'):
        return {'status': 'error',
                'message': f"git pull не удался: {res.get('error', '')}", **report}

    # ---------- ФАЗА 2: ЗАВИСИМОСТИ ----------
    if plan['strategy'] in (ServerstrategyModule.STRATEGY_PHP,
                            ServerstrategyModule.STRATEGY_PYTHON):
        res = ServerstrategyModule.run_dependencies(server_path, pre, plan)
        report['phases']['dependencies'] = res
        for step in res.get('steps', []):
            if step.get('warning'):
                report.setdefault('warnings', []).append(step['warning'])
        if not res.get('ok'):
            rollback('dependencies_failed')
            return {'status': 'error',
                    'message': 'Зависимости не установились — выполнен откат', **report}

    # ---------- ФАЗА 3: DOCKER-КОНФИГ ----------
    if (plan.get('docker') or {}).get('regenerate_compose') or \
       (plan.get('docker') or {}).get('merge_env_example'):
        res = ServerstrategyModule.regenerate_docker_config(
            server_path, pre, plan, type_info, server_type)
        report['phases']['docker_config'] = res
        if res.get('env', {}).get('added'):
            report.setdefault('env_added', []).extend(res['env']['added'])
        if not res.get('compose', {}).get('ok', True):
            rollback('docker_config_failed')
            return {'status': 'error',
                    'message': f"Не удалось обновить docker-compose.yml: "
                               f"{res['compose'].get('reason', '')}", **report}

    # ---------- ФАЗА 4: МИГРАЦИИ ----------
    if plan['strategy'] == ServerstrategyModule.STRATEGY_PHP:
        res = ServerstrategyModule.run_migrations(server_path, plan)
        report['phases']['migrate'] = res
        if not res.get('ok'):
            rollback('migrate_failed')
            return {'status': 'error',
                    'message': f"Миграции не прошли: {res.get('error', '')}. "
                               f"{res.get('hint', '')}", **report}

    # ---------- ФАЗА 5: ПЕРЕЗАПУСК ----------
    res = ServerstrategyModule.restart(server_path, plan, pre)
    report['phases']['restart'] = res
    if not res.get('ok'):
        rollback('restart_failed')
        return {'status': 'error', 'message': 'Не удалось перезапустить контейнеры — '
                                             'выполнен откат', **report}

    # ---------- ФАЗА 6: ПРОВЕРКА ----------
    res = ServerstrategyModule.verify(server_path, port, server_type, plan)
    report['phases']['verify'] = res
    if not res.get('ok'):
        rollback('verify_failed')
        return {'status': 'error',
                'message': 'После обновления сервер не отвечает — выполнен откат',
                **report}

    report['message'] = f"{type_info.get('name', server_type)} обновлён"

    if report.get('env_added'):
        report['message'] += f". Добавлено новых переменных в .env: {len(report['env_added'])}"

    _monitor_refresh_path(server_path)
    return {'status': 'success', **report}


def update_module(data, session_obj):
    """Обновить модуль клиента (wall/shop/pages/payments/roles).

    Модуль не клонируется в свой путь — он лежит в code/ хоста как
    composer-пакет. Поэтому обновление = composer update пакета +
    artisan migrate + пересоздание php-контейнера.
    """
    user = session_obj.get('user') or session_obj.get('user_info')
    if not user:
        return {'status': 'error', 'message': 'Unauthorized'}

    server_type = (data.get('server_type') or '').strip()
    host_path = (data.get('host_path') or data.get('server_id') or '').strip()

    merged = _get_merged_server_types(session_obj)
    if server_type not in merged:
        return {'status': 'error', 'message': f'Unknown server type: {server_type}'}

    type_info = merged[server_type]
    package = type_info.get('composer_package')
    if not package:
        return {'status': 'error', 'message': f'{server_type}: composer_package не задан'}
    if not host_path:
        return {'status': 'error',
                'message': 'Укажите host_path — клиент, в котором установлен модуль'}

    host = Path(host_path)
    code_dir = host / 'src'
    vendor_dir = code_dir / 'vendor' / package.replace('/', os.sep)

    if not vendor_dir.exists():
        return {'status': 'error', 'code': 'NOT_INSTALLED',
                'message': f'{package} не установлен в {host.name}'}

    dry_run = str(data.get('dry_run', '')).lower() in ('1', 'true', 'yes')

    # где лежит исходник пакета
    #
    # Держим два значения: строка - для ответа (её ожидает jsonify),
    # Path - для работы с файлами. Раньше здесь была только строка, и
    # выражение module_path / '.git' падало с
    #   TypeError: unsupported operand type(s) for /: 'str' and 'str'
    module_path_str = type_info.get('module_path') or ''
    module_path = Path(module_path_str) if module_path_str else None

    installed_version, available_version, has_update = None, None, None

    if module_path and module_path.exists():
        src_cj = module_path / 'composer.json'
        if src_cj.exists():
            available_version = _json_get(src_cj, 'version') or 'dev'

    cj = code_dir / 'composer.json'
    if cj.exists():
        installed_version = _json_get(cj, f'packages.{package}.version')

    installed_sha = ''
    if module_path and (module_path / '.git').exists():
        r = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=str(module_path),
                           capture_output=True, text=True, encoding='utf-8',
                           errors='replace')
        installed_sha = (r.stdout or '').strip()[:12]

    if dry_run:
        return {
            'status': 'success', 'dry_run': True,
            'message': f'Проверка модуля {package} в {host.name}, изменения не применялись',
            'module': {'package': package, 'host': str(host),
                       'module_path': module_path_str,
                       'installed_version': installed_version,
                       'available_version': available_version,
                       'installed_commit': installed_sha,
                       'path_exists': bool(module_path and module_path.exists())},
        }

    from files.core.software.default.serverstrategy import ServerstrategyModule
    plan = ServerstrategyModule.get_update_plan(server_type, type_info)

    composer = _composer_cmd()
    if not composer:
        return {'status': 'error', 'message': 'Composer не найден на хосте'}

    logger.info(f'Updating module {package} in {code_dir}')
    proc = subprocess.run(
        composer + ['update', package, '--no-interaction',
                    '--working-dir=' + str(code_dir)],
        **_subprocess_kwargs(plan['timeout']['deps'])
    )
    if proc.returncode != 0:
        tail = ((proc.stdout or '') + (proc.stderr or ''))[-1500:]
        return {'status': 'error', 'module_update_failed': True,
                'message': f'composer update {package} вернул код {proc.returncode}',
                'output': tail}

    project = _compose_project_name(host, '')
    container = 'php-' + project

    migrate_error = None
    try:
        mig = subprocess.run(['docker', 'exec', container, 'php', 'artisan', 'migrate', '--force'],
                             **_subprocess_kwargs(plan['timeout']['migrate']))
        if mig.returncode != 0:
            migrate_error = (mig.stderr or mig.stdout or '')[-1500:]
    except Exception as e:
        migrate_error = str(e)

    compose = host / 'docker' / 'docker-compose.yml'
    restarted = False
    if compose.exists():
        try:
            up = subprocess.run(
                _compose_cmd(host, 'up', '-d', '--force-recreate', container),
                cwd=str(host / 'docker'), env=_compose_env(host / 'docker'),
                **_subprocess_kwargs(300))
            restarted = up.returncode == 0
        except Exception as e:
            logger.warning('module restart failed: %s', e)

    if migrate_error:
        return {'status': 'error', 'code': 'MIGRATE_FAILED',
                'message': f'{package} обновлён в {host.name}, но миграции не прошли. '
                           f'Вручную: docker exec {container} php artisan migrate --force',
                'output': migrate_error, 'restarted': restarted}

    return {'status': 'success', 'restarted': restarted,
            'message': f'{package} обновлён в {host.name}'}


def update_all_clients(data, session_obj):
    """Обновить все клиенты из реестра — по стратегии каждого.

    По умолчанию — только dry_run по всем: сначала показываем, что
    изменится, и лишь потом применяем.
    """
    user = session_obj.get('user') or session_obj.get('user_info')
    if not user:
        return {'status': 'error', 'message': 'Unauthorized'}

    apply_changes = str(data.get('apply', '')).lower() in ('1', 'true', 'yes')
    only = (data.get('project_type') or '').strip()

    registry = get('registry')
    if not registry:
        return {'status': 'error', 'message': 'Registry not available'}

    merged = _get_merged_server_types(session_obj)
    results = []

    for p in registry.load_registry().get('projects', []):
        if not p.get('installed_by_starter'):
            continue
        stype = p.get('project_type', '')
        type_info = merged.get(stype) or SERVER_TYPES.get(stype) or {}
        if not type_info:
            continue
        if not (type_info.get('is_client') or type_info.get('is_module')):
            continue
        if only and stype != only:
            continue

        payload = {
            'server_id': p['path'],
            'project_type': stype,
            'dry_run': '0' if apply_changes else '1',
        }
        if type_info.get('is_module'):
            payload['server_type'] = stype
            payload['host_path'] = p['path']
            payload['server_id'] = p['path']

        try:
            res = update_server(payload, session_obj)
        except Exception as e:
            res = {'status': 'error', 'message': str(e)}

        results.append({
            'path': p['path'],
            'name': Path(p['path']).name,
            'project_type': stype,
            'status': res.get('status'),
            'message': res.get('message'),
            'strategy': (res.get('strategy') or
                         (res.get('plan') or {}).get('strategy')),
            'preflight': res.get('preflight'),
        })

    ok = [r for r in results if r['status'] == 'success']
    bad = [r for r in results if r['status'] != 'success']

    return {
        'status': 'success' if not bad else 'partial',
        'apply': apply_changes,
        'total': len(results),
        'succeeded': len(ok),
        'failed': len(bad),
        'results': results,
    }


def server_git_log(data, session_obj):
    """Получить последние коммиты + статус обновления из server_types"""
    user = session_obj.get('user') or session_obj.get('user_info')
    if not user:
        return {'status': 'error', 'message': 'Unauthorized'}

    server_id = data.get('server_id')
    if not server_id:
        return {'status': 'error', 'message': 'Server ID required'}

    import subprocess

    server_path = Path(server_id)
    code_path = server_path / 'src'
    if not (code_path / '.git').exists() and (server_path / '.git').exists():
        code_path = server_path

    if not (code_path / '.git').exists():
        return {'status': 'success', 'log': [], 'has_update': False, 'message': 'Not a git repository'}

    try:
        kw = _subprocess_kwargs(10)

        # Получаем URL remote
        remote_url = (subprocess.run(
            ['git', 'remote', 'get-url', 'origin'],
            cwd=str(code_path), **kw
        ).stdout or '').strip()

        # Получаем текущий коммит
        local_commit = (subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            cwd=str(code_path), **kw
        ).stdout or '').strip()

        # Получаем ветку
        branch = (subprocess.run(
            ['git', 'branch', '--show-current'],
            cwd=str(code_path), **kw
        ).stdout or '').strip()

        # Fetch remote и получаем удалённый коммит
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
            ).stdout or '').strip()
            has_update = bool(remote_commit) and local_commit != remote_commit

        # Получаем последние коммиты
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
