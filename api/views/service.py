from django.db.models import Avg, Count, Q
from django_filters import rest_framework as filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, permissions, status
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response
from rest_framework_extensions.mixins import NestedViewSetMixin

from services.models import Service

from ..filters import ServiceFilter
from ..pagination import OptimizedServiceCursorPagination
from ..serializers import ServiceSerializer
from ..services.service_service import ServiceService
from ..unified_base_views import (CRUDTemplateMixin, UnifiedAdminViewSet,
                                  UnifiedBaseGenericView)


class CustomOrderingFilter(filters.OrderingFilter):
    def filter(self, qs, value):
        if value:
            # Apply field mappings to use cached fields instead of computed ones
            ordering_fields = []
            for param in value:
                if param == "avg_rating":
                    ordering_fields.append("cached_avg_rating")
                elif param == "-avg_rating":
                    ordering_fields.append("-cached_avg_rating")
                elif param == "popularity":
                    ordering_fields.append("cached_rating_count")
                elif param == "-popularity":
                    ordering_fields.append("-cached_rating_count")
                else:
                    ordering_fields.append(param)

            # Always add 'id' as the final tiebreaker to ensure consistent pagination
            ordering_fields.append("id")
            return qs.order_by(*ordering_fields)

        return qs


class ServiceFilterWithOrdering(ServiceFilter):
    """Service filter with ordering capabilities"""

    ordering = CustomOrderingFilter(
        fields=(
            ("name", "name"),
            ("price", "price"),
            ("created", "created"),
            ("cached_avg_rating", "avg_rating"),  # Use the cached field name
            ("cached_rating_count", "popularity"),  # Use the cached field name
        ),
        field_labels={
            "name": "Name",
            "price": "Price",
            "created": "Date Created",
            "avg_rating": "Rating",
            "popularity": "Popularity",
        },
    )

    class Meta(ServiceFilter.Meta):
        fields = ServiceFilter.Meta.fields


class ServiceListView(UnifiedBaseGenericView, generics.ListAPIView):
    """List services with optimized queries to prevent N+1 problems"""

    serializer_class = ServiceSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = ServiceFilterWithOrdering
    ordering_fields = ["name", "price", "created", "avg_rating"]
    ordering = ["-created"]
    pagination_class = (
        OptimizedServiceCursorPagination  # Use cursor pagination for large datasets
    )
    service_class = ServiceService

    def get_queryset(self):
        """Optimized queryset for services with performance in mind using cached fields"""

        # Handle schema generation case
        if getattr(self, "swagger_fake_view", False):
            return Service.objects.none()

        # Optimized queryset using cached rating fields to eliminate expensive JOINs
        queryset = (
            Service.objects.select_related(
                "category", "owner"
            )  # Required relationships
            .only(
                "id",
                "name",
                "slug",
                "price",
                "short_desc",
                "description",
                "image",
                "is_active",
                "created",
                "modified",
                "owner_id",
                "category_id",
                "cached_avg_rating",
                "cached_rating_count",  # Use cached fields
                "category__id",
                "category__name",
                "category__slug",
                "category__description",
                "owner__id",
                "owner__username",
                "owner__first_name",
                "owner__last_name",
            )  # Only fetch necessary fields to improve performance
            .filter(is_active=True)  # Only include active services
        )

        # Apply search if provided
        if search_query := self.request.GET.get("search"):
            queryset = queryset.filter(
                Q(name__icontains=search_query)
                | Q(description__icontains=search_query)
                | Q(category__name__icontains=search_query)
            )

        return queryset

    def list(self, request, *args, **kwargs) -> Response:
        """List services with enhanced caching and pagination"""
        from django.core.cache import cache

        # Create a cache key based on request parameters
        ordering = request.GET.get("ordering", "created")
        search = request.GET.get("search", "")
        page = request.GET.get("page", "1")
        page_size = request.GET.get("page_size", "20")

        # Create a cache key based on parameters
        cache_key = f"services_list_{ordering}_{search}_page_{page}_size_{page_size}"

        # Try to get cached response
        cached_response = cache.get(cache_key)
        if cached_response:
            return Response(cached_response)

        # If not cached, execute the query
        queryset = self.filter_queryset(self.get_queryset())

        # Apply pagination
        page_result = self.paginate_queryset(queryset)
        if page_result is not None:
            serializer = self.get_serializer(page_result, many=True)
            response_data = self.get_paginated_response(serializer.data).data
            # Cache the result for 2 minutes (adjust as needed)
            cache.set(cache_key, response_data, 120)
            return Response(response_data)

        serializer = self.get_serializer(queryset, many=True)
        response_data = serializer.data
        # Cache the result for 2 minutes (adjust as needed)
        cache.set(cache_key, response_data, 120)
        return Response(response_data)


