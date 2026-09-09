# files/web/sections/scheduler.py
"""
Веб-секция планировщика задач — API для фронтенда
"""
from flask import jsonify
from files.core.utils.loader_utils import get
from files.core.utils.log_utils import LogManager

logger = LogManager.get_logger('scheduler_web')


def get_tasks(data, session):
    """Получить все задачи"""
    try:
        return jsonify(get('scheduler', 'get_tasks'))
    except Exception as e:
        logger.error(f"get_tasks error: {e}")
        return jsonify({'status': 'error', 'message': str(e)})


def get_task(data, session):
    """Получить одну задачу"""
    try:
        name = data.get('name')
        return jsonify(get('scheduler', 'get_task', name))
    except Exception as e:
        logger.error(f"get_task error: {e}")
        return jsonify({'status': 'error', 'message': str(e)})


def add_task(data, session):
    """Добавить задачу"""
    try:
        task_data = {
            'name': data.get('name'),
            'enabled': data.get('enabled', True),
            'schedule': data.get('schedule', 'daily'),
            'custom_schedule': data.get('custom_schedule'),
            'module': data.get('module'),
            'func': data.get('func'),
            'description': data.get('description', ''),
            'params': data.get('params', {}),
            'category': data.get('category', 'custom'),
            'events': data.get('events', ['on_schedule'])
        }
        return jsonify(get('scheduler', 'add_task', task_data))
    except Exception as e:
        logger.error(f"add_task error: {e}")
        return jsonify({'status': 'error', 'message': str(e)})


def update_task(data, session):
    """Обновить задачу"""
    try:
        task_data = {
            'name': data.get('name'),
            'enabled': data.get('enabled'),
            'schedule': data.get('schedule'),
            'custom_schedule': data.get('custom_schedule'),
            'module': data.get('module'),
            'func': data.get('func'),
            'description': data.get('description'),
            'params': data.get('params'),
            'category': data.get('category'),
            'events': data.get('events')
        }
        # Remove None values
        task_data = {k: v for k, v in task_data.items() if v is not None}
        return jsonify(get('scheduler', 'update_task', task_data))
    except Exception as e:
        logger.error(f"update_task error: {e}")
        return jsonify({'status': 'error', 'message': str(e)})


def delete_task(data, session):
    """Удалить задачу"""
    try:
        return jsonify(get('scheduler', 'delete_task', {'name': data.get('name')}))
    except Exception as e:
        logger.error(f"delete_task error: {e}")
        return jsonify({'status': 'error', 'message': str(e)})


def toggle_task(data, session):
    """Включить/выключить задачу"""
    try:
        return jsonify(get('scheduler', 'toggle_task', {'name': data.get('name')}))
    except Exception as e:
        logger.error(f"toggle_task error: {e}")
        return jsonify({'status': 'error', 'message': str(e)})


def run_task_now(data, session):
    """Запустить задачу немедленно"""
    try:
        return jsonify(get('scheduler', 'run_task_now', {'name': data.get('name')}))
    except Exception as e:
        logger.error(f"run_task_now error: {e}")
        return jsonify({'status': 'error', 'message': str(e)})


def get_task_log(data, session):
    """Получить лог задачи"""
    try:
        return jsonify(get('scheduler', 'get_task_log', {'name': data.get('name')}))
    except Exception as e:
        logger.error(f"get_task_log error: {e}")
        return jsonify({'status': 'error', 'message': str(e)})


def clear_task_log(data, session):
    """Очистить лог задачи"""
    try:
        return jsonify(get('scheduler', 'clear_task_log', {'name': data.get('name')}))
    except Exception as e:
        logger.error(f"clear_task_log error: {e}")
        return jsonify({'status': 'error', 'message': str(e)})


def get_task_history(data, session):
    """Получить историю выполнения"""
    try:
        return jsonify(get('scheduler', 'get_task_history'))
    except Exception as e:
        logger.error(f"get_task_history error: {e}")
        return jsonify({'status': 'error', 'message': str(e)})


def trigger_event(data, session):
    """Триггер события (для будущего использования)"""
    try:
        event_name = data.get('event')
        if not event_name:
            return jsonify({'status': 'error', 'message': 'Event name required'})
        return jsonify(get('scheduler', 'trigger_event', event_name))
    except Exception as e:
        logger.error(f"trigger_event error: {e}")
        return jsonify({'status': 'error', 'message': str(e)})
