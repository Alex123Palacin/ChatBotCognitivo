#!/bin/sh
set -eu

# Solo el servidor prepara la base. El worker espera su comprobación de salud.
if [ "${1:-}" = "gunicorn" ]; then
    python manage.py migrate --noinput
    python manage.py preparar_admin_produccion
    python manage.py collectstatic --noinput
    python manage.py precalentar_modelo
fi

exec "$@"
