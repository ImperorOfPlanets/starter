#!/bin/sh
set -e

LOG_DIR="/var/log/nginx"
mkdir -p "$LOG_DIR"
ENTRYPOINT_LOG="$LOG_DIR/entrypoint.log"

entrypoint_log() {
    local message="$@"
    [ -z "${NGINX_ENTRYPOINT_QUIET_LOGS:-}" ] && echo "$message"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $message" >> "$ENTRYPOINT_LOG"
}

entrypoint_log "=== Starting Nginx Entrypoint ==="

export MAX_BODY_SIZE=${MAX_BODY_SIZE:-8M}
entrypoint_log "MAX_BODY_SIZE set to: $MAX_BODY_SIZE"

if [ "$1" = "nginx" -o "$1" = "nginx-debug" ]; then
    if find "/docker-entrypoint.d/" -mindepth 1 -print -quit 2>/dev/null | grep -q .; then
        entrypoint_log "Processing /docker-entrypoint.d/"
        find "/docker-entrypoint.d/" -follow -type f -print | sort -n | while read -r f; do
            case "$f" in
                *.sh)
                    if [ -x "$f" ]; then
                        entrypoint_log "Executing: $f"
                        "$f" >> "$ENTRYPOINT_LOG" 2>&1
                    fi
                    ;;
                *) entrypoint_log "Skipping: $f";;
            esac
        done
    fi
fi

entrypoint_log "Generating Nginx config..."
cat /etc/nginx/templates/default.conf.template | \
    sed 's/\${MAX_BODY_SIZE}/'"${MAX_BODY_SIZE}"'/g' | \
    sed 's/\${NGINX_DOMAIN}/'"${NGINX_DOMAIN}"'/g' > /etc/nginx/conf.d/default.conf

# Выводим конфиг в лог и на экран
entrypoint_log "Generated Nginx configuration content:"
[ -z "${NGINX_ENTRYPOINT_QUIET_LOGS:-}" ] && cat /etc/nginx/conf.d/default.conf
cat /etc/nginx/conf.d/default.conf >> "$ENTRYPOINT_LOG"

entrypoint_log "Generated config validation:"
nginx -t >> "$ENTRYPOINT_LOG" 2>&1

exec "$@"