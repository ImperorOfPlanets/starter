#!/bin/bash

# Ожидаем готовности приложения
while [ ! -f /var/www/html/ready.txt ]; do
    echo "Ожидаем появления /var/www/html/ready.txt..."
    sleep 5
done

exec php artisan horizon