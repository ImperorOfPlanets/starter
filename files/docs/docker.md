# Docker

## Обзор

Starter управляет серверами через Docker Compose. Docker Desktop должен быть запущен.

## Требования

- Docker Desktop (Windows/Mac)
- Docker Compose v2
- Минимум 4GB RAM выделено Docker

## Команды Docker через Starter

### Запуск сервера

```bash
# Через API
curl -k -X POST https://localhost:2000/api/v1/servers/{id}/start \
  -H "X-API-Key: YOUR_KEY"
```

### Остановка сервера

```bash
curl -k -X POST https://localhost:2000/api/v1/servers/{id}/stop \
  -H "X-API-Key: YOUR_KEY"
```

## Решение проблем

### "error while creating mount source path"

Это баг Docker Desktop WSL2. Решения:

1. Перезапустите Docker Desktop
2. Выполните `wsl --shutdown` в PowerShell
3. Переключитесь на Hyper-V backend (Settings → General)

### "Cannot connect to the Docker daemon"

1. Убедитесь что Docker Desktop запущен
2. Проверьте статус: `docker info`
3. Перезапустите Docker Desktop

## Настройка Docker

### .env файла сервера

```env
# Порт сервера
PORT=8000

# Путь к коду
CODE_PATH=/app/code

# Docker network
NETWORK_NAME=mynet
```

### docker-compose.yml

```yaml
services:
  app:
    image: alpine:latest
    container_name: myapp
    ports:
      - "8000:8000"
    volumes:
      - ./code:/app
    working_dir: /app
    command: sh -c "echo 'Running' && sleep infinity"
```
