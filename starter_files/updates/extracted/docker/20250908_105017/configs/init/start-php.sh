#!/bin/bash

# Настройка логов
LOG_FILE="/var/log/php/init.log"
mkdir -p /var/log/php
touch "$LOG_FILE"
chown www-data:www-data "$LOG_FILE"

# Функция логирования
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "Очистка кэша с временной конфигурацией..."

php artisan cache:clear

log "=== Запуск инициализации проекта ==="
# Проверяем режим работы
MODE=${INIT_MODE:-"full"}
log "Режим работы: $MODE"

# ------- ПРОВЕРКА НА DEFAULT ------ #
if [ "$MODE" == "default" ]; then
    # -------------------------------------- Копирование файлов
    if [ -z "$(ls -A /var/www/html)" ]; then
        log "=== Этап копирования файлов ==="
        
        log "Копирование базовых файлов проекта..."
        cp -ra /var/www/html.dist/{.,}* /var/www/html/

        if [ -n "$DIR_COPY" ] && [ -d "/var/www/html.copy" ]; then
            log "Добавление кастомных файлов из $DIR_COPY..."
            rsync -a --ignore-existing /var/www/html.copy/ /var/www/html/
    
        fi
    fi
fi

# -------------------------------------- Создание структуры каталогов и настройка прав

log "=== Создание структуры каталогов и настройка прав ==="
# Создаем структуру каталогов
DIRS=(
    "/var/www/html/storage/framework/cache"
    "/var/www/html/storage/framework/sessions"
    "/var/www/html/storage/framework/views"
    "/var/www/html/storage/logs"
    "/var/www/html/bootstrap/cache"
)

for dir in "${DIRS[@]}"; do
    mkdir -p "$dir"
    log "Создана директория: $dir"
done

# Выставляем права
chown -R www-data:www-data /var/www/html/storage
chown -R www-data:www-data /var/www/html/bootstrap/cache

find /var/www/html/storage -type d -exec chmod 775 {} \;
find /var/www/html/storage -type f -exec chmod 664 {} \;
find /var/www/html/bootstrap/cache -type d -exec chmod 775 {} \;
find /var/www/html/bootstrap/cache -type f -exec chmod 664 {} \;

log "Проверка прав:"
ls -ld /var/www/html/storage >> "$LOG_FILE"
ls -l /var/www/html/storage/framework >> "$LOG_FILE"
# -------------------------------------- Настройка .env
ENV_FILE="/var/www/html/.env"
[ ! -f "$ENV_FILE" ] && cp "$ENV_FILE.example" "$ENV_FILE"

# Парсим текущий APP_KEY
APP_KEY=$(grep -E '^APP_KEY=' "$ENV_FILE" | cut -d '=' -f2)
# Если APP_KEY пустой - генерируем новый
if [ -z "$APP_KEY" ]; then
    log "Генерация нового APP_KEY..."
    NEW_APP_KEY="base64:$(openssl rand -base64 32)"
    export APP_KEY="$NEW_APP_KEY" # Экспортируем в переменные окружения
    log "Сгенерирован APP_KEY: $NEW_APP_KEY"
else
    log "Обнаружен существующий APP_KEY: $APP_KEY"
    export APP_KEY  # Используем существующий ключ
fi

trap 'rm -f "$ENV_FILE.tmp"' EXIT

declare -A ENV_VARS=(
    ["APP_ENV"]="${APP_ENV:-production}"
    ["APP_KEY"]="${APP_KEY}"
    ["APP_DEBUG"]="${APP_DEBUG:-false}"
    ["APP_URL"]="${APP_URL:-http://localhost}"
    ["APP_LOCALE"]="${APP_LOCALE:-ru}"
    ["DB_CONNECTION"]="${DB_CONNECTION:-mysql}"
    ["DB_HOST"]="${DB_HOST:-db}"
    ["DB_PORT"]="${DB_PORT:-3306}"
    ["DB_DATABASE"]="${DB_DATABASE:-laravel}"
    ["DB_USERNAME"]="${DB_USERNAME:-root}"
    ["DB_PASSWORD"]="${DB_PASSWORD:-}"
    ["CACHE_STORE"]="${CACHE_STORE:-redis}"
    ["QUEUE_CONNECTION"]="${QUEUE_CONNECTION:-redis}"
    ["OAUTH_REDIRECT_URI"]="${OAUTH_REDIRECT_URI:-${APP_URL}/auth/callback}"
    ["OAUTH_CLIENT_ID"]="${OAUTH_CLIENT_ID:-}"
    ["OAUTH_SECRET"]="${OAUTH_SECRET:-}"
)

