# Переменные окружения
EMAIL_TO="logs@myidon.site"
PROJECT="${PROJECT_NAME}"
LOG_DIR="/var/log/php"
TMP_DIR="/tmp"

# Создание архива
TS=$(date +%Y%m%d-%H%M%S)
ARCHIVE="${TMP_DIR}/${PROJECT}_logs_${TS}.tar.gz"

# Архивируем логи
tar -czf "${ARCHIVE}" -C "${LOG_DIR}" . || {
    echo "$(date) - Ошибка архивации" >> "${LOG_DIR}/sender-error.log"
    exit 1
}

# Формируем письмо с вложением
BOUNDARY="BOUNDARY-$(date +%s)"
(
    echo "From: ${PROJECT}-noreply@myidon.site"
    echo "To: ${EMAIL_TO}"
    echo "Subject: [${PROJECT}] Логи ${TS}"
    echo "MIME-Version: 1.0"
    echo "Content-Type: multipart/mixed; boundary=\"${BOUNDARY}\""
    echo ""
    echo "--${BOUNDARY}"
    echo "Content-Type: text/plain; charset=UTF-8"
    echo ""
    echo "Логи проекта за ${TS}"
    echo ""
    echo "--${BOUNDARY}"
    echo "Content-Type: application/gzip; name=\"$(basename ${ARCHIVE})\""
    echo "Content-Disposition: attachment; filename=\"$(basename ${ARCHIVE})\""
    echo "Content-Transfer-Encoding: base64"
    echo ""
    base64 "${ARCHIVE}"
    echo "--${BOUNDARY}--"
) | sendmail -t -i

# Проверка результата
if [ $? -ne 0 ]; then
    echo "$(date) - Ошибка отправки" >> "${LOG_DIR}/sender-error.log"
    rm -f "${ARCHIVE}"
    exit 2
fi

rm -f "${ARCHIVE}"
exit 0