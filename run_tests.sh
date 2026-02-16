#!/bin/bash
export DATABASE_URL="sqlite:///test_db.sqlite3"
export DJANGO_DEBUG=True
export DJANGO_SECRET_KEY="test-key-for-testing-purposes"
export DJANGO_ALLOWED_HOSTS="localhost,testserver"
export DJANGO_SETTINGS_MODULE="config.settings"

python -m pytest "$@"
