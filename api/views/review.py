from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, permissions, status
from rest_framework.response import Response

from services.models import Review

from ..filters import ReviewFilter
from ..serializers import ReviewSerializer
from ..services.review_service import ReviewService
from ..services.service_service import ServiceService
from ..unified_base_views import (
    UnifiedBaseGenericView,
    UnifiedBaseViewSet,
)


class ServiceReviewsView(UnifiedBaseGenericView, generics.ListCreateAPIView):
    """List and create reviews for a service"""

    serializer_class = ReviewSerializer
    service_class = ServiceService
    filter_backends = [DjangoFilterBackend]
    filterset_class = ReviewFilter

    def get_permissions(self):
        """Set custom permissions based on request method"""
        from api.utils.permissions import UniversalObjectPermission

        if self.request.method == "POST":
            return [permissions.IsAuthenticated(), UniversalObjectPermission()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            # Return an empty queryset when generating schema
            return Review.objects.none()
        service_id = self.kwargs["service_id"]
        return self.get_service().get_service_reviews(service_id)

    def perform_create(self, serializer):
        service_id = self.kwargs["service_id"]
        rating = self.request.data.get("rating")
        text = self.request.data.get("text")

        try:
            review = self.get_service().create_service_review(
                service_id,
                self.request.user,
                rating,
                text,
            )
            serializer.instance = review
        except Exception as e:
            from rest_framework.serializers import ValidationError

            # If it's already a ValidationError, re-raise it directly
            if isinstance(e, ValidationError):
                raise e
            # Return a proper 400 response with simple string message
            raise ValidationError(
                "You can only review services you have purchased and received",
            )


class UserReviewsView(UnifiedBaseGenericView, generics.ListAPIView):
    """List reviews submitted by the current user"""

    serializer_class = ReviewSerializer
    service_class = ReviewService
    filter_backends = [DjangoFilterBackend]
    filterset_class = ReviewFilter
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return reviews where the current user is the author"""
        if getattr(self, "swagger_fake_view", False):
            # Return an empty queryset when generating schema
            return Review.objects.none()
        return (
            Review.objects.filter(user=self.request.user)
            .select_related("service")
            .order_by("-created_at")
        )


class ReviewDeleteView(UnifiedBaseGenericView, generics.DestroyAPIView):
    """Delete a review - only the author or admin can delete"""

    serializer_class = ReviewSerializer
    service_class = ReviewService
    model_class = Review
    filter_backends = [DjangoFilterBackend]
    filterset_class = ReviewFilter

    def get_permissions(self):
        """Set custom permissions for this view"""
        from api.utils.permissions import UniversalObjectPermission

        return [permissions.IsAuthenticated(), UniversalObjectPermission()]

    def get_queryset(self):
        """Only allow users to delete their own reviews or let admins delete any"""
        from services.models import Review

        # Permission checking is handled in the service layer
        return Review.objects.all()


class AdminReviewViewSet(UnifiedBaseViewSet):
    """Admin review management endpoints"""

    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Review.objects.all().select_related("user", "service")
    service_class = ReviewService
    model_class = Review
    filter_backends = [DjangoFilterBackend]
    filterset_class = ReviewFilter

    def get_queryset(self):
        """Only staff users can access this endpoint"""
        # Permission checking is handled in the service layer
        return self.get_service().get_reviews(self.request.user)

    def get_object(self):
        """Get a specific review by ID"""
        # Permission checking is handled in the service layer
        return super().get_object()

    def update(self, request, *args, **kwargs):
        """Update a review"""
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        try:
            # Use ReviewService to update review
            review = self.get_service().update_review(
                instance.id,
                serializer.validated_data,
                request.user,
            )
            serializer.instance = review
            return Response(serializer.data)
        except Exception as e:
            return self.handle_service_exception(e)

    def destroy(self, request, *args, **kwargs):
        """Delete a review"""
        instance = self.get_object()

        try:
            # Use ReviewService to delete review
            self.get_service().delete_review(instance.id, request.user)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return self.handle_service_exception(e)
