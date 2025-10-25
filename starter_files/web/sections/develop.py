import json
from pathlib import Path
from starter_files.core.utils.globalVars_utils import get_all_globals
from starter_files.core.utils.loader_utils import get, collect_modules_info
from starter_files.core.utils.log_utils import LogManager

this_section_in_control_panel = False
section_name = "Develop"
section_icon = "bi-terminal"
section_order = 999

# Документация проекта
DOCUMENTATION = {
    "overview": {
        "title": "Обзор проекта",
        "content": """
        <h3>Что такое Starter?</h3>
        <p><strong>Starter Ночной (Night Starter)</strong> - это универсальный инструмент для развертывания и управления проектами на различных операционных системах. Он предоставляет унифицированный интерфейс для работы с Docker, управления зависимостями и автоматизации процессов развертывания.</p>

        <div class="alert alert-danger">
            <strong>ВНИМАНИЕ!</strong> Это нестабильная ветка! Программа может снести вашу систему! Устанавливайте только если вы являетесь администратором или сотрудником проекта.
        </div>

        <h3>Основные возможности:</h3>
        <ul>
            <li>Кроссплатформенная поддержка (Linux, Windows, macOS)</li>
            <li>Автоматическое управление Docker-контейнерами</li>
            <li>Система модулей для разных ОС</li>
            <li>Веб-интерфейс для управления</li>
            <li>Система обновлений</li>
            <li>Интерактивная документация и руководства</li>
        </ul>

        <h3>Ссылки на дополнительную информацию:</h3>
        <ul>
            <li><a href="https://myidon.site/instruction/starter" target="_blank">Официальная инструкция</a></li>
            <li><a href="/readme.html" target="_blank">Локальная документация (readme.html)</a></li>
            <li><a href="/README.md" target="_blank">README проекта</a></li>
        </ul>
        """
    },
    "architecture": {
        "title": "Архитектура",
        "content": """
        <h3>Структура проекта:</h3>
        <pre><code>starter/
├── starter.py              # Главный скрипт запуска
├── starter_files/          # Основные файлы проекта
│   ├── core/              # Ядро системы
│   │   ├── oss/          # Модули для разных ОС
│   │   └── utils/        # Утилиты
│   └── web/              # Веб-интерфейс
│       ├── sections/     # Разделы веб-интерфейса
│       └── templates/    # HTML шаблоны
├── requirements/          # Зависимости для разных ОС
└── venv/                  # Виртуальное окружение</code></pre>

        <h3>Система модулей:</h3>
        <p>Проект использует иерархическую систему модулей с приоритетами:</p>
        <ol>
            <li><strong>Уровень 0:</strong> Специфичные для версии ОС модули (высший приоритет)</li>
            <li><strong>Уровень 1:</strong> Модули по умолчанию для ОС</li>
            <li><strong>Уровень 2:</strong> Глобальные модули (низший приоритет)</li>
        </ol>
        """
    },
    "api": {
        "title": "API документация",
        "content": """
        <h3>Веб-API</h3>
        <p>Starter предоставляет REST API для взаимодействия с системой:</p>

        <h4>Разделы (Sections):</h4>
        <ul>
            <li><code>develop</code> - Раздел разработчика</li>
            <li><code>docker</code> - Управление Docker</li>
            <li><code>firewall</code> - Настройки фаервола</li>
            <li><code>network</code> - Сетевое управление</li>
            <li><code>service</code> - Управление службой</li>
        </ul>

        <h4>Пример запроса:</h4>
        <pre><code>POST /
Content-Type: application/x-www-form-urlencoded

section=develop&action=globalVariables</code></pre>
        """
    },
    "deployment": {
        "title": "Развертывание",
        "content": """
        <h3>Первый запуск:</h3>
        <ol>
            <li>Установите Python 3.8+</li>
            <li>Запустите <code>python starter.py</code></li>
            <li>Следуйте инструкциям первичной настройки</li>
            <li>Откройте веб-интерфейс в браузере</li>
        </ol>

        <h3>Режимы работы:</h3>
        <ul>
            <li><strong>Интерактивный режим:</strong> <code>python starter.py</code></li>
            <li><strong>Сервисный режим:</strong> <code>python starter.py --service</code></li>
            <li><strong>Режим отладки:</strong> <code>python starter.py --debug</code></li>
        </ul>

        <h3>Дополнительная информация:</h3>
        <p>Подробную инструкцию по работе со starter.py можно найти в файле <a href="/readme.html" target="_blank">readme.html</a> в корневой директории проекта.</p>
        """
    },
    "faq": {
        "title": "Часто задаваемые вопросы",
        "content": """
        <h3>Общие вопросы:</h3>

        <h4>Почему не запускается Docker?</h4>
        <p>Убедитесь, что Docker установлен и запущен. Проверьте права доступа пользователя к Docker.</p>

        <h4>Как изменить порт веб-интерфейса?</h4>
        <p>Измените переменную <code>PORT</code> в файле <code>.env</code>.</p>

        <h4>Где находятся логи?</h4>
        <p>Логи сохраняются в директории <code>starter_files/logs/</code>.</p>

        <h4>Как обновить Starter?</h4>
        <p>Используйте раздел "Обновления" в веб-интерфейсе или запустите с флагом <code>--update</code>.</p>
        """
    }
}

