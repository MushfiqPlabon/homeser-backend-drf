"""Common view base classes for the HomeSer backend.
This module provides standardized base classes for all view implementations.
"""

import logging

from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, viewsets

from utils.response_utils import format_error_response

logger = logging.getLogger(__name__)


class BaseViewMixin:
    """Simplified mixin that provides common functionality for all views."""

    service_class = None  # Must be set in subclasses

    def get_service(self):
        """Get the service class instance."""
        if not self.service_class:
            raise ValueError("service_class must be set in subclass")
        return self.service_class

    def handle_exception(self, exception):
        """Handle exceptions in a standardized way.

        Args:
            exception (Exception): The exception to handle

        Returns:
            Response: Formatted error response

        """
        from rest_framework import serializers
        from rest_framework.exceptions import (AuthenticationFailed,
                                               MethodNotAllowed,
                                               NotAuthenticated, NotFound,
                                               ParseError, PermissionDenied)

        # Handle authentication and permission exceptions
        if isinstance(exception, (NotAuthenticated, AuthenticationFailed)):
            return format_error_response(
                error_code="AUTHENTICATION_ERROR",
                message="Authentication credentials were not provided or are invalid",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )
        if isinstance(exception, PermissionDenied):
            return format_error_response(
                error_code="PERMISSION_DENIED",
                message="You do not have permission to perform this action",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        # Handle DRF standard exceptions
        if isinstance(exception, NotFound):
            return format_error_response(
                error_code="NOT_FOUND",
                message=str(exception),
                status_code=status.HTTP_404_NOT_FOUND,
            )
        if isinstance(exception, (MethodNotAllowed, ParseError)):
            return format_error_response(
                error_code="BAD_REQUEST",
                message=str(exception),
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Handle ValidationError specifically
        if isinstance(exception, serializers.ValidationError):
            return format_error_response(
                error_code="VALIDATION_ERROR",
                message=str(exception),
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        logger.error(f"Unhandled exception in view: {exception}")
        return format_error_response(
            error_code="INTERNAL_ERROR",
            message="An internal error occurred",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


class BaseViewSet(viewsets.ModelViewSet, BaseViewMixin):
    """Simplified base ViewSet with common functionality."""

    permission_classes = [permissions.IsAuthenticated]

    def handle_exception(self, exception):
        """Handle exceptions with proper error formatting."""
        from rest_framework import serializers
        from rest_framework.exceptions import (AuthenticationFailed,
                                               MethodNotAllowed,
                                               NotAuthenticated, NotFound,
                                               ParseError, PermissionDenied)

        if isinstance(exception, (NotAuthenticated, AuthenticationFailed)):
            return format_error_response(
                error_code="AUTHENTICATION_ERROR",
                message="Authentication credentials were not provided or are invalid",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )
        if isinstance(exception, PermissionDenied):
            return format_error_response(
                error_code="PERMISSION_DENIED",
                message="You do not have permission to perform this action",
                status_code=status.HTTP_403_FORBIDDEN,
            )
        if isinstance(exception, NotFound):
            return format_error_response(
                error_code="NOT_FOUND",
                message=str(exception),
                status_code=status.HTTP_404_NOT_FOUND,
            )
        if isinstance(
            exception, (MethodNotAllowed, ParseError, PermissionError, ValueError)
        ):
            return format_error_response(
                error_code="BAD_REQUEST",
                message=str(exception),
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        if isinstance(exception, serializers.ValidationError):
            return format_error_response(
                error_code="VALIDATION_ERROR",
                message=str(exception),
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        # For other exceptions, return a generic error with 500 status
        logger.error(f"Unhandled exception in view: {exception}")
        return format_error_response(
            error_code="INTERNAL_ERROR",
            message="An internal error occurred",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    def get_object_or_404(self, obj_id):
        """Get an object by ID or raise 404.

        Args:
            obj_id (int): ID of the object

        Returns:
            Model instance

        """
        if hasattr(self, "get_model") and self.get_model():
            return get_object_or_404(self.get_model(), id=obj_id)
        return get_object_or_404(self.queryset.model, id=obj_id)

    def get_queryset(self):
        """Get the base queryset for this view.

        Returns:
            QuerySet: Base queryset

        """
        if hasattr(self, "model_class") and self.model_class:
            return self.model_class.objects.all()
        return super().get_queryset()


class ReadOnlyViewSet(BaseViewSet):
    """Base read-only viewset with common functionality."""

    def __init__(self, *args, **kwargs):
        """Initialize the viewset with read-only HTTP methods."""
        super().__init__(*args, **kwargs)
        # Restrict to read-only methods
        self.http_method_names = ["get", "head", "options"]


class UserViewSet(ReadOnlyViewSet):
    """Base viewset for user-specific data with automatic user filtering."""

    def get_queryset(self):
        """Filter queryset to only include data for the current user."""
        queryset = super().get_queryset()
        if hasattr(queryset.model, "user"):
            return queryset.filter(user=self.request.user)
        return queryset


class AdminViewSet(BaseViewSet):
    """Base viewset for admin operations with standardized admin permissions."""

    def get_permissions(self):
        """Set admin-specific permissions."""
        from ..permissions import UniversalObjectPermission

        return [permissions.IsAuthenticated(), UniversalObjectPermission()]


# Export simplified classes for convenience
__all__ = [
    "AdminViewSet",
    "BaseViewMixin",
    "BaseViewSet",
    "ReadOnlyViewSet",
    "UserViewSet",
]
