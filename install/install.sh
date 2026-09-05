#!/bin/sh
# ============================================================================
# INSTALL.SH - Точка входа
# Скачивается с myidon.site, всегда доступен
# ============================================================================

set -e

# Конфигурация myidon.site (всегда доступен)
MYIDON_URL="https://myidon.site"
VARIABLES_URL="$MYIDON_URL/install/variables.sh"
STARTER_URL="$MYIDON_URL/install/start.sh"

# Лог
LOG="/tmp/starter_install_$(date +%Y%m%d_%H%M%S).log"
log() { echo "[$(date +%H:%M:%S)] $1" | tee -a "$LOG"; }

log "=== Установка Starter ==="
log "Источник: myidon.site"

# 1. Скачиваем variables.sh (пакеты для разных ОС)
log "Загрузка variables.sh..."
if ! wget -q -O /tmp/variables.sh "$VARIABLES_URL" 2>/dev/null; then
    if ! curl -s -o /tmp/variables.sh "$VARIABLES_URL" 2>/dev/null; then
        log "ОШИБКА: Не удалось скачать variables.sh"
        exit 1
    fi
fi

# 2. Скачиваем start.sh (установщик)
log "Загрузка start.sh..."
if ! wget -q -O /tmp/start.sh "$STARTER_URL" 2>/dev/null; then
    if ! curl -s -o /tmp/start.sh "$STARTER_URL" 2>/dev/null; then
        log "ОШИБКА: Не удалось скачать start.sh"
        exit 1
    fi
fi

chmod +x /tmp/start.sh

# 3. Запускаем start.sh (передаём ему variables.sh)
log "Запуск start.sh..."
exec /tmp/start.sh /tmp/variables.sh "$@"
