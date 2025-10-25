import os
import platform
import re
import subprocess
import sys
from pathlib import Path
from typing import Tuple

from starter_files.core.utils.globalVars_utils import GlobalVars, set_global, get_global

def get_python_cmd():
    """Определяет команду для запуска Python"""
    return sys.executable

def get_pip_command():
    """Определяет рабочую команду pip для текущей системы с улучшенной логикой"""
    python_cmd = get_python_cmd()

    # Проверяем, работаем ли мы в виртуальном окружении
    from starter_files.core.utils.venv_utils import in_venv, get_venv_pip
    from starter_files.core.utils.globalVars_utils import get_global
    from pathlib import Path

    if in_venv():
        # В venv используем pip из виртуального окружения
        script_path = Path(get_global('script_path'))
        venv_dir = script_path / "venv"
        venv_pip = get_venv_pip(venv_dir)
        if venv_pip:
            return [str(venv_pip)]

    # Проверяем возможные варианты вызова pip
    pip_commands = [
        [python_cmd, "-m", "pip"],  # Самый надежный способ
        ["pip3"],                   # Для Linux/Unix систем
        ["pip"]                     # Последний вариант
    ]

    for pip_cmd in pip_commands:
        try:
            result = subprocess.run(
                [*pip_cmd, "--version"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10
            )
            print(f"✅ Найден pip: {' '.join(pip_cmd)} (версия: {result.stdout.strip()})")
            return pip_cmd
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            continue

    raise RuntimeError("Не удалось найти рабочую команду pip. Убедитесь, что pip установлен.")

def validate_requirements_file(file_path):
    """Валидирует файл зависимостей"""
    if not file_path.exists():
        return False, f"Файл не существует: {file_path}"

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Проверяем на пустой файл
        if not content.strip():
            return False, "Файл зависимостей пустой"

        # Проверяем на корректный формат (каждая строка должна содержать имя пакета)
        lines = content.strip().split('\n')
        valid_lines = 0
        invalid_lines = []

        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue  # Пропускаем пустые строки и комментарии

            # Проверяем базовый формат пакета (имя>=версия или просто имя)
            if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9._-]*', line.split('>=')[0].split('==')[0].split('<')[0].split('>')[0].split(';')[0].strip()):
                invalid_lines.append(f"Строка {i}: '{line}' - некорректное имя пакета")
            else:
                valid_lines += 1

        if invalid_lines:
            return False, f"Найдены некорректные строки:\n" + "\n".join(invalid_lines)

        if valid_lines == 0:
            return False, "Файл не содержит ни одной корректной зависимости"

        return True, f"Файл валиден, содержит {valid_lines} зависимостей"

    except Exception as e:
        return False, f"Ошибка чтения файла: {str(e)}"

def get_linux_distro_info() -> Tuple[str, str]:
    """Определяет информацию о Linux дистрибутиве"""
    major_version = platform.release().split('.')[0]

    # Метод 1: используем distro если доступен
    try:
        import distro  # type: ignore
        name = distro.name().lower().split()[0]
        version = distro.version().split('.')[0]
        print(f"Определен дистрибутив через distro: {name} {version}")
        return name, version
    except ImportError:
        pass

    # Метод 2: парсим /etc/os-release
    try:
        with open("/etc/os-release", 'r', encoding='utf-8') as f:
            content = f.read()

        os_release = {}
        for line in content.split('\n'):
            if '=' in line:
                key, value = line.split('=', 1)
                os_release[key] = value.strip().strip('"')

        distro_id = os_release.get('ID', 'linux').lower()
        version_id = os_release.get('VERSION_ID', major_version)

        # Очищаем версию от дополнительных символов
        version_clean = re.sub(r'[^0-9.]', '', version_id).split('.')[0]

        print(f"Определен дистрибутив через /etc/os-release: {distro_id} {version_clean}")
        return distro_id, version_clean

    except (FileNotFoundError, KeyError, ValueError, OSError) as e:
        print(f"Не удалось прочитать /etc/os-release: {e}")

    # Метод 3: fallback на platform
    print(f"Используем fallback определение: linux {major_version}")
    return "linux", major_version

def get_requirements_path():
    """Находит подходящий файл требований для текущей ОС с улучшенной логикой"""
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

    # 3. Улучшенная логика определения версии ОС
    version_parts = release.split('.')
    major_version = version_parts[0] if version_parts else release

    # Для Linux определяем дистрибутив более точно
    if system == "linux":
        distro_name, distro_version = get_linux_distro_info()
    else:
        distro_name = system
        distro_version = major_version

    # 4. Проверяем возможные пути в порядке приоритета
    possible_paths = [
        reqs_dir / distro_name / f"{distro_version}.txt",  # ubuntu/22.txt, rocky/9.txt, almalinux/8.txt
        reqs_dir / distro_name / f"{release}.txt",         # ubuntu/22.04.txt, rocky/9.2.txt
        reqs_dir / distro_name / "default.txt",            # ubuntu/default.txt, rocky/default.txt, almalinux/default.txt
        reqs_dir / system / f"{major_version}.txt",        # linux/22.txt
        reqs_dir / system / "default.txt",                 # linux/default.txt
        reqs_dir / "default.txt"                           # default.txt (fallback)
    ]

    # Для Windows добавляем дополнительные пути
    if system == "windows":
        windows_paths = [
            reqs_dir / "windows" / f"{major_version}.txt",  # windows/10.txt
            reqs_dir / "windows" / "default.txt",           # windows/default.txt
        ]
        possible_paths.extend(windows_paths)

    print("\nПроверяемые пути:")
    for path in possible_paths:
        exists = "НАЙДЕН" if path.exists() else "не найден"
        print(f" - {path}: {exists}")

    for path in possible_paths:
        if path.exists():
            # Валидируем найденный файл
            is_valid, validation_msg = validate_requirements_file(path)
            if is_valid:
                print(f"\nИспользуем файл зависимостей: {path}")
                print(f"Валидация: {validation_msg}")
                return path
            else:
                print(f"\nПропускаем файл {path}: {validation_msg}")
                continue

    print("\nОШИБКА: Ни один из файлов зависимостей не найден или не прошел валидацию!")
    print("Попробуйте создать файл по одному из путей:")
    for path in possible_paths:
        print(f" - {path}")

    return None

