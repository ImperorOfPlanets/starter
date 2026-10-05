# Установка, модули и обновления — рабочее руководство

> Документ описывает полный жизненный цикл сервера через API стартера:
> удаление → установка → установка модулей → обновление.
> Все примеры проверялись на живых установках.

---

## 1. Что нужно знать до начала

| Что | Значение |
|---|---|
| API | `https://localhost:2000/api/v1` |
| Заголовок | `X-API-Key: <ключ из C:\control\starter\files\crypto\.api_key>` |
| Стартер | `python starter.py` из `C:\control\starter`, переменная `PYTHONIOENCODING=utf-8` |
| Реестр | `C:\ProgramData\starter-registry.json` — источник правды о том, что установлено |
| Логи | `C:\control\starter\logs\` |

Стартер работает по **https с самоподписанным сертификатом**. Для `curl`
нужен `-k`, для Python — отключённая проверка:

```python
import ssl
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
urllib.request.urlopen(req, context=ctx)
```

---

## 2. Типы серверов

Полный список с признаками:

```
GET /api/v1/servers/types
```

Ответ содержит:

| Поле | Смысл |
|---|---|
| `is_client` | это клиент (Laravel + роли + модули) |
| `is_module` | это модуль, ставится **внутрь** клиента через composer |
| `composer_package` | имя пакета для `composer require` |
| `module_path` | путь к каталогу модуля |

Клиенты:

| key | Папка по умолчанию | Репозиторий |
|---|---|---|
| `client` | `client` | imperor/client |
| `clientv2` | `clientv2` | imperor/clientv2 |
| `client_core` | `client-core` | imperor/clientv2 |
| `client_city` | `client-city` | imperor/clientv2 |
| `client_medical` | `CLIENT-MEDICAL` | imperor/clientv2 |

Модули:

| key | Пакет | Таблицы |
|---|---|---|
| `wall` | `imperor/wall` | `post_objects`, `section_objects` + пивоты |
| `shop` | `imperor/shop` | `products`, `categories`, `orders`, `basket` + пивоты |
| `pages` | `imperor/pages` | нет (blade-файлы) |
| `payments` | `imperor/payments` | `payments`, `currencys`, `provaiders`, `payment_statuses` + пивоты |
| `roles` | `imperor/client-roles` | нет (роли в ядре клиента) |

---

## 3. Установка сервера

```
POST /api/v1/servers/install
{"server_type": "clientv2", "path": "C:\\control\\CLIENTv2", "name": "CLIENTv2", "force": true}
```

| Поле | Обязательно | Смысл |
|---|---|---|
| `server_type` | да | ключ из `/servers/types` |
| `path` | да | папка установки. Из неё берётся имя compose-проекта |
| `name` | нет | отображаемое имя |
| `force` | нет | переустановить поверх существующей папки |

Ответ при успехе:

```json
{"status": "success", "message": "AI Помощник v2 установлен в C:\\control\\CLIENTv2"}
```

### Что происходит внутри

Установка и запуск — **два разных вызова**. `install` только готовит
папку, контейнеры поднимает `start`.

**`install`:**

1. Клонирование репозитория типа в `path/code`
2. `composer install` **на хосте** в `path/code` → появляется `vendor/`
3. Выделение подсети Docker (`DOCKER_NETWORK_PREFIX`)
4. Копирование `docker/docker-compose.example` → `docker-compose.yml`
5. Копирование `docker/.env.example` → `docker/.env`
6. **`_copy_docker_payload()`** — перенос `configs/`, `dockerfiles/`, `db/`
   из репозитория в `docker/` (иначе compose создаст на месте файлов
   каталоги — см. раздел 9)
7. **`_apply_instance_env()`** — приведение `.env` к этому экземпляру
8. Подстановка переменных из `.env` в `docker-compose.yml`
9. Регистрация в реестре, отметка установки на myidon.site

**`start`:**

1. Предварительные проверки: docker, `docker compose config`, `.env`,
   наличие образов
2. `docker compose -p <имя_папки> up -d`
3. **`_provision_laravel()`** — только для PHP-серверов, только если в
   `code/` есть `artisan`:
   `config:clear` → `key:generate` (если `APP_KEY` пуст) → `storage:link`
   → `migrate --force`

В ответе `start` шаг `laravel` показывает, что произошло. Если
`migrate` не прошёл, шаг имеет статус `warn` и содержит вывод artisan.

> Почему `key:generate` выполняется только при пустом ключе: смена
> `APP_KEY` делает нечитаемыми сессии, cookie и зашифрованные значения.

### Имя compose-проекта

Берётся из **имени папки установки**, не из `server_type`:

```python
_compose_project_name(server_path, server_type)
# C:\control\client-core  ->  client-core
```

Причина: у всех клиентов каталог называется `docker`, поэтому без явного
`-p` compose взял бы проект из `docker` и все экземпляры управляли бы
одними и теми же контейнерами (`php-clientv2` и т.д.).

---

## 4. Запуск, остановка, удаление

```
POST /api/v1/servers/<path:server_id>/start
POST /api/v1/servers/<path:server_id>/stop
DELETE /api/v1/servers/<path:server_id>/remove
```

`server_id` — **полный путь**, URL-кодированный. Слэши можно заменять на
`%2F`, обратные слэши на `/`:

```
DELETE /api/v1/servers/C%3A%2Fcontrol%2FCLIENTv2/remove
```

Удаление делает `docker compose down -v`, убирает запись из реестра и
**удаляет папку**.

> Файлы `.git` создаются read-only, и на Windows `shutil.rmtree` на них
> падает с `WinError 5`. Раньше исключение глоталось, API отвечал `200`,
> а папка оставалась — следующая установка шла поверх неё. Сейчас есть
> обработчик `onerror`, снимающий атрибут, а статус ответа отражает
> реальность: осталась папка — `success: false`, код `500`.

---

## 5. Установка модулей

Модуль ставится **внутрь клиента** через `composer require` на хосте.

Причины именно такого подхода:

* модуль добавляется в `vendor/` конкретного клиента, а не общий
* у каждого клиента своя копия библиотек: в одном `imperor/wall`, в другом нет
* версии пакетов могут различаться между клиентами
* `composer` на хосте отрабатывает за секунды, в контейнере — минутами

Пути репозиториев в `composer.json` клиента используют `symlink: false`,
поэтому composer **копирует** пакет, а не делает ссылку:

```json
{"type": "path", "url": "C:/control/WALL", "options": {"symlink": false}}
```

### Порядок работы

```
1. найти клиентов, в которые можно поставить модуль  (_module_hosts)
2. проверить, не стоит ли уже
3. проверить, не стоит ли в другом клиенте  -> нужен перенос через заявку
4. добавить path-репозиторий в composer.json клиента
5. composer require <пакет>:@dev   (на хосте)
6. docker exec php-<проект> php artisan migrate --force
7. docker compose -p <проект> up -d --force-recreate php-<проект>
8. отметить в реестре
```

### Ограничения

* Модуль ставится **только в одного клиента**. Если он уже стоит в другом —
  отказ с кодом `TRANSFER_REQUIRES_APPLICATION`
* Повторная установка в тот же клиент — `ALREADY_INSTALLED`
* Хосты ищутся по флагу `is_client` у типа, поэтому новый тип клиента
  подхватывается автоматически, без правок в модулях

### Коды ответа

| Код | Значение |
|---|---|
| `ALREADY_INSTALLED` | пакет уже в этом клиенте |
| `TRANSFER_REQUIRES_APPLICATION` | пакет в другом клиенте, нужен перенос |
| `MIGRATE_FAILED` | пакет поставлен, но миграции не прошли |

`MIGRATE_FAILED` важен: пакет формально установлен, но без таблиц он не
работает. Ответ содержит хвост вывода миграций.

---

## 6. Обновления

```
GET  /api/v1/servers/<path:server_id>/update/plan       # что изменится
GET  /api/v1/servers/<path:server_id>/update/preflight   # готов ли к обновлению
POST /api/v1/servers/<path:server_id>/update             # обновить
POST /api/v1/servers/update-clients                      # все клиенты
```

`update_server` идёт по фазам:

| Фаза | Что делает |
|---|---|
| 0. PREFLIGHT | проверки перед изменением |
| 1. БЭКАП | копия данных, которые можно потерять |
| 2. PULL | `git pull` репозитория |
| 3. ЗАВИСИМОСТИ | `composer install/update` |
| 4. DOCKER-КОНФИГ | обновление `docker-compose.yml` из шаблона |
| 5. МИГРАЦИИ | `artisan migrate --force` |
| 6. ПЕРЕЗАПУСК | пересоздание контейнеров |
| 7. ПРОВЕРКА | контроль результата |

Модули обновляются отдельно:

```
update_module(server_type, host_path, dry_run)
```

Перед обновлением клиента полезно сначала прогнать `plan` и `preflight` —
они ничего не меняют.

---

## 7. Что проверять после установки

```bash
# контейнеры
docker ps --format "{{.Names}} {{.Status}}" | grep client

