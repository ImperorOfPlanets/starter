#!/bin/sh

# ==================== КОНФИГУРАЦИЯ ====================
LOG_FILE="/tmp/starter_install_$(date +%Y%m%d_%H%M%S).log"
SUDO_CACHE_FILE="/tmp/.sudo.cache"
DEBUG=1

SYSTEM_DIRS="/bin /boot /dev /etc /lib /lib64 /proc /root /run /sbin /srv /sys /tmp /usr /var /opt"

# Папки по умолчанию
DEFAULT_DIR="/apps/starter"
FALLBACK_DIRS="/home/apps/starter /opt/apps/starter /data/apps/starter"

# Режим: auto (по умолчанию) или manual
INSTALL_MODE="auto"
PROJECT_DIR=""

# ==================== РЕПОЗИТОРИИ (обновлять часто!) ====================
# Формат: name|url|branch
# Это ОСНОВНОЙ список — отсюда скачиваем variables.sh и стартёр
REPOSITORIES="
starter|https://github.com/ImperorOfPlanets/starter/archive/refs/heads/master.zip|master
starter|https://gitflic.ru/project/imperor/starter/file/downloadAll?branch=master&format=zip|master
"

# API для получения списка репозиториев (если доступен)
API_URL="https://myidon.site/api/v1/install/repositories"
API_KEY=""

# URLs для скачивания variables.sh (fallback если репозиторий недоступен)
VARIABLES_FALLBACK_URLS="
https://raw.githubusercontent.com/ImperorOfPlanets/starter/master/install/variables.sh
https://gitflic.ru/project/imperor/starter/raw/branch/master/install/variables.sh
https://myidon.site/install/variables.sh
"

# =====================================================

log() {
    printf "%s - %s\n" "$(date '+%Y-%m-%d %H:%M:%S')" "$1" >> "$LOG_FILE"
}

info() {
    printf "%s\n" "$1"
    log "$1"
}

error() {
    printf "ERROR: %s\n" "$1" >&2
    log "ERROR: $1"
}

warn() {
    printf "WARN: %s\n" "$1"
    log "WARN: $1"
}

debug() {
    if [ "$DEBUG" = "1" ]; then
        printf "DEBUG: %s\n" "$1" >&2
    fi
    log "DEBUG: $1"
}

# ==================== ПРОВЕРКА ЗАВИСИМОСТЕЙ ====================

check_deps() {
    missing=""
    for cmd in wget unzip; do
        if ! command -v "$cmd" >/dev/null 2>&1; then
            missing="$missing $cmd"
        fi
    done
    if [ -n "$missing" ]; then
        error "Отсутствуют команды:$missing"
        error "Установите: apt install wget unzip (или yum/dnf)"
        exit 1
    fi
}

# ==================== ПАРСИНГ АРГУМЕНТОВ ====================

usage() {
    cat << 'EOF'
Использование: install.sh [опции]

Опции:
  -d PATH    Путь для установки (по умолчанию: /apps/starter)
  -m         Ручной режим (запрос папки)
  -a         Автоматический режим (по умолчанию)
  -l         Показать доступные диски
  -h         Показать справку

Примеры:
  ./install.sh                    # Авто: /apps/starter
  ./install.sh -d /home/bot       # Указать путь
  ./install.sh -m                 # Ручной режим
EOF
    exit 0
}

list_disks() {
    info "=== Доступные диски и разделы ==="
    if command -v lsblk >/dev/null 2>&1; then
        lsblk -o NAME,SIZE,MOUNTPOINT,FSTYPE -n 2>/dev/null | while read -r line; do
            info "  $line"
        done
    fi
    info ""
    info "Точки монтирования:"
    df -h 2>/dev/null | grep "^/dev" | while read -r line; do
        info "  $line"
    done
}

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

