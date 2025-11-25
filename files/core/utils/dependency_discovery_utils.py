import os
import re
import ast
import importlib.util
from pathlib import Path
from typing import Dict, Any, List, Set, Optional, Tuple
from files.core.utils.globalVars_utils import get_global
from files.core.utils.log_utils import LogManager

# Логгер будет инициализирован позже, при необходимости
logger = None

class DependencyDiscovery:
    """Класс для автоматического обнаружения зависимостей проекта"""

    # Известные пакеты и их импорты
    KNOWN_PACKAGES = {
        'flask': ['flask', 'Flask'],
        'django': ['django'],
        'fastapi': ['fastapi'],
        'requests': ['requests'],
        'numpy': ['numpy', 'np'],
        'pandas': ['pandas', 'pd'],
        'matplotlib': ['matplotlib', 'plt'],
        'scipy': ['scipy'],
        'scikit-learn': ['sklearn'],
        'tensorflow': ['tensorflow', 'tf'],
        'torch': ['torch'],
        'pillow': ['PIL', 'Image'],
        'opencv-python': ['cv2'],
        'beautifulsoup4': ['bs4'],
        'lxml': ['lxml'],
        'selenium': ['selenium'],
        'pytest': ['pytest'],
        'sqlalchemy': ['sqlalchemy'],
        'psycopg2': ['psycopg2'],
        'pymysql': ['pymysql'],
        'redis': ['redis'],
        'celery': ['celery'],
        'python-dotenv': ['dotenv'],
        'pyyaml': ['yaml'],
        'click': ['click'],
        'jinja2': ['jinja2'],
        'werkzeug': ['werkzeug'],
        'itsdangerous': ['itsdangerous'],
        'blinker': ['blinker'],
        'simplejson': ['simplejson'],
        'ujson': ['ujson'],
        'orjson': ['orjson'],
        'cryptography': ['cryptography'],
        'bcrypt': ['bcrypt'],
        'passlib': ['passlib'],
        'python-jose': ['jose'],
        'pyjwt': ['jwt'],
        'gunicorn': ['gunicorn'],
        'uvicorn': ['uvicorn'],
        'hypercorn': ['hypercorn'],
        'daphne': ['daphne'],
        'aiohttp': ['aiohttp'],
        'httpx': ['httpx'],
        'starlette': ['starlette'],
        'pydantic': ['pydantic'],
        'typing-extensions': ['typing_extensions'],
        'dataclasses': ['dataclasses'],  # В Python < 3.7
        'asyncio': ['asyncio'],  # В Python < 3.4
    }

    @staticmethod
    def scan_project_imports(project_path: Optional[Path] = None) -> Set[str]:
        """
        Сканирует проект и находит все импорты
        Возвращает множество найденных импортов
        """
        if project_path is None:
            project_path = Path(get_global('script_path'))

        imports = set()

        # Сканируем все Python файлы
        for py_file in project_path.rglob('*.py'):
            try:
                file_imports = DependencyDiscovery._extract_imports_from_file(py_file)
                imports.update(file_imports)
            except Exception as e:
                if logger:
                    logger.warning(f"Ошибка при обработке файла {py_file}: {str(e)}")

        return imports

    @staticmethod
    def _extract_imports_from_file(file_path: Path) -> Set[str]:
        """Извлекает импорты из Python файла"""
        imports = set()

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            if logger:
                logger.warning(f"Ошибка при открытии файла {file_path}: {str(e)}")
            return imports

        try:
            # Парсим AST для точного извлечения импортов
            tree = ast.parse(content, filename=str(file_path))

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    # import module
                    for alias in node.names:
                        imports.add(alias.name.split('.')[0])
                elif isinstance(node, ast.ImportFrom):
                    # from module import ...
                    if node.module:
                        imports.add(node.module.split('.')[0])

        except (SyntaxError, UnicodeDecodeError) as e:
            # Fallback: используем регулярные выражения
            if logger:
                logger.debug(f"AST парсинг не удался для {file_path}, используем regex: {str(e)}")
            imports.update(DependencyDiscovery._extract_imports_regex(content))

        return imports

    @staticmethod
    def _extract_imports_regex(content: str) -> Set[str]:
        """Извлекает импорты с помощью регулярных выражений (fallback метод)"""
        imports = set()

        # Регулярные выражения для импортов
        patterns = [
            r'^import\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)',
            r'^from\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)\s+import',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, content, re.MULTILINE)
            for match in matches:
                imports.add(match.split('.')[0])

        return imports

    @staticmethod
    def map_imports_to_packages(imports: Set[str]) -> Dict[str, str]:
        """
        Сопоставляет найденные импорты с пакетами PyPI
        Возвращает словарь: import_name -> package_name
        """
        package_mapping = {}

        for import_name in imports:
            # Ищем точное совпадение
            if import_name in DependencyDiscovery.KNOWN_PACKAGES:
                package_mapping[import_name] = import_name
                continue

            # Ищем в списке импортов пакетов
            for package, package_imports in DependencyDiscovery.KNOWN_PACKAGES.items():
                if import_name in package_imports:
                    package_mapping[import_name] = package
                    break

        return package_mapping

    @staticmethod
    def check_installed_packages(packages: List[str]) -> Dict[str, bool]:
        """
        Проверяет, установлены ли указанные пакеты
        Возвращает словарь: package_name -> is_installed
        """
        installed = {}

        for package in packages:
            try:
                importlib.import_module(package.replace('-', '_'))
                installed[package] = True
            except ImportError:
                installed[package] = False

        return installed

    @staticmethod
    def generate_requirements_file(project_path: Optional[Path] = None,
                                 output_file: Optional[Path] = None) -> Tuple[bool, str]:
        """
        Генерирует файл requirements.txt на основе анализа проекта
        Возвращает: (success, message)
        """
        try:
            # Сканируем импорты
            imports = DependencyDiscovery.scan_project_imports(project_path)
            if logger:
                logger.info(f"Найдено импортов: {len(imports)}")

            # Сопоставляем с пакетами
            package_mapping = DependencyDiscovery.map_imports_to_packages(imports)
            if logger:
                logger.info(f"Сопоставлено пакетов: {len(package_mapping)}")

            if not package_mapping:
                return False, "Не найдено ни одного известного пакета в импортах"

            # Определяем путь к файлу
            if output_file is None:
                if project_path is None:
                    project_path = Path(get_global('script_path'))
                output_file = project_path / 'requirements_discovered.txt'

            # Генерируем содержимое файла
            lines = []
            lines.append("# Автоматически сгенерированные зависимости")
            lines.append(f"# Найдено импортов: {len(imports)}")
            lines.append(f"# Сопоставлено пакетов: {len(package_mapping)}")
            lines.append("")

            # Сортируем пакеты по имени
            sorted_packages = sorted(package_mapping.values())

            for package in sorted_packages:
                # Пробуем определить версию (простая логика)
                version = DependencyDiscovery._get_package_version(package)
                if version:
                    lines.append(f"{package}>={version}")
                else:
                    lines.append(package)

            # Записываем файл
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))

            return True, f"Файл сгенерирован: {output_file} ({len(sorted_packages)} пакетов)"

        except Exception as e:
            error_msg = f"Ошибка при генерации requirements: {str(e)}"
            if logger:
                logger.error(error_msg)
            return False, error_msg

    @staticmethod
    def _get_package_version(package_name: str) -> Optional[str]:
        """Пытается определить минимальную версию пакета"""
        # Простая логика определения версий для известных пакетов
        version_map = {
            'flask': '2.0',
            'django': '3.2',
            'fastapi': '0.68',
            'requests': '2.25',
            'numpy': '1.19',
            'pandas': '1.3',
            'matplotlib': '3.3',
            'tensorflow': '2.6',
            'torch': '1.9',
            'pillow': '8.0',
            'opencv-python': '4.5',
            'sqlalchemy': '1.4',
            'python-dotenv': '0.19',
            'pyyaml': '6.0',
            'cryptography': '36.0',
            'pydantic': '1.8',
        }

        return version_map.get(package_name)

    @staticmethod
    def analyze_project_dependencies(project_path: Optional[Path] = None) -> Dict[str, Any]:
        """
        Полный анализ зависимостей проекта
        Возвращает детальную информацию
        """
        if project_path is None:
            project_path = Path(get_global('script_path'))

        # Сканируем импорты
        imports = DependencyDiscovery.scan_project_imports(project_path)

        # Сопоставляем с пакетами
        package_mapping = DependencyDiscovery.map_imports_to_packages(imports)

        # Проверяем установку пакетов
        packages_list = list(package_mapping.values())
        installed_status = DependencyDiscovery.check_installed_packages(packages_list)

        # Группируем по статусу установки
        installed_packages = [p for p, installed in installed_status.items() if installed]
        missing_packages = [p for p, installed in installed_status.items() if not installed]

        # Анализируем неизвестные импорты
        known_imports = set()
        for package_imports in DependencyDiscovery.KNOWN_PACKAGES.values():
            known_imports.update(package_imports)

        unknown_imports = imports - known_imports

        return {
            'total_imports': len(imports),
            'mapped_packages': len(package_mapping),
            'installed_packages': installed_packages,
            'missing_packages': missing_packages,
            'unknown_imports': list(unknown_imports),
            'package_mapping': package_mapping,
            'scan_path': str(project_path)
        }

    @staticmethod
    def get_dependency_report() -> Dict[str, Any]:
        """Возвращает полный отчет о зависимостях проекта"""
        analysis = DependencyDiscovery.analyze_project_dependencies()

        # Генерируем текстовый отчет
        report_lines = []
        report_lines.append("=== ОТЧЕТ ОБНАРУЖЕНИЯ ЗАВИСИМОСТЕЙ ===")
        report_lines.append(f"Путь сканирования: {analysis['scan_path']}")
        report_lines.append(f"Всего импортов: {analysis['total_imports']}")
        report_lines.append(f"Сопоставлено пакетов: {analysis['mapped_packages']}")
        report_lines.append("")

        if analysis['installed_packages']:
            report_lines.append("✅ Установленные пакеты:")
            for pkg in sorted(analysis['installed_packages']):
                report_lines.append(f"  - {pkg}")
            report_lines.append("")

        if analysis['missing_packages']:
            report_lines.append("❌ Отсутствующие пакеты:")
            for pkg in sorted(analysis['missing_packages']):
                report_lines.append(f"  - {pkg}")
            report_lines.append("")

        if analysis['unknown_imports']:
            report_lines.append("❓ Неизвестные импорты:")
            for imp in sorted(analysis['unknown_imports']):
                report_lines.append(f"  - {imp}")
            report_lines.append("")

        analysis['text_report'] = '\n'.join(report_lines)
        return analysis