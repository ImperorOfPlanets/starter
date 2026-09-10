"""
Базовый класс для задач планировщика.

Как создать свою задачу:
1. Создай файл в files/tasks/custom/ (например my_task.py)
2. Наследуй от BaseTask
3. Реализуй методы execute() и metadata()
4. Задача автоматически появится в списке

Пример:

    from files.core.oss.default.task_base import BaseTask

    class MyTask(BaseTask):
        @staticmethod
        def metadata():
            return {
                'name': 'my_task',
                'description': {'ru': 'Моя задача', 'en': 'My task', 'cn': '我的任务'},
                'category': 'custom',
                'params': [
                    {'name': 'count', 'type': 'int', 'default': 10, 'label': {'ru': 'Количество', 'en': 'Count', 'cn': '数量'}},
                ],
                'default_schedule': 'daily',
            }

        @staticmethod
        def execute(params):
            count = params.get('count', 10)
            print(f"Выполняю my_task с count={count}")
            return {'status': 'success', 'message': f'Done {count} iterations'}
"""

import os
import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, List
from files.core.utils.globalVars_utils import get_global
from files.core.utils.log_utils import LogManager

logger = LogManager.get_logger('task_base')


class BaseTask(ABC):
    """Базовый класс для всех задач планировщика"""

    @staticmethod
    @abstractmethod
    def metadata() -> Dict[str, Any]:
        """
        Метаданные задачи. Должен вернуть dict:
        {
            'name': 'unique_task_name',
            'description': {'ru': 'Описание', 'en': 'Description', 'cn': '描述'},
            'category': 'custom',        # custom / system / monitoring / maintenance
            'default_enabled': True,
            'default_schedule': 'daily',  # every_5min / hourly / daily / weekly
            'params': [                   # параметры с настройками
                {
                    'name': 'param_name',
                    'type': 'int|str|bool|select',
                    'default': value,
                    'label': {'ru': 'Метка', 'en': 'Label', 'cn': '标签'},
                    'options': ['opt1', 'opt2'],  # только для type=select
                }
            ],
            'events': ['on_schedule'],    # on_startup / on_schedule / on_update / on_demand
        }
        """
        pass

    @staticmethod
    @abstractmethod
    def execute(params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Выполнение задачи.
        Вызывается как отдельный процесс: python starter.py --task <name>
        Не падает!

        Args:
            params: dict параметров из конфигурации

        Returns:
            {'status': 'success'|'error', 'message': '...'}
        """
        pass


def discover_custom_tasks() -> List[Dict[str, Any]]:
    """
    Автоматически находит все задачи в files/tasks/custom/
    и возвращает список метаданных.
    """
    tasks = []
    starter_path = get_global('starter_path')
    if not starter_path:
        return tasks

    custom_dir = Path(starter_path) / 'files' / 'tasks' / 'custom'
    if not custom_dir.exists():
        return tasks

    for py_file in custom_dir.glob('*.py'):
        if py_file.stem.startswith('_'):
            continue

        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                f"files.tasks.custom.{py_file.stem}",
                str(py_file)
            )
            if not spec or not spec.loader:
                continue

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Ищем классы наследующие BaseTask
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and
                    issubclass(attr, BaseTask) and
                    attr is not BaseTask):

                    meta = attr.metadata()
                    if not meta.get('name'):
                        continue

                    # Сохраняем ссылку на класс для execute
                    meta['_class'] = attr
                    meta['_source'] = str(py_file)
                    tasks.append(meta)
                    logger.info(f"Discovered custom task: {meta['name']} from {py_file.name}")

        except Exception as e:
            logger.error(f"Error loading task from {py_file.name}: {e}")
            continue

    return tasks


def get_all_tasks_with_custom() -> List[Dict[str, Any]]:
    """Получить все задачи (встроенные + кастомные)"""
    from files.core.oss.default.scheduler import BUILTIN_TASKS

    all_tasks = []

    # Встроенные
    for name, task_def in BUILTIN_TASKS.items():
        all_tasks.append({
            'name': name,
            'builtin': True,
            **{k: v for k, v in task_def.items() if k != '_class'}
        })

    # Кастомные
    custom = discover_custom_tasks()
    for meta in custom:
        all_tasks.append({
            'name': meta['name'],
            'builtin': False,
            'description': meta.get('description', {}),
            'category': meta.get('category', 'custom'),
            'default_enabled': meta.get('default_enabled', False),
            'default_schedule': meta.get('default_schedule', 'daily'),
            'params': meta.get('params', []),
            'events': meta.get('events', ['on_schedule']),
        })

    return all_tasks


def run_custom_task(task_name: str, params: dict = None) -> dict:
    """Запустить кастомную задачу по имени"""
    custom = discover_custom_tasks()
    for meta in custom:
        if meta['name'] == task_name:
            cls = meta.get('_class')
            if cls:
                return cls.execute(params or {})
    return {'status': 'error', 'message': f'Custom task not found: {task_name}'}
