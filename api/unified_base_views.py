"""Unified base view classes for the HomeSer backend.
This module provides standardized, optimized base classes for all view implementations.
Consolidated to eliminate redundancy and improve maintainability.
"""

from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, serializers, status, viewsets

from api.views.common_view_base import (
    BaseViewMixin,
)
from utils.response_utils import format_error_response, format_success_response


class UnifiedBaseViewSet(
    BaseViewMixin,
    viewsets.ModelViewSet,
):
    """Unified base viewset that can be configured for read-only or full CRUD operations.
    Provides standardized error handling, permission checking, and service integration.
    """

    permission_classes = [permissions.IsAuthenticated]

    model_class = None  # Must be set in subclasses
    service_class = None  # Must be set in subclasses for service integration
    read_only = False  # Set to True for read-only operations

    def __init__(self, *args, **kwargs):
        """Initialize the viewset and configure HTTP methods based on read_only flag."""
        super().__init__(*args, **kwargs)
        if self.read_only:
            # Restrict to read-only methods
            self.http_method_names = ["get", "head", "options"]

    def get_service(self):
        """Get the service class instance."""
        if not self.service_class:
            raise ValueError("service_class must be set in subclass")
        return self.service_class

    def get_queryset(self):
        """Return the base queryset for the viewset."""
        if self.model_class:
            return self.model_class.objects.all()
        return super().get_queryset()

    def get_object(self):
        """Get a specific object by ID with permission checking."""
        if not self.model_class:
            return super().get_object()

        # Get object by primary key
        pk = self.kwargs.get("pk")
        obj = get_object_or_404(self.model_class, pk=pk)
        return obj

    def handle_exception(self, exception):
        """Handle exceptions in a standardized way.

        Args:
            exception (Exception): The exception to handle

        Returns:
            Response: Formatted error response

        """
        from rest_framework.exceptions import (
            AuthenticationFailed,
            NotAuthenticated,
            PermissionDenied,
        )

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
        if isinstance(exception, (PermissionError, ValueError)):
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
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Unhandled exception in view: {exception}")
        return format_error_response(
            error_code="INTERNAL_ERROR",
            message="An internal error occurred",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


class UnifiedBaseGenericView(
    BaseViewMixin,
    generics.GenericAPIView,
):
    """Unified base generic view with common functionality for all generic views.
    Provides standardized error handling, permission checking, and service integration.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return the base queryset for the view."""
        if hasattr(self, "model_class") and self.model_class:
            return self.model_class.objects.all()
        return super().get_queryset()


class UnifiedBaseReadOnlyViewSet(UnifiedBaseViewSet):
    """Base read-only viewset with common functionality."""

    def __init__(self, *args, **kwargs):
        self.read_only = True
        super().__init__(*args, **kwargs)


class UnifiedReadOnlyViewSet(UnifiedBaseViewSet):
    """Base read-only viewset with common functionality."""

    def __init__(self, *args, **kwargs):
        self.read_only = True
        super().__init__(*args, **kwargs)


class UnifiedCRUDViewSet(UnifiedBaseViewSet):
    """Base viewset for full CRUD operations with standardized functionality."""

    def __init__(self, *args, **kwargs):
        self.read_only = False
        super().__init__(*args, **kwargs)


class UnifiedUserViewSet(UnifiedReadOnlyViewSet):
    """Base viewset for user-specific data with automatic user filtering."""

    def get_queryset(self):
        """Filter queryset to only include data for the current user."""
        queryset = super().get_queryset()
        if hasattr(queryset.model, "user"):
            return queryset.filter(user=self.request.user)
        return queryset


class UnifiedAdminViewSet(UnifiedCRUDViewSet):
    """Base viewset for admin operations with standardized admin permissions."""

    permission_classes = [permissions.IsAdminUser]


class CRUDTemplateMixin:
    """Template method pattern for CRUD operations."""

    def create(self, request, *args, **kwargs):
        """Template method for create operation."""
        self._before_create(request)
        response = self._perform_create(request)
        self._after_create(request, response)
        return response

    def _before_create(self, request):
        """Hook method called before create."""
        # Default implementation: no additional processing needed
        # Subclasses can override to provide custom pre-create processing

    def _perform_create(self, request):
        """Core create logic."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            service = self.get_service()
            instance = service.create(serializer.validated_data, request.user)
            serializer.instance = instance
            return format_success_response(
                data=serializer.data,
                message="Resource created successfully",
                status_code=status.HTTP_201_CREATED,
            )
        except Exception as e:
            return self.handle_exception(e)

    def _after_create(self, request, response):
        """Hook method called after create."""
        # Default implementation: no additional processing needed
        # Subclasses can override to provide custom post-create processing

    def update(self, request, *args, **kwargs):
        """Template method for update operation."""
        self._before_update(request)
        response = self._perform_update(request, *args, **kwargs)
        self._after_update(request, response)
        return response

    def _before_update(self, request):
        """Hook method called before update."""
        # Default implementation: no additional processing needed
        # Subclasses can override to provide custom pre-update processing

    def _perform_update(self, request, *args, **kwargs):
        """Core update logic."""
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        try:
            service = self.get_service()
            updated_instance = service.update(
                instance.id,
                serializer.validated_data,
                request.user,
            )
            serializer.instance = updated_instance
            return format_success_response(
                data=serializer.data,
                message="Resource updated successfully",
            )
        except Exception as e:
            return self.handle_exception(e)

    def _after_update(self, request, response):
        """Hook method called after update."""
        # Default implementation: no additional processing needed
        # Subclasses can override to provide custom post-update processing


# Export all classes for convenience
__all__ = [
    "CRUDTemplateMixin",
    "UnifiedAdminViewSet",
    "UnifiedBaseGenericView",
    "UnifiedBaseReadOnlyViewSet",
    "UnifiedBaseViewSet",
    "UnifiedCRUDViewSet",
    "UnifiedReadOnlyViewSet",
    "UnifiedUserViewSet",
]
