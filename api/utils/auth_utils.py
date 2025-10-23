from django.conf import settings


def set_auth_cookies(response, access_token, refresh_token):
    """
    Set authentication cookies with proper security settings.

    Args:
        response: The DRF Response object
        access_token: The JWT access token
        refresh_token: The JWT refresh token
    """
    # Calculate cookie lifetimes from settings
    access_token_lifetime = int(
        settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()
    )
    refresh_token_lifetime = int(
        settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()
    )

    # Set httpOnly cookies for better security
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.SIMPLE_JWT.get("AUTH_COOKIE_SECURE", False),
        samesite=settings.SIMPLE_JWT.get("AUTH_COOKIE_SAMESITE", "Lax"),
        max_age=access_token_lifetime,
        path=settings.SIMPLE_JWT.get("AUTH_COOKIE_PATH", "/"),
    )

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.SIMPLE_JWT.get("AUTH_COOKIE_SECURE", False),
        samesite=settings.SIMPLE_JWT.get("AUTH_COOKIE_SAMESITE", "Lax"),
        max_age=refresh_token_lifetime,
        path=settings.SIMPLE_JWT.get("AUTH_COOKIE_PATH", "/"),
    )

    return response


def set_refresh_auth_cookies(response, new_access_token=None, new_refresh_token=None):
    """
    Set authentication cookies during token refresh with proper security settings.
    Conditionally sets cookies based on which tokens are provided.

    Args:
        response: The DRF Response object
        new_access_token: The new JWT access token (optional)
        new_refresh_token: The new JWT refresh token (optional)
    """
    # Calculate cookie lifetimes from settings
    access_token_lifetime = int(
        settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()
    )
    refresh_token_lifetime = int(
        settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()
    )

    # Set the new access token as a cookie if provided
    if new_access_token:
        response.set_cookie(
            key="access_token",
            value=new_access_token,
            httponly=True,
            secure=settings.SIMPLE_JWT.get("AUTH_COOKIE_SECURE", False),
            samesite=settings.SIMPLE_JWT.get("AUTH_COOKIE_SAMESITE", "Lax"),
            max_age=access_token_lifetime,
            path=settings.SIMPLE_JWT.get("AUTH_COOKIE_PATH", "/"),
        )

    # If a new refresh token was issued, set it as a cookie
    if new_refresh_token:
        response.set_cookie(
            key="refresh_token",
            value=new_refresh_token,
            httponly=True,
            secure=settings.SIMPLE_JWT.get("AUTH_COOKIE_SECURE", False),
            samesite=settings.SIMPLE_JWT.get("AUTH_COOKIE_SAMESITE", "Lax"),
            max_age=refresh_token_lifetime,
            path=settings.SIMPLE_JWT.get("AUTH_COOKIE_PATH", "/"),
        )

    return response
