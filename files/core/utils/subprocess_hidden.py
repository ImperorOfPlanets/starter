# files/core/utils/subprocess_hidden.py
"""
Скрытие консольных окон подпроцессов на Windows.

Стартер — демон: при работе он запускает десятки внешних команд (docker, git,
composer, sc, nssm, powershell). На Windows каждая такая команда без флагов
скрытия создаёт видимое консольное окно — рабочий стол мигает волной окон.

Модуль один раз патчит subprocess.run / subprocess.Popen в рамках процесса
стартера, добавляя STARTUPINFO(SW_HIDE) + CREATE_NO_WINDOW. Патч ставится
только на Windows; на других ОС (Linux/macOS) — безопасная заглушка.

Почему глобальный патч, а не правка отдельных модулей: лоадер загружает
каждый модуль отдельной копией (importlib), поэтому подмена subprocess
«внутри одного модуля» не покрывает остальные копии. Точка установки одна —
процесс целиком, и любые будущие модули тоже скрыты.
"""
import os
import subprocess

_installed = False


def _hidden_startupinfo():
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = subprocess.SW_HIDE
    return si


def install() -> None:
    """Патчит subprocess.run/Popen на скрытие окон (идемпотентно, только Windows)."""
    global _installed
    if _installed or os.name != 'nt':
        return

    orig_run = subprocess.run
    orig_popen = subprocess.Popen

    def run(*args, **kwargs):
        kwargs.setdefault('startupinfo', _hidden_startupinfo())
        kwargs.setdefault('creationflags', subprocess.CREATE_NO_WINDOW)
        return orig_run(*args, **kwargs)

    def popen(*args, **kwargs):
        kwargs.setdefault('startupinfo', _hidden_startupinfo())
        kwargs.setdefault('creationflags', subprocess.CREATE_NO_WINDOW)
        return orig_popen(*args, **kwargs)

    subprocess.run = run
    subprocess.Popen = popen
    _installed = True
