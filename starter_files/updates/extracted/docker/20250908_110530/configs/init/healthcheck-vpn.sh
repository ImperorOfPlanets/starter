#!/bin/sh

echo "[Healthcheck] Проверка состояния VPN"

# Проверяем наличие файла статуса
if [ ! -f "/logs/vpn_ready.txt" ]; then
    echo "[Healthcheck] Файл статуса VPN не найден"
    exit 1
fi

# Проверяем наличие интерфейса
if ! ip addr show "${TUN_DEVICE}" >/dev/null 2>&1; then
    echo "[Healthcheck] Интерфейс ${TUN_DEVICE} не найден"
    exit 1
fi

# Проверяем наличие IP-адреса
if ! ip -4 addr show "${TUN_DEVICE}" | grep -q 'inet '; then
    echo "[Healthcheck] Нет IP-адреса на интерфейсе ${TUN_DEVICE}"
    exit 1
fi

echo "[Healthcheck] VPN работает нормально"
exit 0