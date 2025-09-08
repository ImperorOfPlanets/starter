#!/bin/bash

# Упрощенная версия без изменения прав
mkdir -p /var/log/supervisor
mkdir -p /var/log/worker

# Запуск Supervisor
exec /usr/bin/supervisord -n -c /etc/supervisor/conf.d/supervisord.conf