# homeser/wsgi.py
# This file configures the Web Server Gateway Interface (WSGI) for the HomeSer project.
# WSGI is a standard interface between Python web servers and web applications,
# allowing them to communicate. It's used for handling traditional synchronous HTTP requests.

"""
WSGI config for homeser project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "homeser.settings")

application = get_wsgi_application()
