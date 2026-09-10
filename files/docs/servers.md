# Серверы

## Обзор

Starter управляет серверами через Docker Compose. Каждый сервер — это проект с `docker-compose.yml`.

## Установка сервера

### Через веб-интерфейс

1. Перейдите в **Servers**
2. Нажмите **Установить сервер**
3. Выберите тип сервера
4. Укажите путь для установки
5. Нажмите **Установить**

### Через API

```bash
# Установка
curl -k -X POST https://localhost:2000/api/v1/servers/install \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"server_type":"opencode","path":"C:\\apps\\opencode","name":"opencode"}'
```

## Управление серверами

### Статус серверов

```bash
curl -k https://localhost:2000/api/v1/servers \
  -H "X-API-Key: YOUR_KEY"
```

### Запуск/остановка

```bash
# Запуск
curl -k -X POST https://localhost:2000/api/v1/servers/{id}/start \
  -H "X-API-Key: YOUR_KEY"

# Остановка
curl -k -X POST https://localhost:2000/api/v1/servers/{id}/stop \
  -H "X-API-Key: YOUR_KEY"
```

## Типы серверов

| Сервер | Описание | Порт |
|--------|----------|------|
| opencode | AI-ассистент с Nginx | 2002 |
| streams | Стриминг | 8000 |
| client | AI Помощник | 80 |
| wake_word | Обучение моделей | 8010 |
| core | Ядро системы | 8000 |

## Структура сервера

```
server/
├── code/              # Исходный код
├── docker/
│   ├── docker-compose.yml
│   ├── docker-compose.example
│   └── .env
└── logs/
```
