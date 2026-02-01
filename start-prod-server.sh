#!/bin/sh
python manage.py migrate
python manage.py collectstatic --noinput
gunicorn config.wsgi --bind 0.0.0.0:8001 --timeout 60 --access-logfile - --error-logfile -