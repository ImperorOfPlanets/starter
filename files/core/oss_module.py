import importlib
import platform
from pathlib import Path
from typing import Dict, Any, Optional, Type
from files.core.base_module import BaseModule
from files.core.utils.globalVars_utils import get_global
from files.core.utils.log_utils import LogManager

# Логгер будет инициализирован позже, при необходимости
logger = None

class OSSModuleManager:
    """Менеджер модулей для разных операционных систем"""

    _modules_cache: Dict[str, Dict[str, Type[BaseModule]]] = {}
    _current_os_family: Optional[str] = None
    _current_os_name: Optional[str] = None

    @staticmethod
    def get_os_info() -> Dict[str, str]:
        """Получает информацию об ОС"""
        if OSSModuleManager._current_os_family is None or OSSModuleManager._current_os_name is None:
            system = platform.system().lower()

            # Определяем семейство ОС
            if system == 'windows':
                os_family = 'windows'
                os_name = 'windows'
            elif system == 'darwin':
                os_family = 'macos'
                os_name = 'macos'
            elif system == 'linux':
                # Определяем дистрибутив Linux
                try:
                    with open('/etc/os-release', 'r') as f:
                        content = f.read()
                        if 'ID_LIKE' in content:
                            id_like = content.split('ID_LIKE=')[1].split('\n')[0].strip('"').lower()
                            if 'debian' in id_like or 'ubuntu' in id_like:
                                os_family = 'debian'
                            elif 'rhel' in id_like or 'fedora' in id_like or 'centos' in id_like:
                                os_family = 'rhel'
                            elif 'arch' in id_like:
                                os_family = 'arch'
                            elif 'suse' in id_like:
                                os_family = 'suse'
                            else:
                                os_family = 'linux'
                        else:
                            id_match = content.split('ID=')[1].split('\n')[0].strip('"').lower()
                            os_family = id_match

                    # Получаем имя ОС
                    os_name = os_family

                except (FileNotFoundError, IndexError, KeyError):
                    os_family = 'linux'
                    os_name = 'linux'
            else:
                os_family = 'unknown'
                os_name = 'unknown'

            OSSModuleManager._current_os_family = os_family
            OSSModuleManager._current_os_name = os_name

        return {
            'family': OSSModuleManager._current_os_family or 'unknown',
            'name': OSSModuleManager._current_os_name or 'unknown',
            'system': platform.system().lower()
        }

    @staticmethod
    def _load_modules_for_os(os_name: str) -> Dict[str, Type[BaseModule]]:
        """Загружает модули для конкретной ОС"""
        if os_name in OSSModuleManager._modules_cache:
            return OSSModuleManager._modules_cache[os_name]

        modules = {}
        base_path = Path(get_global('starter_path')) / 'files' / 'core' / 'oss'

        # Пути поиска модулей в порядке приоритета
        search_paths = [
            base_path / os_name / 'default',  # os_name/default (например, ubuntu/default)
            base_path / os_name,              # os_name (например, ubuntu)
            base_path / 'default'             # default
        ]

        for search_path in search_paths:
            if not search_path.exists():
                continue

            # Ищем все .py файлы в директории
            for py_file in search_path.glob('*.py'):
                if py_file.name.startswith('__'):
                    continue

                module_name = py_file.stem
                module_path = f"files.core.oss.{os_name}.default.{module_name}"

                # Если не нашли в os_name/default, пробуем os_name
                if not OSSModuleManager._try_import_module(module_path):
                    module_path = f"files.core.oss.{os_name}.{module_name}"
                    if not OSSModuleManager._try_import_module(module_path):
                        continue

                try:
                    module = importlib.import_module(module_path)
                    # Ищем класс модуля в модуле
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (isinstance(attr, type) and
                            issubclass(attr, BaseModule) and
                            attr != BaseModule):
                            modules[module_name] = attr
                            if logger:
                                logger.debug(f"Загружен модуль {module_name} из {module_path}")
                            break

                except Exception as e:
                    if logger:
                        logger.warning(f"Ошибка загрузки модуля {module_path}: {str(e)}")
                    continue

        OSSModuleManager._modules_cache[os_name] = modules
        return modules

    @staticmethod
    def _try_import_module(module_path: str) -> bool:
        """Проверяет возможность импорта модуля"""
        try:
            importlib.import_module(module_path)
            return True
        except ImportError:
            return False

    @staticmethod
    def get_module(module_name: str) -> Optional[Type[BaseModule]]:
        """Получает модуль для текущей ОС"""
        os_info = OSSModuleManager.get_os_info()

        # Порядок поиска: конкретная ОС -> семейство -> default
        search_order = [
            os_info['name'],      # например, 'ubuntu'
            os_info['family'],    # например, 'debian'
            'default'             # fallback
        ]

        for os_name in search_order:
            modules = OSSModuleManager._load_modules_for_os(os_name)
            if module_name in modules:
                return modules[module_name]

        if logger:
            logger.warning(f"Модуль {module_name} не найден для ОС {os_info['name']} (семейство: {os_info['family']})")
        return None

    @staticmethod
    def get_available_modules() -> Dict[str, Dict[str, Type[BaseModule]]]:
        """Возвращает все доступные модули для всех ОС"""
        os_info = OSSModuleManager.get_os_info()
        result = {}

        # Загружаем модули для текущей ОС и ее семейства
        for os_name in [os_info['name'], os_info['family'], 'default']:
            if os_name not in result:
                result[os_name] = OSSModuleManager._load_modules_for_os(os_name)

        return result

    @staticmethod
    def call_module_method(module_name: str, method_name: str, *args, **kwargs) -> Any:
        """Вызывает метод модуля для текущей ОС"""
        module_class = OSSModuleManager.get_module(module_name)
        if not module_class:
            raise ModuleNotFoundError(f"Модуль {module_name} не найден")

        if not hasattr(module_class, method_name):
            raise AttributeError(f"Метод {method_name} не найден в модуле {module_name}")

        method = getattr(module_class, method_name)
        if not callable(method):
            raise AttributeError(f"{method_name} не является вызываемым методом")

        return method(*args, **kwargs)

    @staticmethod
    def clear_cache():
        """Очищает кеш загруженных модулей"""
        OSSModuleManager._modules_cache.clear()
        OSSModuleManager._current_os_family = None
        OSSModuleManager._current_os_name = None