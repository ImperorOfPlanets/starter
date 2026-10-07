"""
Сквозной тест: удалить клиентов -> установить через API -> модули -> обновления.

Запуск:
    python e2e_test.py            # все фазы
    python e2e_test.py delete      # только удаление
    python e2e_test.py install    # только установка
    python e2e_test.py modules    # только модули
    python e2e_test.py updates    # только обновления

Каждая фаза пишет в лог и печатает отчёт. Скрипт перезапускаемый:
удалённые клиенты переустанавливаются, результаты пишутся в
C:\\Users\\...\\e2e_result.json
"""
import json
import os
import subprocess
import sys
import time
import ssl
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# Стартер работает по https с самоподписанным сертификатом, поэтому
# проверку отключаем: это локальный адрес 127.0.0.1/localhost.
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

API_KEY = 'fc5b3dc89b4998cf2fddb7278690c6813ca265b408618d78b53b6f4d68d51a1f'
# 127.0.0.1, а не localhost: на этой машине Docker Desktop держит
# wslrelay на [::1]:2000, и localhost по IPv6 уходит в него вместо
# стартера - получаем SSL: WRONG_VERSION_NUMBER.
BASE = 'https://127.0.0.1:2000/api/v1'

CONTROL = Path(r'C:\control')
RESULT = Path(os.environ.get('TEMP', '.')) / 'e2e_result.json'

CLIENTS = [
    ('clientv2',       r'C:\control\CLIENTv2'),
    ('client_core',    r'C:\control\client-core'),
    ('client_city',    r'C:\control\client-city'),
    ('client_medical', r'C:\control\CLIENT-MEDICAL'),
]

MODULES = [
    ('wall',     'client_city'),
    ('shop',     'client_core'),
    ('payments', 'client_medical'),
    ('pages',    'clientv2'),
]


def log(msg):
    print(msg, flush=True)


