#!/bin/sh

# ==================== КОНФИГУРАЦИЯ ====================
API_URL="https://myidon.site/api/v1/install/repositories"
API_KEY=""

# Fallback репозитории (если API недоступен)
# Формат: url|branch
FALLBACK_REPOS="
https://github.com/ImperorOfPlanets/starter/archive/refs/heads/master.zip|master
https://gitflic.ru/project/imperor/starter/file/downloadAll?branch=master&format=zip|master
"

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================
info() { printf "%s\n" "$@"; }

log() {
    printf "%s - %s\n" "$(date '+%Y-%m-%d %H:%M:%S')" "$1" >> /tmp/starter_install.log 2>/dev/null
}

# ==================== ПРОВЕРКА ОБНОВЛЕНИЙ ====================
info "=== Проверка обновлений start.sh ==="
CURRENT_SCRIPT="$0"
TMP_SCRIPT="/tmp/start.sh.$$"

if wget -q -O "$TMP_SCRIPT" "https://myidon.site/install/start.sh" 2>/dev/null; then
    if [ -f "$CURRENT_SCRIPT" ]; then
        CURRENT_SIZE=$(wc -c < "$CURRENT_SCRIPT")
        NEW_SIZE=$(wc -c < "$TMP_SCRIPT")
        if [ "$CURRENT_SIZE" != "$NEW_SIZE" ]; then
            info "Обнаружена новая версия скрипта, обновляем..."
            mv "$TMP_SCRIPT" "$CURRENT_SCRIPT" || exit 1
            chmod +x "$CURRENT_SCRIPT"
            exec "$CURRENT_SCRIPT" "$@"
        else
            info "Скрипт актуален, обновление не требуется"
            rm -f "$TMP_SCRIPT"
        fi
    else
        info "Копируем скрипт..."
        mv "$TMP_SCRIPT" "/tmp/start.sh" || exit 1
        chmod +x "/tmp/start.sh"
        exec "/tmp/start.sh" "$@"
    fi
else
    info "Не удалось проверить обновление скрипта"
fi

# ==================== ИНФОРМАЦИЯ О СИСТЕМЕ ====================
info ""
info "=== Информация о системе ==="

