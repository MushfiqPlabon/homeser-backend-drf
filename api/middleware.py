import json

from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import AccessToken

User = get_user_model()


class JWTAuthMiddleware:
    """
    Custom middleware to authenticate WebSocket connections using JWT tokens
    from httpOnly cookies. This middleware extracts the access token from
    cookies and authenticates the user.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        # Extract cookies from the scope headers
        headers = dict(scope.get("headers", []))

        # Look for access token in cookies
        cookie_header = headers.get(b"cookie")
        if cookie_header:
            cookies = self._parse_cookies(cookie_header.decode("utf-8"))
            access_token = cookies.get("access_token")

            if access_token:
                user = await self.get_user_from_token(access_token)
                scope["user"] = user
            else:
                scope["user"] = AnonymousUser()
        else:
            scope["user"] = AnonymousUser()

        return await self.app(scope, receive, send)

    def _parse_cookies(self, cookie_string):
        """
        Parse cookie string into a dictionary of key-value pairs.
        """
        cookies = {}
        if cookie_string:
            cookie_pairs = cookie_string.split(";")
            for pair in cookie_pairs:
                if "=" in pair:
                    key, value = pair.split("=", 1)
                    cookies[key.strip()] = value.strip()
        return cookies

    @database_sync_to_async
    def get_user_from_token(self, token):
        """
        Get user from JWT token.
        """
        try:
            # Decode the access token
            access_token = AccessToken(token)
            user_id = access_token.get("user_id")

            # Fetch the user from the database
            try:
                user = User.objects.get(id=user_id)
                return user
            except User.DoesNotExist:
                return AnonymousUser()
        except (InvalidToken, TokenError, json.JSONDecodeError):
            # If token is invalid, return anonymous user
            return AnonymousUser()


# Helper function to wrap an ASGI application with JWTAuthMiddleware
def JWTAuthMiddlewareStack(inner):
    return JWTAuthMiddleware(inner)
