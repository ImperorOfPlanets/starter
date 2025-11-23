import os
import sys
import venv
import subprocess
from pathlib import Path
import platform
from typing import Optional, Tuple
from starter_files.core.utils.log_utils import LogManager

# Логгер будет инициализирован позже, при необходимости
logger = None

def in_venv():
    """Проверяет, находится ли скрипт в виртуальном окружении"""
    return sys.prefix != sys.base_prefix

def create_venv() -> Path:
    """Создает виртуальное окружение в папке venv с улучшенной обработкой ошибок"""
    base_dir = Path(sys.argv[0]).absolute().parent
    venv_dir = base_dir / "venv"

    if venv_dir.exists():
        if logger:
            logger.debug(f"Виртуальное окружение уже существует: {venv_dir}")
        return venv_dir

    print(f"\nСоздание виртуального окружения в {venv_dir}...")

    try:
        # Создаем venv с дополнительными опциями для лучшей совместимости
        builder = venv.EnvBuilder(
            with_pip=True,
            upgrade_deps=True,
            clear=False,
            symlinks=platform.system() != "Windows"  # Симлинки на Unix-подобных системах
        )
        builder.create(venv_dir)

        # Проверяем, что venv создалось корректно
        python_exe = get_venv_python(venv_dir)
        if not python_exe.exists():
            raise RuntimeError(f"Интерпретатор Python не найден в venv: {python_exe}")

        # Тестируем venv
        test_result = subprocess.run(
            [str(python_exe), "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if test_result.returncode != 0:
            raise RuntimeError(f"Ошибка тестирования venv: {test_result.stderr}")

        print(f"[OK] Виртуальное окружение создано успешно: {venv_dir}")
        return venv_dir

    except Exception as e:
        if logger:
            logger.error(f"Ошибка создания виртуального окружения: {str(e)}")
        # Пытаемся удалить неполное venv
        try:
            if venv_dir.exists():
                import shutil
                shutil.rmtree(venv_dir)
        except Exception as cleanup_error:
            if logger:
                logger.warning(f"Ошибка очистки неполного venv: {str(cleanup_error)}")

        raise RuntimeError(f"Не удалось создать виртуальное окружение: {str(e)}")

def get_venv_python(venv_dir):
    """Возвращает путь к интерпретатору в виртуальном окружении"""
    venv_dir = Path(venv_dir)
    if platform.system() == "Windows":
        return venv_dir / "Scripts" / "python.exe"
    else:
        return venv_dir / "bin" / "python"

def restart_in_venv(venv_dir: Path) -> None:
    """Перезапускает скрипт в указанном виртуальном окружении с улучшенной обработкой"""
    venv_python = get_venv_python(venv_dir)
    script_path = Path(sys.argv[0]).absolute()

    if not venv_python.exists():
        raise FileNotFoundError(f"Интерпретатор Python не найден в venv: {venv_python}")

    # Проверяем, что скрипт существует
    if not script_path.exists():
        raise FileNotFoundError(f"Скрипт не найден: {script_path}")

    args = [str(venv_python), str(script_path)] + sys.argv[1:]
    print(f"Перезапуск в виртуальном окружении: {' '.join(args)}")

    try:
        # Устанавливаем переменные окружения для корректной работы в venv
        env = os.environ.copy()
        env['VIRTUAL_ENV'] = str(venv_dir)
        env['PATH'] = str(venv_python.parent) + os.pathsep + env.get('PATH', '')

        if logger:
            logger.debug(f"Установка VIRTUAL_ENV: {venv_dir}")
            logger.debug(f"Обновление PATH: {venv_python.parent}")

        os.execve(str(venv_python), args, env)

    except Exception as e:
        if logger:
            logger.error(f"Ошибка при перезапуске в venv: {str(e)}")
        raise

def ensure_venv() -> bool:
    """
    Гарантирует работу в виртуальном окружении с улучшенной обработкой:
    - Если не в venv, создает его и перезапускает скрипт
    - Возвращает True если перезапуск произошел
    """
    if in_venv():
        if logger:
            logger.debug("Уже работаем в виртуальном окружении")
        return False

    try:
        venv_dir = create_venv()
        if logger:
            logger.info(f"Создано виртуальное окружение: {venv_dir}")

        # Небольшая пауза для обеспечения корректной работы файловой системы
        import time
        time.sleep(0.5)

        restart_in_venv(venv_dir)
        return True  # Этот код выполнится только если execve не сработал

    except Exception as e:
        if logger:
            logger.error(f"Критическая ошибка при настройке venv: {str(e)}")
        print(f"\n[ERROR] Ошибка настройки виртуального окружения: {str(e)}")
        print("Попробуйте:")
        print("1. Проверить права доступа к директории")
        print("2. Удалить существующую папку venv и попробовать снова")
        print("3. Проверить доступность Python")
        sys.exit(1)

def get_venv_pip(venv_dir: Path) -> Optional[Path]:
    """Возвращает путь к pip в виртуальном окружении"""
    venv_dir = Path(venv_dir)
    if platform.system() == "Windows":
        pip_exe = venv_dir / "Scripts" / "pip.exe"
    else:
        pip_exe = venv_dir / "bin" / "pip"

    return pip_exe if pip_exe.exists() else None

def install_package_in_venv(venv_dir: Path, package: str) -> bool:
    """Устанавливает пакет в указанное виртуальное окружение"""
    pip_exe = get_venv_pip(venv_dir)
    if not pip_exe:
        if logger:
            logger.error(f"pip не найден в venv: {venv_dir}")
        return False

    try:
        result = subprocess.run(
            [str(pip_exe), "install", package],
            capture_output=True,
            text=True,
            timeout=300  # 5 минут таймаут
        )

        if result.returncode == 0:
            if logger:
                logger.debug(f"Пакет {package} установлен успешно")
            return True
        else:
            if logger:
                logger.error(f"Ошибка установки пакета {package}: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        if logger:
            logger.error(f"Таймаут при установке пакета {package}")
        return False
    except Exception as e:
        if logger:
            logger.error(f"Неожиданная ошибка при установке {package}: {str(e)}")
        return False