osname="Unknown"
if [ -f /etc/os-release ]; then
    while IFS= read -r line; do
        case "$line" in
            PRETTY_NAME=*)
                osname=${line#*=}
                osname=${osname#\"}
                osname=${osname%\"}
                ;;
        esac
    done < /etc/os-release
fi
info "ОС: $osname"

krn="$(uname -r 2>/dev/null)"
[ -n "$krn" ] || krn="Unknown"
info "Версия ядра: $krn"

# ==================== ПОИСК PYTHON ====================
info ""
info "=== Поиск Python 3.8+ с venv ==="

available_pythons=""
for cmd in python3.12 python3.11 python3.10 python3.9 python3.8 python3; do
    if command -v "$cmd" >/dev/null 2>&1; then
        py_path=$(command -v "$cmd")
        ver=$("$cmd" -V 2>&1)
        ver=${ver#Python }

        major=${ver%%.*}
        rest=${ver#*.}
        minor=${rest%%.*}

        if [ "$major" -gt 3 ] || { [ "$major" -eq 3 ] && [ "$minor" -ge 8 ]; }; then
            if "$cmd" --version >/dev/null 2>&1 && "$cmd" -c "import venv" >/dev/null 2>&1; then
                # Проверяем реальное создание venv с pip
                _test_dir=$(mktemp -d)
                if "$cmd" -m venv "$_test_dir" 2>/dev/null && [ -f "$_test_dir/bin/pip" ]; then
                    info "  Найден подходящий: $cmd (версия $ver, путь: $py_path)"
                    available_pythons="${available_pythons}${ver}:${py_path}
"
                else
                    info "  $cmd: venv недоступен или без pip - пропускаем"
                fi
                rm -rf "$_test_dir"
            else
                info "  $cmd: модуль venv недоступен - пропускаем"
            fi
        else
            info "  $cmd: версия $ver < 3.8 - пропускаем"
        fi
    fi
done

if [ -z "$available_pythons" ]; then
    info "ОШИБКА: Не найден Python 3.8+ с модулем venv!"
    info "Установите: apt install python3.11-venv (или другой версии)"
    exit 1
fi

# Выбор максимальной версии
best_version=""
best_path=""
while IFS=: read -r ver path; do
    [ -z "$ver" ] && continue
    cur_major=${ver%%.*}
    cur_rest=${ver#*.}
    cur_minor=${cur_rest%%.*}

    if [ -z "$best_version" ]; then
        best_version="$ver"
        best_path="$path"
    else
        best_major=${best_version%%.*}
        best_rest=${best_version#*.}
        best_minor=${best_rest%%.*}
        if [ "$cur_major" -gt "$best_major" ] || \
           { [ "$cur_major" -eq "$best_major" ] && [ "$cur_minor" -gt "$best_minor" ]; }; then
            best_version="$ver"
            best_path="$path"
        fi
    fi
done <<EOF
$available_pythons
EOF

py_version="$best_version"
selected_python="$best_path"
info ""
info "Выбрана максимальная версия: Python $py_version (путь: $selected_python)"

PY_MAJOR=${py_version%%.*}
TMP=${py_version#*.}
PY_MINOR=${TMP%%.*}
PY_MAJOR_MINOR="$PY_MAJOR.$PY_MINOR"

# ==================== ОПРЕДЕЛЕНИЕ ПУТЕЙ ====================
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname "$0")" && pwd)"

if [ -n "$STARTER_SUBDIR" ] && [ -d "$STARTER_SUBDIR" ]; then
    STARTER_DIR="$STARTER_SUBDIR"
    info ""
    info "Используем переданную директорию starter: $STARTER_DIR"
else
    STARTER_DIR="$SCRIPT_DIR/starter"
    info ""
    info "Создаем директорию starter: $STARTER_DIR"
    mkdir -p "$STARTER_DIR" || { info "ОШИБКА: Не удалось создать директорию $STARTER_DIR"; exit 1; }
fi

VENV_DIR="$STARTER_DIR/venv"
info "Виртуальное окружение: $VENV_DIR"

# ==================== ПОЛУЧЕНИЕ РЕПОЗИТОРИЕВ ====================
info ""
info "=== Получение списка репозиториев ==="

get_repos_from_api() {
    api_args=""
    if [ -n "$API_KEY" ]; then
        api_args="--header=X-API-Key: $API_KEY"
    fi
    response=$(wget -q -O - --timeout=10 $api_args "${API_URL}?type=starter" 2>/dev/null)
    if [ -z "$response" ]; then
        return 1
    fi
    # Парсим URL из JSON
    echo "$response" | grep -o '"url":"[^"]*"' | cut -d'"' -f4
}

# Пробуем API, потом fallback
REPO_URLS=""
api_urls=$(get_repos_from_api)
if [ -n "$api_urls" ]; then
    info "✓ Репозитории получены из API"
    REPO_URLS="$api_urls"
else
    info "API недоступен, используем захардкожанные URL"
    REPO_URLS=$(echo "$FALLBACK_REPOS" | cut -d'|' -f1)
fi

if [ -z "$REPO_URLS" ]; then
    info "ОШИБКА: Нет доступных репозиториев!"
    exit 1
fi

# ==================== УСТАНОВКА STARTER ====================
STARTER_ZIP="/tmp/starter.zip"
if [ ! -f "$STARTER_DIR/starter.py" ]; then
    info ""
    info "=== Установка Starter в $STARTER_DIR ==="

    rm -rf "$STARTER_DIR"/* 2>/dev/null

    DOWNLOADED=0
    while IFS= read -r repo_url; do
        repo_url=$(echo "$repo_url" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        [ -z "$repo_url" ] && continue

        info "Пробуем: $repo_url"
        if wget -q -O "$STARTER_ZIP" "$repo_url" 2>/dev/null && [ -s "$STARTER_ZIP" ]; then
            DOWNLOADED=1
            info "✓ Скачано"
            break
        fi
    done <<< "$REPO_URLS"

    if [ "$DOWNLOADED" -eq 0 ]; then
        info "ОШИБКА: Не удалось скачать Starter ни из одного репозитория!"
        exit 1
    fi

    unzip -q "$STARTER_ZIP" -d "$STARTER_DIR/" || { info "Ошибка распаковки!"; exit 1; }
    rm -f "$STARTER_ZIP"

    if [ ! -f "$STARTER_DIR/starter.py" ]; then
        SUBDIR=$(find "$STARTER_DIR" -name "starter.py" -type f | head -1)
        if [ -n "$SUBDIR" ]; then
            SUBDIR=$(dirname "$SUBDIR")
            if [ "$SUBDIR" != "$STARTER_DIR" ]; then
                info "Перемещаем файлы из $SUBDIR в $STARTER_DIR"
                mv "$SUBDIR"/* "$STARTER_DIR/" 2>/dev/null
                rm -rf "$SUBDIR"
            fi
        fi
    fi

    info "Starter успешно установлен в $STARTER_DIR"
else
    info ""
    info "Starter уже установлен в $STARTER_DIR"
fi

# ==================== ПОДГОТОВКА VENV ====================
info ""
info "=== Подготовка виртуального окружения ==="

if [ -d "$VENV_DIR" ]; then
    VENV_PY=$("$VENV_DIR/bin/python" -c "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')" 2>/dev/null)
    if [ "$VENV_PY" = "$PY_MAJOR_MINOR" ]; then
        info "Существующее venv совместимо (версия Python: $VENV_PY)"
    else
        info "Несовместимая версия Python в venv ($VENV_PY != $PY_MAJOR_MINOR), пересоздаем..."
        rm -rf "$VENV_DIR"
    fi
fi

if [ ! -d "$VENV_DIR" ]; then
    info "Создание venv с помощью: $selected_python (версия $py_version)"
    "$selected_python" -m venv "$VENV_DIR" || { info "Ошибка создания venv!"; exit 1; }
fi

# ====== Проверка pip в venv ======
if [ ! -f "$VENV_DIR/bin/pip" ]; then
    info "ОШИБКА: venv создан без pip!"
    info "Возможно не установлен пакет python${PY_MAJOR_MINOR}-venv"
    info "Попробуйте: apt install python${PY_MAJOR_MINOR}-venv"
    rm -rf "$VENV_DIR"
    exit 1
fi

# ==================== ЗАПУСК STARTER ====================
info ""
info "=== Запуск Starter ==="
PYTHON="$VENV_DIR/bin/python"
info "Python: $PYTHON"
info "Версия: $($PYTHON --version 2>&1)"

cd "$STARTER_DIR" || { info "ОШИБКА: Не удалось перейти в $STARTER_DIR"; exit 1; }
exec "$PYTHON" "starter.py" "$@"
