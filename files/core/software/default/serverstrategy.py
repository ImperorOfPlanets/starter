# files/core/software/default/serverstrategy.py
"""
Стратегии установки и обновления серверов — в зависимости от типа.

Зачем этот модуль
-----------------
`install_server()` (web/sections/servers.py) работает ТОЛЬКО на установке
и целиком опирается на SERVER_TYPES: репозиторий, ветка, порт, подсеть,
compose-шаблон, генерация .env, подстановка переменных.

`update_server()` — это 6 строк хардкода (`git pull` + `compose up -d`),
которые НЕ смотрят в SERVER_TYPES вообще. Из-за этого:

  * ветка/remote не сверяются с конфигом типа;
  * новый docker-compose.example из репозитория игнорируется;
  * новые переменные из .env.example не попадают в docker/.env;
  * composer install / npm ci / artisan migrate не выполняются;
  * нет бэкапа, нет health-check, нет отката.

Этот модуль делает update зеркалом install и добавляет недостающие фазы.
Общие хелперы рендеринга compose и слияния env вынесены сюда, чтобы
install и update использовали ОДИН и тот же код.

Стратегии
---------
php_docker      client, clientv2, client_core, client_city, client_medical
                git -> code/, composer install, npm ci+build, artisan migrate
python_docker   embeddings, tts, stt, browser, slam, yolo, voice,
                simulator, fileserver, phone
                git -> code/, pip install -r requirements.txt
static_docker   reverse_proxy — git -> code/, без зависимостей
composer_module wall, shop, pages, payments, roles
                НЕ клонируется в свой путь: composer require внутрь
                code/ хоста-клиента + artisan migrate

Фазы обновления
---------------
0 preflight   тип из реестра, сверка remote/ветки, проверка на грязное
              дерево, бэкап, расчёт плана (изменённые коммиты/файлы)
1 pull        git pull --ff-only (merge-коммит запрещён)
2 deps        composer install / npm ci + npm run build / pip install
3 docker      регенерация docker-compose.yml из .example + слияние .env
4 migrate     docker exec php-<project> php artisan migrate --force
5 restart     docker compose build (если менялся Dockerfile) + up -d
6 verify      _check_server_status + HTTP-проба; при провале — откат
"""

import os
import re
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path

from files.core.utils.globalVars_utils import get_global
from files.core.utils.log_utils import LogManager

logger = LogManager.get_logger('server-strategy')


# ======================== ХЕЛПЕРЫ (вынесены из servers.py) ========================

def _subprocess_kwargs(timeout=10, cwd=None):
    """kwargs для subprocess — скрытие окон на Windows, UTF-8, таймаут."""
    kwargs = {
        'capture_output': True, 'text': True,
        'timeout': timeout, 'encoding': 'utf-8', 'errors': 'replace',
    }
    if cwd:
        kwargs['cwd'] = str(cwd)
    if get_global('os') == 'Windows':
        try:
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = subprocess.SW_HIDE
            kwargs['startupinfo'] = si
        except Exception:
            pass
    return kwargs


def compose_project_name(server_path, server_type: str = '') -> str:
    """Имя docker-compose проекта — из папки установки.

    Должно быть уникальным на каждый сервер, иначе контейнеры получат
    одинаковый container_name. Допустимы только [a-z0-9-].
    Дублирует _compose_project_name из servers.py — здесь нужна копия,
    чтобы модуль не зависел от web-слоя (иначе циклический импорт).
    """
    raw = os.path.basename(str(server_path).rstrip('\\/'))
    name = re.sub(r'[^a-z0-9-]+', '-', raw.lower()).strip('-')
    if not name:
        name = re.sub(r'[^a-z0-9-]+', '-', str(server_type).lower()).strip('-')
    return name or 'server'


def compose_cmd(server_path, *args):
    """docker compose с явным -p <имя пафки>, иначе все серверы затирают друг друга."""
    return ['docker', 'compose', '-p', compose_project_name(server_path, ''), *args]


def _compose_env_for(docker_path):
    """Окружение compose без переменных стартера (PORT=2000 и т.п.).

    Иначе ${PORT:-80} в compose resolves в порт панели, а не в порт
    проекта из docker/.env. Ленивый импорт — чтобы не было цикла
    с web-слоем.
    """
    try:
        from files.web.sections.servers import _compose_env
        return _compose_env(docker_path)
    except Exception:
        import os
        return os.environ.copy()


def git_root(server_path):
    """Где лежит .git: src/ (Laravel-раскладка) или корень проекта.

    Единая архитектура: .git в корне проекта, приложение в src/.
    У php-проектов может быть git внутри src/ — обновление работает
    с обоими вариантами.
    """
    server_path = Path(server_path)
    if (server_path / 'src' / '.git').exists():
        return server_path / 'src'
    if (server_path / '.git').exists():
        return server_path
    return server_path / 'src'