def api(method, path, payload=None, timeout=3600):
    url = BASE + path
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={'X-API-Key': API_KEY,
                                          'Accept': 'application/json',
                                          'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as r:
            body = r.read().decode('utf-8', errors='replace')
            try:
                return r.status, json.loads(body)
            except Exception:
                return r.status, body
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, body
    except Exception as e:
        return None, str(e)


def save_result(data):
    RESULT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def load_result():
    if RESULT.exists():
        return json.loads(RESULT.read_text(encoding='utf-8'))
    return {}


# ------------------------------------------------------------------ фаза DELETE
def phase_delete():
    log('=' * 70)
    log('ФАЗА 1. УДАЛЕНИЕ клиентов через API')
    log('=' * 70)

    out = {}
    for server_id, path in CLIENTS:
        url_path = '/servers/' + urllib.parse.quote(path.replace('\\', '/'), safe='') + '/remove'
        log(f'\n--- удаляю {path}')
        log(f'    DELETE {url_path}')
        st, body = api('DELETE', url_path, timeout=600)
        log(f'    HTTP {st}: {json.dumps(body, ensure_ascii=False)[:200] if isinstance(body, dict) else str(body)[:200]}')
        out[path] = {'http': st, 'body': body}

        time.sleep(2)

    # проверяем, что папок нет
    log('\n--- проверка папок')
    for server_id, path in CLIENTS:
        exists = Path(path).exists()
        log(f'    {path}: {"ОСТАЛАСЬ" if exists else "удалена"}')

    r = load_result()
    r['delete'] = out
    save_result(r)
    return out


# ----------------------------------------------------------------- фаза INSTALL
def phase_install():
    log('')
    log('=' * 70)
    log('ФАЗА 2. УСТАНОВКА через API')
    log('=' * 70)

    out = {}
    for server_id, path in CLIENTS:
        log(f'\n=== установка {server_id} -> {path}')
        t0 = time.time()
        st, body = api('POST', '/servers/install',
                       {'server_type': server_id, 'path': path,
                        'name': Path(path).name, 'force': True}, timeout=3600)
        dt = time.time() - t0
        log(f'    HTTP {st} за {dt:.0f} с')
        if isinstance(body, dict):
            log('    ' + json.dumps(body, ensure_ascii=False)[:600])
        else:
            log('    ' + str(body)[:600])
        out[server_id] = {'http': st, 'body': body, 'seconds': round(dt)}

    r = load_result()
    r['install'] = out
    save_result(r)
    return out


# ------------------------------------------------------------ проверка .env
def check_env():
    log('')
    log('=' * 70)
    log('ПРОВЕРКА: .env каждого клиента (порты и хосты должны различаться)')
    log('=' * 70)

    rows = {}
    for server_id, path in CLIENTS:
        env_path = Path(path) / 'docker' / '.env'
        if not env_path.exists():
            log(f'  {server_id}: .env НЕ СОЗДАН')
            continue

        vals = {}
        for line in env_path.read_text(encoding='utf-8', errors='replace').replace('\r\n', '\n').split('\n'):
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, _, v = line.partition('=')
                vals[k.strip()] = v.strip()

        rows[server_id] = {
            'PROJECTNAME': vals.get('PROJECTNAME', ''),
            'PORT': vals.get('PORT', ''),
            'PORT_SSL': vals.get('PORT_SSL', ''),
            'DB_HOST': vals.get('DB_HOST', ''),
            'REDIS_HOST': vals.get('REDIS_HOST', ''),
            'PATH_APP_CODE': vals.get('PATH_APP_CODE', ''),
        }
        log(f'  {server_id}:')
        for k, v in rows[server_id].items():
            log(f'      {k:14} = {v}')

    # проверки
    log('')
    log('--- проверки ---')
    ports = [v['PORT'] for v in rows.values() if v['PORT']]
    log(f'  порты HTTP: {ports}  {"УНИКАЛЬНЫ" if len(set(ports)) == len(ports) and ports else "ПРОБЛЕМА"}')
    ssls = [v['PORT_SSL'] for v in rows.values() if v['PORT_SSL']]
    log(f'  порты SSL:  {ssls}  {"УНИКАЛЬНЫ" if len(set(ssls)) == len(ssls) and ssls else "ПРОБЛЕМА"}')
    dbs = [v['DB_HOST'] for v in rows.values() if v['DB_HOST']]
    log(f'  DB_HOST:    {dbs}  {"УНИКАЛЬНЫ" if len(set(dbs)) == len(dbs) and dbs else "ПРОБЛЕМА"}')
    paths = [v['PATH_APP_CODE'] for v in rows.values() if v['PATH_APP_CODE']]
    log(f'  PATH_APP_CODE уникальны: {"ДА" if len(set(paths)) == len(paths) and paths else "НЕТ"}')

    r = load_result()
    r['env'] = rows
    save_result(r)
    return rows


# ------------------------------------------------------------ проверка клиентов
def check_clients():
    log('')
    log('=' * 70)
    log('ПРОВЕРКА: контейнеры и таблицы')
    log('=' * 70)

    out = {}
    for server_id, path in CLIENTS:
        pn = Path(path).name
        log(f'\n--- {pn}')

        r = subprocess.run(['docker', 'ps', '--format', '{{.Names}} {{.Status}}'],
                           capture_output=True, text=True, encoding='utf-8', errors='replace')
        mine = [l for l in r.stdout.splitlines() if pn.lower() in l.lower()]
        log(f'    контейнеров запущено: {len(mine)}')
        for l in mine:
            log(f'        {l}')

        # таблицы
        proj = pn.lower()
        mr = subprocess.run(['docker', 'exec', f'mariadb-{proj}',
                             'mysql', '-uroot', '-N', '-B', '-e',
                             "SELECT COUNT(*) FROM information_schema.tables "
                             "WHERE table_schema='client'"],
                            capture_output=True, text=True, encoding='utf-8', errors='replace')
        tables = (mr.stdout or '').strip().splitlines()
        tables = tables[-1] if tables else '?'
        log(f'    таблиц в БД: {tables}')

        out[server_id] = {'containers': len(mine), 'tables': tables}

    r = load_result()
    r['clients'] = out
    save_result(r)
    return out


# ---------------------------------------------------------------- фаза MODULES
def phase_modules():
    log('')
    log('=' * 70)
    log('ФАЗА 3. УСТАНОВКА МОДУЛЕЙ поверх установленных клиентов (через API)')
    log('=' * 70)

    out = {}

    log('\n--- какие типы модулей известны стартеру')
    st, body = api('GET', '/servers/modules')
    log(f'    HTTP {st}: ' + ', '.join(m['key'] for m in (body.get('modules') or []))
        if isinstance(body, dict) else f'    HTTP {st}: {str(body)[:200]}')

    for module, target in MODULES:
        path = dict(CLIENTS)[target]
        name = Path(path).name

        log(f'\n=== модуль {module} -> {name}')

        log(f'    GET /servers/modules/hosts?server_type={module}')
        st, hosts = api('GET', f'/servers/modules/hosts?server_type={module}')
        if isinstance(hosts, dict):
            names = [h.get('name') for h in (hosts.get('hosts') or [])]
            log(f'    кандидаты: {names}')

        t0 = time.time()
        st, body = api('POST', '/servers/modules/install',
                       {'server_type': module, 'host_path': path}, timeout=3600)
        dt = time.time() - t0
        log(f'    POST /servers/modules/install -> HTTP {st} за {dt:.0f} с')

        if isinstance(body, dict):
            log('    ' + json.dumps(body, ensure_ascii=False, default=str)[:700])
        else:
            log('    ' + str(body)[:400])

        out[module] = {'host': target, 'path': path, 'http': st,
                       'body': body, 'seconds': round(dt)}

    r = load_result()
    r['modules'] = out
    save_result(r)
    return out


def check_modules():
    log('')
    log('--- проверка таблиц модулей')

    for module, target in MODULES:
        path = dict(CLIENTS)[target]
        proj = Path(path).name.lower()
        mr = subprocess.run(['docker', 'exec', f'mariadb-{proj}', 'mysql', '-uroot', '-N', '-B', '-e',
                             "SELECT table_name FROM information_schema.tables "
                             "WHERE table_schema='client' ORDER BY table_name"],
                            capture_output=True, text=True, encoding='utf-8', errors='replace')
        tables = [l for l in mr.stdout.splitlines() if l.strip()]
        mrch = subprocess.run(['docker', 'exec', f'php-{proj}', 'php', 'artisan', 'route:list'],
                              capture_output=True, text=True, encoding='utf-8', errors='replace',
                              cwd=None)
        log(f'  {module} в {proj}: таблиц всего {len(tables)}, маршрутов '
            f'{[l for l in mrch.stdout.splitlines() if "Showing" in l]}')

    r = load_result()
    r['modules_checked'] = True
    save_result(r)


# ---------------------------------------------------------------- фаза UPDATES
def phase_updates():
    log('')
    log('=' * 70)
    log('ФАЗА 4. ОБНОВЛЕНИЯ (разные виды серверов)')
    log('=' * 70)

    out = {}

    def sid(path):
        return '/servers/' + urllib.parse.quote(path.replace(chr(92), '/'), safe='')

    def show(title, res, limit=700):
        log(f'\n--- {title}')
        if isinstance(res, tuple):
            code, body = res
            log(f'    HTTP {code}')
            log('    ' + json.dumps(body, ensure_ascii=False, default=str)[:limit])
        else:
            log('    ' + json.dumps(res, ensure_ascii=False, default=str)[:limit])

    # 4a. plan и preflight по всем четырём типам клиентов: ничего не меняют
    for server_id, path in CLIENTS:
        show(f'4a. plan: {Path(path).name}', api('GET', sid(path) + '/update/plan'), 400)
        show(f'4a. preflight: {Path(path).name}', api('GET', sid(path) + '/update/preflight'), 500)

    # 4b. реальное обновление одного клиента (clientv2 + модуль pages)
    target, target_path = CLIENTS[0]
    t0 = time.time()
    res = api('POST', sid(target_path) + '/update', {'dry_run': True}, timeout=1800)
    show(f'4b. update dry_run: {Path(target_path).name} ({time.time() - t0:.0f} с)', res, 900)
    out['dry_run'] = {'server': target, 'result': str(res[1])[:2000]}

    t0 = time.time()
    res = api('POST', sid(target_path) + '/update', {}, timeout=3600)
    show(f'4c. update реально: {Path(target_path).name} ({time.time() - t0:.0f} с)', res, 1600)
    out['update'] = {'server': target, 'result': str(res[1])[:3000]}

    # 4d. обновление модуля: сначала всухую, затем по-настоящему
    res = api('POST', '/servers/modules/update',
              {'server_type': 'wall', 'host_path': dict(CLIENTS)['client_city'],
               'dry_run': True}, timeout=1800)
    show('4d. update_module dry_run (wall -> client-city)', res, 900)

    t0 = time.time()
    res = api('POST', '/servers/modules/update',
              {'server_type': 'wall', 'host_path': dict(CLIENTS)['client_city']},
              timeout=3600)
    show(f'4e. update_module реально ({time.time() - t0:.0f} с)', res, 1200)
    out['update_module'] = {'module': 'wall', 'result': str(res[1])[:2500]}

    # 4f. обновление всех клиентов разом
    t0 = time.time()
    res = api('POST', '/servers/update-clients', {'dry_run': True}, timeout=3600)
    show(f'4f. update-clients dry_run ({time.time() - t0:.0f} с)', res, 1600)
    out['update_clients_dry'] = str(res[1])[:3000]

    r = load_result()
    r['updates'] = out
    save_result(r)
    return out


# ---------------------------------------------------------------------- main
def phase_start():
    log('')
    log('=' * 70)
    log('ФАЗА 2b. ЗАПУСК через API')
    log('=' * 70)

    out = {}
    for server_id, path in CLIENTS:
        url_path = '/servers/' + urllib.parse.quote(path.replace(chr(92), '/'), safe='') + '/start'
        log(f'\n--- старт {Path(path).name}')
        t0 = time.time()
        st, body = api('POST', url_path, timeout=3600)
        dt = time.time() - t0
        log(f'    HTTP {st} за {dt:.0f} с')
        if isinstance(body, dict):
            for c in (body.get('checks') or []):
                log(f"        [{c.get('status',''):6}] {c.get('step','')}: {str(c.get('message',''))[:110]}")
            if not body.get('checks'):
                log('    ' + json.dumps(body, ensure_ascii=False)[:300])
        else:
            log('    ' + str(body)[:300])
        out[server_id] = {'http': st, 'body': body, 'seconds': round(dt)}

    r = load_result()
    r['start'] = out
    save_result(r)
    return out


PHASES = {
    'delete': phase_delete,
    'install': phase_install,
    'start': phase_start,
    'env': check_env,
    'clients': check_clients,
    'modules': phase_modules,
    'modules_check': check_modules,
    'updates': phase_updates,
}

ORDER = ['delete', 'install', 'start', 'env', 'clients', 'modules', 'modules_check', 'updates']

if __name__ == '__main__':
    want = sys.argv[1:] or ORDER

    log(f'Старт: {time.strftime("%Y-%m-%d %H:%M:%S")}')
    log(f'Фазы: {", ".join(want)}')

    for name in want:
        fn = PHASES.get(name)
        if not fn:
            log(f'\n!!! неизвестная фаза: {name}')
            continue
        try:
            fn()
        except Exception as e:
            log(f'\n!!! ФАЗА {name} УПАЛА: {type(e).__name__}: {e}')
            import traceback
            log(traceback.format_exc()[:1500])
            r = load_result()
            r.setdefault('errors', []).append(f'{name}: {e}')
            save_result(r)

    log('')
    log('=' * 70)
    log(f'Готово. Результат: {RESULT}')
    log('=' * 70)