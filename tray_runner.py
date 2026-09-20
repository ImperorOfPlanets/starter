#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
tray_runner.py -- Standalone tray icon process for Starter Server.
Launched by the service (pythonw.exe) via subprocess using python.exe.
Must run under python.exe (NOT pythonw.exe) for pystray message loop.

Usage:
    python.exe tray_runner.py --port 2000 --starter-path C:\\control\\starter
"""
import sys
import os
import argparse
import json
import logging
import re
import socket
import subprocess
import time
import threading
from pathlib import Path
from logging.handlers import RotatingFileHandler

# Add starter_path to sys.path BEFORE any project imports
_starter_path = None

# --- File logging (so errors are visible) ---
_logger = None

# --- Tray translations (separate from web i18n) ---
TRAY_TRANSLATIONS = {
    'en': {
        'show': 'Show Starter',
        'start': 'Start web server',
        'stop': 'Stop web server',
        'servers': 'Servers',
        'restart': 'Restart',
        'status': 'Status',
        'settings': 'Settings',
        'quit': 'Quit',
        'no_servers': '(no servers)',
        'lang_tab': 'Language',
        'general_tab': 'General',
        'servers_tab': 'Servers',
        'apply': 'Apply',
        'port': 'Port:',
        'web_server': 'Web server:',
        'service': 'Service:',
        'url': 'URL:',
        'lang_changed': 'Language changed',
        'service_status': 'Starter Status',
        'on': 'ON',
        'off': 'OFF',
    },
    'ru': {
        'show': 'Показать Starter',
        'start': 'Запустить веб-сервер',
        'stop': 'Остановить веб-сервер',
        'servers': 'Серверы',
        'restart': 'Перезапустить',
        'status': 'Статус',
        'settings': 'Настройки',
        'quit': 'Выйти',
        'no_servers': '(нет серверов)',
        'lang_tab': 'Язык',
        'general_tab': 'Основные',
        'servers_tab': 'Серверы',
        'apply': 'Применить',
        'port': 'Порт:',
        'web_server': 'Веб-сервер:',
        'service': 'Сервис:',
        'url': 'URL:',
        'lang_changed': 'Язык изменён',
        'service_status': 'Статус Starter',
        'on': 'ВКЛ',
        'off': 'ВЫКЛ',
    },
    'cn': {
        'show': '显示 Starter',
        'start': '启动 Web 服务器',
        'stop': '停止 Web 服务器',
        'servers': '服务器',
        'restart': '重启',
        'status': '状态',
        'settings': '设置',
        'quit': '退出',
        'no_servers': '(没有服务器)',
        'lang_tab': '语言',
        'general_tab': '基本',
        'servers_tab': '服务器',
        'apply': '应用',
        'port': '端口:',
        'web_server': 'Web 服务器:',
        'service': '服务:',
        'url': 'URL:',
        'lang_changed': '语言已更改',
        'service_status': 'Starter 状态',
        'on': '开启',
        'off': '关闭',
    }
}


def _get_tray_config_path():
    return _starter_path / 'tray_config.json'


def _load_tray_config():
    cfg = {'lang': 'en'}
    try:
        p = _get_tray_config_path()
        if p.exists():
            with open(p, 'r', encoding='utf-8') as f:
                cfg.update(json.load(f))
    except Exception:
        pass
    return cfg


def _save_tray_config(cfg):
    try:
        with open(_get_tray_config_path(), 'w', encoding='utf-8') as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    except Exception as e:
        if _logger:
            _logger.error(f"Failed to save tray config: {e}")


def _tr(key, lang='en'):
    """Get translated tray string"""
    return TRAY_TRANSLATIONS.get(lang, TRAY_TRANSLATIONS['en']).get(key, key)


def _setup_logging(starter_path):
    global _logger
    log_dir = Path(starter_path) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "tray_runner.log"

    _logger = logging.getLogger("tray_runner")
    _logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        '[%(asctime)s] [%(levelname)-7s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    fh = RotatingFileHandler(str(log_file), maxBytes=2*1024*1024, backupCount=3, encoding='utf-8')
    fh.setFormatter(fmt)
    fh.setLevel(logging.DEBUG)
    _logger.addHandler(fh)

    _logger.info(f"tray_runner started, PID={os.getpid()}, log={log_file}")
    return _logger


def _setup_path(starter_path):
    global _starter_path
    _starter_path = Path(starter_path)
    sp = str(_starter_path)
    if sp not in sys.path:
        sys.path.insert(0, sp)


def _si():
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = subprocess.SW_HIDE
    return si


def _find_starter_pids():
    """Find PIDs of all starter.py processes (pythonw.exe only)"""
    pids = []
    try:
        output = subprocess.check_output(
            ['tasklist', '/FI', 'IMAGENAME eq pythonw.exe', '/FO', 'CSV', '/NH'],
            text=True, startupinfo=_si(), timeout=10
        )
        for line in output.split('\n'):
            if not line.strip():
                continue
            match = re.search(r'"(\d+)"', line)
            if match:
                pid = int(match.group(1))
                try:
                    import psutil
                    proc = psutil.Process(pid)
                    cmdline = ' '.join(proc.cmdline())
                    if 'starter.py' in cmdline:
                        pids.append(pid)
                except Exception:
                    pass
    except Exception:
        pass
    return pids


def _is_web_running(port):
    """Check if the web server is responding on the given port"""
    for host in ('localhost', '127.0.0.1'):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                if s.connect_ex((host, port)) == 0:
                    return True
        except Exception:
            pass
    return False


def _is_service_running():
    """Check if a --service process is running"""
    for pid in _find_starter_pids():
        try:
            import psutil
            proc = psutil.Process(pid)
            cmdline = ' '.join(proc.cmdline())
            if '--service' in cmdline:
                return True
        except Exception:
            pass
    return False


def _start_web_server():
    """Start the web server (without --service, without --tray)"""
    if _is_web_running(get_global_port()):
        return True

    venv_pythonw = str(_starter_path / "venv" / "Scripts" / "pythonw.exe")
    script = str(_starter_path / "starter.py")

    if not os.path.exists(venv_pythonw):
        return False

    subprocess.Popen(
        [venv_pythonw, script, '--no-tray'],
        cwd=str(_starter_path),
        startupinfo=_si(),
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    return True


def _stop_web_server():
    """Stop web server processes (non-service starter.py)"""
    stopped = 0
    current_pid = os.getpid()
    for pid in _find_starter_pids():
        if pid == current_pid:
            continue
        try:
            import psutil
            proc = psutil.Process(pid)
            cmdline = ' '.join(proc.cmdline())
            if 'starter.py' in cmdline and '--service' not in cmdline:
                subprocess.run(['taskkill', '/F', '/PID', str(pid)],
                               capture_output=True, startupinfo=_si(), timeout=10)
                stopped += 1
        except Exception:
            pass
    return stopped


def _kill_all():
    """Kill all starter processes"""
    for pid in _find_starter_pids():
        subprocess.run(['taskkill', '/F', '/PID', str(pid)],
                       capture_output=True, startupinfo=_si(), timeout=10)


def _balloon(title, message):
    """Show Windows balloon notification via PowerShell"""
    ps_cmd = f'''
    Add-Type -AssemblyName System.Windows.Forms
    $notify = New-Object System.Windows.Forms.NotifyIcon
    $notify.Icon = [System.Drawing.Icon]::ExtractAssociatedIcon([System.Windows.Forms.Application]::ExecutablePath)
    $notify.Visible = $true
    $notify.ShowBalloonTip(3000, "{title}", "{message}", [System.Windows.Forms.ToolTipIcon]::Info)
    '''
    try:
        subprocess.run(['powershell', '-Command', ps_cmd],
                       capture_output=True, startupinfo=_si(), timeout=10)
    except Exception:
        pass


def _wait_for_port(port, timeout=15):
    """Wait until the port is open, returns True if success"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _is_web_running(port):
            return True
        time.sleep(0.5)
    return False


