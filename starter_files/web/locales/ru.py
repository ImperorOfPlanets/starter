translations = {
    # ==================== ОБЩИЕ ПЕРЕМЕННЫЕ ====================
    "common":{
        # Настройки языка
        "this_language": "Русский",
        "this_language_code": "ru",
        "this_language_select_text": "Выберите язык",

        # Текста выводимы при ошибка или отсутствии переводов
        "this_error_missing_common": "[{lang}] Отсутствует перевод: common['{key}']",
        "this_error_missing_module": "[{lang}] Отсутствует перевод: modules['{module}']['?']['{key}']",
        "this_error_invalid_module": "[{lang}] Некорректный модуль: modules['{module}'] не является словарём",
        "this_error_missing_main": "[{lang}] Отсутствует перевод: main['{section}']['{key}']",
        "this_error_missing_section": "[{lang}] Отсутствует раздел: main['{section}'] не существует",
        "this_error_invalid_key": "[{lang}] Некорректный ключ: '{key}' (ожидается section_key или module_file_key)"
    },

    # ==================== ПЕРЕМЕННЫЕ ОСНОВНОГО ШАБЛОНА (Файлы находящиеся в папке templates) ====================

    "main":{
        # ==================== ОСНОВНОЙ ФАЙЛ ШАБЛОНА ====================
        "layout":{
            "default_title": "Стартер", # Название проекта обозначающая часть автомобиля (при переводе находить аналог на нужном языке)
            "system_info": "Системная информация",
            "logout_button": "Выйти",
            "logout_error": "Ошибка при выходе из системы",
            "unauthorized_access": "Неавторизованный доступ. Пожалуйста, войдите снова.",
            "network_error": "Ошибка сети. Пожалуйста, проверьте подключение."
        },

        # ==================== Подвал ====================
        "footer":{
            "copyright": "© 2025 MyIDon.SITE. Все права защищены."
        },

        # ==================== АУТЕНТИФИКАЦИЯ ====================
        "login":{
            "username_label": "Имя пользователя",
            "password_label": "Пароль",
            "submit_button": "Войти",
            "network_error": "Ошибка сети. Пожалуйста, проверьте соединение.",
            "error_occurred": "Произошла ошибка",
            "missing_credentials": "Требуется имя пользователя и пароль",
            "invalid_credentials": "Неверные учетные данные",
            "auth_not_configured": "Система аутентификации не настроена"
        },

        # ==================== СМЕНА ЯЗЫКА ====================

        "changeLanguage":{
            "selector_label": "Выбор языка",
            "no_languages": "Нет доступных языков",
            "network_error": "Ошибка сети. Пожалуйста, проверьте соединение.",
            "change_failed": "Не удалось изменить язык",
            "unknown_error": "Произошла неизвестная ошибка",
            "language_changed": "Язык изменен успешно",
            "invalid_language": "Неверный язык",
        },

        # ==================== ОСНОВНАЯ ПАНЕЛЬ УПРАВЛЕНИЯ ====================
        "controlPanel":{
            "loading": "Загрузка...",
            "action_error": "Ошибка выполнения действия",
            "module_error": "Ошибка загрузки модуля",
            "parse_error": "Ошибка разбора данных",
            "status": "Статус",
            "error": "Ошибка",
        }
    },

    # ==================== ПЕРЕМЕННЫЕ МОДУЛЕЙ (Файлы находящиеся в папке templates/modules) ====================

    "modules":{

        # ==================== DASHBOARD ====================
        'dashboard': {
            # Базовые настройки модуля
            'basic':{
                # Отображаемое в панели управления
                'title':"Система",
                "description": "Основная информационная панель"
            },

            'index': {
                "dashboard": "Информационные панели",
                "system_info": "Системная информация",
                "system": "Система",
                "hostname": "Имя хоста",
                "os": "Операционная система",
                "os_version": "Версия ОС",
                "python_version": "Версия Python",
                "implementation": "Реализация",
                "current_time": "Текущее время",
                "uptime": "Время работы",
                "system_uptime": "Время работы системы",
                "version": "Версия",
                "refresh": "Обновить",
                "username": "Имя пользователя",
                "disk": "Диск",
                "total": "Всего",
                "used": "Использовано",
                "free": "Свободно",
                "docker_info": "Информация о Docker",
                "docker_status": "Статус Docker",
                "docker_compose_status": "Статус Docker Compose",
                "installed": "Установлен",
                "not_installed": "Не установлен",
                "registry_auth": "Аутентификация в реестре",
                "authenticated": "Аутентифицирован",
                "not_authenticated": "Не аутентифицирован",
                "registry_url": "URL реестра",
                "network_info": "Сетевая информация",
                "no_ips_found": "IP-адреса не найдены",
                'corporate': 'Corporate',
                'other': 'Other',
                'disabled': 'Disabled',
                'active': 'Active',
                'inactive': 'Inactive',
                'ip_address': 'IP Address',
                'netmask': 'Netmask',
                'mac_address': 'MAC Address',
                'status': 'Status',
                'external': 'External',
                'default_gateway': 'Default Gateway',
                'no_network_interfaces': 'No network interfaces found',
                "cpu": "Процессор",
                "processor": "Модель",
                "cores": "Ядра",
                "logical": "потоков",
                "usage": "Загрузка",
                "memory": "Память",
                "total": "Всего",
                "used": "Использовано",
                "available": "Доступно"
            }
        },

        # ==================== DOCKER ====================
        'docker':{

            "basic": {
                "title": "Docker",
                "description": "Управление контейнерами"
            },

            'info': {
                "docker_info": "Информация о Docker",
                "docker_status": "Статус Docker",
                "docker_compose_status": "Статус Docker Compose",
                "registry_auth": "Аутентификация в реестре",
                "registry_url": "URL реестра",
                "installed": "Установлен",
                "not_installed": "Не установлен",
                "authenticated": "Аутентифицирован",
                "not_authenticated": "Не аутентифицирован",
                "docker_restarted_successfully": "Docker успешно перезапущен",
                "failed_to_restart_docker": "Не удалось перезапустить Docker",
                "system_pruned_successfully": "Система Docker успешно очищена",
                "failed_to_prune_system": "Не удалось очистить систему Docker",
                "docker_dashboard": "Docker Панель",
                "refresh": "Обновить",
                "docker_version": "Версия Docker",
                "last_updated": "Последнее обновление",
                "containers": "Контейнеры",
                "total": "Всего",
                "running": "Запущено",
                "stopped": "Остановлено",
                "images": "Образы",
                "total_images": "Всего образов",
                "disk_usage": "Использование диска",
                "resources": "Ресурсы",
                "cpu_usage": "Использование CPU",
                "memory_usage": "Использование памяти",
                "docker_compose": "Docker Compose",
                "projects": "Проекты",
                "services": "Сервисы",
                "quick_actions": "Быстрые действия",
                "restart_docker": "Перезапустить Docker",
                "prune_system": "Очистить систему",
                "confirm_restart_docker": "Вы уверены, что хотите перезапустить Docker? Это может остановить все работающие контейнеры.",
                "confirm_prune_system": "Вы уверены, что хотите очистить систему Docker? Это удалит все неиспользуемые контейнеры, сети, образы и тома.",
                "request_failed": "Не удалось выполнить запрос"
            },

            'containers': {
                "containers": "Контейнеры",
                "refresh": "Обновить",
                "show_all": "Показать все",
                "name": "Имя",
                "image": "Образ",
                "status": "Статус",
                "ports": "Порты",
                "running_for": "Работает",
                "size": "Размер",
                "actions": "Действия",
                "stop": "Остановить",
                "restart": "Перезапустить",
                "start": "Запустить",
                "remove": "Удалить",
                "view_logs": "Просмотр логов",
                "no_containers_found": "Контейнеры не найдены",
                "confirm_remove_container": "Вы уверены, что хотите удалить контейнер?",
                "request_failed": "Не удалось выполнить запрос"
            },

            'volumes': {
                "volumes": "Тома",
                "refresh": "Обновить",
                "name": "Имя",
                "driver": "Драйвер",
                "scope": "Область",
                "mountpoint": "Точка монтирования",
                "labels": "Метки",
                "created": "Создан",
                "no_volumes_found": "Тома не найдены"
            },

            'networks': {
                "networks": "Сети",
                "refresh": "Обновить",
                "name": "Имя",
                "driver": "Драйвер",
                "scope": "Область",
                "ipv6": "IPv6",
                "internal": "Внутренняя",
                "created": "Создана",
                "no_networks_found": "Сети не найдены"
            },

            'logs': {
                "logs": "Логи",
                "select_container": "Выберите контейнер",
                "refresh": "Обновить",
                "logs_for_container": "Логи контейнера",
                "select_container_to_view_logs": "Выберите контейнер для просмотра логов"
            },

            'images': {
                "images": "Образы",
                "refresh": "Обновить",
                "repository": "Репозиторий",
                "tag": "Тег",
                "image_id": "ID образа",
                "created": "Создан",
                "size": "Размер",
                "actions": "Действия",
                "remove": "Удалить",
                "no_images_found": "Образы не найдены",
                "confirm_remove_image": "Вы уверены, что хотите удалить этот образ?",
                "request_failed": "Не удалось выполнить запрос"
            }
        },

        # ==================== Port Knocking ====================
        'knocking':{

            'title':"Port Knocking",

            "index": {
                "knocking_title": "Port Knocking",
                "knocking_status": "Статус",
                "knocking_ports": "Последовательность портов", 
                "knocking_timeout": "Таймаут",
                "knocking_description": "Метод открытия портов через последовательность подключений",
                "knocking_how_it_works": "Как это работает",
                "knocking_step1": "1. Настройте последовательность портов",
                "knocking_step2": "2. Подключитесь к портам по очереди",
                "knocking_step3": "3. Нужный порт откроется автоматически",
                "active": "Активен",
                "inactive": "Неактивен", 
                "seconds": "сек.",
                "refresh": "Обновить",
                "start_service": "Запустить сервис",
                "stop_service": "Остановить сервис",
                "service_started": "Сервис запущен",
                "service_stopped": "Сервис остановлен",
                "install":"Установить",
                "knocking_not_installed": "Port Knocking не установлен",
                "knocking_install_instructions": "Нажмите кнопку ниже для установки службы Port Knocking",
                "knocking_already_installed": "Port Knocking уже установлен",
                "knocking_install_success": "Port Knocking успешно установлен",
                "knocking_install_failed": "Не удалось установить Port Knocking",
                "knocking_install_error": "Ошибка во время установки",
            },

            "info": {
                "title": "Информация о Port Knocking",
                "about": "О технологии",
                "what_is": "Что это?",
                "definition": "Техника безопасности для скрытого открытия портов",
                "benefits": "Преимущества",
                "benefit1": "Дополнительный уровень защиты",
                "benefit2": "Скрытие от сканеров портов", 
                "benefit3": "Динамическое управление доступом",
                "limitations": "Ограничения",
                "limit1": "Требует клиентской настройки",
                "limit2": "Возможны replay-атаки",
                "limit3": "Сложность настройки",
                "current_config": "Текущие настройки",
                "configure_btn": "Настроить",
                "active_status": "Активен",
                "inactive_status": "Выключен"
            },

            "settings": {
                "title": "Настройки Port Knocking",
                "configuration": "Конфигурация",
                "ports_label": "Порты",
                "ports_help": "Через запятую (напр. 1000,2000,3000)",
                "timeout_label": "Таймаут (сек)",
                "timeout_help": "Интервал между попытками (1-10 сек)",
                "test_section": "Проверка работы",
                "test_description": "Тестирование последовательности портов",
                "test_button": "Проверить",
                "min_ports": "Нужно минимум 2 порта",
                "invalid_timeout": "Допустимо 1-10 секунд",
                "save_btn": "Сохранить",
                "save_success": "Настройки сохранены",
                "save_error": "Ошибка сохранения"
            }
        },

        # ==================== Logs ====================
        "logs": {
            "basic": {
                "title": "Логи",
                "description": "Просмотр и управление системными логами"
            },
            "index": {
                "logs_title": "Логи системы",
                "refresh": "Обновить",
                "logs_types": "Типы логов",
                "logs_info": "Информация о логах",
                "logs_about": "О системных логах",
                "logs_description": "Здесь вы можете просматривать и анализировать логи системы, приложений и служб.",
                "logs_how_to_use": "Как использовать:",
                "logs_step1": "Выберите тип логов из списка слева",
                "logs_step2": "Выберите конкретный файл логов",
                "logs_step3": "Используйте фильтры для поиска нужных записей"
            },
            "view": {
                "download": "Скачать",
                "logs_files": "Файлы логов",
                "logs_no_files": "Нет доступных файлов логов",
                "logs_filters": "Фильтры логов",
                "logs_level": "Уровень логов",
                "all_levels": "Все уровни",
                "log_levels": {
                    "DEBUG": "Отладка",
                    "INFO": "Информация",
                    "WARNING": "Предупреждение",
                    "ERROR": "Ошибка",
                    "CRITICAL": "Критическая"
                },
                "logs_source": "Источник",
                "logs_source_placeholder": "Имя модуля или службы",
                "logs_search": "Поиск",
                "logs_search_placeholder": "Текст для поиска в логах",
                "apply_filters": "Применить фильтры",
                "logs_no_file_selected": "Файл не выбран",
                "logs_top": "В начало",
                "logs_bottom": "В конец",
                "logs_time": "Время",
                "logs_message": "Сообщение",
                "logs_no_entries": "Нет записей в логах",
                "logs_entries_shown": "записей показано"
            }
        },

        # ==================== NETWORK ====================
        'network': {
            'basic': {
                'title': 'Сетевые подключения',
                'description': 'Управление сетевыми интерфейсами'
            }
        },

        # ==================== VPN ====================
        'vpn': {
            'basic': {
                'title': 'Подключения и клиенты VPN',
                'description': 'Управление VPN'
            },

            "index": {
                "vpn_title": "VPN (SoftEther)",
                "refresh": "Обновить",
                "vpn_status": "Статус VPN",
                "details": "Подробности",
                "vpn_installed": "Установлен",
                "yes": "Да",
                "no": "Нет",
                "vpn_version": "Версия",
                "vpn_connected": "Подключен",
                "vpn_quick_actions": "Быстрые действия",
                "vpn_disconnect": "Отключиться",
                "vpn_connect": "Подключиться",
                "vpn_restart": "Перезапустить",
                "vpn_not_installed": "SoftEther VPN не установлен",
                "vpn_install_instructions": "Для использования VPN необходимо установить SoftEther VPN Client",
                "vpn_download": "Скачать SoftEther",
                "vpn_info_title": "Информация о VPN",
                "vpn_technical_info": "Техническая информация",
                "vpn_os": "Операционная система",
                "vpn_installation_details": "Инструкции по установке",
                "vpn_windows_instructions": "1. Скачайте и установите SoftEther VPN Client для Windows\n2. Запустите программу и настройте подключение",
                "vpn_linux_instructions": "1. Установите пакет softether-vpnclient через ваш менеджер пакетов\n2. Настройте подключение в терминале",
                "vpn_mac_instructions": "1. Скачайте и установите SoftEther VPN Client для macOS\n2. Настройте подключение в программе",
                "vpn_management": "Управление VPN",
                "vpn_configure": "Настроить",
                "vpn_uninstall": "Удалить",
                "vpn_not_installed_instructions": "Для управления VPN необходимо сначала установить клиент"
            }
        },

        # ==================== UPDATES ====================
        'updates': {
            'basic': {
                'title': 'Обновления',
                'description': 'Информация об обновления'
            }
        },
   
        # ==================== SERVICE ====================
        'service': {
            'basic': {
                'title': 'Сервисная служба СТАРТЕР',
                'description': 'Информация о службе "СТАРТЕР"'
            }
        },
    }
}