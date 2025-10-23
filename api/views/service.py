from django.db.models import Avg, Count, Q
from django_filters import rest_framework as filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework_extensions.mixins import NestedViewSetMixin

from services.models import Service

from ..filters import ServiceFilter
from ..serializers import ServiceSerializer
from ..services.service_service import ServiceService
from ..unified_base_views import (CRUDTemplateMixin, UnifiedAdminViewSet,
                                  UnifiedBaseGenericView)


class ServiceFilterWithOrdering(ServiceFilter):
    """Service filter with ordering capabilities"""

    ordering = filters.OrderingFilter(
        fields=(
            ("name", "name"),
            ("price", "price"),
            ("created", "created"),
            ("rating_aggregation__average", "avg_rating"),
            ("rating_aggregation__count", "popularity"),
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
    filter_backends = [DjangoFilterBackend]
    filterset_class = ServiceFilterWithOrdering
    ordering_fields = ["name", "price", "created", "avg_rating"]
    ordering = ["-created"]
    service_class = ServiceService

    def get_queryset(self):
        """Simplified queryset for services"""
        # Handle schema generation case
        if getattr(self, "swagger_fake_view", False):
            return Service.objects.none()

        # Simple queryset that works
        queryset = Service.objects.select_related("category", "owner").filter(
            is_active=True
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
        """List services with caching and pagination"""
        queryset = self.filter_queryset(self.get_queryset())

        # Apply pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


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
