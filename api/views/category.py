from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, permissions, status
from rest_framework.response import Response

from services.models import ServiceCategory

from ..filters import ServiceCategoryFilter
from ..serializers import ServiceCategorySerializer
from ..services.category_service import CategoryService
from ..unified_base_views import (
    CRUDTemplateMixin,
    UnifiedAdminViewSet,
    UnifiedBaseGenericView,
)


class CategoryListView(UnifiedBaseGenericView, generics.ListAPIView):
    """API endpoint that allows clients to view the list of service categories.

    Features:
    - Filter categories by name or description
    - Search for specific categories
    - Get the hierarchical structure of service offerings

    No authentication required - available to all users.
    """

    serializer_class = ServiceCategorySerializer
    permission_classes = [permissions.AllowAny]
    service_class = CategoryService
    filter_backends = [DjangoFilterBackend]
    filterset_class = ServiceCategoryFilter

    def get_queryset(self):
        return self.get_service().get_categories()


class CategoryDetailView(UnifiedBaseGenericView, generics.RetrieveAPIView):
    """API endpoint that allows clients to view detailed information about a specific category.

    Features:
    - Get complete category details including name, description, and slug
    - Load associated services within the category

    No authentication required - available to all users.
    """

    serializer_class = ServiceCategorySerializer
    permission_classes = [permissions.AllowAny]
    service_class = CategoryService
    lookup_field = "id"


class CategoryViewSet(UnifiedAdminViewSet, CRUDTemplateMixin):
    """API endpoint for staff members to manage service categories.

    Features:
    - Create new service categories
    - Update existing category details
    - Delete categories (with proper authorization checks)
    - List all categories with advanced filtering options
    - Retrieve detailed information about specific categories

    Authentication required - only staff members can access these endpoints.
    """

    serializer_class = ServiceCategorySerializer
    queryset = ServiceCategory.objects.all()
    service_class = CategoryService
    model_class = ServiceCategory
    filter_backends = [DjangoFilterBackend]
    filterset_class = ServiceCategoryFilter

    def get_queryset(self):
        """Only staff users can access this endpoint"""
        return self.get_service().get_categories()

    def _before_create(self, request):
        """Hook method called before create."""

    def _perform_create(self, request):
        """Core create logic."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            # Use CategoryService to create category
            category = self.get_service().create_category(
                serializer.validated_data,
                request.user,
            )
            serializer.instance = category
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return self.handle_service_exception(e)

    def _after_create(self, request, response):
        """Hook method called after create."""

    def _before_update(self, request):
        """Hook method called before update."""

    def _perform_update(self, request, *args, **kwargs):
        """Core update logic."""
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        try:
            # Use CategoryService to update category
            category = self.get_service().update_category(
                instance.id,
                serializer.validated_data,
                request.user,
            )
            serializer.instance = category
            return Response(serializer.data)
        except Exception as e:
            return self.handle_service_exception(e)

    def _after_update(self, request, response):
        """Hook method called after update."""

    def destroy(self, request, *args, **kwargs):
        """Delete a category"""
        instance = self.get_object()

        try:
            # Use CategoryService to delete category
            result = self.get_service().delete_category(instance.id, request.user)
            if result:
                return Response(status=status.HTTP_204_NO_CONTENT)
            return Response(status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return self.handle_service_exception(e)