# таблицы
docker exec mariadb-<проект> mysql -uroot -N -B -e \
  "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='client'"

# миграции
docker exec php-<проект> php artisan migrate:status

# маршруты
docker exec php-<проект> php artisan route:list

# сайт
curl -sk -o /dev/null -w "%{http_code}" https://localhost:<PORT_SSL>/
```

Ожидаемое число маршрутов без модулей — **419**. Каждый модуль добавляет
свои: `shop` +49, `wall` +21.

Число таблиц: ядро — **64**, плюс таблицы модуля
(`shop` +8, `wall` +4, `payments` +8).

---

## 8. Как настраивается экземпляр

Функция `_apply_instance_env()` в `files/web/sections/servers.py` приводит
`docker/.env` к конкретной установке.

**Пути** — `PATH_APP_CODE`, `PATH_APP_PROJECT`, `PATH_APP_DOCKER`,
`PATH_APP_DOCKER_LOGS`, `PATH_APP_STARTER`.

**Имя проекта** — `PROJECTNAME`, `COMPOSE_PROJECT_NAME` из имени папки.

**Хосты сервисов своего compose-проекта.** Ключи сервисов в
`docker-compose.yml` имеют вид `<svc>-${PROJECTNAME}`, поэтому:

```
DB_HOST     = mariadb-<проект>
REDIS_HOST  = redis-<проект>
QDRANT_HOST = http://qdrant-<проект>:6333
```

**Порты.** Подбираются свободные на хосте: HTTP в диапазоне 9000–9199,
SSL в 9400–9599. Перед подбором собираются занятые порты из `.env` всех
проектов реестра (`PORT`, `PORT_SSL` и смещения `*_PLUS`), поэтому порт
не выдаётся дважды.

> Почему это важно. В шаблоне клиента значения были **жёстко зашиты на
> первый экземпляр**: `DB_HOST=mariadb-clientv2`, `REDIS_HOST=redis-clientv2`,
> `PATH_APP_CODE=C:\control\clientv2\code`, а `PORT` был пустым и подставлялся
> как 80. Установщик подставлял `${PATH_APP_*}`, но в шаблоне были готовые
> пути, поэтому подстановка не срабатывала, и второй клиент ходил в базу
> первого. `PORT_SSL`, `DIR_COPY` и `PHP_CONTAINER` отсутствовали вовсе,
> хотя compose их использует, — nginx вставал на 443.

`REVERB_PORT` — **внутренний** порт контейнера, хост не публикуется, поэтму
конфликта между экземплярами нет.

---

## 9. Известные проблемы

| Симптом | Причина | Что делать |
|---|---|---|
| `port is already allocated` | порт занят | `_allocate_client_ports` проверяет занятость; если диапазон исчерпан — поднимается выше |
| Клиент не стартует, в логах `mariadb-clientv2` | в `.env` хост чужого экземпляра | проверить `DB_HOST` / `REDIS_HOST` в `docker/.env` |
| Модуль установлен, таблиц нет | миграции не прошли | `docker exec php-<проект> php artisan migrate --force`, в ответе смотреть `MIGRATE_FAILED` |
| `Interface "App\Models\X" not found` | интерфейс использован без `use` | PHP валиден синтаксически, но падает при загрузке класса; проверять через `artisan optimize` на копии |
| Почта не уходит | сертификат SMTP и пароль | см. раздел 10 |
| `exec: start-supervisor.sh: Permission denied` | в `docker/configs/` нет файлов, compose создал на их месте каталоги | перенести конфиги: `_copy_docker_payload()` при установке |
| `require(/var/www/html/vendor/autoload.php): Failed to open stream` | не установлены зависимости PHP | `composer install` в `path/code` на хосте |
| `Access denied for user 'root'@... (using password: YES)` | `MARIADB_USER=root` в образе MariaDB не создаёт пароль руту | в шаблоне используется `MARIADB_ROOT_PASSWORD` |
| Сайт отдаёт 502 после установки | не инициализирован Laravel: пуст `APP_KEY`, нет миграций | шаг `laravel` в ответе `start`, `docker exec php-<проект> php artisan migrate --force` |
| `Server not found` при `start`/`stop`/`update` | путь из URL не совпал с путём в реестре | вызывать с тем же видом разделителей; в коде пути сверяются нормализованно |
| Ответ `200` со `status: error` | часть проверок возвращает статус в теле, а не кодом | смотреть поле `status` в теле ответа |



---

## 10. Почта

Почта — общая инфраструктура, а не часть клиента, но без неё не работает
подтверждение адреса.

Требования на сервере myidon.site:

1. Сертификат для `mail.<домен>` — валидный, не самоподписанный
2. Учётная запись отправителя в Exim с актуальным паролем
3. SPF (есть), DKIM (нет), DMARC (`p=none` — только наблюдение)

Проверка:

```bash
openssl s_client -connect mail.<домен>:465 -servername mail.<домен> </dev/null \
  | grep "Verify return code"
# должно быть: Verify return code: 0 (ok)
```

При `certificate verify failed` Symfony прерывает отправку до
аутентификации. Временно можно отключить проверку
(`verify_peer=false`), но письма идут шифрованными к **непроверенному**
peer — это временная мера, а не решение.

---

## 11. Скрипт сквозного теста

Полный прогон удаление → установка → модули → обновления:

```
python e2e_test.py               # все фазы
python e2e_test.py delete        # только удаление
python e2e_test.py install       # только установка
python e2e_test.py modules       # только модули
python e2e_test.py updates       # только обновления
```

Фазы выполняются по отдельности и результат пишется в `e2e_result.json`,
поэтому прогон можно продолжить с нужного места.

Скрипт проверяет после установки, что у экземпляров **разные** порты,
хосты БД и пути — именно то, что ломалось при ручной настройке.
