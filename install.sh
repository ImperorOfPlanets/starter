#!/bin/sh

# Массив URL скриптов (порядок важен — первый приоритетный)
SCRIPT_URLS="
https://gitflic.ru/project/imperor/starter/blob/raw?file=starter_files%2Fscripts%2Finstall.sh
"

# 1. Определяем доступную оболочку (проверяем по порядку)
for shell in sh ash dash ksh bash; do
    if command -v "$shell" >/dev/null 2>&1; then
        SHELL_TO_USE="$shell"
        break
    fi
done

[ -z "$SHELL_TO_USE" ] && echo "Ошибка: Нет доступной оболочки!" && exit 1

# 2. Функция для загрузки через /dev/tcp (если доступно)
download_via_tcp() {
    local url="$1"
    local host="${url#*://}"  # Удаляем протокол
    host="${host%%/*}"        # Оставляем только домен
    local path="/${url#*://*/}"

    # Разбираем порт (80 для HTTP, 443 для HTTPS)
    local port=80
    case "$url" in
        https://*) port=443 ;;
    esac

    if [ -w "/dev/tcp/$host/$port" ]; then
        (
            exec 3<>"/dev/tcp/$host/$port"
            printf "GET %s HTTP/1.1\r\nHost: %s\r\nConnection: close\r\n\r\n" "$path" "$host" >&3
            cat <&3 | sed '1,/^\r$/d' > "$2"
        ) && return 0
    fi
    return 1
}

# 3. Функция для загрузки через ftp (если доступно)
download_via_ftp() {
    local url="$1"
    if command -v ftp >/dev/null 2>&1; then
        local host="${url#*://}"
        host="${host%%/*}"
        local path="${url#*://*/}"
        ftp -n "$host" <<EOF
user anonymous ""
get "$path" "$2"
quit
EOF
        [ -s "$2" ] && return 0
    fi
    return 1
}

# 4. Функция для загрузки через lynx/links (если доступно)
download_via_text_browser() {
    local url="$1"
    for cmd in lynx links elinks; do
        if command -v "$cmd" >/dev/null 2>&1; then
            "$cmd" -source "$url" > "$2" && return 0
        fi
    done
    return 1
}

# 5. Основной цикл: пробуем скачать и запустить
for url in $SCRIPT_URLS; do
    tmp_script=$(mktemp 2>/dev/null || echo "/tmp/script_$$.sh")

    echo "Пробуем скачать: $url"
    if download_via_tcp "$url" "$tmp_script" || \
       download_via_ftp "$url" "$tmp_script" || \
       download_via_text_browser "$url" "$tmp_script"; then
        chmod +x "$tmp_script"
        echo "Запускаем через $SHELL_TO_USE..."
        "$SHELL_TO_USE" "$tmp_script"
        rm -f "$tmp_script"
        exit 0
    else
        echo "Ошибка загрузки: $url"
        rm -f "$tmp_script"
    fi
done

echo "Все ссылки недоступны. Не удалось запустить скрипт."
exit 1