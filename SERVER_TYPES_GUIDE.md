# 🖥️ Типы Серверов Imperor

> Из `starter/files/configs/server_types.py`

---

## 📋 Все Типы (11 штук)

| Тип | Название | Описание | Репозиторий |
|-----|----------|----------|-------------|
| **core** | 🎯 Core Server | Центральный сервер бота (Laravel + микросервисы) | imperor/core.git |
| **client** | 💼 Client Server | Веб-сервер клиентской части (Laravel) | imperor/client.git |
| **tei** | 📊 Text Embeddings | Векторные представления текста | imperor/api-server.git |
| **TTS** | 🔊 Text-to-Speech | Синтез речи (CosyVoice) | imperor/tts-server.git |
| **STT** | 🎤 Speech-to-Text | Распознавание речи (Vosk, SpeechBrain) | imperor/stt-server.git |
| **BROWSER** | 🌐 Browser Automation | Автоматизация браузера (Selenium) | imperor/browser-server.git |
| **SLAM** | 🚁 SLAM Server | ORB-SLAM3 для дронов | imperor/slam-server.git |
| **YOLO** | 👁️ YOLO Detector | Детекция объектов | imperor/yolo-server.git |
| **WEBSSH** | 🔑 WebSSH | Веб-SSH сервер (Node.js) | imperor/webssh-server.git |
| **SFERA** | 🛰️ Sfera Simulator | Симулятор дронов (AirSim, Gazebo) | imperor/sfera-server.git |
| **VOICE** | 🎙️ Voice Server | Обработка голоса (STT + TTS + Cloning) | imperor/voice-server.git |

---

## 🎯 Как Использовать

### 1. При Запуске Starter

```bash
cd C:\control\starter
python starter.py
```

Веб-интерфейс покажет **все доступные типы** из `server_types.py`

### 2. Выбрать Тип

```
┌─────────────────────────────────────┐
│  Выбор типа сервера:                │
│  ○ core       — Центральный сервер  │
│  ○ client     — Клиентский сервер   │
│  ○ tei        — Векторизация текста │
│  ○ TTS        — Синтез речи         │
│  ○ STT        — Распознавание речи  │
│  ○ BROWSER    — Браузер-автоматизация│
│  ○ SLAM       — SLAM для дронов     │
│  ○ YOLO       — Детекция объектов   │
│  ○ WEBSSH     — Веб-SSH             │
│  ○ SFERA      — Симулятор дронов    │
│  ○ VOICE      — Обработка голоса    │
└─────────────────────────────────────┘
```

### 3. Starter Скачивает Код

```
starter.py → GitFlic → code/ + docker/ → docker-compose up -d
```

---

## 🔧 Как Добавить Новый Тип

### Шаг 1: Открой `server_types.py`

```python
# C:\control\starter\files\configs\server_types.py
```

### Шаг 2: Добавь Тип

```python
'NEW_TYPE': {
    'name': 'New Server Name',
    'description': 'Описание назначения сервера',
    'repositories': [
        {
            'name': 'main',
            'url': 'https://gitflic.ru/project/imperor/new-server.git',
            'branch': 'master',
            'targets_config': 'targets.json'
        }
    ]
}
```

### Шаг 3: Перезапусти Starter

```bash
python starter.py
```

Новый тип появится в веб-интерфейсе!

---

## 📊 Взаимосвязи Типов

```
                    ┌─────────────┐
                    │    core     │
                    │  (монолит)  │
                    └──────┬──────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
    ┌────▼────┐      ┌────▼────┐      ┌────▼────┐
    │  STT    │      │  TTS    │      │ BROWSER │
    │(распозн.)│     │(синтез) │      │(selenium)
    └─────────┘      └─────────┘      └─────────┘
         │                                   │
    ┌────▼────┐      ┌───────────────────────▼────┐
    │   TEI   │      │    client (веб-интерфейс)  │
    │(vectors)│      │    ← пользователь работает │
    └─────────┘      └────────────────────────────┘

┌──────────────────────────────────────────────────┐
│  Специализированные:                              │
│  - SLAM (дроны)                                   │
│  - YOLO (детекция)                                │
│  - WEBSSH (удалённый доступ)                      │
│  - SFERA (симулятор)                              │
│  - VOICE (комбайн STT+TTS)                        │
└──────────────────────────────────────────────────┘
```

---

## 🐳 Docker Сервисы по Типам

### core / client (Laravel)
```yaml
- nginx    (80/443)
- php      (9000)
- mariadb  (3306)
- redis    (6379)
- qdrant   (6333)
- reverb   (8443)
- vpn      (туннель)
```

### STT / VOICE
```yaml
- voice    (5000)
- vosk     (модель)
- speechbrain (модель)
```

### TTS
```yaml
- tts      (5001)
- cosyvoice (модель)
```

### BROWSER
```yaml
- browser  (5002)
- selenium (Chrome)
```

### YOLO
```yaml
- yolo     (5003)
- detector (CUDA)
```

### SLAM
```yaml
- slam     (5004)
- orb-slam3 (ROS)
```

### WEBSSH
```yaml
- webssh   (2222)
- node.js  (3000)
```

### SFERA
```yaml
- sfera    (5005)
- airsim   (симулятор)
- gazebo   (симулятор)
- msp-bridge (протокол)
```

---

## 📝 Заметки

1. **core** — самый сложный, включает ВСЕ микросервисы
2. **client** — только Laravel (веб-интерфейс)
3. **STT/TTS/VOICE** — могут работать отдельно или с core
4. **BROWSER/SLAM/YOLO** — специализированные сервисы
5. **WEBSSH** — утилита для доступа
6. **SFERA** — симулятор (требует GPU)

---

*Шпаргалка по типам серверов для быстрого выбора!* 🐼  
*Версия: 1.0 | Дата: 2026-03-30*
