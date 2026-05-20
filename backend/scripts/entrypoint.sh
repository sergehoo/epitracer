#!/usr/bin/env bash
# Entrypoint container backend EpidemiTracker.
# Selon la commande passée, exécute le rôle approprié.
set -euo pipefail

cd /app

echo ">>> EpidemiTracker backend - $(date -u +"%Y-%m-%dT%H:%M:%SZ")"

# Attente Postgres si DATABASE_URL définie
if [ -n "${DATABASE_URL:-}" ]; then
  python -c "
import os, time, sys
from urllib.parse import urlparse
import socket
u = urlparse(os.environ['DATABASE_URL'])
host, port = u.hostname, u.port or 5432
deadline = time.time() + 60
while time.time() < deadline:
    try:
        with socket.create_connection((host, port), timeout=2):
            print(f'Postgres OK ({host}:{port})')
            sys.exit(0)
    except OSError:
        time.sleep(1)
print('Postgres injoignable', file=sys.stderr)
sys.exit(1)
"
fi

case "${1:-}" in
  web|gunicorn|"")
    echo ">>> Migrations + collectstatic"
    python manage.py migrate --noinput
    python manage.py collectstatic --noinput
    echo ">>> Démarrage Gunicorn"
    exec gunicorn config.wsgi:application \
        --bind 0.0.0.0:8000 \
        --workers "${GUNICORN_WORKERS:-3}" \
        --threads "${GUNICORN_THREADS:-2}" \
        --timeout "${GUNICORN_TIMEOUT:-60}" \
        --access-logfile - --error-logfile -
    ;;
  asgi|daphne)
    echo ">>> Migrations + collectstatic (asgi)"
    python manage.py migrate --noinput
    python manage.py collectstatic --noinput
    echo ">>> Démarrage Daphne (ASGI - WebSocket)"
    exec daphne -b 0.0.0.0 -p 8001 config.asgi:application
    ;;
  worker)
    echo ">>> Démarrage Celery worker"
    exec celery -A config worker -l info -Q default,notifications,quarantine,passes,surveillance --concurrency="${CELERY_CONCURRENCY:-4}"
    ;;
  beat)
    echo ">>> Démarrage Celery beat"
    exec celery -A config beat -l info
    ;;
  shell)
    exec python manage.py shell_plus
    ;;
  *)
    exec "$@"
    ;;
esac
