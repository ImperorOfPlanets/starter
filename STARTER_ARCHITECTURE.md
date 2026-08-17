# 🔧 STARTER — Главная Программа Проекта

> **Starter — это ПЕРВАЯ программа**, которую ты запускаешь на чистом ПК. Всё начинается с него!

---

## 🎯 Назначение

**Starter** — это **генератор и менеджер проектов**, который:

1. ✅ **Создаёт проекты** из шаблонов
2. ✅ **Скачивает код** серверов из GitFlic
3. ✅ **Настраивает окружение** (venv, Docker, .env)
4. ✅ **Управляет типами серверов** (client, tei, TTS, STT, BROWSER...)
5. ✅ **Обновляет проекты** автоматически
6. ✅ **Предоставляет веб-интерфейс** для настройки

---

## 🏗️ Архитектура Starter

```
starter/
│
├── starter.py              # 🔥 ГЛАВНЫЙ СКРИПТ (запускаешь первым!)
│   ├── Инициализация SystemModule
│   ├── Создание venv
│   ├── Установка зависимостей
│   ├── Первичная настройка
│   ├── Загрузка модулей
│   ├── Настройка фаервола
│   └── Запуск веб-интерфейса
│
├── files/                  # 📦 МОДУЛИ И КОНФИГИ
│   ├── core/               # Базовые модули
│   │   ├── oss/            # OS-специфичные модули
│   │   │   ├── default/    # Стандартные реализации
│   │   │   ├── windows/    # Windows версии
│   │   │   └── rocky/      # Linux версии
│   │   ├── software/       # Модули ПО
│   │   └── utils/          # Утилиты
│   │       ├── SystemModule.py          # Информация об ОС
│   │       ├── LogManager.py            # Логирование
│   │       ├── VenvRequirementsManager.py # venv и зависимости
│   │       ├── FirstSetupUtils.py       # Первичная настройка
│   │       ├── SSLUtils.py              # SSL сертификаты
│   │       ├── FirewallModule.py        # Фаервол
│   │       ├── LoaderUtils.py           # Загрузка модулей
│   │       ├── RegistryManager.py       # Реестр проектов
│   │       ├── EnvUtils.py              # Работа с .env
│   │       └── ExceptionHandler.py      # Обработка ошибок
│   │
│   ├── configs/            # ⭐ КОНФИГУРАЦИИ
│   │   ├── server_types.py      # ТИПЫ СЕРВЕРОВ (client, tei, TTS...)
│   │   └── starter_repos.py     # Репозитории стартера
│   │
│   ├── web/                # Веб-интерфейс
│   │   ├── templates/      # HTML шаблоны
│   │   ├── static/         # CSS, JS
│   │   └── ssl/            # SSL сертификаты
│   │
│   ├── data/               # Данные
│   ├── logs/               # Логи
│   └── requirements/       # Python зависимости
│
├── .env                    # Настройки стартера
├── .env.example            # Шаблон настроек
└── README.md               # Документация
```

---

## 🚀 Поток Запуска

```
┌─────────────────────────────────────────────────────────┐
│  1. ЗАПУСК: python starter.py                           │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│  2. SYSTEM MODULE: Сбор информации об ОС                │
│     - os_name, os_version, hostname                     │
│     - is_admin, python_version                          │
│     - running_in_docker                                 │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│  3. VENV: Проверка/создание виртуального окружения      │
│     - Если нет venv → создать                           │
│     - Если нет зависимостей → установить                │
│     - Перезапуск в venv                                 │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│  4. FIRST SETUP: Первичная настройка                    │
│     - Генерация APP_SECRET_KEY                          │
│     - Создание ADMIN_LOGIN/PASSWORD                     │
│     - Запись в .env                                     │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│  5. LOAD MODULES: Загрузка модулей проекта              │
│     - Чтение server_types.py                            │
│     - Инициализация глобальных переменных               │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│  6. FIREWALL: Настройка фаервола                        │
│     - Открытие порта PORT                               │
│     - Проверка правил                                   │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│  7. WEB UI: Запуск веб-интерфейса                       │
│     - https://localhost:PORT                            │
│     - Выбор типа сервера                                │
│     - Настройка проекта                                 │
└─────────────────────────────────────────────────────────┘
```

---

## 🖥️ Типы Серверов (server_types.py)

**Это ГЛАВНАЯ конфигурация!** Определяет, какие проекты можно создать:

```python
SERVER_TYPES = {
    'client': {
        'name': 'Client Server',
        'description': 'Веб-сервер для клиентской части',
        'repositories': [{
            'url': 'https://gitflic.ru/project/imperor/client.git',
            'branch': 'master'
        }]
    },
    'tei': {
        'name': 'Text Embeddings Server',
        'repositories': [{
            'url': 'https://gitflic.ru/project/imperor/api-server.git',
            'branch': 'master'
        }]
    },
    'TTS': {
        'name': 'Text-to-Speech Server',
        'repositories': [{
            'url': 'https://gitflic.ru/project/imperor/tts-server.git',
            'branch': 'master'
        }]
    },
    'STT': {
        'name': 'Speech-to-Text Server',
        'repositories': [{
            'url': 'https://gitflic.ru/project/imperor/stt-server.git',
            'branch': 'master'
        }]
    },
    'BROWSER': {
        'name': 'Browser Automation Server',
        'repositories': [{
            'url': 'https://gitflic.ru/project/imperor/browser-server.git',
            'branch': 'master'
        }]
    }
}
```

### Как Добавить Новый Тип Сервера