is_system_path() {
    path="$1"
    case "$path" in
        /*) ;;
        *) return 0 ;;
    esac
    if [ "$path" = "/" ]; then return 0; fi
    case "$path" in
        *\.\.*) return 0 ;;
    esac
    for prefix in $SYSTEM_DIRS; do
        case "$path" in
            "$prefix"|"$prefix/"*) return 0 ;;
        esac
    done
    return 1
}

find_writable_dir() {
    for dir in "$DEFAULT_DIR" $FALLBACK_DIRS; do
        parent="$(dirname "$dir")"
        if [ -d "$parent" ] && [ -w "$parent" ]; then
            mkdir -p "$dir" 2>/dev/null
            if [ -d "$dir" ]; then
                echo "$dir"
                return 0
            fi
        fi
    done

    for root_dir in /mnt /media /home /opt /data /srv; do
        if [ -d "$root_dir" ] && [ -w "$root_dir" ]; then
            dir="$root_dir/apps/starter"
            mkdir -p "$dir" 2>/dev/null
            if [ -d "$dir" ]; then
                echo "$dir"
                return 0
            fi
        fi
    done

    return 1
}

resolve_project_dir() {
    if [ -n "$PROJECT_DIR" ]; then
        if [ ! -d "$PROJECT_DIR" ]; then
            parent_dir="$(dirname "$PROJECT_DIR")"
            if [ ! -w "$parent_dir" ] 2>/dev/null; then
                error "Нет прав на запись в $parent_dir"
                return 1
            fi
            mkdir -p "$PROJECT_DIR" || { error "Не удалось создать $PROJECT_DIR"; return 1; }
        fi

        if is_system_path "$PROJECT_DIR"; then
            error "Запрещено использовать системные директории: $PROJECT_DIR"
            return 1
        fi

        info "Используется папка: $PROJECT_DIR"
        return 0
    fi

    if [ "$INSTALL_MODE" = "auto" ]; then
        found_dir=$(find_writable_dir)
        if [ -n "$found_dir" ]; then
            PROJECT_DIR="$found_dir"
            info "Автоматически выбрана папка: $PROJECT_DIR"
            return 0
        fi
        warn "Не удалось найти доступную папку автоматически"
        warn "Попробуйте: install.sh -d /ваш/путь"
    fi

    # Интерактивный ввод
    while true; do
        printf "\nУкажите папку для установки (абсолютный путь):\n"
        printf "   По умолчанию: %s\n" "$DEFAULT_DIR"
        printf "   Нажмите Enter для использования по умолчанию\n> "
        read -r input_path

        if [ -z "$input_path" ]; then
            input_path="$DEFAULT_DIR"
        fi

        case "$input_path" in
            ~*) input_path="${HOME}${input_path#~}" ;;
        esac

        if [ ! -d "$input_path" ]; then
            parent_dir="$(dirname "$input_path")"
            if [ ! -w "$parent_dir" ] 2>/dev/null; then
                error "Нет прав на запись в $(dirname "$input_path")"
                continue
            fi
            mkdir -p "$input_path" 2>/dev/null || { error "Не удалось создать $input_path"; continue; }
        fi

        abs_path="$(cd "$input_path" 2>/dev/null && pwd)" || continue

        if is_system_path "$abs_path"; then
            error "Запрещено использовать системные директории!"
            continue
        fi

        PROJECT_DIR="$abs_path"
        info "Выбрана папка: $PROJECT_DIR"
        return 0
    done
}

# ==================== SUDO ====================

check_sudo_requirements() {
    if [ "$(id -u)" -eq 0 ]; then
        SUDO=""
        SUDO_REQUIRED=false
        info "Запуск от root, sudo не требуется"
        return 0
    fi

    if [ -f "$SUDO_CACHE_FILE" ]; then
        SUDO_PASSWORD=$(cat "$SUDO_CACHE_FILE")
        if echo "$SUDO_PASSWORD" | sudo -S true 2>/dev/null; then
            SUDO="sudo -S"
            SUDO_REQUIRED=true
            info "Используется кэшированный пароль sudo"
            return 0
        fi
    fi

    if sudo -n true 2>/dev/null; then
        SUDO="sudo"
        SUDO_REQUIRED=false
        info "Пользователь в sudoers без пароля"
        return 0
    fi

    SUDO_REQUIRED=true
    printf "Для установки пакетов нужны права администратора\nВведите пароль sudo:\n"
    stty -echo 2>/dev/null
    read -r SUDO_PASSWORD
    stty echo 2>/dev/null
    echo

    if ! echo "$SUDO_PASSWORD" | sudo -S true 2>/dev/null; then
        error "Неверный пароль sudo"
        exit 1
    fi

    echo "$SUDO_PASSWORD" > "$SUDO_CACHE_FILE"
    chmod 600 "$SUDO_CACHE_FILE"
    SUDO="sudo -S"
    info "Пароль сохранён в кэш"
}

run_command() {
    cmd="$1"
    desc="$2"
    info "Выполнение: $desc"
    debug "Команда: $cmd"

    tmpout="/tmp/cmd_out.$$"
    if [ "$SUDO_REQUIRED" = "true" ]; then
        echo "$SUDO_PASSWORD" | $SUDO sh -c "$cmd" > "$tmpout" 2>&1
    else
        sh -c "$cmd" > "$tmpout" 2>&1
    fi
    status=$?

    if [ -s "$tmpout" ]; then
        while IFS= read -r line || [ -n "$line" ]; do
            info "$line"
        done < "$tmpout"
    fi
    rm -f "$tmpout"

    return $status
}

# ==================== ОПРЕДЕЛЕНИЕ ОС ====================

detect_os() {
    if [ -f /etc/os-release ]; then
        ID="unknown"
        while IFS='=' read -r key value; do
            case "$key" in
                ID) ID="$value" ;;
            esac
        done < /etc/os-release
        echo "$ID" | tr '[:upper:]' '[:lower:]' | tr -d '"'
    elif [ -f /etc/debian_version ]; then
        echo "debian"
    elif [ -f /etc/redhat-release ]; then
        if grep -q "centos" /etc/redhat-release; then
            echo "centos"
        elif grep -q "almalinux" /etc/redhat-release; then
            echo "almalinux"
        elif grep -q "rocky" /etc/redhat-release; then
            echo "rocky"
        else
            echo "rhel"
        fi
    else
        echo "unknown"
    fi
}

detect_os_version() {
    if [ -f /etc/os-release ]; then
        VERSION_ID="unknown"
        while IFS='=' read -r key value; do
            case "$key" in
                VERSION_ID) VERSION_ID="$value" ;;
            esac
        done < /etc/os-release
        echo "$VERSION_ID" | tr -d '"'
    elif [ -f /etc/debian_version ]; then
        cat /etc/debian_version
    elif [ -f /etc/redhat-release ]; then
        sed -n 's/.*\([0-9][0-9]*\.[0-9][0-9]*\).*/\1/p' /etc/redhat-release | head -1
    else
        echo "unknown"
    fi
}