def _in_changed(changed, name):
    """Файл менялся в этом обновлении.

    Пути в git diff корневые: для Laravel-раскладки 'composer.lock',
    для корневой — 'code/requirements.txt' или 'docker/docker-compose.example'.
    """
    name = name.lower()
    return any(f.lower() == name or f.lower().endswith('/' + name)
               for f in changed)


def find_compose_example(server_path):
    """Ищет docker-compose.example в клоне. Кандидаты — как в install_server."""
    server_path = Path(server_path)
    for candidate in (
        server_path / 'src' / 'docker' / 'docker-compose.example',
        server_path / 'src' / 'docker-compose.example',
        server_path / 'docker' / 'docker-compose.example',
    ):
        if candidate.exists():
            return candidate
    return None


def read_env(env_path):
    """Читает .env в dict. Наивный парсер — как в servers.py, для совместимости."""
    env_path = Path(env_path)
    if not env_path.exists():
        return {}
    out = {}
    for line in env_path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, _, value = line.partition('=')
            out[key.strip()] = value.strip()
    return out


def set_env_keys(env_path, keys: dict, preserve_missing=True):
    """Точечно обновляет .env, сохраняя комментарии и порядок.

    Существующий ключ перезаписывается. Отсутствующий — добавляется в конец.
    В отличие от _write_server_env (полная перезапись) не теряет комментарии.
    """
    env_path = Path(env_path)
    if not env_path.exists():
        env_path.write_text('', encoding='utf-8')

    content = env_path.read_text(encoding='utf-8')
    for key, value in keys.items():
        if not value:
            # Пустое значение в compose подставляется как '${KEY}' без дефолта —
            # переменная должна остаться в файле, но без значения (как в install).
            continue
        pattern = rf'^{re.escape(key)}=.*$'
        if re.search(pattern, content, flags=re.MULTILINE):
            content = re.sub(pattern, f'{key}={value}', content, flags=re.MULTILINE)
        else:
            if not content.endswith('\n'):
                content += '\n'
            content += f'{key}={value}\n'
    env_path.write_text(content, encoding='utf-8')
    return content


def merge_env_example(code_path, docker_path):
    """Копирует НОВЫЙ .env.example и доливает недостающие ключи в .env.

    Это ключевая недостающая фаза: без неё после обновления в docker/.env
    не хватает переменных, которые появились в новой версии репозитория,
    и контейнер стартует с неполным окружением.

    Правила:
      * .env.example — всегда перезаписывается свежим из репозитория;
      * .env — НИКОГДА не перезаписывается; в него только добавляются
        отсутствующие ключи (со значением из .env.example);
      * существующие значения в .env не трогаются — это настройки проекта.
    """
    code_path, docker_path = Path(code_path), Path(docker_path)
    docker_path.mkdir(parents=True, exist_ok=True)

    compose_example = find_compose_example(code_path.parent)
    example_src = (compose_example.parent / '.env.example') if compose_example else None
    if not example_src or not example_src.exists():
        return {'ok': False, 'reason': '.env.example не найден в репозитории', 'added': []}

    shutil.copy2(example_src, docker_path / '.env.example')

    env_path = docker_path / '.env'
    existing = set(read_env(env_path).keys())
    incoming = read_env(docker_path / '.env.example')

    added = []
    for key, value in incoming.items():
        if key not in existing:
            added.append(key)

    if added:
        set_env_keys(env_path, {k: incoming.get(k, '') for k in added})

    return {
        'ok': True,
        'added': added,
        'kept': sorted(existing),
        'example_keys': len(incoming),
    }


def render_compose(server_path, env_vars: dict):
    """Копирует docker-compose.example -> docker-compose.yml с подстановкой.

    Логика идентична install_server (шаги 12-17), вынесена для переиспользования.
    Поддерживает синтаксис ${VAR} и ${VAR:-default}; пустое значение удаляет
    подстановку целиком.
    """
    server_path = Path(server_path)
    docker_path = server_path / 'docker'
    compose_example = find_compose_example(server_path)
    if not compose_example:
        return {'ok': False, 'reason': 'docker-compose.example не найден в репозитории'}

    content = compose_example.read_text(encoding='utf-8')
    for key, value in (env_vars or {}).items():
        pattern = r'\$\{' + re.escape(key) + r'(:-[^}]*)?\}'
        if value:
            content = re.sub(pattern, lambda m, v=value: v, content)
        else:
            content = re.sub(pattern, '', content)

    docker_path.mkdir(parents=True, exist_ok=True)
    (docker_path / 'docker-compose.yml').write_text(content, encoding='utf-8')
    return {'ok': True, 'source': str(compose_example), 'vars_applied': len(env_vars or {})}


