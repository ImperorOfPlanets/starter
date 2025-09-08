import os
import shutil
from pathlib import Path

def get_diff_files(laravel_dir, copy_dir, subdirs):
    diff_files = []
    for subdir in subdirs:
        laravel_subdir = laravel_dir / subdir
        copy_subdir = copy_dir / subdir
        
        if not laravel_subdir.exists() or not copy_subdir.exists():
            continue
        
        # Рекурсивно проверяем файлы
        for root, _, files in os.walk(laravel_subdir):
            for file in files:
                laravel_file = Path(root) / file
                relative_path = laravel_file.relative_to(laravel_subdir)
                copy_file = copy_subdir / relative_path
                
                # Если файла нет в copy или он отличается
                if not copy_file.exists() or not filecmp.cmp(laravel_file, copy_file, shallow=False):
                    diff_files.append((laravel_file, copy_file))
    
    return diff_files

def select_files_to_copy(diff_files):
    if not diff_files:
        print("Нет отличающихся файлов!")
        return []
    
    print("\nОтличающиеся файлы:")
    for i, (laravel_file, copy_file) in enumerate(diff_files, 1):
        print(f"{i}. [Laravel] {laravel_file} → [Copy] {copy_file}")
    
    selected_indices = input(
        "\nВыберите файлы для копирования (через запятую, например: 1,3,5)\n"
        "Или нажмите Enter, чтобы скопировать все: "
    ).strip()
    
    if not selected_indices:
        return diff_files
    
    selected_files = []
    for idx in selected_indices.split(","):
        try:
            selected_files.append(diff_files[int(idx) - 1])
        except (ValueError, IndexError):
            continue
    
    return selected_files

def copy_selected_files(selected_files):
    if not selected_files:
        print("Не выбрано ни одного файла!")
        return
    
    for laravel_file, copy_file in selected_files:
        # Создаем папки, если их нет
        copy_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(laravel_file, copy_file)
        print(f"Скопировано: {laravel_file} → {copy_file}")

def main():
    # Определяем пути
    current_dir = Path(__file__).parent.resolve()
    parent_dir = current_dir.parent
    laravel_dir = parent_dir / "laravel"
    copy_dir = parent_dir / "copy"
    
    if not laravel_dir.exists() or not copy_dir.exists():
        print("Ошибка: Папки 'laravel' или 'copy' не найдены!")
        return
    
    # Какие подпапки сравниваем
    subdirs_to_compare = [
        "app",
        "resources/views",
        "database/migrations",
        "public",
        "routes",
    ]
    
    # Получаем отличающиеся файлы
    diff_files = get_diff_files(laravel_dir, copy_dir, subdirs_to_compare)
    
    # Выбираем файлы для копирования
    selected_files = select_files_to_copy(diff_files)
    
    # Копируем выбранные
    copy_selected_files(selected_files)

if __name__ == "__main__":
    import filecmp  # Для сравнения файлов
    main()