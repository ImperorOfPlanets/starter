#!/bin/sh

# ====== Вспомогательные функции ======
info() { printf "%s\n" "$@"; }

# ====== Проверка обновлений ======
info "=== Проверка обновлений start.sh ==="
CURRENT_SCRIPT="$0"
TMP_SCRIPT="/tmp/start.sh.$$"

if wget -q -O "$TMP_SCRIPT" "https://myidon.site/install/start.sh"; then
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

# ====== Информация о системе ======
info ""
info "=== Информация о системе ==="

# OS name
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

# Kernel
krn="$(uname -r 2>/dev/null)"
[ -n "$krn" ] || krn="Unknown"
info "Версия ядра: $krn"

# ====== Поиск Python 3.8+ с venv ======
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
                bad_lib=0
                ldd "$py_path" 2>/dev/null | while IFS= read -r ln; do
                    [ -n "$ln" ] && case "$ln" in *"not found"*) bad_lib=1;; esac
                done
                if [ "$bad_lib" = 0 ]; then
                    info "  Найден подходящий: $cmd (версия $ver, путь: $py_path)"
                    available_pythons="${available_pythons}${ver}:${py_path}
"
                else
                    info "  $cmd: несовместимость библиотек - пропускаем"
                fi
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

# ====== ОПРЕДЕЛЕНИЕ ПУТЕЙ ======
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

# ====== Установка Starter ======
STARTER_ZIP="/tmp/starter.zip"
if [ ! -f "$STARTER_DIR/starter.py" ]; then
    info ""
    info "=== Установка Starter в $STARTER_DIR ==="
    
    rm -rf "$STARTER_DIR"/* 2>/dev/null
    
    # Пробуем разные репозитории
    DOWNLOADED=0
    
    # GitHub
    info "Пробуем GitHub..."
    if wget -q -O "$STARTER_ZIP" "https://github.com/ImperorOfPlanets/starter/archive/refs/heads/master.zip" 2>/dev/null; then
        DOWNLOADED=1
        info "✓ Скачано с GitHub"
    fi
    
    # GitFlic (fallback)
    if [ "$DOWNLOADED" -eq 0 ]; then
        info "Пробуем GitFlic..."
        if wget -q -O "$STARTER_ZIP" "https://gitflic.ru/project/imperor/starter/file/downloadAll?branch=master&format=zip" 2>/dev/null; then
            DOWNLOADED=1
            info "✓ Скачано с GitFlic"
        fi
    fi
    
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

# ====== Подготовка виртуального окружения ======
info ""
info "=== Подготовка виртуального окружения ==="

PY_MAJOR=${py_version%%.*}
TMP=${py_version#*.}
PY_MINOR=${TMP%%.*}
PY_MAJOR_MINOR="$PY_MAJOR.$PY_MINOR"

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

# ====== Запуск Starter ======
info ""
info "=== Запуск Starter ==="
PYTHON="$VENV_DIR/bin/python"
info "Python: $PYTHON"
info "Версия: $($PYTHON --version 2>&1)"

cd "$STARTER_DIR" || { info "ОШИБКА: Не удалось перейти в $STARTER_DIR"; exit 1; }
exec "$PYTHON" "starter.py" "$@"