def _git(code_path, *args, timeout=60, strip=True):
    """git в code/. Никогда не падает — возвращает (code, out, err).

    strip=False нужен для `git status --porcelain`: первые два символа
    строки - коды состояния, и у изменённого, но не добавленного файла
    это ' M' с ведущим пробелом. Обрезка съедала его, путь читался не с
    того места, и composer.json после установки модуля считался
    чужим изменением, блокирующим обновление.
    """
    try:
        kw = _subprocess_kwargs(timeout, cwd=code_path)
        env = os.environ.copy()
        env['GIT_TERMINAL_PROMPT'] = '0'
        env['GIT_ASKPASS'] = 'echo'
        kw['env'] = env
        r = subprocess.run(['git', *args], **kw)
        out = r.stdout or ''
        err = r.stderr or ''
        return r.returncode, out.strip() if strip else out, err.strip()
    except FileNotFoundError:
        return 127, '', 'git не установлен'
    except subprocess.TimeoutExpired:
        return 124, '', f'git {args[0]} превысил {timeout}s'
    except Exception as e:
        return 1, '', str(e)


# ======================== МОДУЛЬ ========================

# ======================== НЕЗАКОММИЧЕННЫЕ ИЗМЕНЕНИЯ ========================
#
# Установка модуля идёт через composer require, а сборка ассетов - через
# npm, поэтому после них рабочее дерево клиента всегда содержит изменения.
# Раньше любое из них блокировало обновление (DIRTY_TREE), и клиент с
# модулем обновить было невозможно.
#
# Здесь перечислены пути, которые меняются штатно и не должны мешать
# обновлению. Всё остальное по-прежнему блокирует.

BENIGN_DIRTY_EXACT = (
    'composer.json',
    'composer.lock',
    'package-lock.json',
    'yarn.lock',
    'public/hot',
    'public/mix-manifest.json',
    '.env',
    '.env.backup',

    # создаются нашим же конвейером: docker/configs/init/client-init.sh
    # копирует их при каждом старте контейнера, а artisan storage:link
    # делает public/storage
    'public/storage',
    'public/css/app.css',
    'public/js/app.js',
)

# пути сравниваются по началу строки, поэтому сюда только каталоги
BENIGN_DIRTY_PREFIXES = (
    'public/build/',
    'storage/framework/',
    'bootstrap/cache/',
)


def _is_benign_dirty(line: str) -> bool:
    """Относится ли строка `git status --porcelain` к штатным изменениям.

    Строка porcelain имеет вид `XY путь`, где XY - коды состояния, а путь
    может быть в кавычках, если содержит необычные символы.
    """
    # ВАЖНО: слева строку не обрезаем. Формат porcelain - это ровно
    # два символа состояния и пробел, поэтому ' M composer.json'
    # (изменён, не добавлен) после strip() теряет первый пробел и путь
    # съезжает на символ.
    raw = line.rstrip()

    if len(raw) < 4 or raw[2] != ' ':
        return False

    path = raw[3:].strip()

    if path.startswith('"') and path.endswith('"') and len(path) >= 2:
        path = path[1:-1]

    # пара «путь -> новый путь» при переименовании
    if ' -> ' in path:
        path = path.split(' -> ', 1)[1]

    path = path.replace('\\', '/')

    # lstrip('./') здесь не годится: он срезает ведущие точки и слэши
    # как набор символов, и '.env' превратился бы в 'env'
    if path.startswith('./'):
        path = path[2:]

    if path in BENIGN_DIRTY_EXACT:
        return True

    return any(path.startswith(p) for p in BENIGN_DIRTY_PREFIXES)