# ==================== УСТАНОВКА ПАКЕТОВ ====================

find_value() {
    os="$1"
    ver="$2"
    name="$3"
    pattern="$os,$ver,$name"
    value=$(echo "$CONFIG_MAP" | tr ';' '\n' | grep -F "$pattern=" | head -1 | cut -d= -f2-)
    if [ -n "$value" ]; then
        echo "$value"
        return 0
    fi
    major_ver=$(echo "$ver" | cut -d. -f1)
    pattern="$os,$major_ver,$name"
    value=$(echo "$CONFIG_MAP" | tr ';' '\n' | grep -F "$pattern=" | head -1 | cut -d= -f2-)
    if [ -n "$value" ]; then
        echo "$value"
        return 0
    fi
    pattern="$os,default,$name"
    value=$(echo "$CONFIG_MAP" | tr ';' '\n' | grep -F "$pattern=" | head -1 | cut -d= -f2-)
    if [ -n "$value" ]; then
        echo "$value"
        return 0
    fi
    return 1
}

load_variables() {
    variables_content="$1"
    CONFIG_MAP=""
    while IFS= read -r line || [ -n "$line" ]; do
        line=$(echo "$line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        [ -z "$line" ] && continue
        case "$line" in
            \#*) continue ;;
        esac
        case "$line" in
            \[*\]=*)
                key=$(echo "$line" | sed -n 's/^\[\(.*\)\]=.*$/\1/p')
                value=$(echo "$line" | sed -n 's/^\[.*\]=\(.*\)$/\1/p' | sed 's/^"//;s/"$//')
                CONFIG_MAP="$CONFIG_MAP$key=$value;"
                ;;
        esac
    done <<< "$variables_content"
}

install_packages() {
    os="$1"
    ver="$2"
    shift 2
    pkgs=""
    for pkg in "$@"; do
        pkgs="$pkgs $pkg"
    done
    info "=== Установка пакетов:$pkgs ==="
    pre_cmd=$(find_value "$os" "$ver" "pre_install")
    install_cmd=$(find_value "$os" "$ver" "install")
    post_cmd=$(find_value "$os" "$ver" "post_install")
    packages=""
    for pkg in "$@"; do
        pkg_name=$(find_value "$os" "$ver" "$pkg")
        case "$pkg_name" in
            ""|" ") continue ;;
        esac
        packages="$packages $pkg_name"
    done
    packages=$(echo "$packages" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    if [ -n "$pre_cmd" ]; then
        run_command "$pre_cmd" "pre-команда" || return $?
    fi
    if [ -n "$install_cmd" ] && [ -n "$packages" ]; then
        run_command "$install_cmd $packages" "установка" || return $?
    fi
    if [ -n "$post_cmd" ]; then
        run_command "$post_cmd" "post-команда" || return $?
    fi
    return 0
}

