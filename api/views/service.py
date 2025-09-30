from django_filters import rest_framework as filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework_extensions.mixins import NestedViewSetMixin

from services.models import Service

from ..filters import ServiceFilter
from ..serializers import ServiceSerializer
from ..services.service_service import ServiceService
from ..smart_prefetch import SmartPrefetcher
from ..unified_base_views import (
    CRUDTemplateMixin,
    UnifiedAdminViewSet,
    UnifiedBaseGenericView,
)


class ServiceOrderingFilter(filters.OrderingFilter):
    """Custom ordering filter for services"""

    def filter(self, qs, value):
        """Apply ordering to queryset"""
        if not value:
            return qs

        ordering = []
        for param in value:
            if param == "rating":
                # Use precomputed aggregations for efficient rating-based ordering
                ordering.append("-rating_aggregation__average")
            elif param == "popular":
                # Use precomputed aggregations for popular services
                ordering.extend(
                    ["-rating_aggregation__count", "-rating_aggregation__average"],
                )
            elif param == "price_low":
                ordering.append("price")
            elif param == "price_high":
                ordering.append("-price")
            elif param == "newest":
                ordering.append(
                    "-created_at",
                )  # Using created_at instead of 'created' if that's the field name
            else:
                # Default ordering
                ordering.append("name")

        return qs.order_by(*ordering)


class ServiceFilterWithOrdering(ServiceFilter):
    """Extended service filter with ordering support"""

    ordering = ServiceOrderingFilter(
        fields=(
            ("name", "name"),
            ("price", "price"),
            ("created_at", "newest"),
            ("rating_aggregation__average", "rating"),
            ("rating_aggregation__count", "popular"),
        ),
        field_labels={
            "name": "Name",
            "price": "Price",
            "created_at": "Newest",
            "rating_aggregation__average": "Rating",
            "rating_aggregation__count": "Popularity",
        },
    )

    class Meta(ServiceFilter.Meta):
        fields = ServiceFilter.Meta.fields


class ServiceListView(UnifiedBaseGenericView, generics.ListAPIView):
    """API endpoint that allows clients to view the list of available services.

    Features:
    - Filter services by category, price range, and availability
    - Order services by price, rating, or creation date
    - Search for specific services by name or description
    - Efficiently loads related data using smart prefetching

    No authentication required - available to all users.
    """

    serializer_class = ServiceSerializer
    permission_classes = [permissions.AllowAny]
    service_class = ServiceService
    filter_backends = [DjangoFilterBackend]
    filterset_class = ServiceFilterWithOrdering

    def get_queryset(self):
        # Use ServiceService to get services
        queryset = self.get_service().get_services()

        # Always prefetch rating aggregation to avoid N+1 queries in the serializer
        queryset = queryset.prefetch_related("rating_aggregation")

        # Apply filters from django-filter
        # Filters are automatically applied by the DjangoFilterBackend

        return queryset


class ServiceDetailView(UnifiedBaseGenericView, generics.RetrieveAPIView):
    """API endpoint that allows clients to view detailed information about a specific service.

    Features:
    - Get complete service details including name, description, price, and image
    - Include aggregated rating and review count
    - Load associated reviews with the service
    - Efficiently loads related data using smart prefetching

    No authentication required - available to all users.
    """

    serializer_class = ServiceSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = "id"
    service_class = ServiceService

    def get_queryset(self):
        service_id = self.kwargs.get("id")
        service = self.get_service().get_service_detail(service_id)
        if service:
            # Use smart prefetching for related data
            base_queryset = Service.objects.filter(id=service_id).prefetch_related(
                "rating_aggregation",
            )
            with SmartPrefetcher(base_queryset, self.request) as queryset:
                return queryset
        return Service.objects.none()


class AdminServiceViewSet(NestedViewSetMixin, UnifiedAdminViewSet, CRUDTemplateMixin):
    """API endpoint for staff members to manage services.

    Features:
    - Create new services with name, description, price, and category
    - Update existing service details
    - Delete services (with proper authorization checks)
    - List all services with advanced filtering options
    - Retrieve detailed information about specific services

    Authentication required - only staff members can access these endpoints.
    """

    serializer_class = ServiceSerializer
    queryset = Service.objects.all()
    service_class = ServiceService
    model_class = Service
    filter_backends = [DjangoFilterBackend]
    filterset_class = ServiceFilterWithOrdering

    def get_queryset(self):
        """Only staff users can access this endpoint"""
        # Permission checking is handled in the service layer
        queryset = self.get_service().get_services(
            user=self.request.user, admin_mode=True,
        )

        # Always prefetch rating aggregation to avoid N+1 queries in the serializer
        queryset = queryset.prefetch_related("rating_aggregation")

        # Apply filters from django-filter
        # Filters are automatically applied by the DjangoFilterBackend

        return queryset

    def get_object(self):
        """Get a specific service by ID"""
        # Permission checking is handled in the service layer
        return super().get_object()

    def _before_create(self, request):
        """Hook method called before create."""
        # Add any pre-create logic here

    def _perform_create(self, request):
        """Core create logic."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            # Use ServiceService to create service
            service = self.get_service().create_service(
                serializer.validated_data, request.user,
            )
            serializer.instance = service
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return self.handle_service_exception(e)

    def _after_create(self, request, response):
        """Hook method called after create."""
        # Add any post-create logic here

    def _before_update(self, request):
        """Hook method called before update."""
        # Add any pre-update logic here

    def _perform_update(self, request, *args, **kwargs):
        """Core update logic."""
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        try:
            # Use ServiceService to update service
            service = self.get_service().update_service(
                instance.id, serializer.validated_data, request.user,
            )
            serializer.instance = service
            return Response(serializer.data)
        except Exception as e:
            return self.handle_service_exception(e)

    def _after_update(self, request, response):
        """Hook method called after update."""
        # Add any post-update logic here

    def destroy(self, request, *args, **kwargs):
        """Delete a service"""
        instance = self.get_object()

        try:
            # Use ServiceService to delete service
            self.get_service().delete_service(instance.id, request.user)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return self.handle_service_exception(e)