def get_global_port():
    """Read port from .env or processes.json, default 2000"""
    # Try .env first
    env_file = _starter_path / '.env'
    try:
        if env_file.exists():
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('PORT=') and not line.startswith('#'):
                        val = line.split('=', 1)[1].strip()
                        if val.isdigit():
                            return int(val)
    except Exception:
        pass
    # Fallback to processes.json
    processes_file = _starter_path / 'processes.json'
    try:
        if processes_file.exists():
            with open(processes_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for pid_str, info in data.items():
                if info.get('port'):
                    return info['port']
    except Exception:
        pass
    return 2000


def _get_servers_from_api(port):
    """Get server list from starter API"""
    import urllib.request
    import ssl
    api_key_file = _starter_path / 'files' / 'crypto' / '.api_key'
    api_key = ''
    try:
        if api_key_file.exists():
            api_key = api_key_file.read_text().strip()
    except Exception:
        pass
    if not api_key:
        return []

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        req = urllib.request.Request(
            f'https://localhost:{port}/api/v1/servers',
            headers={'X-API-Key': api_key}
        )
        resp = urllib.request.urlopen(req, context=ctx, timeout=5)
        data = json.loads(resp.read().decode('utf-8'))
        return data.get('servers', [])
    except Exception as e:
        if _logger:
            _logger.debug(f"API servers fetch failed: {e}")
        return []


def _get_icon_path():
    """Get path to .ico file"""
    icon_path = _starter_path / 'files' / 'web' / 'public' / 'icon.ico'
    if icon_path.exists():
        return str(icon_path)
    return None


def _get_available_languages():
    """Scan locales/ directory for available languages"""
    locales_dir = _starter_path / 'files' / 'web' / 'locales'
    langs = []
    if not locales_dir.exists():
        return langs
    for f in sorted(locales_dir.glob('*.py')):
        if f.name.startswith('_'):
            continue
        code = f.stem
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(f'locale_{code}', str(f))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            tr = getattr(mod, 'translations', {})
            common = tr.get('common', {})
            name = common.get('this_language', code)
            langs.append({'code': code, 'name': name})
        except Exception:
            langs.append({'code': code, 'name': code})
    return langs


def _get_current_language():
    """Read current language from .env"""
    env_file = _starter_path / '.env'
    try:
        if env_file.exists():
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('LANGUAGE=') and not line.startswith('#'):
                        return line.split('=', 1)[1].strip()
    except Exception:
        pass
    return 'en'


def _set_language(code):
    """Set language via API (updates .env + in-memory state)"""
    import urllib.request
    import ssl

    api_key_file = _starter_path / 'files' / 'crypto' / '.api_key'
    api_key = ''
    try:
        if api_key_file.exists():
            api_key = api_key_file.read_text().strip()
    except Exception:
        pass

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    # Try API first (updates .env + os.environ in running server)
    port = get_global_port()
    try:
        data_urlencoded = f'section=language&action=changeLanguage&lang={code}'.encode('utf-8')
        req = urllib.request.Request(
            f'https://localhost:{port}/',
            data=data_urlencoded,
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'application/json'
            },
            method='POST'
        )
        # We need session cookie — use cookie jar
        import http.cookiejar
        cj = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
        resp = opener.open(req, timeout=5)
        result = json.loads(resp.read().decode('utf-8'))
        if result.get('status') == 'success':
            if _logger:
                _logger.info(f"Language changed via API: {code}")
            return True
    except Exception as e:
        if _logger:
            _logger.warning(f"API language change failed: {e}, falling back to .env")

    # Fallback: write .env directly
    env_file = _starter_path / '.env'
    try:
        content = env_file.read_text(encoding='utf-8') if env_file.exists() else ''
        if 'LANGUAGE=' in content:
            import re
            content = re.sub(r'LANGUAGE=.*', f'LANGUAGE={code}', content)
        else:
            content += f'\nLANGUAGE={code}\n'
        env_file.write_text(content, encoding='utf-8')
        if _logger:
            _logger.info(f"Language written to .env: {code}")
        return True
    except Exception as e:
        if _logger:
            _logger.error(f"Failed to set language: {e}")
        return False


