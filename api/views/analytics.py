from django.db.models import Avg, Count
from rest_framework import permissions, status
from rest_framework.response import Response

from services.models import Review  # Import the Review model
from utils.email.email_service import EmailAnalytics

from ..serializers import (EmailAnalyticsSerializer,
                           SentimentAnalyticsSerializer)
from ..unified_base_views import UnifiedBaseGenericView


class EmailAnalyticsView(UnifiedBaseGenericView):
    """Get email analytics and statistics"""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = EmailAnalyticsSerializer

    def get(self, request, *args, **kwargs):
        """Handle email analytics data retrieval"""
        # Check if user is admin
        if not request.user.is_staff:
            return Response(
                {
                    "success": False,
                    "message": "Only admin users can access email analytics",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Get date range from query parameters
        days = request.query_params.get("days", 30)
        try:
            days = int(days)
        except (ValueError, TypeError):
            days = 30

        # Get email statistics using EmailAnalytics service
        stats = EmailAnalytics.get_email_statistics(days=days)

        return Response(
            {
                "success": True,
                "data": stats,
                "message": "Email analytics retrieved successfully",
            },
            status=status.HTTP_200_OK,
        )


class SentimentAnalyticsView(UnifiedBaseGenericView):
    """Get sentiment analytics for reviews"""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = SentimentAnalyticsSerializer

    def get(self, request, *args, **kwargs):
        """Handle sentiment analytics data retrieval"""
        # Check if user is admin
        if not request.user.is_staff:
            return Response(
                {
                    "success": False,
                    "message": "Only admin users can access sentiment analytics",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Get service ID if provided for service-specific analytics
        service_id = request.query_params.get("service_id")

        if service_id:
            # Get reviews for specific service
            reviews = Review.objects.filter(service_id=service_id)
        else:
            # Get all reviews for overall statistics
            reviews = Review.objects.all()

        if not reviews.exists():
            stats = {
                "total_reviews": 0,
                "average_rating": 0,
                "rating_distribution": {
                    "1_star": 0,
                    "2_star": 0,
                    "3_star": 0,
                    "4_star": 0,
                    "5_star": 0,
                },
            }
        else:
            # Calculate average rating
            avg_rating = reviews.aggregate(Avg("rating"))["rating__avg"] or 0

            # Calculate rating distribution
            rating_counts = reviews.values("rating").annotate(count=Count("rating"))
            rating_distribution = {f"{i}_star": 0 for i in range(1, 6)}
            for item in rating_counts:
                rating_distribution[f"{int(item['rating'])}_star"] = item["count"]

            stats = {
                "total_reviews": reviews.count(),
                "average_rating": round(avg_rating, 2),
                "rating_distribution": rating_distribution,
            }

        return Response(
            {
                "success": True,
                "data": stats,
                "message": "Sentiment analytics retrieved successfully",
            },
            status=status.HTTP_200_OK,
        )
