# utils.py
import sys
from datetime import datetime,timedelta
from starter_files.config import MAX_RUNS_PER_PERIOD, PERIOD_MINUTES, EXECUTION_LOG_FILE

def check_execution_limit():
    """
    Функция ограничивает количество запусков приложения.
    Если зафиксировано более N запусков за последние M минут,
    возвращает ошибку и прекращает выполнение.
    """

    now = datetime.now()
    cutoff_time = now - timedelta(minutes=PERIOD_MINUTES)

    # Чтение существующих меток
    timestamps = []
    if EXECUTION_LOG_FILE.exists():
        with open(EXECUTION_LOG_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        ts = datetime.fromisoformat(line)
                        if ts >= cutoff_time:
                            timestamps.append(ts)
                    except ValueError:
                        continue

    # Проверяем, не превысит ли новый запуск лимит
    if len(timestamps) >= MAX_RUNS_PER_PERIOD:
        print(f"Ошибка: Лимит {MAX_RUNS_PER_PERIOD} запусков за {PERIOD_MINUTES} минут.")
        return False

    # Добавляем текущий запуск и сохраняем
    timestamps.append(now)
    with open(EXECUTION_LOG_FILE, 'w') as f:
        for ts in timestamps:
            f.write(ts.isoformat() + "\n")

    return True