```python
# 1. Открой starter/files/configs/server_types.py
# 2. Добавь новый тип:

'NEW_TYPE': {
    'name': 'New Server Name',
    'description': 'Описание назначения',
    'repositories': [{
        'name': 'main',
        'url': 'https://gitflic.ru/project/imperor/new-server.git',
        'branch': 'master',
        'targets_config': 'targets.json'
    }]
}
```

---

## 📦 Модули Starter (files/core/)

### SystemModule
**Сбор информации об ОС:**
```python
SystemModule.collect_basic_system_info()
# → os_name, os_version, hostname, python_version, is_admin...
```

### LogManager
**Логирование:**
```python
LogManager.initialize(service_mode=False)
logger = LogManager.get_logger("main")
logger.info("Запуск...")
```

### VenvRequirementsManager
**Управление venv:**
```python
VenvRequirementsManager.create_venv()
VenvRequirementsManager.install_requirements()
VenvRequirementsManager.restart_in_venv()
```

### FirstSetupUtils
**Первичная настройка:**
```python
is_first_run, credentials = first_run_setup()
# → Генерирует логин/пароль для веб-интерфейса
```

### SSLUtils
**SSL сертификаты:**
```python
ssl_context = get_ssl_context()
# → Создаёт самоподписанные сертификаты
```

### FirewallModule
**Фаервол:**
```python
FirewallModule.ensure_port_open(PORT, 'tcp')
# → Открывает порт в фаерволе
```

### LoaderUtils
**Загрузка модулей:**
```python
modules = load_modules()
# → Загружает модули проекта
```

### RegistryManager
**Реестр проектов:**
```python
RegistryManager.register_initializing(project_path)
# → Регистрирует проект в реестре
```

---

## 🌐 Веб-интерфейс

### Страницы

| Страница | Назначение |
|----------|------------|
| `/` | Главная (выбор типа сервера) |
| `/setup` | Настройка проекта |
| `/vpn` | Загрузка VPN конфига |
| `/ssl` | Настройка SSL |
| `/docker` | Запуск Docker |
| `/settings` | Настройки стартера |

### Процесс Настройки

```
1. Выбор типа сервера
   ↓
2. Скачивание кода из GitFlic
   ↓
3. Генерация .env
   ↓
4. Настройка OAuth (myidon.site)
   ↓
5. Загрузка VPN config.ovpn
   ↓
6. Генерация SSL сертификатов
   ↓
7. Запуск docker-compose up -d
   ↓
8. Проект запущен!
```

---

## 🔄 Обновление Стартера

**Автоматическое обновление** из `starter_repos.py`:

```python
STARTER_REPOSITORIES = [
    {
        'name': 'Основной',
        'url': 'https://gitflic.ru/project/imperor/starter/file/downloadAll?branch=master&format=zip',
        'priority': 1
    },
    {
        'name': 'Резервный',
        'url': '...?branch=main&format=zip',
        'priority': 2
    },
    {
        'name': 'Dev',
        'url': '...?branch=develop&format=zip',
        'priority': 3
    }
]
```

**Процесс:**
1. Проверяет репозиторий
2. Скачивает архив
3. Сравнивает файлы
4. Обновляет changed
5. Перезапускается

---

## 🔑 Ключевые Файлы

| Файл | Назначение |
|------|------------|
| `starter.py` | Главный скрипт запуска |
| `files/configs/server_types.py` | **ТИПЫ СЕРВЕРОВ** (добавляй новые тут!) |
| `files/configs/starter_repos.py` | Репозитории для обновления |
| `files/core/utils/*.py` | Модули утилит |
| `files/core/oss/` | OS-специфичные модули |
| `.env` | Настройки стартера |

---

## 🚀 Быстрый Старт

### 1. Первый Запуск

```bash
cd C:\control\starter
python starter.py
```

### 2. Веб-интерфейс

Откроется автоматически: `https://localhost:PORT`

**Логин/пароль** → показаны в консоли при первом запуске!

### 3. Создание Проекта

```
1. Выбери тип сервера (client, tei, TTS, STT, BROWSER)
2. Введи название проекта
3. Настрой OAuth (myidon.site)
4. Загрузи VPN config.ovpn
5. Запусти Docker
```

---

## 📊 Взаимодействие с Проектами

### Starter → Проект

```
starter.py
    ↓ создаёт
code/ + docker/ + .env
    ↓ запускает
docker-compose up -d
    ↓ проект работает
```

### Проект → Starter

```
Проект использует:
- starter/files/core/* (модули)
- starter.py (обновление)
- server_types.py (тип сервера)
```

---

## 🎯 Для AI

### Как Понимать Starter

1. **Читай `starter.py`** → Главный поток
2. **Смотри `server_types.py`** → Типы серверов
3. **Изучай `files/core/utils/`** → Модули
4. **Проверяй `.env`** → Настройки

### Ключевые Переменные

```python
# Глобальные переменные (из globalVars_utils.py)
get_global('starter_path')      # Путь к стартеру
get_global('project_path')      # Путь к проекту
get_global('PORT')              # Порт веб-интерфейса
get_global('TYPE_SERVER')       # Тип сервера
get_global('WERKZEUG')          # Запущен ли Flask
```

---

## 📝 Планы Развития

- [ ] **Больше типов серверов** (YOLO, SLAM, WebSSH...)
- [ ] **GUI для управления** (Lenivec интеграция)
- [ ] **Авто-обновление проектов**
- [ ] **Мониторинг статуса проектов**
- [ ] **Экспорт/импорт конфигов**

---

*Документ создан для понимания Starter — главной программы!* 🐼  
*Версия: 1.0 | Дата: 2026-03-30*