def install_dependencies():
    """Устанавливает зависимости используя правильную команду pip с улучшенной обработкой ошибок"""
    pip_cmd = get_pip_command()
    req_file = get_requirements_path()

    if not req_file:
        print("Ошибка: Не найден файл зависимостей для вашей ОС")
        return False

    # Дополнительная валидация перед установкой
    is_valid, validation_msg = validate_requirements_file(req_file)
    if not is_valid:
        print(f"Ошибка валидации файла зависимостей: {validation_msg}")
        return False

    print(f"Установка зависимостей из {req_file.name}...")
    print(f"Команда: {' '.join(pip_cmd)} install -r {req_file}")

    try:
        # Устанавливаем таймаут для предотвращения зависания
        result = subprocess.run(
            [*pip_cmd, "install", "-r", str(req_file)],
            check=True,
            text=True,
            capture_output=True,
            timeout=300  # 5 минут таймаут
        )

        if result.stdout:
            print("Вывод установки:")
            print(result.stdout)

        if result.stderr:
            print("Предупреждения:")
            print(result.stderr)

        print("Зависимости установлены успешно")
        return True

    except subprocess.TimeoutExpired:
        print("Ошибка: Установка зависимостей превысила таймаут (5 минут)")
        return False
    except subprocess.CalledProcessError as e:
        print(f"Ошибка установки зависимостей (код {e.returncode}):")
        if e.stdout:
            print("Вывод stdout:")
            print(e.stdout)
        if e.stderr:
            print("Вывод stderr:")
            print(e.stderr)
        return False
    except Exception as e:
        print(f"Неожиданная ошибка при установке зависимостей: {str(e)}")
        return False

def restart_application():
    """Перезапускает приложение с теми же аргументами с улучшенной обработкой"""
    try:
        # Определяем правильный Python для перезапуска
        from starter_files.core.utils.venv_utils import in_venv, get_venv_python
        from starter_files.core.utils.globalVars_utils import get_global
        from pathlib import Path

        script_path = Path(sys.argv[0]).absolute()

        # Проверяем, что скрипт существует
        if not script_path.exists():
            raise FileNotFoundError(f"Скрипт не найден: {script_path}")

        if in_venv():
            # В venv используем Python из виртуального окружения
            script_dir = Path(get_global('script_path'))
            venv_dir = script_dir / "venv"
            python_cmd = str(get_venv_python(venv_dir))
        else:
            # Используем системный Python
            python_cmd = get_python_cmd()

        args = [python_cmd, str(script_path)] + sys.argv[1:]
        print(f"Перезапуск приложения: {' '.join(args)}")

        # Устанавливаем переменные окружения для корректного перезапуска
        env = os.environ.copy()

        # Добавляем специальный флаг для предотвращения бесконечного цикла перезапуска
        env['STARTER_RESTARTING'] = '1'

        # Используем execve для полной замены процесса (только для Unix-подобных систем)
        if os.name == 'posix':
            os.execve(python_cmd, args, env)
        else:
            # Для Windows используем subprocess для перезапуска
            subprocess.run(args, env=env)
            sys.exit(0)

    except Exception as e:
        print(f"Критическая ошибка при перезапуске приложения: {str(e)}")
        print("Попробуйте перезапустить приложение вручную")
        raise

def install_and_restart():
    """Основная функция для установки и перезапуска с улучшенной обработкой"""
    print("=== Установка необходимых зависимостей ===")

    # Проверяем, не в цикле ли мы перезапуска
    restart_flag = os.environ.get('STARTER_RESTARTING')
    if restart_flag:
        print("⚠️  Обнаружен флаг перезапуска. Это может указывать на проблему с зависимостями.")
        print("Попробуйте установить зависимости вручную или проверить логи.")
        sys.exit(1)

    if not install_dependencies():
        print("\n[ERROR] Не удалось установить зависимости!")
        print("\nВозможные решения:")
        print("1. Проверьте подключение к интернету")
        print("2. Проверьте права доступа к директории venv")
        print("3. Попробуйте установить зависимости вручную:")

        req_file = get_requirements_path()
        if req_file:
            pip_cmd = get_pip_command()
            print(f"   {' '.join(pip_cmd)} install -r {req_file}")
        else:
            pip_cmd = get_pip_command()
            print(f"   {' '.join(pip_cmd)} install flask python-dotenv requests")

        print("4. Проверьте файл зависимостей на корректность")
        print("5. Убедитесь, что у вас достаточно места на диске")

        # Предлагаем продолжить без перезапуска
        try:
            response = input("\nПродолжить выполнение без перезапуска? (y/N): ").strip().lower()
            if response == 'y':
                print("Продолжаем выполнение...")
                return
        except (EOFError, KeyboardInterrupt):
            pass

        sys.exit(1)

    print("\n✅ Зависимости успешно установлены, перезапуск приложения...")

    # Небольшая пауза перед перезапуском
    import time
    time.sleep(1)

    try:
        restart_application()
    except Exception as e:
        print(f"[ERROR] Ошибка при перезапуске приложения: {str(e)}")
        print("Попробуйте перезапустить приложение вручную")
        sys.exit(1)