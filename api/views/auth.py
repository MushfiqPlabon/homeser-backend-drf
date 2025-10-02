from django.contrib.auth import get_user_model
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView as SimpleJWTTokenRefreshView

from utils.response_utils import format_error_response

from ..serializers import (
    UserLoginSerializer,
    UserRegistrationSerializer,
    UserSerializer,
)
from ..services.user_service import UserService
from ..unified_base_views import (
    UnifiedBaseGenericView,
)


class TokenRefreshView(SimpleJWTTokenRefreshView):
    """
    Custom token refresh view that extends SimpleJWT's TokenRefreshView.
    This endpoint allows clients to refresh their access token using a refresh token.

    Returns:
    - access (str): New access token
    - refresh (str, optional): New refresh token if rotation is enabled
    """

    def post(self, request, *args, **kwargs):
        # Call the parent post method to handle the token refresh
        response = super().post(request, *args, **kwargs)

        # If the response indicates success, return it as-is since SimpleJWT
        # already formats it correctly with access and refresh tokens
        if response.status_code == 200:
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


User = get_user_model()


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

            return Response(
                {
                    "user": UserSerializer(user).data,
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                },
                status=status.HTTP_201_CREATED,
            )
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

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        # Generate JWT (JSON Web Token) tokens for the authenticated user.
        # 'refresh' token is used to obtain new 'access' tokens after they expire.
        # 'access' token is used for authenticating subsequent API requests.
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserSerializer(user).data,
            },
        )
