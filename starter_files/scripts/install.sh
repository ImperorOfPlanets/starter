#!/bin/sh

# Логирование
LOG_FILE="/tmp/starter_install.log"
echo "=== Начало установки $(date) ===" > "$LOG_FILE"

# Функция для логирования
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Проверка пользователя root
if [ "$(id -u)" -eq 0 ]; then
    SUDO=""
else
    SUDO="sudo"
fi

# Определение ОС
detect_os() {
    # Для современных Linux систем
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
    # Для старых RedHat/CentOS
    elif [ -f /etc/redhat-release ]; then
        OS="centos"
    # Для BSD систем
    elif ls /etc/*bsd-release >/dev/null 2>&1; then
        OS=$(uname | tr '[:upper:]' '[:lower:]')
    # Для Solaris
    elif [ -f /etc/release ] && grep -q Solaris /etc/release; then
        OS="solaris"
    # Для AIX
    elif [ -x /usr/bin/oslevel ]; then
        OS="aix"
    # Для HP-UX
    elif [ -f /usr/convex/getsysinfo ]; then
        OS="hpux"
    # Для macOS
    elif [ "$(uname)" = "Darwin" ]; then
        OS="macos"
    # Для z/OS
    elif [ "$(uname)" = "OS/390" ]; then
        OS="zos"
    # Для Redox
    elif [ -f /etc/redox-release ]; then
        OS="redox"
    else
        OS="unknown"
    fi
    echo "$OS"
}

# Определение команды Python
detect_python() {
    for cmd in python3 python3.{12,11,10,9,8,7} python; do
        if command -v "$cmd" >/dev/null 2>&1; then
            echo "$cmd"
            return 0
        fi
    done
    echo ""
}

# Установка пакетов в зависимости от ОС
install_packages() {
    case $OS in
        ubuntu|debian)
            $SUDO apt-get update >> "$LOG_FILE" 2>&1
            $SUDO apt-get install -y "$@" >> "$LOG_FILE" 2>&1
            ;;
        centos|rhel|fedora)
            if command -v dnf >/dev/null 2>&1; then
                $SUDO dnf install -y "$@" >> "$LOG_FILE" 2>&1
            else
                $SUDO yum install -y "$@" >> "$LOG_FILE" 2>&1
            fi
            ;;
        alpine)
            $SUDO apk add --no-cache "$@" >> "$LOG_FILE" 2>&1
            ;;
        macos)
            if ! command -v brew >/dev/null 2>&1; then
                /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" >> "$LOG_FILE" 2>&1
            fi
            brew install "$@" >> "$LOG_FILE" 2>&1
            ;;
        freebsd|openbsd|netbsd)
            $SUDO pkg install -y "$@" >> "$LOG_FILE" 2>&1
            ;;
        solaris)
            $SUDO pkgutil -i -y "$@" >> "$LOG_FILE" 2>&1
            ;;
        aix)
            $SUDO installp -a -d "$@" >> "$LOG_FILE" 2>&1
            ;;
        *)
            log "Неизвестная ОС. Установите пакеты вручную: $*"
            return 1
            ;;
    esac
}

# Основная установка
OS=$(detect_os)
PYTHON_CMD=$(detect_python)

log "Определена ОС: $OS"
log "Используемая команда Python: ${PYTHON_CMD:-не найдена}"

# Установка Python если не найден
if [ -z "$PYTHON_CMD" ]; then
    log "Установка Python..."
    case $OS in
        ubuntu|debian)
            install_packages python3
            ;;
        centos|rhel|fedora)
            install_packages python3
            ;;
        alpine)
            install_packages python3
            ;;
        macos)
            install_packages python
            ;;
        freebsd|openbsd|netbsd)
            install_packages python3
            ;;
        *)
            log "Ошибка: Не удалось установить Python для этой ОС"
            exit 1
            ;;
    esac
    PYTHON_CMD=$(detect_python)
    if [ -z "$PYTHON_CMD" ]; then
        log "Ошибка: Python не установлен"
        exit 1
    fi
fi

# Установка зависимостей
log "Установка необходимых пакетов..."
case $OS in
    solaris)
        # Solaris требует особого подхода
        if [ ! -x "/usr/bin/wget" ]; then
            log "Установка wget для Solaris..."
            $SUDO pkgadd -d http://get.opencsw.org/now all >> "$LOG_FILE" 2>&1
            $SUDO /opt/csw/bin/pkgutil -U >> "$LOG_FILE" 2>&1
            $SUDO /opt/csw/bin/pkgutil -y -i wget unzip >> "$LOG_FILE" 2>&1
            export PATH=$PATH:/opt/csw/bin
        fi
        ;;
    aix)
        # AIX требует rpm пакеты
        if [ ! -x "/usr/bin/wget" ]; then
            log "Установка wget для AIX..."
            $SUDO rpm -ivh http://www.oss4aix.org/download/RPMS/wget/wget-1.14-1.aix6.1.ppc.rpm >> "$LOG_FILE" 2>&1
        fi
        ;;
    *)
        install_packages wget unzip
        ;;
esac

# Создание папки
log "Создание папки /app/starter..."
if [ "$OS" = "macos" ]; then
    $SUDO mkdir -p /app/starter >> "$LOG_FILE" 2>&1
    $SUDO chown "$(whoami):wheel" /app/starter >> "$LOG_FILE" 2>&1
else
    $SUDO mkdir -p /app/starter >> "$LOG_FILE" 2>&1
    $SUDO chown "$(whoami):$(id -gn)" /app/starter >> "$LOG_FILE" 2>&1
fi

# Скачивание Starter
log "Скачивание Starter..."
if ! wget -O /app/starter/starter.zip "https://gitflic.ru/project/imperor/starter/file/downloadAll?branch=master&format=zip" >> "$LOG_FILE" 2>&1; then
    # Альтернативная попытка через curl если wget нет
    if ! curl -L -o /app/starter/starter.zip "https://gitflic.ru/project/imperor/starter/file/downloadAll?branch=master&format=zip" >> "$LOG_FILE" 2>&1; then
        log "Ошибка при скачивании Starter"
        exit 1
    fi
fi

# Распаковка
log "Распаковка Starter..."
if ! unzip /app/starter/starter.zip -d /app/starter/ >> "$LOG_FILE" 2>&1; then
    log "Ошибка при распаковке Starter"
    exit 1
fi
rm -f /app/starter/starter.zip >> "$LOG_FILE" 2>&1

# Запуск Starter
log "Запуск Starter..."
cd /app/starter || exit 1
$PYTHON_CMD starter.py 2>&1 | tee -a "$LOG_FILE"

log "Установка и запуск завершены!"
log "Лог установки сохранен в $LOG_FILE"
echo "Для повторного запуска используйте:"
echo "cd /app/starter && $PYTHON_CMD starter.py"