# ==================== ПРОВЕРКА ДОСТУПНОСТИ URL ====================

check_url() {
    url="$1"
    timeout=5
    if wget -q --spider --timeout="$timeout" "$url" 2>/dev/null; then
        return 0
    fi
    return 1
}

# ==================== ПОЛУЧЕНИЕ РЕПОЗИТОРИЕВ ====================

try_api_repos() {
    info "=== Попытка получить репозитории из API ==="
    api_args=""
    if [ -n "$API_KEY" ]; then
        api_args="--header=X-API-Key: $API_KEY"
    fi
    api_response=$(wget -q -O - --timeout=10 $api_args "$API_URL?type=starter" 2>/dev/null)
    if [ -z "$api_response" ]; then
        warn "API недоступен, используем захардкоженные URL"
        return 1
    fi
    # Парсим JSON простым grep (без jq)
    urls=$(echo "$api_response" | grep -o '"url":"[^"]*"' | cut -d'"' -f4)
    if [ -z "$urls" ]; then
        warn "API не вернул URL репозиториев"
        return 1
    fi
    echo "$urls"
    return 0
}

get_repositories() {
    # Сначала пробуем API
    api_urls=$(try_api_repos)
    if [ $? -eq 0 ] && [ -n "$api_urls" ]; then
        echo "$api_urls"
        return 0
    fi

    # Fallback — захардкоженные URL из REPOSITORIES
    info "=== Используем захардкожанные репозитории ==="
    echo "$REPOSITORIES" | while IFS='|' read -r name url branch; do
        name=$(echo "$name" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        url=$(echo "$url" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        [ -z "$name" ] && continue
        [ -z "$url" ] && continue
        echo "$url"
    done
}

# ==================== ПОЛУЧЕНИЕ VARIABLES.SH ====================

download_variables() {
    info "=== Поиск variables.sh ==="

    # Пробуем скачать variables.sh из доступного репозитория
    # Формат URL для GitHub: .../archive/refs/heads/master.zip → .../raw/master/install/variables.sh
    # Формат URL для GitFlic: .../file/downloadAll?... → .../raw/branch/master/install/variables.sh

    repos=$(get_repositories)
    while IFS= read -r repo_url; do
        repo_url=$(echo "$repo_url" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        [ -z "$repo_url" ] && continue

        # Преобразуем URL zip-архива в URL raw-файла
        variables_url=""
        case "$repo_url" in
            *github.com*)
                # https://github.com/user/repo/archive/refs/heads/master.zip
                # → https://raw.githubusercontent.com/user/repo/master/install/variables.sh
                base=$(echo "$repo_url" | sed 's|/archive/refs/heads/.*||')
                branch=$(echo "$repo_url" | sed 's|.*refs/heads/||;s|\.zip||')
                owner_repo=$(echo "$base" | sed 's|https://github.com/||')
                variables_url="https://raw.githubusercontent.com/${owner_repo}/${branch}/install/variables.sh"
                ;;
            *gitflic.ru*)
                # https://gitflic.ru/project/imperor/starter/file/downloadAll?branch=master&format=zip
                # → https://gitflic.ru/project/imperor/starter/raw/branch/master/install/variables.sh
                base=$(echo "$repo_url" | sed 's|/file/downloadAll.*||')
                branch=$(echo "$repo_url" | sed 's|.*branch=||;s|&.*||')
                variables_url="${base}/raw/branch/${branch}/install/variables.sh"
                ;;
        esac

        if [ -n "$variables_url" ]; then
            info "Пробуем: $variables_url"
            if check_url "$variables_url"; then
                wget -q -O /tmp/variables.sh "$variables_url" 2>/dev/null
                if [ -s /tmp/variables.sh ]; then
                    info "✓ variables.sh скачан из $repo_url"
                    cat /tmp/variables.sh
                    rm -f /tmp/variables.sh
                    return 0
                fi
            fi
        fi
    done <<< "$repos"

    # Fallback — прямые URLs
    info "=== Прямые fallback URLs для variables.sh ==="
    while IFS= read -r fallback_url; do
        fallback_url=$(echo "$fallback_url" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        [ -z "$fallback_url" ] && continue

        info "Пробуем: $fallback_url"
        if check_url "$fallback_url"; then
            wget -q -O /tmp/variables.sh "$fallback_url" 2>/dev/null
            if [ -s /tmp/variables.sh ]; then
                info "✓ variables.sh скачан из fallback"
                cat /tmp/variables.sh
                rm -f /tmp/variables.sh
                return 0
            fi
        fi
    done <<< "$VARIABLES_FALLBACK_URLS"

    error "Не удалось скачать variables.sh ни из одного источника!"
    return 1
}

# ==================== ОСНОВНОЙ ХОД ====================

while getopts "d:mahl" opt; do
    case $opt in
        d) PROJECT_DIR="$OPTARG" ;;
        m) INSTALL_MODE="manual" ;;
        a) INSTALL_MODE="auto" ;;
        l) list_disks; exit 0 ;;
        h) usage ;;
        *) usage ;;
    esac
