#!/bin/bash
#!/bin/bash

# Проверка существования app.py
if [ ! -f "/app/app.py" ]; then
  echo "ERROR: app.py not found in /app directory!"
  exit 1
fi

if [ "$DEVICE" = "cuda" ] || 
   ([ "$DEVICE" = "auto" ] && nvidia-smi -L 2>/dev/null); then
  workers=1
  device=cuda
else
  workers=$(($(nproc) / 2))
  device=cpu
fi

[ $workers -lt 1 ] && workers=1

if [ -n "$UVICORN_WORKERS" ] && [ "$UVICORN_WORKERS" != "auto" ]; then
  workers=$UVICORN_WORKERS
fi

echo "Using $workers workers with device $device"
exec uvicorn app:app --host 0.0.0.0 --port 5000 --workers $workers