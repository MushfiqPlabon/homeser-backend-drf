from django.conf import settings
from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import \
    TokenRefreshView as SimpleJWTTokenRefreshView

from utils.response_utils import format_error_response

from ..serializers import (UserLoginSerializer, UserRegistrationSerializer,
                           UserSerializer)
from ..services.user_service import UserService
from ..throttling import LoginAttemptsThrottle, RegistrationThrottle
from ..unified_base_views import UnifiedBaseGenericView

User = get_user_model()


class TokenRefreshView(SimpleJWTTokenRefreshView):
    """
    Custom token refresh view that extends SimpleJWT's TokenRefreshView.
    This endpoint allows clients to refresh their access token using a refresh token.

    Returns:
    - access (str): New access token
    - refresh (str, optional): New refresh token if rotation is enabled
    """

    def post(self, request, *args, **kwargs):
        # Get refresh token from cookies if available
        refresh_token = request.COOKIES.get("refresh_token")

        # If refresh token is in cookies, add it to request data
        if refresh_token and not request.data.get("refresh"):
            request.data._mutable = True
            request.data["refresh"] = refresh_token
            request.data._mutable = False

        # Call the parent post method to handle the token refresh
        response = super().post(request, *args, **kwargs)

        # If the response indicates success, return it as-is since SimpleJWT
        # already formats it correctly with access and refresh tokens
        if response.status_code == 200:
            # Set the new access token as a cookie
            new_access_token = response.data.get("access")
            if new_access_token:
                access_token_lifetime = int(
                    settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()
                )

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
            new_refresh_token = response.data.get("refresh")
            if new_refresh_token:
                refresh_token_lifetime = int(
                    settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()
                )

                response.set_cookie(
                    key="refresh_token",
                    value=new_refresh_token,
                    httponly=True,
                    secure=settings.SIMPLE_JWT.get("AUTH_COOKIE_SECURE", False),
                    samesite=settings.SIMPLE_JWT.get("AUTH_COOKIE_SAMESITE", "Lax"),
                    max_age=refresh_token_lifetime,
                    path=settings.SIMPLE_JWT.get("AUTH_COOKIE_PATH", "/"),
                )

            # Remove tokens from response data for security
            if "access" in response.data:
                del response.data["access"]
            if "refresh" in response.data:
                del response.data["refresh"]

            response.data["message"] = "Token refreshed successfully"

            return response

        # If there was an error, format it using our standard error format
        # Get the original error response from SimpleJWT
        try:
            original_error = response.data
            if "detail" in original_error and "code" in original_error:
                # Format using standard error response
                return format_error_response(
                    error_code=original_error.get("code", "TOKEN_ERROR"),
                    message=original_error.get("detail", "Token refresh failed"),
                    status_code=response.status_code,
                )
        except Exception:
            # If there's an issue processing the original error, return a generic error
            return format_error_response(
                error_code="TOKEN_REFRESH_ERROR",
                message="Token refresh failed",
                status_code=response.status_code,
            )

        return response


class LogoutSerializer(serializers.Serializer):
    """Serializer for logout endpoint"""

    refresh = serializers.CharField(
        required=False, help_text="Refresh token to blacklist"
    )


@extend_schema(
    request=LogoutSerializer,
    responses={200: {"type": "object", "properties": {"detail": {"type": "string"}}}},
    description="Logout user and invalidate tokens",
)
class LogoutView(UnifiedBaseGenericView):
    """
    API endpoint for user logout.
    Clears authentication cookies from the client.
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = LogoutSerializer

    def post(self, request, *args, **kwargs):
        """
        Handle user logout by clearing authentication cookies.
        """
        response = Response(
            {"message": "Logged out successfully"}, status=status.HTTP_200_OK
        )

        # Clear authentication cookies
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")

        return response


class RegisterView(UnifiedBaseGenericView):
    """API endpoint for user registration.

    Features:
    - Create a new user account with username, email, and password
    - Automatically creates a user profile upon successful registration
    - Returns JWT authentication tokens for immediate login

    No authentication required - available to all users.
    """

    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [RegistrationThrottle]

    def post(self, request, *args, **kwargs):
        """Handle user registration via POST request"""
        return self.create(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            # Use UserService to create user
            user = UserService.create_user(serializer.validated_data)

            # Generate JWT (JSON Web Token) tokens for the newly registered user.
            # 'refresh' token is used to obtain new 'access' tokens after they expire.
            # 'access' token is used for authenticating subsequent API requests.
            refresh = RefreshToken.for_user(user)

            # Set tokens as httpOnly cookies
            response_data = {
                "user": UserSerializer(user).data,
                "message": "Registration successful",
            }

            response = Response(response_data, status=status.HTTP_201_CREATED)

            # Set httpOnly cookies for better security
            access_token_lifetime = int(
                settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()
            )
            refresh_token_lifetime = int(
                settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()
            )

            response.set_cookie(
                key="access_token",
                value=str(refresh.access_token),
                httponly=True,
                secure=settings.SIMPLE_JWT.get("AUTH_COOKIE_SECURE", False),
                samesite=settings.SIMPLE_JWT.get("AUTH_COOKIE_SAMESITE", "Lax"),
                max_age=access_token_lifetime,
                path=settings.SIMPLE_JWT.get("AUTH_COOKIE_PATH", "/"),
            )

            response.set_cookie(
                key="refresh_token",
                value=str(refresh),
                httponly=True,
                secure=settings.SIMPLE_JWT.get("AUTH_COOKIE_SECURE", False),
                samesite=settings.SIMPLE_JWT.get("AUTH_COOKIE_SAMESITE", "Lax"),
                max_age=refresh_token_lifetime,
                path=settings.SIMPLE_JWT.get("AUTH_COOKIE_PATH", "/"),
            )

            return response
        except Exception as e:
            return self.handle_exception(e)


class LoginView(UnifiedBaseGenericView):
    """API endpoint for user login.

    Features:
    - Authenticate users using username/email and password
    - Returns JWT access and refresh tokens for API authentication
    - Supports login with either username or email

    No authentication required - available to all users.
    """

    serializer_class = UserLoginSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [LoginAttemptsThrottle]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        # Generate JWT (JSON Web Token) tokens for the authenticated user.
        # 'refresh' token is used to obtain new 'access' tokens after they expire.
        # 'access' token is used for authenticating subsequent API requests.
        refresh = RefreshToken.for_user(user)

        # Set tokens as httpOnly cookies
        response_data = {
            "message": "Login successful",
            "user": UserSerializer(user).data,
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }

        response = Response(response_data)

        # Set httpOnly cookies for better security
        access_token_lifetime = int(
            settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()
        )
        refresh_token_lifetime = int(
            settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()
        )

        response.set_cookie(
            key="access_token",
            value=str(refresh.access_token),
            httponly=True,
            secure=settings.SIMPLE_JWT.get("AUTH_COOKIE_SECURE", False),
            samesite=settings.SIMPLE_JWT.get("AUTH_COOKIE_SAMESITE", "Lax"),
            max_age=access_token_lifetime,
            path=settings.SIMPLE_JWT.get("AUTH_COOKIE_PATH", "/"),
        )

        response.set_cookie(
            key="refresh_token",
            value=str(refresh),
            httponly=True,
            secure=settings.SIMPLE_JWT.get("AUTH_COOKIE_SECURE", False),
            samesite=settings.SIMPLE_JWT.get("AUTH_COOKIE_SAMESITE", "Lax"),
            max_age=refresh_token_lifetime,
            path=settings.SIMPLE_JWT.get("AUTH_COOKIE_PATH", "/"),
        )

        return response
