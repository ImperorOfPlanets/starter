import os
import platform
import subprocess
import sys
from pathlib import Path

from starter_files.core.utils.globalVars_utils import GlobalVars, set_global, get_global

def get_python_cmd():
    """Определяет команду для запуска Python"""
    return sys.executable

def get_pip_command():
    """Определяет рабочую команду pip для текущей системы"""
    python_cmd = get_python_cmd()
    
    # Проверяем возможные варианты вызова pip
    for pip_cmd in [
        [python_cmd, "-m", "pip"],  # Самый надежный способ
        ["pip3"],                   # Для Linux/Unix систем
        ["pip"]                     # Последний вариант
    ]:
        try:
            subprocess.run(
                [*pip_cmd, "--version"],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return pip_cmd
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue
    
    raise RuntimeError("Не удалось найти рабочую команду pip")

def get_requirements_path():
    """Находит подходящий файл требований для текущей ОС"""
    system = platform.system().lower()
    release = platform.release()
    
    print(f"\n=== Отладочная информация ===")
    print(f"Определенная ОС: {system}")
    print(f"Версия ОС: {release}")
    
    # 1. Определяем корень проекта (где лежит starter.py)
    starter_path = get_global('script_path')
    print(f"\nПуть к starter.py: {starter_path}")
    
    # 2. Ищем requirements относительно starter.py
    reqs_dir = starter_path / "starter_files" / "requirements"
    print(f"Ищем requirements в: {reqs_dir}")
    
    # 3. Проверяем возможные пути
    possible_paths = [
        reqs_dir / system / f"{release}.txt",
        reqs_dir / system / "default.txt",
        reqs_dir / "default.txt"
    ]
    
    print("\nПроверяемые пути:")
    for path in possible_paths:
        exists = "НАЙДЕН" if path.exists() else "не найден"
        print(f" - {path}: {exists}")
    
    for path in possible_paths:
        if path.exists():
            print(f"\nИспользуем файл зависимостей: {path}")
            return path
    
    print("\nОШИБКА: Ни один из файлов зависимостей не найден!")
    print("Попробуйте создать файл по одному из путей:")
    for path in possible_paths:
        print(f" - {path}")
    
    return None

def install_dependencies():
    """Устанавливает зависимости используя правильную команду pip"""
    pip_cmd = get_pip_command()
    req_file = get_requirements_path()
    
    if not req_file:
        print("Ошибка: Не найден файл зависимостей для вашей ОС")
        return False
    
    print(f"Установка зависимостей из {req_file.name}...")
    
    try:
        result = subprocess.run(
            [*pip_cmd, "install", "-r", str(req_file)],
            check=True,
            text=True,
            capture_output=True
        )
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Ошибка установки зависимостей:\n{e.stderr}")
        return False

def restart_application():
    """Перезапускает приложение с теми же аргументами"""
    python_cmd = get_python_cmd()
    os.execv(python_cmd, [python_cmd, *sys.argv])

def install_and_restart():
    """Основная функция для установки и перезапуска"""
    print("=== Установка необходимых зависимостей ===")
    
    if not install_dependencies():
        print("\nНе удалось установить зависимости!")
        print("Попробуйте установить их вручную:")
        print(f"  {get_python_cmd()} -m pip install -r requirements/{platform.system().lower()}/default.txt")
        sys.exit(1)
        
    print("\nЗависимости успешно установлены, перезапуск...")
    restart_application()