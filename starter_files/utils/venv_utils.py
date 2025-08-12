import os
import sys
import venv
from pathlib import Path
import platform

def in_venv():
    """Проверяет, находится ли скрипт в виртуальном окружении"""
    return sys.prefix != sys.base_prefix

def create_venv():
    """Создает виртуальное окружение в папке venv"""
    base_dir = Path(sys.argv[0]).absolute().parent
    venv_dir = base_dir / "venv"
    
    if venv_dir.exists():
        return venv_dir
    
    print(f"\nСоздание виртуального окружения в {venv_dir}...")
    builder = venv.EnvBuilder(with_pip=True)
    builder.create(venv_dir)
    return venv_dir

def get_venv_python(venv_dir):
    """Возвращает путь к интерпретатору в виртуальном окружении"""
    venv_dir = Path(venv_dir)
    if platform.system() == "Windows":
        return venv_dir / "Scripts" / "python.exe"
    else:
        return venv_dir / "bin" / "python"

def restart_in_venv(venv_dir):
    """Перезапускает скрипт в указанном виртуальном окружении"""
    venv_python = get_venv_python(venv_dir)
    script_path = Path(sys.argv[0]).absolute()
    
    if not venv_python.exists():
        raise FileNotFoundError(f"Интерпретатор не найден: {venv_python}")
    
    args = [str(venv_python), str(script_path)] + sys.argv[1:]
    print(f"Перезапуск в виртуальном окружении: {' '.join(args)}")
    os.execv(str(venv_python), args)

def ensure_venv():
    """
    Гарантирует работу в виртуальном окружении:
    - Если не в venv, создает его и перезапускает скрипт
    - Возвращает True если перезапуск произошел
    """
    if in_venv():
        return False
    
    venv_dir = create_venv()
    restart_in_venv(venv_dir)
    return True  # Этот код выполнится только если execv не сработал