done

info "=== Начало установки $(date) ==="
info "Режим: $INSTALL_MODE"
printf "%s\n" "=== Начало установки $(date) ===" > "$LOG_FILE"

check_deps

resolve_project_dir || { error "Не удалось определить папку проекта"; exit 1; }

export STARTER_SUBDIR="$PROJECT_DIR"

check_sudo_requirements

# Скачиваем variables.sh из репозитория
variables_content=$(download_variables) || { error "Ошибка загрузки variables.sh"; exit 1; }

# Загружаем конфигурацию пакетов
load_variables "$variables_content"

OS=$(detect_os)
OS_VERSION=$(detect_os_version)
info "ОС: $OS, версия: $OS_VERSION"

install_packages "$OS" "$OS_VERSION" python python-venv pip python-dev unzip || {
    error "Ошибка установки пакетов"
    exit 1
}

PYTHON_CMD=$(command -v python3 || command -v python)
PIP_CMD=$(command -v pip3 || command -v pip)
[ -z "$PYTHON_CMD" ] && { error "Python не установлен"; exit 1; }
[ -z "$PIP_CMD" ] && { error "pip не установлен"; exit 1; }
command -v unzip >/dev/null 2>&1 || { error "unzip не установлен"; exit 1; }

info "=== Системные зависимости установлены ==="

# Сохраняем URL репозитория для start.sh
REPO_URLS=$(get_repositories)
export STARTER_REPO_URLS="$REPO_URLS"

cd "$PROJECT_DIR" || { error "Не удалось перейти в $PROJECT_DIR"; exit 1; }
info "Скачивание start.sh в $PROJECT_DIR..."
STARTER_URL="https://myidon.site/install/start.sh"
if ! wget -q -O start.sh "$STARTER_URL" 2>/dev/null; then
    # Fallback — start.sh из репозитория
    while IFS= read -r repo_url; do
        repo_url=$(echo "$repo_url" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        [ -z "$repo_url" ] && continue
        case "$repo_url" in
            *github.com*)
                base=$(echo "$repo_url" | sed 's|/archive/refs/heads/.*||')
                branch=$(echo "$repo_url" | sed 's|.*refs/heads/||;s|\.zip||')
                owner_repo=$(echo "$base" | sed 's|https://github.com/||')
                start_url="https://raw.githubusercontent.com/${owner_repo}/${branch}/install/start.sh"
                ;;
            *gitflic.ru*)
                base=$(echo "$repo_url" | sed 's|/file/downloadAll.*||')
                branch=$(echo "$repo_url" | sed 's|.*branch=||;s|&.*||')
                start_url="${base}/raw/branch/${branch}/install/start.sh"
                ;;
            *) continue ;;
        esac
        info "Пробуем start.sh из репозитория: $start_url"
        if wget -q -O start.sh "$start_url" 2>/dev/null && [ -s start.sh ]; then
            info "✓ start.sh скачан из репозитория"
            break
        fi
    done <<< "$REPO_URLS"
fi

if [ ! -s start.sh ]; then
    error "Не удалось скачать start.sh"
    exit 1
fi

chmod +x start.sh || { error "Не удалось сделать start.sh исполняемым"; exit 1; }

info "Проект инициализирован в: $PROJECT_DIR"
info "Запуск..."

exec ./start.sh "$@"