# Добавляем переменные REVERB, если включены
if [[ ",${ENABLED_SERVICES}," =~ ",REVERB," ]]; then
    declare -A REVERB_VARS=(
        ["REVERB_APP_ID"]="${REVERB_APP_ID:-$(openssl rand -hex 10)}"
        ["REVERB_APP_KEY"]="${REVERB_APP_KEY:-$(openssl rand -hex 16)}"
        ["REVERB_APP_SECRET"]="${REVERB_APP_SECRET:-$(openssl rand -hex 32)}"
        ["REVERB_HOST"]="${REVERB_HOST:-0.0.0.0}"
        ["REVERB_PORT"]="${REVERB_HOST:-443}"
        ["REVERB_SCHEME"]="${REVERB_SCHEME:-https}"
        ["REVERB_APP_MAX_MESSAGE_SIZE"]="${REVERB_APP_MAX_MESSAGE_SIZE:-1048576}"
        ["VITE_REVERB_APP_KEY"]="${REVERB_APP_KEY:-}"
        ["VITE_REVERB_HOST"]="${REVERB_HOST:-}"
        ["VITE_REVERB_PORT"]="${REVERB_PORT:-}"
        ["VITE_REVERB_SCHEME"]="${REVERB_SCHEME:-}"
    )
    for key in "${!REVERB_VARS[@]}"; do
        ENV_VARS["$key"]="${REVERB_VARS[$key]}"
    done
fi

ENV_VARS_STR=$(for key in "${!ENV_VARS[@]}"; do echo "$key=${ENV_VARS[$key]}"; done)

awk -v env_vars_str="$ENV_VARS_STR" '
BEGIN {
    split(env_vars_str, lines, "\n");
    for (i in lines) {
        split(lines[i], parts, "=");
        key = parts[1];
        val = substr(lines[i], length(key)+2);
        vars[key] = val;
    }
}

