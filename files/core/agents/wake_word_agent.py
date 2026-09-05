"""
WakeWordAgent — Агент для работы с сервером обнаружения имён

Проверяет установлен ли сервер wake_word,
предоставляет подсказки и управление через веб-интерфейс.
"""
import json
import logging
from pathlib import Path
from typing import Optional, Dict

logger = logging.getLogger('starter.wake_word_agent')


class WakeWordAgent:
    """Агент для взаимодействия с сервером wake_word"""

    def __init__(self):
        self.server_url = "http://localhost:8010"
        self.server_type = "wake_word"

    def is_server_installed(self) -> bool:
        """Проверяет, установлен ли сервер wake_word"""
        try:
            import requests
            resp = requests.get(f"{self.server_url}/api/health", timeout=2)
            return resp.status_code == 200
        except Exception:
            return False

    def get_install_hints(self) -> str:
        """Возвращает подсказки по установке сервера wake_word"""
        return """
🎯 Сервер Wake Word не установлен!

Для установки:
1. Откройте Starter (https://localhost:2000)
2. Перейдите в "Установка серверов"
3. Выберите тип: "Обнаружение имён" (wake_word)
4. Нажмите "Установить"

Или через консоль:
  cd C:\\control\\wake_word
  docker-compose up -d

После установки веб-интерфейс будет доступен:
  http://localhost:8010
"""

    def get_status(self) -> Dict:
        """Получает статус сервера wake_word"""
        if not self.is_server_installed():
            return {
                "installed": False,
                "status": "not_installed",
                "message": "Сервер не установлен",
            }

        try:
            import requests
            resp = requests.get(f"{self.server_url}/api/health", timeout=5)
            data = resp.json()

            return {
                "installed": True,
                "status": "running",
                "models_count": data.get("models_count", 0),
                "message": "Сервер работает",
            }
        except Exception as e:
            return {
                "installed": True,
                "status": "error",
                "message": f"Ошибка подключения: {e}",
            }

    def get_wake_words(self) -> list:
        """Получает список wake words с сервера"""
        if not self.is_server_installed():
            return []

        try:
            import requests
            resp = requests.get(f"{self.server_url}/api/wake-words", timeout=5)
            data = resp.json()
            return data.get("wake_words", [])
        except Exception:
            return []

    def get_models(self) -> list:
        """Получает список обученных моделей"""
        if not self.is_server_installed():
            return []

        try:
            import requests
            resp = requests.get(f"{self.server_url}/api/models", timeout=5)
            data = resp.json()
            return data.get("models", [])
        except Exception:
            return []

    def get_stats(self) -> Dict:
        """Получает статистику"""
        if not self.is_server_installed():
            return {"installed": False}

        try:
            import requests
            resp = requests.get(f"{self.server_url}/api/stats", timeout=5)
            return resp.json()
        except Exception:
            return {}

    def get_usage_guide(self) -> str:
        """Возвращает руководство по использованию"""
        status = self.get_status()

        if not status.get("installed"):
            return self.get_install_hints()

        wake_words = self.get_wake_words()
        models = self.get_models()

        guide = "🎤 **Wake Word Server — Руководство**\n\n"

        guide += f"📊 Статус: {status.get('message', 'Н/д')}\n"
        guide += f"🏷️ Wake words: {len(wake_words)}\n"
        guide += f"📦 Моделей: {len(models)}\n\n"

        if not wake_words:
            guide += "**Добавьте wake word:**\n"
            guide += "1. Откройте http://localhost:8010\n"
            guide += "2. Введите имя или фразу\n"
            guide += "3. Нажмите 'Добавить'\n\n"

        if wake_words and not models:
            guide += "**Обучите модель:**\n"
            guide += "1. Запишите сэмплы (5-10 на каждый wake word)\n"
            guide += "2. Нажмите 'Начать обучение'\n"
            guide += "3. Скачайте обученную модель\n\n"

        if models:
            guide += "**Обученные модели:**\n"
            for m in models:
                ww = ", ".join(m.get("wake_words", []))
                acc = m.get("accuracy", 0) * 100
                guide += f"  • {m['id']}: {ww} ({acc:.1f}%)\n"

        guide += "\n**Интеграция с другими серверами:**\n"
        guide += "После обучения модель можно загрузить в любой сервер\n"
        guide += "для обнаружения wake words в реальном времени.\n"

        return guide

    def handle_command(self, text: str) -> Optional[str]:
        """Обработка команд, связанных с wake word"""
        text_lower = text.lower().strip()

        if any(kw in text_lower for kw in ["wake word", "wake-word", "имя для ассистента", "обнаружение имени"]):
            return self.get_usage_guide()

        if any(kw in text_lower for kw in ["статус wake", "status wake", "wake word сервер"]):
            status = self.get_status()
            if status.get("installed"):
                return f"🎤 Wake Word Server: {status.get('message', 'Н/д')}\nМоделей: {status.get('models_count', 0)}"
            else:
                return "🎤 Wake Word Server не установлен.\n" + self.get_install_hints()

        if any(kw in text_lower for kw in ["обучить wake", "train wake", "обучение wake"]):
            if not self.is_server_installed():
                return self.get_install_hints()
            return "Для обучения перейдите на http://localhost:8010\nИли скажите 'обучить wake word' в чате сервера."

        return None