class ServerstrategyModule:
    """Разрешение стратегии и пофазное обновление сервера."""

    # --- имена стратегий
    STRATEGY_PHP = 'php_docker'
    STRATEGY_PYTHON = 'python_docker'
    STRATEGY_STATIC = 'static_docker'
    STRATEGY_MODULE = 'composer_module'

    # --- дефолты секции update в SERVER_TYPES
    DEFAULT_UPDATE = {
        'enabled': True,
        'auto_update': False,
        'check_interval': 86400,
        'strategy': None,               # None -> resolve по типу
        'allow_dirty': False,           # False -> грязное дерево блокирует обновление
        'force_reset': False,           # True -> reset --hard вместо pull
        'pull_mode': '--ff-only',
        'backup': {'git_bundle': True, 'docker_dir': True},
        'deps': {
            'composer': 'auto',         # auto -> только если composer.lock изменился
            'npm': 'auto',              # auto -> только если package.json есть
            'npm_build': True,
            'pip': 'auto',              # auto -> только если requirements.txt изменился
        },
        'docker': {
            'regenerate_compose': True,
            'merge_env_example': True,
            'apply_storage_settings': True,
            'build': 'auto',            # auto -> только если Dockerfile изменился
            'restart': True,
        },
        'migrate': 'auto',              # auto -> только если есть artisan
        'health_check': {'enabled': True, 'retries': 10, 'interval': 5},
        'rollback_on_failure': True,
        'timeout': {'pull': 120, 'deps': 900, 'docker': 900, 'migrate': 600},
    }

    @staticmethod
    def _deep_merge(base: dict, override: dict) -> dict:
        """Рекурсивное слияние: значения override побеждают."""
        out = dict(base)
        for k, v in (override or {}).items():
            if isinstance(v, dict) and isinstance(out.get(k), dict):
                out[k] = ServerstrategyModule._deep_merge(out[k], v)
            else:
                out[k] = v
        return out

    # ==================== РАЗРЕШЕНИЕ ====================

    @staticmethod
    def resolve_strategy(server_type: str, type_info: dict = None) -> str:
        """Какая стратегия установки/обновления у типа сервера.

        Порядок: явный 'strategy' -> is_module -> is_client -> эвристика.
        """
        info = type_info or {}
        explicit = (info.get('update') or {}).get('strategy') or info.get('strategy')
        if explicit:
            return explicit

        if info.get('is_module'):
            return ServerstrategyModule.STRATEGY_MODULE

        # Клиенты на PHP/Laravel — всегда php_docker
        if info.get('is_client'):
            return ServerstrategyModule.STRATEGY_PHP

        # Клиент, чей репозиторий содержит composer.json, — тоже php
        repo = info.get('repository') or {}
        if 'client' in str(repo.get('url', '')):
            return ServerstrategyModule.STRATEGY_PHP

        return ServerstrategyModule.STRATEGY_PYTHON

    @staticmethod
    def get_update_plan(server_type: str, type_info: dict = None) -> dict:
        """Итоговый план обновления: DEFAULT_UPDATE + секция update типа."""
        info = type_info or {}
        plan = ServerstrategyModule._deep_merge(
            ServerstrategyModule.DEFAULT_UPDATE, info.get('update') or {}
        )
        plan['strategy'] = ServerstrategyModule.resolve_strategy(server_type, info)
        return plan

    @staticmethod
    def describe(server_type: str, type_info: dict = None) -> dict:
        """Что именно будет сделано при обновлении этого типа. Для UI и dry-run."""
        plan = ServerstrategyModule.get_update_plan(server_type, type_info)
        strategy = plan['strategy']
        deps = plan.get('deps') or {}

        steps = ['preflight', 'pull']
        if strategy == ServerstrategyModule.STRATEGY_PHP:
            steps += ['composer', 'npm', 'docker_config', 'migrate', 'restart', 'verify']
        elif strategy == ServerstrategyModule.STRATEGY_PYTHON:
            steps += ['pip', 'docker_config', 'restart', 'verify']
        elif strategy == ServerstrategyModule.STRATEGY_STATIC:
            steps += ['docker_config', 'restart', 'verify']
        elif strategy == ServerstrategyModule.STRATEGY_MODULE:
            steps = ['preflight', 'composer_update', 'migrate', 'restart_php', 'verify']

        return {
            'server_type': server_type,
            'strategy': strategy,
            'steps': steps,
            'enabled': plan.get('enabled', True),
            'auto_update': plan.get('auto_update', False),
            'deps': deps,
            'docker': plan.get('docker') or {},
            'migrate': plan.get('migrate'),
            'rollback_on_failure': plan.get('rollback_on_failure', True),
        }

    # ==================== ФАЗА 0: PREFLIGHT ====================

    @staticmethod
    def preflight(server_path, server_type: str, type_info: dict = None, port: int = 0) -> dict:
        """Проверки до любых изменений. Ничего не мутирует.

        Возвращает план с коммитами, веткой, remote, грязным деревом,
        изменёнными файлами и списком файлов для бэкапа.
        """
        server_path = Path(server_path)
        code_path = server_path / 'src'
        git_path = git_root(server_path)
        plan = ServerstrategyModule.get_update_plan(server_type, type_info)

        result = {
            'ok': False,
            'strategy': plan['strategy'],
            'server_type': server_type,
            'path': str(server_path),
            'code_path': str(code_path),
            'git_path': str(git_path),
            'port': port,
        }

        if not (git_path / '.git').exists():
            return {**result, 'error': 'Не git-репозиторий: нет ни src/.git, ни code/.git, ни .git в корне',
                    'code': 'NOT_A_REPO'}

        expected = (type_info or {}).get('repository') or {}
        want_branch = expected.get('branch', 'main')
        want_url = expected.get('url', '')

        # --- текущее состояние
        _, local_sha, _ = _git(git_path, 'rev-parse', 'HEAD')
        _, branch, _ = _git(git_path, 'branch', '--show-current')
        _, remote_url, _ = _git(git_path, 'remote', 'get-url', 'origin')

        # --- рабочее дерево
        # без strip: ведущие пробелы - часть кодов состояния porcelain
        rc, dirty_raw, _ = _git(git_path, 'status', '--porcelain', strip=False)
        dirty = [l for l in dirty_raw.splitlines() if l.strip()] if rc == 0 else []

        result.update({
            'local_commit': local_sha,
            'branch': branch,
            'remote_url': remote_url,
            'expected_branch': want_branch,
            'expected_url': want_url,
            'dirty': bool(dirty),
            'dirty_count': len(dirty),
            'dirty_sample': dirty[:15],
        })

        # --- несоответствия конфигурации типа
        warnings = []
        if want_branch and branch and branch != want_branch:
            warnings.append(f'Ветка {branch} != {want_branch} из SERVER_TYPES')
        if want_url and remote_url:
            if want_url.rstrip('/') not in remote_url.rstrip('/'):
                warnings.append(f'origin {remote_url} не соответствует {want_url}')
        # штатные изменения (composer/npm/ассеты/кэш) обновлению не мешают,
        # остальные по-прежнему блокируют
        blocking = [l for l in dirty if not _is_benign_dirty(l)]
        benign = [l for l in dirty if _is_benign_dirty(l)]

        result['dirty_benign'] = benign
        result['dirty_benign_count'] = len(benign)
        result['dirty_blocking'] = blocking
        result['dirty_blocking_count'] = len(blocking)

        if benign:
            warnings.append(
                f'Штатных изменений {len(benign)} (composer/npm/ассеты/кэш) — обновлению не мешают'
            )

        if blocking and not plan.get('allow_dirty'):
            return {**result, 'error': (
                f'Рабочее дерево содержит {len(blocking)} незакоммиченных изменений. '
                'Обновление остановлено — зафиксируйте или отмените их.'
            ), 'code': 'DIRTY_TREE', 'warnings': warnings,
                'blocking_sample': blocking[:15]}
        if dirty and plan.get('allow_dirty') and plan.get('force_reset'):
            warnings.append('force_reset: незакоммиченные изменения будут потеряны')

        result['warnings'] = warnings

        # --- что приедет
        plan_fetch = {'fetch': True, 'behind': None, 'ahead': None,
                      'incoming': [], 'changed_files': []}
        if remote_url:
            rc, _, err = _git(git_path, 'fetch', '--quiet', 'origin', timeout=plan['timeout']['pull'])
            if rc != 0:
                result['warnings'] = warnings + [f'git fetch не удался: {err[:200]}']
            else:
                _, remote_sha, _ = _git(git_path, 'rev-parse', '@{u}')
                plan_fetch['remote_commit'] = remote_sha
                if local_sha and remote_sha:
                    behind = _git(git_path, 'rev-list', '--count', 'HEAD..@{u}')[1]
                    ahead = _git(git_path, 'rev-list', '--count', '@{u}..HEAD')[1]
                    plan_fetch['behind'] = int(behind) if behind.isdigit() else None
                    plan_fetch['ahead'] = int(ahead) if ahead.isdigit() else None
                    _, log, _ = _git(
                        git_path, 'log', '--oneline', '--no-decorate',
                        '-20', f'HEAD..@{{u}}', timeout=30)
                    plan_fetch['incoming'] = log.splitlines()
                    _, files, _ = _git(
                        git_path, 'diff', '--name-only', 'HEAD..@{u}', timeout=60)
                    plan_fetch['changed_files'] = files.splitlines()
                    plan_fetch['up_to_date'] = (local_sha == remote_sha)
        result['fetch'] = plan_fetch

        # --- чего ждём по файлам (для решения "нужны ли зависимости")
        # пути в diff корневые: для корневого репозитория requirements.txt
        # приезжает как code/requirements.txt — сравниваем по последнему сегменту
        changed = set(plan_fetch['changed_files'])
        result['detected'] = {
            'composer': bool((code_path / 'composer.json').exists()),
            'composer_lock': (code_path / 'composer.lock').exists(),
            'composer_lock_changed': _in_changed(changed, 'composer.lock'),
            'package_json': (code_path / 'package.json').exists(),
            'package_json_changed': _in_changed(changed, 'package.json') or _in_changed(changed, 'package-lock.json'),
            'requirements_txt': (code_path / 'requirements.txt').exists(),
            'requirements_changed': _in_changed(changed, 'requirements.txt'),
            'artisan': (code_path / 'artisan').exists(),
            'dockerfile_changed': any(
                f.lower().startswith(('dockerfile', 'code/docker/', 'src/docker/', 'docker/'))
                for f in changed
            ),
            'compose_example_changed': any(
                'docker-compose.example' in f for f in changed
            ),
            'env_example_changed': any(
                f.endswith('.env.example') for f in changed
            ),
        }

        # --- нечего делать
        if plan_fetch.get('up_to_date'):
            return {**result, 'ok': True, 'no_changes': True,
                    'error': 'Уже на последнем коммите', 'code': 'UP_TO_DATE'}

        result['ok'] = True
        return result

    # ==================== ФАЗА 0.5: БЭКАП ====================

    @staticmethod
    def backup(server_path, preflight: dict, plan: dict) -> dict:
        """Бэкап перед обновлением. Возвращает пути для отката."""
        server_path = Path(server_path)
        code_path = git_root(server_path)
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = server_path / 'storage' / 'starter_backups' / stamp
        backup_cfg = (plan.get('backup') or {})

        info = {'dir': str(backup_dir), 'stamp': stamp, 'git_bundle': None, 'docker_dir': None}

        backup_dir.mkdir(parents=True, exist_ok=True)

        # 1. git bundle — содержимое репозитория целиком, восстанавливается офлайн
        if backup_cfg.get('git_bundle', True):
            bundle = backup_dir / 'code.bundle'
            try:
                kw = _subprocess_kwargs(300, cwd=code_path)
                r = subprocess.run(
                    ['git', 'bundle', 'create', str(bundle), '--all'], **kw)
                if r.returncode == 0 and bundle.exists():
                    info['git_bundle'] = str(bundle)
                else:
                    info['git_bundle_error'] = (r.stderr or '')[:300]
            except Exception as e:
                info['git_bundle_error'] = str(e)

        # 2. копия docker/.env и docker-compose.yml — их руками правит пользователь,
        #    в git их нет, откатить через bundle невозможно
        if backup_cfg.get('docker_dir', True):
            snap = backup_dir / 'docker'
            snap.mkdir(parents=True, exist_ok=True)
            for name in ('.env', '.env.example', 'docker-compose.yml'):
                src = server_path / 'docker' / name
                if src.exists():
                    shutil.copy2(src, snap / name)
                    info.setdefault('docker_files', []).append(name)
            info['docker_dir'] = str(snap)

        info['ok'] = bool(info.get('git_bundle') or info.get('docker_dir'))
        if not info['ok']:
            logger.warning('Backup создан не полностью: %s', info)
        return info

    # ==================== ФАЗА 1: PULL ====================

    @staticmethod
    def pull(server_path, preflight: dict, plan: dict) -> dict:
        """git pull --ff-only. Merge-коммит запрещён — иначе расхождение веток
        при следующем обновлении уже не разрешится."""
        code_path = git_root(Path(server_path))

        if plan.get('force_reset'):
            target = preflight.get('fetch', {}).get('remote_commit', '')
            if not target:
                return {'ok': False, 'error': 'force_reset без remote_commit'}
            rc, out, err = _git(code_path, 'reset', '--hard', target,
                                timeout=plan['timeout']['pull'])
            return {'ok': rc == 0, 'action': 'reset --hard',
                    'output': out or err[:300]}

        mode = plan.get('pull_mode', '--ff-only')
        args = ['pull', mode, '--no-rebase'] if mode == '--ff-only' else ['pull', mode]
        rc, out, err = _git(code_path, *args, timeout=plan['timeout']['pull'])
        if rc == 0:
            _, new_sha, _ = _git(code_path, 'rev-parse', 'HEAD')
            return {'ok': True, 'action': 'pull', 'commit': new_sha, 'output': out[:500]}
        return {'ok': False, 'action': 'pull', 'error': err[:500] or out[:500]}

    # ==================== ФАЗА 2: ЗАВИСИМОСТИ ====================

    @staticmethod
    def _run(cmd, cwd, timeout, log_tail=800, env=None):
        try:
            kw = _subprocess_kwargs(timeout, cwd=cwd)
            if env is not None:
                kw['env'] = env
            r = subprocess.run(cmd, **kw)
            out = ((r.stdout or '') + (r.stderr or '')).strip()
            return {'ok': r.returncode == 0, 'code': r.returncode, 'output': out[-log_tail:]}
        except FileNotFoundError:
            return {'ok': False, 'error': f'{cmd[0]} не найден'}
        except subprocess.TimeoutExpired:
            return {'ok': False, 'error': f'{cmd[0]} превысил {timeout}s'}

    @staticmethod
    def run_dependencies(server_path, preflight: dict, plan: dict) -> dict:
        """Зависимости и сборка фронта — по стратегии и по факту изменения файлов."""
        server_path = Path(server_path)
        code_path = server_path / 'src'
        det = preflight.get('detected') or {}
        deps = plan.get('deps') or {}
        strategy = plan['strategy']
        timeout = plan['timeout']['deps']
        steps = []

        # composer — только для php и только если lock реально менялся
        if strategy == ServerstrategyModule.STRATEGY_PHP and det.get('composer'):
            mode = deps.get('composer', 'auto')
            needed = (mode is True) or (mode == 'auto' and det.get('composer_lock_changed'))
            if needed:
                from files.web.sections.servers import _composer_cmd
                composer = _composer_cmd()
                if not composer:
                    steps.append({'name': 'composer', 'ok': False,
                                  'error': 'composer не найден на хосте'})
                else:
                    steps.append({
                        'name': 'composer',
                        'cmd': 'install --no-dev --optimize-autoloader',
                        **ServerstrategyModule._run(
                            composer + ['install', '--no-dev', '--optimize-autoloader',
                                        '--no-interaction', '--working-dir=' + str(code_path)],
                            code_path, timeout),
                    })
            else:
                steps.append({'name': 'composer', 'skipped': 'composer.lock не менялся'})

        # npm ci + build
        if strategy == ServerstrategyModule.STRATEGY_PHP and deps.get('npm'):
            mode = deps.get('npm', 'auto')
            needed = (mode is True) or (mode == 'auto' and det.get('package_json'))
            if not needed:
                steps.append({'name': 'npm', 'skipped': 'package.json не менялся'})
            elif not det.get('package_json'):
                # Критично для клиентов без package.json в репозитории:
                # фронт нечем пересобрать — сообщаем явно, молча не пропускаем.
                steps.append({
                    'name': 'npm', 'skipped': True,
                    'warning': 'package.json отсутствует в code/ — сборка фронта невозможна. '
                               'Если в репозитории нет package.json, public/build должен '
                               'быть закоммичен, иначе после обновления CSS/JS пропадут.',
                })
            else:
                ci = ServerstrategyModule._run(
                    ['npm', 'ci', '--no-audit', '--no-fund'], code_path, timeout)
                steps.append({'name': 'npm_ci', **ci})
                if ci['ok'] and deps.get('npm_build', True):
                    build = ServerstrategyModule._run(
                        ['npm', 'run', 'build'], code_path, timeout)
                    steps.append({'name': 'npm_build', **build})
                elif not ci['ok']:
                    steps.append({'name': 'npm_build', 'skipped': 'npm ci не прошёл'})

        # pip install -r requirements.txt
        if strategy == ServerstrategyModule.STRATEGY_PYTHON and det.get('requirements_txt'):
            mode = deps.get('pip', 'auto')
            needed = (mode is True) or (mode == 'auto' and det.get('requirements_changed'))
            if needed:
                steps.append({
                    'name': 'pip',
                    'cmd': 'pip install -r requirements.txt',
                    **ServerstrategyModule._run(
                        pip_cmd() + ['install', '-r', 'requirements.txt'],
                        code_path, timeout),
                })
            else:
                steps.append({'name': 'pip', 'skipped': 'requirements.txt не менялся'})

        return {'ok': all(s.get('ok', True) for s in steps), 'steps': steps}

    # ==================== ФАЗА 3: DOCKER-КОНФИГ ====================

    @staticmethod
    def regenerate_docker_config(server_path, preflight: dict, plan: dict,
                                 type_info: dict = None, server_type: str = '') -> dict:
        """Регенерация docker/ из шаблона репозитория + слияние .env.

        Раньше эта фаза отсутствовала: после git pull новый
        docker-compose.example из репозитория просто игнорировался,
        а новые переменные не попадали в docker/.env.
        """
        server_path = Path(server_path)
        docker_path = server_path / 'docker'
        dock = plan.get('docker') or {}
        out = {}

        if dock.get('merge_env_example', True):
            out['env'] = merge_env_example(server_path / 'src', docker_path)

        if dock.get('regenerate_compose', True):
            env_vars = read_env(docker_path / '.env')
            # подставляем вычисляемые значения, как в install_server
            project = compose_project_name(server_path, server_type)
            env_vars['PROJECTNAME'] = project
            prefix = preflight.get('docker_network_prefix')
            if prefix:
                env_vars['DOCKER_NETWORK_PREFIX'] = prefix
            env_vars['PATH_APP_CODE'] = str(server_path / 'src')
            env_vars['PATH_APP_DOCKER'] = str(docker_path)
            env_vars['PATH_APP_DOCKER_LOGS'] = str(docker_path / 'logs')
            env_vars['PATH_APP_PROJECT'] = str(server_path / 'src')

            set_env_keys(docker_path / '.env',
                         {k: env_vars[k] for k in
                          ('PROJECTNAME', 'DOCKER_NETWORK_PREFIX') if env_vars.get(k)})

            out['compose'] = render_compose(server_path, env_vars)

        if dock.get('apply_storage_settings', True):
            try:
                from files.web.sections.servers import _apply_storage_settings
                out['storage'] = _apply_storage_settings(
                    server_type, type_info or {}, docker_path, None)
            except Exception as e:
                out['storage'] = {'error': str(e)}

        return out

    # ==================== ФАЗА 4: МИГРАЦИИ ====================

    @staticmethod
    def run_migrations(server_path, plan: dict) -> dict:
        """artisan migrate внутри контейнера php-<project>.

        На хосте PHP нет, поэтому только через docker exec.
        Схема БД после обновления может разъехаться с кодом.
        """
        mode = plan.get('migrate', 'auto')
        code_path = Path(server_path) / 'src'
        has_artisan = (code_path / 'artisan').exists()

        if mode == False or mode is False:
            return {'ok': True, 'skipped': 'отключено в конфиге типа'}
        if mode == 'auto' and not has_artisan:
            return {'ok': True, 'skipped': 'нет artisan'}

        project = compose_project_name(server_path, '')
        container = f'php-{project}'
        res = ServerstrategyModule._run(
            ['docker', 'exec', container, 'php', 'artisan', 'migrate', '--force'],
            None, plan['timeout']['migrate'])
        if not res['ok']:
            return {**res, 'container': container,
                    'hint': f'вручную: docker exec {container} php artisan migrate --force'}
        return {'ok': True, 'container': container, 'output': res.get('output', '')[-400:]}

    # ==================== ФАЗА 5: ПЕРЕЗАПУСК ====================

    @staticmethod
    def restart(server_path, plan: dict, preflight: dict = None) -> dict:
        """docker compose build (если менялся Dockerfile) + up -d."""
        dock = plan.get('docker') or {}
        if not dock.get('restart', True):
            return {'ok': True, 'skipped': 'перезапуск отключён в конфиге типа'}

        server_path = Path(server_path)
        docker_path = server_path / 'docker'
        if not (docker_path / 'docker-compose.yml').exists():
            return {'ok': True, 'skipped': 'нет docker-compose.yml'}

        steps = []
        mode = dock.get('build', 'auto')
        det = (preflight or {}).get('detected') or {}
        need_build = (mode is True) or (mode == 'auto' and det.get('dockerfile_changed'))

        if need_build:
            steps.append({'name': 'build',
                          **ServerstrategyModule._run(compose_cmd(server_path, 'build'),
                                                       docker_path, plan['timeout']['docker'],
                                                       env=_compose_env_for(docker_path))})
        up = ServerstrategyModule._run(compose_cmd(server_path, 'up', '-d'),
                                       docker_path, plan['timeout']['docker'],
                                       env=_compose_env_for(docker_path))
        steps.append({'name': 'up', **up})

        return {'ok': up['ok'], 'steps': steps,
                'built': need_build, 'project': compose_project_name(server_path, '')}

    # ==================== ФАЗА 6: ПРОВЕРКА ====================

    @staticmethod
    def verify(server_path, port: int = 0, server_type: str = '',
               plan: dict = None) -> dict:
        """Контейнеры running? Порт отвечает? Если нет — сигнал на откат."""
        hc = (plan or {}).get('health_check') or {}
        if not hc.get('enabled', True):
            return {'ok': True, 'skipped': 'health-check отключён в конфиге типа'}

        try:
            from files.web.sections.servers import _check_server_status
            status = _check_server_status(server_path, server_type)
        except Exception as e:
            status = f'error: {e}'

        result = {'ok': status == 'running', 'container_status': status}

        if port:
            retries = int(hc.get('retries', 10))
            interval = int(hc.get('interval', 5))
            up = False
            for _ in range(retries):
                if ServerstrategyModule._probe_port(port, hc.get('path', '/')):
                    up = True
                    break
                time.sleep(interval)
            result['http'] = up
            if not up:
                result['ok'] = False

        return result

    @staticmethod
    def _probe_port(port: int, path: str = '/') -> bool:
        import urllib.request
        url = f'http://127.0.0.1:{int(port)}{path or "/"}'
        try:
            req = urllib.request.Request(url, method='GET')
            with urllib.request.urlopen(req, timeout=5) as r:
                return 200 <= r.status < 500
        except urllib.error.HTTPError as e:
            # 4xx — сервер жив, просто маршрут не тот
            return 400 <= e.code < 500
        except Exception:
            return False

    # ==================== ОТКАТ ====================

    @staticmethod
    def rollback(server_path, backup_info: dict, plan: dict) -> dict:
        """Возврат к сохранённому состоянию."""
        server_path = Path(server_path)
        code_path = server_path / 'src'
        out = {'restored': [], 'ok': False}

        prev = backup_info.get('local_commit')
        if prev:
            rc, _, err = _git(code_path, 'reset', '--hard', prev)
            out['code'] = {'ok': rc == 0, 'error': err[:300]}
            if rc == 0:
                out['restored'].append(f'code -> {prev[:12]}')

        snap = backup_info.get('docker_dir')
        if snap and Path(snap).exists():
            for name in backup_info.get('docker_files', []):
                src = Path(snap) / name
                if src.exists():
                    shutil.copy2(src, server_path / 'docker' / name)
                    out['restored'].append(f'docker/{name}')

        try:
            up = ServerstrategyModule._run(
                compose_cmd(server_path, 'up', '-d'),
                server_path / 'docker', plan['timeout']['docker'],
                env=_compose_env_for(server_path / 'docker'))
            out['restart'] = up
        except Exception as e:
            out['restart'] = {'ok': False, 'error': str(e)}

        out['ok'] = all(c.get('ok', True) for c in out.values() if isinstance(c, dict))
        return out


def pip_cmd():
    """pip может отсутствовать как отдельная команда — берём '<python> -m pip'."""
    import sys
    return [sys.executable, '-m', 'pip']