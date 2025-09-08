#!/bin/sh

# Функция проверки VPN подключения
check_vpn_connection() {
    # Максимальное время ожидания в секундах
    MAX_WAIT=30
    WAIT_INTERVAL=2
    
    log "Начало проверки VPN подключения..."
    
    i=0
    while [ $i -lt $((MAX_WAIT/WAIT_INTERVAL)) ]; do
        # 1. Проверяем наличие любого TUN-интерфейса, если TUN_DEVICE не указан
        if [ -z "$TUN_DEVICE" ]; then
            TUN_DEVICE=$(ip -o link show type tun | head -1 | awk -F': ' '{print $2}')
            [ -n "$TUN_DEVICE" ] && log "Обнаружен TUN-интерфейс: $TUN_DEVICE"
        fi

        # 2. Проверяем конкретный интерфейс или любой TUN
        if [ -n "$TUN_DEVICE" ] && ip link show "$TUN_DEVICE" >/dev/null 2>&1; then
            VPN_IP=$(ip -4 addr show "$TUN_DEVICE" | grep -oP '(?<=inet\s)\d+(\.\d+){3}')
            
            # 3. Дополнительная проверка маршрута (опционально)
            DEFAULT_ROUTE=$(ip route show default | grep "$TUN_DEVICE")
            
            if [ -n "$VPN_IP" ]; then
                echo "VPN_CONNECTED=1" > "$READY_FILE"
                echo "VPN_IP=$VPN_IP" >> "$READY_FILE"
                echo "VPN_INTERFACE=$TUN_DEVICE" >> "$READY_FILE"
                log "VPN успешно подключен, IP: $VPN_IP"
                [ -n "$DEFAULT_ROUTE" ] && log "Маршрут по умолчанию через VPN: $DEFAULT_ROUTE"
                return 0
            fi
        fi
        
        sleep $WAIT_INTERVAL
        log "Ожидание VPN подключения... Попытка $((i+1))"
        i=$((i + 1))
    done
    
    log "Превышено время ожидания VPN подключения"
    log "Доступные TUN-интерфейсы: $(ip -o link show type tun 2>/dev/null || echo 'не найдены')"
    log "Текущие IP-адреса: $(ip -4 addr show 2>/dev/null)"
    log "Маршруты: $(ip route show 2>/dev/null)"
    return 1
}

# Лок-файл для предотвращения дублирования
LOCK_FILE="/tmp/vpn_manager.lock"
LOG_FILE="/logs/vpn_manager.log"

# Простое логирование (совместимое с Alpine)
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Проверка блокировки
if [ -f "$LOCK_FILE" ]; then
    log "Обнаружен lock-файл. Возможно, процесс уже запущен."
    exit 0
fi

# Создание lock-файла
touch "$LOCK_FILE"
trap 'rm -f "$LOCK_FILE"; log "Завершение работы VPN менеджера"' EXIT

# Основные параметры
CONFIG_FILE="/vpn/config.ovpn"
READY_FILE="/logs/vpn_ready.txt"
ERROR_FILE="/logs/vpn_error.txt"

log "Запуск в режиме: $VPN_REQUIRED"
log "Путь к файлу конфигурации: $CONFIG_FILE"

# Проверка конфигурации
if [ ! -f "$CONFIG_FILE" ]; then
    log "ОШИБКА: Файл конфигурации не найден!"
    echo "ОШИБКА: Файл конфигурации не найден!" > "$ERROR_FILE"
    exit 1
fi

# Детальное логирование конфигурации TUN
log "=== НАЧАЛО КОНФИГУРИРОВАНИЯ TUN ==="
log "Проверяем наличие TUN_DEVICE: '$TUN_DEVICE'"

if [ -n "$TUN_DEVICE" ]; then
    log "TUN_DEVICE получено: $TUN_DEVICE"
    log "Оригинальное содержимое конфига перед изменением:"
    grep -E '^dev tun|^dev-type tun' "$CONFIG_FILE" | tee -a "$LOG_FILE"
    
    log "Изменяем dev tun на $TUN_DEVICE"
    sed -i "s/^dev tun.*$/dev $TUN_DEVICE/" "$CONFIG_FILE"
    
    log "Изменяем dev-type tun"
    sed -i "s/^dev-type tun.*$/dev-type tun/" "$CONFIG_FILE"
    
    if ! grep -q "^dev-type tun" "$CONFIG_FILE"; then
        log "Добавляем dev-type tun в конфиг"
        echo "dev-type tun" >> "$CONFIG_FILE"
    fi
    
    log "Проверяем изменения:"
    log "Содержимое конфига после изменений:"
    grep -E '^dev |^dev-type ' "$CONFIG_FILE" | tee -a "$LOG_FILE"
else
    log "TUN_DEVICE не указано, оставляем конфиг без изменений"
fi

log "=== ЗАВЕРШЕНИЕ КОНФИГУРИРОВАНИЯ TUN ==="

# Обработка режимов работы
case "$VPN_REQUIRED" in
    "required")
        log "Обязательное VPN подключение"
        log "Подключение к VPN..."
        
        # Запускаем OpenVPN в foreground режиме
        openvpn --config "$CONFIG_FILE" \
                --dev "$TUN_DEVICE" \
                --auth-nocache \
                --log /logs/openvpn.log \
                --verb 3 &
        OPENVPN_PID=$!
        
        # Проверяем подключение с учетом времени установки соединения
        if ! check_vpn_connection; then
            log "ОШИБКА: VPN не подключен после нескольких попыток"
            kill $OPENVPN_PID 2>/dev/null
            echo "ОШИБКА: VPN не подключен" > "$ERROR_FILE"
            exit 1
        fi

        # Ждем завершения OpenVPN (контейнер будет работать пока работает OpenVPN)
        wait $OPENVPN_PID
        log "OpenVPN завершил работу"
        exit $?
        ;;
        
    "optional")
        log "Опциональное VPN подключение"
        log "Попытка подключения к VPN..."
        if openvpn --config "$CONFIG_FILE" --dev "$TUN_DEVICE" --auth-nocache --daemon; then
            sleep 5
            if check_vpn_connection; then
                log "VPN подключен (опциональный режим)"
            else
                log "VPN не подключен (продолжаем без VPN)"
                echo "VPN_CONNECTED=0" > "$READY_FILE"
            fi
        else
            log "Не удалось запустить VPN (продолжаем без VPN)"
            echo "VPN_CONNECTED=0" > "$READY_FILE"
        fi
        ;;
        
    "disabled")
        log "VPN отключен"
        echo "VPN_CONNECTED=0" > "$READY_FILE"
        tail -f /dev/null
        ;;
        
    *)
        log "ОШИБКА: Неверный режим VPN"
        echo "ОШИБКА: Неверный режим VPN" > "$ERROR_FILE"
        exit 1
        ;;
esac

# Держим контейнер активным
log "VPN менеджер работает в фоновом режиме"
tail -f /dev/null