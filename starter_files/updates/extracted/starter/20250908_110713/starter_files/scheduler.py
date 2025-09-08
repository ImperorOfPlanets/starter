import schedule
import time
from threading import Event
from starter_files.untils.logger import logger

class TaskScheduler:
    def __init__(self):
        self.stop_event = Event()
        self.jobs = []
        self._init_scheduler()  # Явная инициализация при создании
        
    def _init_scheduler(self):
        """Инициализация задач планировщика"""
        from starter_files.config import SCHEDULER_CONFIG
        
        for task_name, config in SCHEDULER_CONFIG.items():
            if not config['enabled']:
                continue
                
            try:
                # Динамический импорт функции
                module = __import__('starter_files.tasks', fromlist=[config['function']])
                func = getattr(module, config['function'])
                
                # Создаем задачу
                job = schedule.every(config['interval_minutes']).minutes.do(func)
                self.jobs.append(job)
                logger.log(f"Задача '{task_name}' запланирована", "SCHEDULER")
                
            except Exception as e:
                logger.log(f"Ошибка планирования задачи '{task_name}': {str(e)}", "ERROR")

    def run_pending(self):
        """Выполняет все готовые к выполнению задачи"""
        schedule.run_pending()
        
    def run(self):
        """Основной цикл выполнения задач"""
        logger.log("Планировщик задач запущен", "SCHEDULER")
        while not self.stop_event.is_set():
            self.run_pending()
            time.sleep(1)
            
    def stop(self):
        """Остановка планировщика"""
        self.stop_event.set()
        for job in self.jobs:
            schedule.cancel_job(job)
        logger.log("Планировщик задач остановлен", "SCHEDULER")