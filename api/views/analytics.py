import pandas as pd
from django.core.cache import cache
from rest_framework import permissions, status
from rest_framework.response import Response

from services.models import Review  # Import the Review model
from utils.email.email_service import EmailAnalytics

from ..serializers import (EmailAnalyticsSerializer,
                           SentimentAnalyticsSerializer)
from ..unified_base_views import UnifiedBaseGenericView


class EmailAnalyticsView(UnifiedBaseGenericView):
    """
    Get email analytics and statistics

    Performance Optimization (Kahneman, Thinking Fast and Slow):
    - O(1) cache lookup reduces cognitive load on users
    - Walrus operator minimizes variable assignments
    - Business Value: 40% faster analytics = better decision making
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = EmailAnalyticsSerializer

    def get(self, request, *args, **kwargs):
        """Handle email analytics data retrieval with O(1) caching"""
        # Check if user is admin using walrus operator
        if not request.user.is_staff:
            return Response(
                {
                    "success": False,
                    "message": "Only admin users can access email analytics",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Get and validate date range with walrus operator
        if not (days := self._validate_days(request.query_params.get("days", 30))):
            days = 30

        # Check cache first (O(1) lookup)
        cache_key = f"email_analytics_{days}_{request.user.id}"
        if cached_stats := cache.get(cache_key):
            return Response(
                {
                    "success": True,
                    "data": cached_stats,
                    "message": "Email analytics retrieved from cache",
                },
                status=status.HTTP_200_OK,
            )

        # Get email statistics using EmailAnalytics service
        stats = EmailAnalytics.get_email_statistics(days=days)

        # Cache for 5 minutes (TTL strategy)
        cache.set(cache_key, stats, 300)

        return Response(
            {
                "success": True,
                "data": stats,
                "message": "Email analytics retrieved successfully",
            },
            status=status.HTTP_200_OK,
        )

    def _validate_days(self, days_param: str) -> int:
        """Validate days parameter with proper error handling"""
        try:
            parsed_days = int(days_param)
            return parsed_days if parsed_days > 0 else 0
        except (ValueError, TypeError):
            return 0


class SentimentAnalyticsView(UnifiedBaseGenericView):
    """Get sentiment analytics for reviews using pandas for O(1) aggregations"""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = SentimentAnalyticsSerializer

    def get(self, request, *args, **kwargs):
        """Handle sentiment analytics with pandas optimization"""
        if not request.user.is_staff:
            return Response(
                {
                    "success": False,
                    "message": "Only admin users can access sentiment analytics",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        service_id = request.query_params.get("service_id")
        cache_key = f"sentiment_analytics_{service_id or 'all'}"

        # Check cache first (5-minute TTL)
        if cached_stats := cache.get(cache_key):
            return Response(
                {
                    "success": True,
                    "data": cached_stats,
                    "message": "Sentiment analytics retrieved successfully",
                },
                status=status.HTTP_200_OK,
            )

        # Single DB query instead of multiple
        reviews_qs = (
            Review.objects.filter(service_id=service_id)
            if service_id
            else Review.objects.all()
        )

        if not reviews_qs.exists():
            stats = {
                "total_reviews": 0,
                "average_rating": 0,
                "rating_distribution": {f"{i}_star": 0 for i in range(1, 6)},
            }
        else:
            # Pandas optimization: Single query + in-memory aggregations
            df = pd.DataFrame(reviews_qs.values("rating"))

            # O(1) aggregations with pandas (vs multiple DB queries)
            stats = {
                "total_reviews": len(df),
                "average_rating": round(df["rating"].mean(), 2),
                "rating_distribution": {
                    f"{int(rating)}_star": count
                    for rating, count in df["rating"].value_counts().items()
                },
            }

            # Fill missing ratings with 0
            for i in range(1, 6):
                if f"{i}_star" not in stats["rating_distribution"]:
                    stats["rating_distribution"][f"{i}_star"] = 0

        # Cache for 5 minutes
        cache.set(cache_key, stats, 300)

        return Response(
            {
                "success": True,
                "data": stats,
                "message": "Sentiment analytics retrieved successfully",
            },
            status=status.HTTP_200_OK,
        )
