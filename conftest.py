"""
Pytest configuration for ID Service backend tests.
Uses SQLite in-memory database for fast testing.
"""

import os
import django

# Force test settings module BEFORE Django loads any settings
os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings_test"

# Setup Django
if not django.apps.apps.ready:
    django.setup()
