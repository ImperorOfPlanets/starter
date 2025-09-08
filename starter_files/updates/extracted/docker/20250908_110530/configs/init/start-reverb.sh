#!/bin/bash

# Проверяем наличие всех необходимых файлов
if [ ! -f "/var/www/html/bootstrap/app.php" ]; then
    echo "Ошибка: файл app.php не найден"
    exit 1
fi

if [ ! -f "/var/www/html/vendor/autoload.php" ]; then
    echo "Ошибка: vendor/autoload.php не найден"
    exit 1
fi

if [ ! -d "/var/www/html/storage" ]; then
    echo "Ошибка: директория storage не найдена"
    exit 1
fi

# Проверяем права доступа
chmod -R 755 /var/www/html/storage
chmod -R 755 /var/www/html/bootstrap/cache

# Запускаем Reverb
php artisan reverb:start --host=127.0.0.1 --port=8443 --hostname=client.myidon.site --debug