def globalVariables(data, session):
    """Возвращает все глобальные переменные с обработкой специальных типов."""
    try:
        globals_data = get_all_globals()
        
        # Рекурсивно применяем сериализатор ко всем данным
        def serialize_data(data):
            if isinstance(data, (int, float, str, bool, type(None))):
                return data
            elif isinstance(data, Path):
                return str(data)
            elif isinstance(data, dict):
                return {k: serialize_data(v) for k, v in data.items()}
            elif isinstance(data, (list, tuple, set)):
                return [serialize_data(item) for item in data]
            elif hasattr(data, '__dict__'):
                return serialize_data(data.__dict__)
            elif callable(data):
                return f"<function {data.__name__}>"
            else:
                try:
                    return str(data)
                except:
                    return f"<{type(data).__name__} object>"
        
        serializable_data = serialize_data(globals_data)
        
        return {
            "status": "success",
            "data": serializable_data
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

def modules(data, session):
    """Возвращает информацию о модулях со всеми реализациями."""
    try:
        logger = LogManager.get_logger()
        logger.info("Starting modules collection")

        # Собираем информацию о модулях
        modules_data = collect_modules_info()
        logger.info(f"Received {len(modules_data)} raw module records")

        # Логируем первые 3 записи для диагностики
        for i, module in enumerate(modules_data[:3]):
            logger.info(f"Module #{i+1}: {module.get('module_name')} | "
                         f"Path: {module.get('path')} | "
                         f"OS: {module.get('os')} | "
                         f"Functions: {len(module.get('functions', []))}")

        # Группируем реализации по имени модуля
        grouped_modules = {}
        for module in modules_data:
            module_name = module["module_name"]

            if not module_name:
                logger.info("Skipping module with empty name")
                continue

            if module_name not in grouped_modules:
                logger.info(f"New module group: {module_name}")
                grouped_modules[module_name] = {
                    "module_name": module_name,
                    "implementations": []
                }

            grouped_modules[module_name]["implementations"].append(module)

        logger.info(f"Created {len(grouped_modules)} module groups")

        # Преобразуем в список и сортируем реализации
        result = []
        for module_name, module_data in grouped_modules.items():
            # Сортируем реализации по уровню приоритета (0 - высший)
            module_data["implementations"].sort(key=lambda x: x["level"])
            result.append(module_data)

            # Логируем информацию о реализациях
            impls = module_data["implementations"]
            logger.info(f"Module '{module_name}' has {len(impls)} implementations:")
            for i, impl in enumerate(impls):
                logger.info(f"  Impl #{i+1}: Level={impl['level']} | "
                             f"OS={impl.get('os')} | "
                             f"Path={impl.get('path')}")

        logger.info(f"Returning {len(result)} module groups")

        return {
            "status": "success",
            "data": result
        }

    except Exception as e:
        logger = LogManager.get_logger()
        logger.info("Critical error in modules endpoint")
        return {
            "status": "error",
            "message": f"{str(e)} (See server logs for details)"
        }

def documentation(data, session):
    """Возвращает документацию проекта."""
    try:
        doc_type = data.get('type', 'overview')

        if doc_type not in DOCUMENTATION:
            return {
                "status": "error",
                "message": f"Документация '{doc_type}' не найдена"
            }

        doc = DOCUMENTATION[doc_type]

        return {
            "status": "success",
            "data": {
                "type": doc_type,
                "title": doc["title"],
                "content": doc["content"]
            }
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Ошибка при получении документации: {str(e)}"
        }

def search_documentation(data, session):
    """Поиск по документации."""
    try:
        query = data.get('query', '').lower().strip()

        if not query:
            return {
                "status": "error",
                "message": "Не указан поисковый запрос"
            }

        results = []

        for doc_type, doc in DOCUMENTATION.items():
            title_lower = doc["title"].lower()
            content_lower = doc["content"].lower()

            if query in title_lower or query in content_lower:
                # Находим контекст вокруг найденного текста
                context = _extract_context(content_lower, query)

                results.append({
                    "type": doc_type,
                    "title": doc["title"],
                    "context": context,
                    "relevance": 1 if query in title_lower else 0.5
                })

        # Сортируем по релевантности
        results.sort(key=lambda x: x["relevance"], reverse=True)

        return {
            "status": "success",
            "data": {
                "query": query,
                "results": results,
                "total": len(results)
            }
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Ошибка при поиске: {str(e)}"
        }

def _extract_context(text, query, context_length=100):
    """Извлекает контекст вокруг найденного текста."""
    try:
        query_pos = text.find(query)
        if query_pos == -1:
            return text[:context_length] + "..."

        start = max(0, query_pos - context_length // 2)
        end = min(len(text), query_pos + len(query) + context_length // 2)

        context = text[start:end]
        if start > 0:
            context = "..." + context
        if end < len(text):
            context = context + "..."

        return context
    except:
        return text[:context_length] + "..."