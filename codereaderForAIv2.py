import os
import sys
import fnmatch
from pathlib import Path
from html import escape

class CodeReaderConfig:
    IGNORE_DIRS = ['.git', '__pycache__', 'venv', '.idea',
        'node_modules',
        # L
        'differences','extracted','backups',
        # Файлы проекта docker
        'docker','logs','public',
        
        # Исключаем переводы
        'locales',

        # Шаблоны
        'templates',

        # Зависимости
        'requirements',

        # Исключения
        'exceptions',

        # web
        'web'          
    ]
    IGNORE_FILES = [
        # Дефолтный мусор
        '*.pyc', '*.pyo', '*.pyd', '.DS_Store', '*.db', '*.log',
        # Генерируемая структура файлов и дефолтные файлы для git
        # 'codereaderForAIv2.py',
        'project_structure.html','readme.html','README.md',
        # Файлы с папки public
        'bootstrap.bundle.min.js','bootstrap.min.css','bootstrap.min.js','jquery-3.6.0.min.js','popper.min.js',
        # Файлы сертификатов
        'selfsigned.crt','selfsigned.key','ssl.py'
    ]
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

    def _escape_code_content(self, content: str) -> str:
        """Экранирует только содержимое внутри тегов code, заменяя < и > с пробелами вокруг"""
        # Разделяем содержимое на части до, внутри и после тегов code
        parts = []
        last_pos = 0
        while True:
            code_start = content.find('<code>', last_pos)
            if code_start == -1:
                parts.append(content[last_pos:])
                break
            
            code_end = content.find('</code>', code_start)
            if code_end == -1:
                parts.append(content[last_pos:])
                break
                
            # Добавляем часть до тега code
            parts.append(content[last_pos:code_start + 6])  # +6 чтобы включить <code>
            
            # Обрабатываем содержимое тега code
            code_content = content[code_start + 6:code_end]
            
            # Заменяем только < и > с пробелами вокруг
            escaped_content = []
            i = 0
            while i < len(code_content):
                if code_content[i] in ('<', '>'):
                    # Проверяем есть ли пробелы вокруг
                    prev_char = code_content[i-1] if i > 0 else ''
                    next_char = code_content[i+1] if i < len(code_content)-1 else ''
                    
                    if (prev_char.isspace() or not prev_char) and (next_char.isspace() or not next_char):
                        replacement = '&lt;' if code_content[i] == '<' else '&gt;'
                        escaped_content.append(replacement)
                        i += 1
                        continue
                
                escaped_content.append(code_content[i])
                i += 1
            
            parts.append(''.join(escaped_content))
            parts.append('</code>')
            last_pos = code_end + 7  # +7 чтобы пропустить </code>
            
        return ''.join(parts)

    def generate_report(self, data: list, output_file: str):
        """Генерирует отчет в указанном формате"""
        with open(output_file, 'w', encoding='utf-8') as f:
            for path, content in data:
                f.write(f"##{path}\n")
                f.write(f"<code>\n{content}\n</code>\n\n")
        
        # После записи файла обрабатываем его для экранирования
        with open(output_file, 'r+', encoding='utf-8') as f:
            file_content = f.read()
            escaped_content = self._escape_code_content(file_content)
            f.seek(0)
            f.write(escaped_content)
            f.truncate()

if __name__ == "__main__":
    reader = CodeReader()
    
    print("Сканирование...")
    project_data = reader.scan(os.getcwd())
    
    print("Генерация отчета...")
    reader.generate_report(project_data, 'project_structure.html')
    
    print("Готово! Результат сохранен в project_structure.html")