import platform
import subprocess
from flask import render_template, jsonify
from starter_files.core.utils.i18n_utils import t
from starter_files.core.utils.log_utils import LogManager
from starter_files.core.utils.loader_utils import get
from starter_files.core.utils.globalVars_utils import get_global

logger = LogManager.get_logger()

# Конфигурация модуля для панели управления
this_section_in_control_panel = True
section_icon = "bi-gear"
section_name = "Service"
section_order = 6

SERVICE_NAME = "starter-service"

def index(data, session):
    """Главная страница модуля"""
    status = get_service_status()
    return render_template(
        'sections/service/index.html',
        service_status=status,
        service_name=SERVICE_NAME,
        t=t
    )

def info(data, session):
    """Страница информации о сервисе"""
    status = get_service_status()
    return render_template(
        'sections/service/info.html',
        service_status=status,
        service_name=SERVICE_NAME,
        t=t
    )

def service_action(data, session):
    """Обработка действий с сервисом"""
    action = data.get('action')
    if not action:
        return jsonify({'status': 'error', 'message': 'No action specified'})
    
    try:
        # Используем модуль service для выполнения действия
        result = get('service', 'service_action', {'action': action})
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error performing service action {action}: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)})

def install_service(data, session):
    """Установка сервиса"""
    try:
        log_file_path = get_global('path_log_install') / f"install_service_{SERVICE_NAME}.log"
        result = get('service', 'install_service', str(log_file_path))
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error installing service: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)})

def uninstall_service(data, session):
    """Удаление сервиса"""
    try:
        log_file_path = get_global('path_log_install') / f"uninstall_service_{SERVICE_NAME}.log"
        result = get('service', 'uninstall_service', str(log_file_path))
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error uninstalling service: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)})

def get_service_status():
    """Получение статуса сервиса"""
    try:
        return get('service', 'get_service_status')
    except Exception as e:
        logger.error(f"Error getting service status: {str(e)}")
        return {
            'installed': False,
            'running': False,
            'enabled': False,
            'os': platform.system().lower()
        }

def add_scheduled_task(data, session):
    """Добавление периодической задачи"""
    try:
        # Реализация добавления задачи в планировщик
        task_name = data.get('task_name')
        task_command = data.get('task_command')
        task_schedule = data.get('task_schedule')
        
        # Здесь будет логика добавления задачи (cron, systemd timer, etc.)
        # Пока заглушка
        return jsonify({
            'status': 'success', 
            'message': f'Task {task_name} added successfully'
        })
    except Exception as e:
        logger.error(f"Error adding scheduled task: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)})

def get_scheduled_tasks(data, session):
    """Получение списка периодических задач"""
    try:
        # Здесь будет логика получения списка задач
        # Пока заглушка
        return jsonify({
            'status': 'success',
            'tasks': []
        })
    except Exception as e:
        logger.error(f"Error getting scheduled tasks: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)})

def diagnose_service(data, session):
    """Диагностика сервиса"""
    try:
        # Используем модуль service для диагностики
        result = get('service', 'diagnose_service')
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error diagnosing service: {str(e)}")
        return jsonify({
            'status': 'error', 
            'message': str(e),
            'problems': ['Diagnosis failed']
        })