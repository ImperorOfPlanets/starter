# Кастомные задачи

## Как создать задачу

### Шаг 1: Создайте файл

Создайте файл `files/tasks/custom/my_task.py`:

```python
from files.core.oss.default.task_base import BaseTask

class MyCleanupTask(BaseTask):
    
    @staticmethod
    def metadata():
        return {
            'name': 'my_cleanup',
            'description': {
                'ru': 'Очистка моих файлов',
                'en': 'My file cleanup',
                'cn': '我的文件清理'
            },
            'category': 'maintenance',
            'default_enabled': False,
            'default_schedule': 'weekly',
            'params': [
                {
                    'name': 'max_age_days',
                    'type': 'int',
                    'default': 7,
                    'label': {
                        'ru': 'Макс. возраст (дни)',
                        'en': 'Max age (days)',
                        'cn': '最大天数'
                    }
                },
                {
                    'name': 'target_dir',
                    'type': 'str',
                    'default': 'C:\\temp',
                    'label': {
                        'ru': 'Папка для очистки',
                        'en': 'Cleanup directory',
                        'cn': '清理目录'
                    }
                },
            ],
            'events': ['on_schedule'],
        }

    @staticmethod
    def execute(params):
        """Выполнение задачи — вызывается как отдельный процесс"""
        import os
        from pathlib import Path
        import time

        max_age = params.get('max_age_days', 7)
        target = params.get('target_dir', '')

        if not target:
            return {'status': 'error', 'message': 'target_dir is required'}

        target_path = Path(target)
        if not target_path.exists():
            return {'status': 'error', 'message': f'Directory not found: {target}'}

        cutoff = time.time() - (max_age * 86400)
        removed = 0

        for f in target_path.rglob('*'):
            if f.is_file():
                try:
                    if f.stat().st_mtime < cutoff:
                        f.unlink()
                        removed += 1
                except Exception:
                    continue

        return {
            'status': 'success',
            'message': f'Removed {removed} files older than {max_age} days'
        }
```

### Шаг 2: Перезапустите стартер

```bash
python starter.py
```

Задача автоматически появится в планировщике.

### Шаг 3: Настройте

1. Перейдите в **Сервис → Планировщик задач**
2. Найдите вашу задачу
3. Включите её и настройте расписание
4. Настройте параметры

## Системные типы параметров

| Тип | Описание | Пример |
|-----|----------|--------|
| `str` | Строка | `C:\temp` |
| `int` | Целое число | `30` |
| `bool` | Логическое | `true` / `false` |
| `select` | Выбор из списка | `option1`, `option2` |

## События

| Событие | Описание |
|---------|----------|
| `on_schedule` | По расписанию |
| `on_startup` | При запуске стартера |
| `on_update` | При обновлении |
| `on_demand` | По требованию (только ручной запуск) |

## Безопасность

- Задачи выполняются как **отдельные процессы**
- Падение задачи **не уронит стартер**
- Каждая задача логируется в `files/tasks/<name>.log`
- Кастомные задачи **не попадают в git** (.gitignore)
