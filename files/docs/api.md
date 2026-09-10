# REST API

## Базовый URL

```
https://localhost:2000/api/v1
```

## Аутентификация

Все запросы требуют заголовок `X-API-Key`.

Ключ хранится в `files/crypto/.api_key`.

```bash
curl -k https://localhost:2000/api/v1/status \
  -H "X-API-Key: YOUR_KEY"
```

## Эндпоинты

### Статус

```
GET /api/v1/status
```

Ответ:
```json
{
  "api_version": "1.0.0",
  "docker_installed": true,
  "servers_count": 5,
  "success": true
}
```

### Серверы

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| GET | `/servers` | Список серверов |
| GET | `/servers/types` | Типы серверов |
| POST | `/servers/install` | Установить сервер |
| POST | `/servers/{id}/start` | Запустить сервер |
| POST | `/servers/{id}/stop` | Остановить сервер |
| DELETE | `/servers/{id}` | Удалить сервер |
| GET | `/servers/{id}` | Информация о сервере |

### Примеры

#### Список серверов

```bash
curl -k https://localhost:2000/api/v1/servers \
  -H "X-API-Key: KEY"
```

#### Установка сервера

```bash
curl -k -X POST https://localhost:2000/api/v1/servers/install \
  -H "X-API-Key: KEY" \
  -H "Content-Type: application/json" \
  -d '{"server_type":"opencode","path":"C:\\apps\\opencode","name":"opencode"}'
```

#### Запуск сервера

```bash
curl -k -X POST "https://localhost:2000/api/v1/servers/C:%5Capps%5Copencode/start" \
  -H "X-API-Key: KEY"
```

### Прочее

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| GET | `/drives` | Список дисков |
| GET | `/folders` | Список папок |
