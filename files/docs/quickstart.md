# Быстрый старт

## Установка

1. Клонируйте репозиторий:
```bash
git clone https://gitflic.ru/project/imperor/starter.git
cd starter
```

2. Запустите установщик:
```bash
python starter.py
```

3. Следуйте инструкциям — будет предложено ввести логин и пароль.

4. Откройте веб-интерфейс: `https://localhost:2000`

## Структура проекта

```
starter/
├── starter.py              # Точка входа
├── .env                    # Конфигурация (генерируется автоматически)
├── files/
│   ├── core/
│   │   ├── oss/            # ОС-зависимые модули
│   │   │   ├── default/    # Общие модули
│   │   │   └── windows/    # Windows-специфичные
│   │   └── software/       # Модули ПО (Docker, Git, etc.)
│   ├── web/
│   │   ├── sections/       # Секции панели управления
│   │   ├── templates/      # HTML шаблоны
│   │   ├── locales/        # Переводы (ru, en, cn)
│   │   └── api.py          # REST API
│   ├── configs/
│   │   └── server_types.py # Типы серверов
│   ├── tasks/
│   │   └── custom/         # Кастомные задачи
│   └── docs/               # Документация
└── venv/                   # Виртуальное окружение
```

## Первый запуск

```bash
# Windows
python starter.py

# Сервер запустится на https://localhost:2000
```

## Команды

| Команда | Описание |
|---------|----------|
| `python starter.py` | Запуск веб-интерфейса |
| `python starter.py --service` | Запуск как сервис |
| `python starter.py --status` | Статус процессов |
| `python starter.py --kill-all` | Остановить все процессы |
| `python starter.py --task <name>` | Запустить задачу |