{
    processed = 0;
    
    # Check for active variables
    if ($0 ~ /^[[:blank:]]*[^#]/) {
        line = $0;
        sub(/^[[:blank:]]+/, "", line);
        split(line, parts, "=");
        key = parts[1];
        sub(/[[:blank:]].*/, "", key);
        if (key in vars) {
            print key "=" vars[key];
            delete vars[key];
            processed = 1;
        }
    }
    
    # Check for commented variables
    if (!processed && $0 ~ /^[[:blank:]]*#/) {
        line = $0;
        sub(/^[[:blank:]]*#+[[:blank:]]*/, "", line);
        split(line, parts, "=");
        key = parts[1];
        sub(/[[:blank:]].*/, "", key);
        if (key in vars) {
            print key "=" vars[key];
            delete vars[key];
            processed = 1;
        }
    }
    
    if (!processed) print $0;
}

END {
    if (length(vars) > 0) {
        print "\n# ДОБАВЛЕНО СКРИПТОМ";
        for (k in vars) {
            print k "=" vars[k] | "sort";
        }
        close("sort");
    }
}
' "$ENV_FILE.example" > "$ENV_FILE.tmp" && mv "$ENV_FILE.tmp" "$ENV_FILE"


# Выставляем права
chown -R www-data:www-data /var/www/html

# -------------------------------------- Проверка подключения к БД
log "=== Проверка подключения к БД ==="
log "Параметры подключения:"
log "Хост: $DB_HOST"
log "Порт: $DB_PORT"
log "Пользователь: $DB_USERNAME"
log "База данных: $DB_DATABASE"
log "Длина пароля: ${#DB_PASSWORD} символов"

check_db() {
    local max_attempts=3
    local attempt=0
    local delay=2
    
    log "Начало проверки подключения к БД (попыток: $max_attempts)"
    
    while [ $attempt -lt $max_attempts ]; do
        # 1. Проверка TCP подключения
        log "Попытка $((attempt+1)): Проверка порта $DB_HOST:$DB_PORT..."
        if timeout 2 bash -c "</dev/tcp/${DB_HOST}/${DB_PORT}" 2>/dev/null; then
            log "Порт доступен"
        else
            log "❌ Ошибка: порт $DB_PORT на $DB_HOST недоступен"
            sleep $delay
            ((attempt++))
            continue
        fi

        # 2. Проверка через mysql client
        log "Проверка через mysql client..."
        if mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USERNAME" -p"$DB_PASSWORD" -e "SELECT 1" 2>>"$LOG_FILE"; then
            log "Успешное подключение через mysql client"
        else
            log "❌ Ошибка mysql client:"
            mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USERNAME" -p"$DB_PASSWORD" -e "SELECT 1" 2>&1 | tee -a "$LOG_FILE"
            sleep $delay
            ((attempt++))
            continue
        fi

        # 3. Проверка через PDO
        log "Проверка через PHP PDO..."
        if php -r '
        try {
            $pdo = new PDO(
                "mysql:host=".getenv("DB_HOST").";port=".getenv("DB_PORT"),
                getenv("DB_USERNAME"),
                getenv("DB_PASSWORD"),
                [PDO::ATTR_TIMEOUT => 2]
            );
            exit(0);
        } catch (PDOException $e) {
            file_put_contents("php://stderr", "PDO ERROR: ".$e->getMessage().PHP_EOL);
            exit(1);
        }
        ' 2>>"$LOG_FILE"; then
            log "✅ Все проверки подключения пройдены успешно!"
            return 0
        else
            log "❌ Ошибка PDO подключения"
            sleep $delay
            ((attempt++))
            continue
        fi
    done
    
    log "🛑 Не удалось подключиться к БД после $max_attempts попыток"
    return 1
}

# Вызываем с проверкой результата
if ! check_db; then
    log "Критическая ошибка: не удалось подключиться к БД"
    exit 1
fi

# ------- ПРОВЕРКА НА DEFAULT ------ #
if [ "$MODE" == "default" ]; then
    # -------------------------------------- Дополнительные сервисы
    if [[ ",${ENABLED_SERVICES}," =~ ",REVERB," ]]; then
        log "Настройка Reverb..."

        # Проверяем установлен ли уже пакет
        if ! composer show laravel/reverb >/dev/null 2>&1; then
            composer require laravel/reverb --no-interaction
            php artisan reverb:install -q
        else
            log "laravel/reverb уже установлен, пропускаем установку"
        fi
    fi

    # -------------------------------------- Установка зависимостей

    log "=== Этап установки зависимостей ==="
                # -------------------------------------- PHP
    log "Установка PHP зависимостей..."
    composer install --no-interaction --optimize-autoloader

    # Проверка и установка отдельных Composer-пакетов
    declare -A COMPOSER_PACKAGES=(
        ["symfony/mailer"]=""
        ["vkcom/vk-php-sdk"]=""
        ["laravel/telescope"]=""
        ["phpseclib/phpseclib"]=""
        ["longman/telegram-bot"]=""
        ["intervention/image"]=""
    )

    for package in "${!COMPOSER_PACKAGES[@]}"; do
        version=${COMPOSER_PACKAGES[$package]}
        log "Проверка пакета $package..."
        if ! composer show "$package" > /dev/null 2>&1; then
            log "Установка $package..."
            if [ -n "$version" ]; then
                composer require "$package:$version" --no-interaction
            else
                composer require "$package" --no-interaction
            fi
        else
            log "$package уже установлен"
        fi
    done
                # -------------------------------------- NPM
    log "Установка основных NPM пакетов..."
    # Добавляем проверку node_modules
    if [ ! -d "node_modules" ]; then
        log "Папка node_modules отсутствует, выполняется npm install..."
        npm install --quiet
        log "Обновление npm до v11.3.0..."
    else
        log "Папка node_modules уже существует, пропускаем npm install"
    fi

    # Умное обновление npm
    log "▸ Проверяем версию npm..."
    current_npm=$(npm -v)
    required_npm="11.3.0"

    if [[ "$current_npm" != "$required_npm" ]]; then
        log "Обновляем npm v$current_npm → v$required_npm..."
        npm install -g npm@$required_npm --quiet 2> /dev/null
        log "✓ Версия npm успешно обновлена"
    else
        log "✓ Текущая версия npm ($required_npm) актуальна"
    fi

    declare -A NPM_PACKAGES=(
        ["bootstrap"]="^5.3.3"
        ["@popperjs/core"]="^2.11.8"
        ["three"]="^0.164.1"
        ["pusher-js"]="^8.4.0"
    )

    for package in "${!NPM_PACKAGES[@]}"; do
        version=${NPM_PACKAGES[$package]}
        log "Проверка пакета $package..."

        # Проверяем существование версии в репозитории
        if ! npm view "$package@$version" version &>/dev/null; then
            log "ОШИБКА: Версия $package@$version не существует!"
            exit 1
        fi

        if ! npm list "$package" &>/dev/null; then
            log "Установка $package..."
            if [ -n "$version" ]; then
                npm install -D "$package@$version" --quiet --force
            else
                npm install -D "$package" --quiet --force
            fi
        else
            log "$package уже установлен"
        fi
    done

    # -------------------------------------- Автоматическая сборка фронтенда
    log "Сборка фронтенда..."
    npm run build

    # -------------------------------------- Миграции и оптимизация
    log "=== Выполнение миграций ==="

    # Получаем список всех миграций
    mapfile -t MIGRATIONS < <(php artisan migrate:status --quiet --no-ansi | awk '{print $2}')

    # Выполняем миграции по одной
    for migration in "${MIGRATIONS[@]}"; do
        printf "▸ Обработка %-50s" "$migration..."
        
        # Проверяем статус миграции
        status=$(php artisan migrate:status --no-ansi | grep "$migration" | awk '{print $4}')
        
        if [[ "$status" == "Ran" ]]; then
            log " [УЖЕ ВЫПОЛНЕНА]"
        else
            # Пытаемся выполнить миграцию
            if php artisan migrate --force --path="database/migrations/${migration}.php" > /dev/null 2>&1; then
                log " ✓ ВЫПОЛНЕНО"
            else
                log " ✗ ОШИБКА"
                log "=== Детали ошибки ==="
                php artisan migrate --force --path="database/migrations/${migration}.php" --no-ansi
                exit 1
            fi
        fi
    done
fi

php artisan config:cache
php artisan route:cache
php artisan view:cache

log "=== Инициализация завершена успешно ==="
exec php-fpm