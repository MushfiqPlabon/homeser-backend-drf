from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication


class JWTCookieAuthentication(JWTAuthentication):
    """
    An authentication class that authenticates users based on a JWT cookie.
    """

    def authenticate(self, request):
        """
        Attempts to authenticate the user using a JWT token from a cookie.

        If the token is valid, it returns a user/token tuple.
        Otherwise, it returns None.
        """
        cookie_name = settings.SIMPLE_JWT.get("AUTH_COOKIE")
        if not cookie_name:
            return None

        raw_token = request.COOKIES.get(cookie_name)
        if raw_token is None:
            return None

        try:
            validated_token = self.get_validated_token(raw_token)
            return self.get_user(validated_token), validated_token
        except Exception:
            return None
