import os
import sys

import django
from django.conf import settings

# Ensure the project directory is in the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set the Django settings module if not already set
if not settings.configured:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "homeser.settings")

# Setup Django
django.setup()


def pytest_configure():
    from django.conf import settings

    if not settings.configured:
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "homeser.settings")
        django.setup()
