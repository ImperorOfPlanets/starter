import os
import sys
import fnmatch
from pathlib import Path

class CodeReaderConfig:
    IGNORE_DIRS = ['.git', '__pycache__', 'venv', '.idea', 'node_modules','differences','extracted','backups','docker','logs']
    IGNORE_FILES = ['*.pyc', '*.pyo', '*.pyd', '.DS_Store', '*.db', '*.log','project_structure.html','readme.html','README.md']
    INCLUDE_HIDDEN = False

class CodeReader:
    def __init__(self):
        self.config = CodeReaderConfig()
        self.script_name = os.path.basename(sys.argv[0])

    def _should_ignore(self, path: Path, root: Path) -> bool:
        """Определяет нужно ли игнорировать путь"""
        try:
            relative_path = path.relative_to(root)
        except ValueError:
            return False

        # Проверяем все части пути на совпадение с игнорируемыми директориями
        for part in relative_path.parts:
            if any(fnmatch.fnmatch(part, pattern) for pattern in self.config.IGNORE_DIRS):
                return True

        # Проверяем файлы
        if any(fnmatch.fnmatch(path.name, pattern) for pattern in self.config.IGNORE_FILES + [self.script_name]):
            return True

        # Проверяем скрытые файлы/папки
        if not self.config.INCLUDE_HIDDEN and any(part.startswith('.') for part in relative_path.parts):
            return True

        return False

    def scan(self, start_path: str) -> list:
        """Сканирует директорию и возвращает структуру"""
        root = Path(start_path).resolve()
        result = []
        
        for item in root.rglob('*'):
            if self._should_ignore(item, root):
                continue
                
            if item.is_file():
                try:
                    content = item.read_text(encoding='utf-8')
                    result.append((
                        str(item.relative_to(root)),
                        content
                    ))
                except UnicodeDecodeError:
                    continue
                except Exception as e:
                    result.append((str(item.relative_to(root)), f"[Error: {str(e)}]"))
                    
        return result

    def generate_report(self, data: list, output_file: str):
        """Генерирует отчет в указанном формате"""
        with open(output_file, 'w', encoding='utf-8') as f:
            for path, content in data:
                f.write(f"##{path}\n")
                f.write(f"<code>\n{content}\n</code>\n\n")

if __name__ == "__main__":
    reader = CodeReader()
    
    print("Сканирование...")
    project_data = reader.scan(os.getcwd())
    
    print("Генерация отчета...")
    reader.generate_report(project_data, 'project_structure.html')  # Изменено расширение
    
    print("Готово! Результат сохранен в project_structure.html")  # Обновлено сообщение