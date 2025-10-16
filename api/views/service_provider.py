from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions
from rest_framework_extensions.mixins import NestedViewSetMixin

from services.models import Service

from ..filters import ServiceFilter
from ..serializers import ServiceSerializer
from ..services.service_service import ServiceService
from ..unified_base_views import CRUDTemplateMixin, UnifiedBaseViewSet


class ServiceProviderServiceViewSet(
    NestedViewSetMixin, UnifiedBaseViewSet, CRUDTemplateMixin
):
    """API endpoint for service providers to manage their own services.

    Features:
    - Create new services with name, description, price, and category
    - Update existing service details for their own services
    - Delete their own services
    - List only services they own
    - Retrieve detailed information about their specific services

    Authentication required - only users with service provider permissions can access these endpoints.
    """

    serializer_class = ServiceSerializer
    queryset = Service.objects.all()  # This will be filtered in get_queryset
    service_class = ServiceService
    model_class = Service
    filter_backends = [DjangoFilterBackend]
    filterset_class = ServiceFilter

    def get_queryset(self):
        """Return only services owned by the current user"""
        # Only return services owned by the current user
        queryset = (
            self.get_service().get_model().objects.filter(owner=self.request.user)
        )

        # Always prefetch rating aggregation to avoid N+1 queries in the serializer
        queryset = queryset.select_related("category").prefetch_related(
            "rating_aggregation"
        )

        # Apply filters from django-filter
        # Filters are automatically applied by the DjangoFilterBackend

        return queryset

    def perform_create(self, serializer):
        """Set the owner to the current user when creating a service"""
        # Check if the user has service provider permissions
        from guardian.shortcuts import assign_perm

        # Create the service with the current user as owner
        service = serializer.save(owner=self.request.user)

        # Assign permissions to the service provider for this service
        assign_perm("services.change_service", self.request.user, service)
        assign_perm("services.delete_service", self.request.user, service)
        assign_perm("services.view_service", self.request.user, service)

        return service

    def get_permissions(self):
        """Instantiates and returns the list of permissions that this view requires."""
        permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]

    def check_object_permissions(self, request, obj):
        """Check if the user has permission to access this object."""
        # Check if user is the owner of the service
        from ..services.service_service import ServiceService

        if not ServiceService._common_permission_check(obj, request.user, "change"):
            self.permission_denied(
                request,
                message=getattr(self, "permission_denied_message", "Not authorized"),
            )
