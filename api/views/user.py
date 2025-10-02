from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import generics, permissions, status
from rest_framework.response import Response

from ..serializers import (
    AdminPromoteSerializer,
    UserProfileSerializer,
    UserRegistrationSerializer,
    UserSerializer,
)
from ..services.user_service import UserService
from ..unified_base_views import (
    CRUDTemplateMixin,
    UnifiedAdminViewSet,
    UnifiedBaseGenericView,
)

User = get_user_model()


class ProfileView(UnifiedBaseGenericView, generics.RetrieveUpdateAPIView):
    """User profile endpoint"""

    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    service_class = UserService

    def get_object(self):
        return self.get_service().get_user_profile(self.request.user)

    def update(self, request, *args, **kwargs):
        """Update user profile"""
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        try:
            # Use UserService to update profile
            profile = self.get_service().update_user_profile(
                self.request.user,
                serializer.validated_data,
            )
            serializer.instance = profile
            return Response(serializer.data)
        except Exception as e:
            return self.handle_service_exception(e)


class AdminPromoteUserView(UnifiedBaseGenericView, generics.CreateAPIView):
    """Promote user to admin (staff) - only admins can do this"""

    serializer_class = AdminPromoteSerializer
    permission_classes = [permissions.IsAuthenticated]
    service_class = UserService

    def create(self, request, *args, **kwargs):
        """Promote user to admin (staff) - only admins can do this"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_id = serializer.validated_data["user_id"]

        try:
            # Use UserService to promote user
            user = self.get_service().promote_user_to_admin(user_id, request.user)

            return Response(
                {
                    "message": f"User {user.get_full_name()} has been promoted to admin",
                    "user": UserSerializer(user).data,
                },
            )
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_403_FORBIDDEN)


@extend_schema(
    parameters=[
        OpenApiParameter(
            name="id",
            type=int,
            location=OpenApiParameter.PATH,
            description="A unique integer value identifying this user.",
        )
    ]
)
class AdminUserViewSet(UnifiedAdminViewSet, CRUDTemplateMixin):
    """Admin user management endpoints"""

    service_class = UserService
    permission_classes = [permissions.IsAdminUser]
    serializer_class = UserSerializer

    def get_queryset(self):
        """Get users with related data for admin view"""
        if getattr(self, "swagger_fake_view", False):
            # Return an empty queryset when generating schema
            return User.objects.none()
        return super().get_queryset().select_related("profile")

    def get_permissions(self):
        """Get permissions for admin endpoints"""
        return [permissions.IsAdminUser()]

    def get_serializer_class(self):
        """Get appropriate serializer based on action"""
        if self.action == "create":
            return UserRegistrationSerializer
        return UserSerializer

    def perform_create(self, serializer):
        """Create user with appropriate permissions"""
        serializer.save()
        # Admins can create users

    def get_object(self):
        """Get a specific user by ID"""
        # Permission checking is handled in the service layer
        return super().get_object()

    def create(self, request, *args, **kwargs):
        """Create a new user"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            # Use UserService to create user
            user = self.get_service().create_user(serializer.validated_data)
            serializer.instance = user
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return self.handle_service_exception(e)

    def update(self, request, *args, **kwargs):
        """Update a user"""
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        try:
            # Use UserService to update user
            user = self.get_service().update_user(
                instance.id,
                serializer.validated_data,
                request.user,
            )
            serializer.instance = user
            return Response(serializer.data)
        except Exception as e:
            return self.handle_service_exception(e)

    def destroy(self, request, *args, **kwargs):
        """Delete a user"""
        instance = self.get_object()

        try:
            # Use UserService to delete user
            self.get_service().delete_user(instance.id, request.user)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            if "cannot delete your own account" in str(e):
                return Response(
                    {"success": False, "message": str(e)},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return self.handle_service_exception(e)
