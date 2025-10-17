# homeser/asgi.py
# This file configures the Asynchronous Server Gateway Interface (ASGI) for the HomeSer project.
# ASGI is a spiritual successor to WSGI, providing a standard interface between
# async-capable Python web servers, frameworks, and applications.
# It's used for handling websockets and long-polling connections.

"""ASGI config for homeser project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

import api.routing

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "homeser.settings")

application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": AllowedHostsOriginValidator(
            AuthMiddlewareStack(URLRouter(api.routing.websocket_urlpatterns))
        ),
    }
)
