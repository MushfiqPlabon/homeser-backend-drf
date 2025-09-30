"""Advanced views using drf-extensions for enhanced functionality.
This module demonstrates the use of drf-extensions features to replace custom boilerplate.
"""

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework_extensions.cache.mixins import CacheResponseMixin
from rest_framework_extensions.key_constructor import bits
from rest_framework_extensions.key_constructor.constructors import DefaultKeyConstructor
from rest_framework_extensions.mixins import NestedViewSetMixin

from services.models import Service, ServiceCategory

from .filters import ServiceCategoryFilter, ServiceFilter
from .serializers import ServiceCategorySerializer, ServiceSerializer
from .services.category_service import CategoryService
from .services.service_service import ServiceService


class UpdatedKeyConstructor(DefaultKeyConstructor):
    """Custom key constructor for enhanced caching
    """

    user = bits.UserKeyBit()
    querystring = (
        bits.QueryParamsKeyBit()
    )  # Changed from QuerystringKeyBit to QueryParamsKeyBit
    pagination = bits.PaginationKeyBit()


class BaseExtendedViewSet(
    CacheResponseMixin, NestedViewSetMixin, viewsets.ModelViewSet,
):
    """Base extended viewset with caching and nested functionality
    """

    cache_key_func = UpdatedKeyConstructor()
    permission_classes = [IsAuthenticated]

    def get_service(self):
        """Get the appropriate service for the model"""
        if hasattr(self, "service_class"):
            return self.service_class()


class ServiceExtendedViewSet(BaseExtendedViewSet):
    """Enhanced service viewset using drf-extensions features
    """

    serializer_class = ServiceSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ServiceFilter

    def get_service(self):
        return ServiceService()

    def get_queryset(self):
        return Service.objects.all()


class CategoryExtendedViewSet(BaseExtendedViewSet):
    """Enhanced category viewset using drf-extensions features
    """

    serializer_class = ServiceCategorySerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ServiceCategoryFilter

    def get_service(self):
        return CategoryService()

    def get_queryset(self):
        return ServiceCategory.objects.all()


# Additional viewset with custom action patterns
class AdvancedServiceViewSet(NestedViewSetMixin, viewsets.ModelViewSet):
    """Advanced service viewset with enhanced drf-extensions functionality
    """

    serializer_class = ServiceSerializer
    queryset = Service.objects.all()
    filter_backends = [DjangoFilterBackend]
    filterset_class = ServiceFilter

    # This would typically be used for nested routes like /categories/{category_pk}/services/
    # It allows for automatic filtering of services based on the parent category
    def get_queryset(self):
        queryset = super().get_queryset()

        # If this is a nested view under a category, filter by the category
        category_pk = self.kwargs.get("parent_lookup_category")
        if category_pk:
            queryset = queryset.filter(category_id=category_pk)

        return queryset
