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

    if _logger:
        _logger.info(f"Starting tray, port={port}, url={url}")

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
                    tooltip = f"Starter | Web: ON | Servers: {running_count} running"
                else:
                    color = '#198754'
                    tooltip = f"Starter | Web: ON | Port: {port}"
            else:
                color = '#dc3545'
                tooltip = f"Starter | Web: OFF"

            if service:
                tooltip += " | Service: ON"

            icon_ref[0].icon = make_icon(color)
            icon_ref[0].title = tooltip
            _status_cache.update({'web': web, 'service': service, 'servers': servers, 'tooltip': tooltip})
        except Exception as e:
            if _logger:
                _logger.error(f"update_icon error: {e}")

    def build_servers_submenu():
        servers = _status_cache.get('servers', [])
        if not servers:
            return [pystray.MenuItem("(no servers)", None, enabled=False)]
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
            f"Service: {'ON' if service else 'OFF'}",
            f"Web: {'ON' if web else 'OFF'}",
            f"Port: {port}",
            f"Running servers: {len(running)}",
        ]
        if running:
            lines.extend([f"  - {n}" for n in running[:5]])
        lines.append(f"Tray PID: {os.getpid()}")
        _balloon("Starter Status", "\n".join(lines))

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

    menu = pystray.Menu(
        pystray.MenuItem("Show Starter", on_show, default=True),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Start web server", on_start),
        pystray.MenuItem("Stop web server", on_stop),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Servers", lambda: pystray.Menu(*build_servers_submenu())),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Restart", on_restart),
        pystray.MenuItem("Status", on_status),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", on_quit)
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
