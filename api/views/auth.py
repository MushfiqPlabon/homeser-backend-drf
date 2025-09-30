from django.contrib.auth import get_user_model
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from ..serializers import (
    UserLoginSerializer,
    UserRegistrationSerializer,
    UserSerializer,
)
from ..services.user_service import UserService
from ..unified_base_views import (
    UnifiedBaseGenericView,
)

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