class ServiceDetailView(UnifiedBaseGenericView, generics.RetrieveAPIView):
    """Retrieve single service with optimized queries"""

    serializer_class = ServiceSerializer
    permission_classes = [permissions.AllowAny]
    service_class = ServiceService
    lookup_field = "id"

    def get_queryset(self):
        """Simplified queryset for single service retrieval"""
        return (
            Service.objects.select_related("category", "owner")
            .prefetch_related("rating_aggregation")
            .filter(is_active=True)
        )

    def get_object(self):
        """Get a specific service by ID with error handling"""
        service_id = self.kwargs.get("id")
        try:
            return self.get_queryset().get(id=service_id, is_active=True)
        except Service.DoesNotExist:
            from rest_framework.exceptions import NotFound

            raise NotFound("Service not found or not active")


class ServiceCreateView(UnifiedBaseGenericView, generics.CreateAPIView):
    """Create service with proper validation"""

    serializer_class = ServiceSerializer
    permission_classes = [permissions.IsAuthenticated]
    service_class = ServiceService

    def perform_create(self, serializer) -> None:
        """Create service with current user as provider"""
        serializer.save(provider=self.request.user.serviceprofile)


class ServiceUpdateView(UnifiedBaseGenericView, generics.UpdateAPIView):
    """Update service with ownership validation"""

    serializer_class = ServiceSerializer
    permission_classes = [permissions.IsAuthenticated]
    service_class = ServiceService
    lookup_field = "id"

    def get_queryset(self):
        """Only allow users to update their own services"""
        return Service.objects.filter(owner=self.request.user)


class ServiceDeleteView(UnifiedBaseGenericView, generics.DestroyAPIView):
    """Delete service with ownership validation"""

    permission_classes = [permissions.IsAuthenticated]
    service_class = ServiceService
    lookup_field = "id"

    def get_queryset(self):
        """Only allow users to delete their own services"""
        return Service.objects.filter(owner=self.request.user)


class PopularServicesView(UnifiedBaseGenericView, generics.ListAPIView):
    """List popular services with optimized aggregations"""

    serializer_class = ServiceSerializer
    permission_classes = [permissions.AllowAny]
    service_class = ServiceService

    def get_queryset(self):
        """Get popular services based on ratings and favorites"""
        return (
            Service.objects.select_related("category", "owner")
            .prefetch_related("reviews", "favorites", "rating_aggregation")
            .annotate(
                avg_rating=Avg("reviews__rating"),
                review_count=Count("reviews", distinct=True),
                favorite_count=Count("favorites", distinct=True),
            )
            .filter(
                is_active=True,
                avg_rating__gte=4.0,  # Only highly rated services
            )
            .order_by("-favorite_count", "-avg_rating", "-review_count")[:20]
        )


class ServiceSearchView(UnifiedBaseGenericView, generics.ListAPIView):
    """Advanced service search with optimized queries"""

    serializer_class = ServiceSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_class = ServiceFilter
    service_class = ServiceService

    def get_queryset(self):
        """Search services with full-text search capabilities"""
        queryset = (
            Service.objects.select_related("category", "owner")
            .prefetch_related("reviews", "favorites", "rating_aggregation")
            .annotate(
                avg_rating=Avg("reviews__rating"),
                review_count=Count("reviews", distinct=True),
            )
            .filter(is_active=True)
        )

        # Apply search query
        if search_query := self.request.GET.get("q"):
            queryset = queryset.filter(
                Q(name__icontains=search_query)
                | Q(description__icontains=search_query)
                | Q(category__name__icontains=search_query)
                | Q(owner__username__icontains=search_query)
            )

        return queryset.order_by("-avg_rating", "-review_count")


class AdminServiceViewSet(NestedViewSetMixin, UnifiedAdminViewSet, CRUDTemplateMixin):
    """Admin API endpoint for managing services with full CRUD operations"""

    serializer_class = ServiceSerializer
    queryset = Service.objects.all()
    service_class = ServiceService
    model_class = Service
    filter_backends = [DjangoFilterBackend]
    filterset_class = ServiceFilterWithOrdering

    def get_queryset(self):
        """Admin access to all services with optimized queries"""
        queryset = self.get_service().get_services(
            user=self.request.user,
            admin_mode=True,
        )
        return queryset.prefetch_related("rating_aggregation")

    def _perform_create(self, request):
        """Create service via service layer"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            service = self.get_service().create_service(
                serializer.validated_data,
                request.user,
            )
            serializer.instance = service
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return self.handle_exception(e)

    def _perform_update(self, request, *args, **kwargs):
        """Update service via service layer"""
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        try:
            service = self.get_service().update_service(
                instance.id,
                serializer.validated_data,
                request.user,
            )
            serializer.instance = service
            return Response(serializer.data)
        except Exception as e:
            return self.handle_exception(e)

    def destroy(self, request, *args, **kwargs):
        """Delete service via service layer"""
        instance = self.get_object()

        try:
            self.get_service().delete_service(instance.id, request.user)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return self.handle_exception(e)
