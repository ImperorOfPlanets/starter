import os
import shutil
from pathlib import Path

from starter_files.untils.logger import logger

# Функция вывода структуры и содержимого словаря
def print_dict_structure(data, indent=0):
    for key, value in data.items():
        # Отступ для лучшей читаемости вложенных структур
        spaces = ' ' * indent
        
        if isinstance(value, dict):
            # Если значение — другой словарь, рекурсивно выводим его содержимое
            print(f"{spaces}{key}:")
            print_dict_structure(value, indent + 4)
        elif isinstance(value, list):
            # Если значение — список, выводим элементы списка
            print(f"{spaces}{key}: {value}")
        else:
            # Для простых типов данных сразу печатаем ключ-значение
            print(f"{spaces}{key}: {value}")

def copy_environment_variables(projects_updates,projects_folders):
    """
    Обрабатывает изменение файла .env.example:
     - Замещает .env.example новым файлом.
     - Считывает переменные из старого .env.
     - Удаляет старый .env.
     - Клонирует .env.example как новый .env.
     - Переносит переменные из старого .env в новый.
    """
    # Пути к ключевым директориям
    backup_dir = projects_folders['BACKUPS_DIR']
    extracted_dir = projects_folders['EXTRACTED_DIR']
    base_path = Path(projects_folders['BASE_PATH'])
    
    # Пути к файлам
    old_env_path = backup_dir / '.env'                   # .env из бекапа
    new_env_example = extracted_dir / '.env.example'     # Новый .env.example
    new_env_path = base_path / '.env'                    # Целевой .env

    # 1. Чтение переменных из бекапа
    old_variables = {}
    if old_env_path.exists():
        with open(old_env_path, 'r', encoding='utf-8') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    old_variables[key] = value
        print(f"Найдено {len(old_variables)} переменных в бекапе")

    # 2. Копирование нового .env.example в целевую директорию
    try:
        shutil.copy(new_env_example, new_env_path)
        print(f"Скопирован новый .env.example -> {new_env_path}")
    except Exception as e:
        print(f"Ошибка копирования: {str(e)}")
        return

    # 3. Обновление переменных (если есть данные из бекапа)
    if old_variables:
        try:
            with open(new_env_path, 'r+', encoding='utf-8') as f:
                lines = f.readlines()
                f.seek(0)
                
                # Обновляем существующие переменные
                for line in lines:
                    if '=' in line and not line.startswith('#'):
                        key, _ = line.split('=', 1)
                        if key in old_variables:
                            line = f"{key}={old_variables[key]}\n"
                    f.write(line)
                f.truncate()
                
            print(f"Обновлено {len(old_variables)} переменных в {new_env_path}")
            
        except Exception as e:
            print(f"Ошибка обновления переменных: {str(e)}")