def run_tray():
    """Main tray entry point"""
    try:
        import pystray
        from PIL import Image, ImageDraw
    except ImportError as e:
        if _logger:
            _logger.error(f"Missing dependency: {e}")
        print(f"ERROR: Missing dependency: {e}")
        print("Install with: pip install pystray Pillow")
        sys.exit(1)

    port = get_global_port()
    url = f"https://localhost:{port}"
    available_langs = _get_available_languages()
    tray_cfg = _load_tray_config()
    tray_lang = tray_cfg.get('lang', 'en')

    if _logger:
        _logger.info(f"Starting tray, port={port}, url={url}, tray_lang={tray_lang}")

    def make_icon(color='#0d6efd', letter='S'):
        try:
            icon_path = _get_icon_path()
            if icon_path:
                img = Image.open(icon_path)
                if img.size != (64, 64):
                    img = img.resize((64, 64), Image.LANCZOS)
                return img
        except Exception:
            pass
        size = 64
        img = Image.new('RGBA', (size, size), color=(0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        margin = 4
        draw.rounded_rectangle([margin, margin, size - margin, size - margin], radius=12, fill=color)
        center = size // 2
        draw.polygon([
            (center - 8, center - 10),
            (center - 8, center + 10),
            (center + 10, center)
        ], fill='white')
        return img

    icon_ref = [None]
    _status_cache = {'web': False, 'service': False, 'servers': [], 'tooltip': 'Starter'}

    def update_icon():
        if not icon_ref[0]:
            return
        try:
            web = _is_web_running(port)
            service = _is_service_running()
            servers = _get_servers_from_api(port) if web else []
            running_count = sum(1 for s in servers if s.get('status') == 'running')

            if web:
                if running_count > 0:
                    color = '#198754'
                    tooltip = f"Starter | {_tr('web_server', tray_lang)} {_tr('on', tray_lang)} | {_tr('servers', tray_lang)}: {running_count}"
                else:
                    color = '#198754'
                    tooltip = f"Starter | {_tr('web_server', tray_lang)} {_tr('on', tray_lang)} | {_tr('port', tray_lang)} {port}"
            else:
                color = '#dc3545'
                tooltip = f"Starter | {_tr('web_server', tray_lang)} {_tr('off', tray_lang)}"

            if service:
                tooltip += f" | {_tr('service', tray_lang)} {_tr('on', tray_lang)}"

            icon_ref[0].icon = make_icon(color)
            icon_ref[0].title = tooltip
            _status_cache.update({'web': web, 'service': service, 'servers': servers, 'tooltip': tooltip})
        except Exception as e:
            if _logger:
                _logger.error(f"update_icon error: {e}")

    def build_servers_submenu():
        servers = _status_cache.get('servers', [])
        if not servers:
            return [pystray.MenuItem(_tr('no_servers', tray_lang), None, enabled=False)]
        items = []
        for s in servers:
            name = s.get('name', s.get('path', '?'))
            status = s.get('status', 'unknown')
            icon_char = '\u25cf' if status == 'running' else '\u25cb'
            items.append(pystray.MenuItem(f"{icon_char} {name} ({status})", None, enabled=False))
        return items

    def on_show(icon, item):
        if not _is_web_running(port):
            _start_web_server()
            _wait_for_port(port)
        import webbrowser
        webbrowser.open(url)

    def on_start(icon, item):
        if _is_web_running(port):
            return
        _start_web_server()
        _wait_for_port(port)
        update_icon()

    def on_stop(icon, item):
        _stop_web_server()
        time.sleep(1)
        update_icon()

    def on_status(icon, item):
        service = _is_service_running()
        web = _is_web_running(port)
        servers = _get_servers_from_api(port) if web else []
        running = [s.get('name', '?') for s in servers if s.get('status') == 'running']
        lines = [
            f"{_tr('service', tray_lang)} {_tr('on', tray_lang) if service else _tr('off', tray_lang)}",
            f"{_tr('web_server', tray_lang)} {_tr('on', tray_lang) if web else _tr('off', tray_lang)}",
            f"{_tr('port', tray_lang)} {port}",
        ]
        if running:
            lines.extend([f"  - {n}" for n in running[:5]])
        _balloon(_tr('service_status', tray_lang), "\n".join(lines))

    def on_restart(icon, item):
        _kill_all()
        time.sleep(2)
        _start_web_server()
        _wait_for_port(port)
        update_icon()

    def on_quit(icon, item):
        _kill_all()
        icon.stop()
        os._exit(0)

    def on_set_tray_lang(code):
        def handler(icon, item):
            nonlocal tray_lang
            tray_lang = code
            tray_cfg['lang'] = code
            _save_tray_config(tray_cfg)
            rebuild_menu()
            _balloon(_tr('lang_changed', tray_lang), f"{_tr('lang_changed', tray_lang)}: {next((l['name'] for l in available_langs if l['code'] == code), code)}")
        return handler

    def build_language_submenu():
        items = []
        for lang in available_langs:
            items.append(pystray.MenuItem(
                f"{'\\u2713 ' if lang['code'] == tray_lang else '   '}{lang['name']}",
                on_set_tray_lang(lang['code']),
                radio=True,
                checked=lambda item, c=lang['code']: c == tray_lang
            ))
        return items

    def on_settings(icon, item):
        """Open settings window"""
        try:
            import tkinter as tk
            from tkinter import ttk
        except ImportError:
            _balloon("Settings", "tkinter not available")
            return

        settings_lang = [tray_lang]

        def settings_thread():
            root = tk.Tk()
            root.title(_tr('settings', settings_lang[0]))
            root.geometry("400x340")
            root.resizable(False, False)

            try:
                root.iconbitmap(str(_starter_path / 'files' / 'web' / 'public' / 'icon.ico'))
            except Exception:
                pass

            notebook = ttk.Notebook(root)
            notebook.pack(fill='both', expand=True, padx=8, pady=8)

            # === General Tab ===
            frame_general = ttk.Frame(notebook)
            notebook.add(frame_general, text=_tr('general_tab', settings_lang[0]))

            ttk.Label(frame_general, text=_tr('port', settings_lang[0])).grid(row=0, column=0, sticky='w', padx=8, pady=4)
            port_var = tk.StringVar(value=str(port))
            ttk.Entry(frame_general, textvariable=port_var, width=10).grid(row=0, column=1, padx=8, pady=4)

            web_status = _tr('on', settings_lang[0]) if _is_web_running(port) else _tr('off', settings_lang[0])
            svc_status = _tr('on', settings_lang[0]) if _is_service_running() else _tr('off', settings_lang[0])
            ttk.Label(frame_general, text=f"{_tr('web_server', settings_lang[0])} {web_status}").grid(row=1, column=0, columnspan=2, sticky='w', padx=8, pady=2)
            ttk.Label(frame_general, text=f"{_tr('service', settings_lang[0])} {svc_status}").grid(row=2, column=0, columnspan=2, sticky='w', padx=8, pady=2)
            ttk.Label(frame_general, text=f"{_tr('url', settings_lang[0])} {url}").grid(row=3, column=0, columnspan=2, sticky='w', padx=8, pady=2)

            # === Language Tab ===
            frame_lang = ttk.Frame(notebook)
            notebook.add(frame_lang, text=_tr('lang_tab', settings_lang[0]))

            lang_var = tk.StringVar(value=tray_lang)
            for i, lang in enumerate(available_langs):
                rb = ttk.Radiobutton(
                    frame_lang,
                    text=f"{lang['name']} ({lang['code']})",
                    variable=lang_var,
                    value=lang['code']
                )
                rb.grid(row=i, column=0, sticky='w', padx=12, pady=4)

            def apply_language():
                code = lang_var.get()
                nonlocal tray_lang
                tray_lang = code
                tray_cfg['lang'] = code
                _save_tray_config(tray_cfg)
                rebuild_menu()
                # Also change web interface language
                _set_language(code)
                _balloon(_tr('lang_changed', tray_lang), f"{_tr('lang_changed', tray_lang)}: {code}")

            ttk.Button(frame_lang, text=_tr('apply', settings_lang[0]), command=apply_language).grid(row=len(available_langs), column=0, pady=8)

            # === Servers Tab ===
            frame_servers = ttk.Frame(notebook)
            notebook.add(frame_servers, text=_tr('servers_tab', settings_lang[0]))

            servers = _status_cache.get('servers', [])
            if servers:
                cols = ('Name', 'Status', 'Type')
                tree = ttk.Treeview(frame_servers, columns=cols, show='headings', height=8)
                tree.heading('Name', text='Name')
                tree.heading('Status', text='Status')
                tree.heading('Type', text='Type')
                tree.column('Name', width=140)
                tree.column('Status', width=80)
                tree.column('Type', width=80)
                tree.pack(fill='both', expand=True, padx=8, pady=4)
                for s in servers:
                    tree.insert('', 'end', values=(
                        s.get('name', s.get('path', '?')),
                        s.get('status', '?'),
                        s.get('type', '?')
                    ))
            else:
                ttk.Label(frame_servers, text=_tr('no_servers', settings_lang[0])).pack(pady=20)

            def on_close():
                root.destroy()

            root.protocol("WM_DELETE_WINDOW", on_close)
            root.mainloop()

        threading.Thread(target=settings_thread, daemon=True).start()

    def rebuild_menu():
        """Rebuild tray menu (for language change)"""
        if not icon_ref[0]:
            return
        new_menu = pystray.Menu(
            pystray.MenuItem(_tr('show', tray_lang), on_show, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(_tr('start', tray_lang), on_start),
            pystray.MenuItem(_tr('stop', tray_lang), on_stop),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(_tr('servers', tray_lang), lambda: pystray.Menu(*build_servers_submenu())),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(_tr('restart', tray_lang), on_restart),
            pystray.MenuItem(_tr('status', tray_lang), on_status),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(_tr('settings', tray_lang), on_settings),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(_tr('quit', tray_lang), on_quit)
        )
        icon_ref[0].menu = new_menu

    menu = pystray.Menu(
        pystray.MenuItem(_tr('show', tray_lang), on_show, default=True),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(_tr('start', tray_lang), on_start),
        pystray.MenuItem(_tr('stop', tray_lang), on_stop),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(_tr('servers', tray_lang), lambda: pystray.Menu(*build_servers_submenu())),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(_tr('restart', tray_lang), on_restart),
        pystray.MenuItem(_tr('status', tray_lang), on_status),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(_tr('settings', tray_lang), on_settings),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(_tr('quit', tray_lang), on_quit)
    )

    icon = pystray.Icon(
        "starter_server",
        make_icon('#0d6efd'),
        "Starter Server",
        menu
    )
    icon_ref[0] = icon

    def monitor_loop():
        while True:
            time.sleep(5)
            update_icon()

    threading.Thread(target=monitor_loop, daemon=True).start()

    if _logger:
        _logger.info("Tray icon started, waiting for user actions")

    icon.run()


def main():
    parser = argparse.ArgumentParser(description='Starter Server Tray Icon')
    parser.add_argument('--port', type=int, default=2000, help='Port of the starter web server')
    parser.add_argument('--starter-path', type=str, required=True, help='Path to starter directory')
    args = parser.parse_args()

    _setup_path(args.starter_path)
    _setup_logging(args.starter_path)

    if _logger:
        _logger.info(f"Arguments: port={args.port}, starter_path={args.starter_path}")

    run_tray()


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        # Last resort: write to stderr or a known file
        try:
            log_path = Path(__file__).parent / "logs" / "tray_runner.log"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(log_path, "a", encoding="utf-8") as f:
                import traceback
                f.write(f"\n[FATAL] {e}\n")
                traceback.print_exc(file=f)
        except Exception:
            pass
        sys.exit(1)
