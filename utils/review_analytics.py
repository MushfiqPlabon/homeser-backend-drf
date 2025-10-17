# utils/review_analytics.py
# Review analytics service for sentiment analysis statistics

import logging
from datetime import timedelta

from django.core.cache import cache
from django.db.models import Avg, Count
from sklearn.linear_model import LinearRegression

from services.models import Review

logger = logging.getLogger(__name__)


class ReviewAnalyticsService:
    """Service for analyzing review sentiment statistics."""

    @staticmethod
    def get_service_sentiment_stats(service_id):
        """Get sentiment statistics for a specific service.

        Args:
            service_id (int): Service ID

        Returns:
            dict: Sentiment statistics

        """
        reviews = Review.objects.filter(service_id=service_id)

        if not reviews.exists():
            return {
                "total_reviews": 0,
                "average_sentiment_polarity": 0,
                "average_sentiment_subjectivity": 0,
                "sentiment_distribution": {
                    "very_negative": 0,
                    "negative": 0,
                    "neutral": 0,
                    "positive": 0,
                    "very_positive": 0,
                },
            }

        # Calculate averages
        avg_polarity = (
            reviews.aggregate(Avg("sentiment_polarity"))["sentiment_polarity__avg"] or 0
        )
        avg_subjectivity = (
            reviews.aggregate(Avg("sentiment_subjectivity"))[
                "sentiment_subjectivity__avg"
            ]
            or 0
        )

        # Calculate sentiment distribution
        sentiment_counts = reviews.values("sentiment_label").annotate(
            count=Count("sentiment_label"),
        )
        sentiment_dist = {
            "very_negative": 0,
            "negative": 0,
            "neutral": 0,
            "positive": 0,
            "very_positive": 0,
        }

        for item in sentiment_counts:
            label = item["sentiment_label"]
            count = item["count"]
            if label in sentiment_dist:
                sentiment_dist[label] = count

        return {
            "total_reviews": reviews.count(),
            "average_sentiment_polarity": round(avg_polarity, 3),
            "average_sentiment_subjectivity": round(avg_subjectivity, 3),
            "sentiment_distribution": sentiment_dist,
        }

    @staticmethod
    def get_overall_sentiment_stats(user=None):
        """Get overall sentiment statistics for all services with caching.

        Args:
            user (User): User requesting the statistics (must be admin)

        Returns:
            dict: Overall sentiment statistics

        Raises:
            PermissionError: If user is not admin

        """
        # Create cache key for overall sentiment stats
        cache_key = "overall_sentiment_stats"

        # Try to get data from cache first
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            # Check permissions even when using cached data
            if user is None or not user.is_staff:
                raise PermissionError("Only admin users can access this endpoint")
            return cached_data

        # Check if user is admin
        if user is None or not user.is_staff:
            raise PermissionError("Only admin users can access this endpoint")
        reviews = Review.objects.all()

        if not reviews.exists():
            result = {
                "total_reviews": 0,
                "average_sentiment_polarity": 0,
                "average_sentiment_subjectivity": 0,
                "top_positive_services": [],
                "top_negative_services": [],
            }
            # Cache the result for 15 minutes
            cache.set(cache_key, result, 900)  # 15 minutes
            return result

        # Calculate averages
        avg_polarity = (
            reviews.aggregate(Avg("sentiment_polarity"))["sentiment_polarity__avg"] or 0
        )
        avg_subjectivity = (
            reviews.aggregate(Avg("sentiment_subjectivity"))[
                "sentiment_subjectivity__avg"
            ]
            or 0
        )

        # Get top positive and negative services
        from services.models import Service

        top_positive = (
            Service.objects.filter(reviews__sentiment_polarity__gt=0)
            .annotate(avg_sentiment=Avg("reviews__sentiment_polarity"))
            .order_by("-avg_sentiment")[:5]
        )

        top_negative = (
            Service.objects.filter(reviews__sentiment_polarity__lt=0)
            .annotate(avg_sentiment=Avg("reviews__sentiment_polarity"))
            .order_by("avg_sentiment")[:5]
        )

        result = {
            "total_reviews": reviews.count(),
            "average_sentiment_polarity": round(avg_polarity, 3),
            "average_sentiment_subjectivity": round(avg_subjectivity, 3),
            "top_positive_services": [
                {
                    "id": service.id,
                    "name": service.name,
                    "average_sentiment": (
                        round(service.avg_sentiment, 3)
                        if hasattr(service, "avg_sentiment")
                        else 0
                    ),
                }
                for service in top_positive
            ],
            "top_negative_services": [
                {
                    "id": service.id,
                    "name": service.name,
                    "average_sentiment": (
                        round(service.avg_sentiment, 3)
                        if hasattr(service, "avg_sentiment")
                        else 0
                    ),
                }
                for service in top_negative
            ],
        }

        # Cache the result for 15 minutes
        cache.set(cache_key, result, 900)  # 15 minutes

        return result

    @staticmethod
    def get_sentiment_trend(service_id, days=30):
        """Get sentiment trend for a service over time with caching.

        Args:
            service_id (int): Service ID
            days (int): Number of days to analyze

        Returns:
            list: Sentiment trend data

        """
        # Create cache key for this specific trend request
        cache_key = f"sentiment_trend_service_{service_id}_days_{days}"

        # Try to get data from cache first
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return cached_data

        from django.utils import timezone

        # Calculate date range
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)

        # Get reviews in date range
        reviews = Review.objects.filter(
            service_id=service_id,
            created_at__gte=start_date,
            created_at__lte=end_date,
        ).order_by("created_at")

        # Group reviews by week and calculate average sentiment
        trend_data = []
        if reviews.exists():
            # Group by week
            from django.db.models import TruncWeek

            weekly_data = (
                reviews.annotate(week=TruncWeek("created_at"))
                .values("week")
                .annotate(avg_polarity=Avg("sentiment_polarity"), count=Count("id"))
                .order_by("week")
            )

            trend_data = [
                {
                    "week": item["week"].strftime("%Y-%m-%d"),
                    "average_sentiment": round(item["avg_polarity"], 3),
                    "review_count": item["count"],
                }
                for item in weekly_data
            ]

        # Cache the result for 15 minutes
        cache.set(cache_key, trend_data, 900)  # 15 minutes

        return trend_data

    @staticmethod
    def predict_sentiment_trend(service_id, days_ahead=7):
        """Predict sentiment trend for a service using linear regression with caching.

        Args:
            service_id (int): Service ID
            days_ahead (int): Number of days to predict ahead

        Returns:
            dict: Prediction results

        """
        # Create cache key for this specific prediction request
        cache_key = f"predict_sentiment_trend_service_{service_id}_days_{days_ahead}"

        # Try to get data from cache first
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return cached_data

        try:
            # Get historical data (last 90 days)
            from datetime import timedelta

            from django.utils import timezone

            end_date = timezone.now()
            start_date = end_date - timedelta(days=90)

            reviews = Review.objects.filter(
                service_id=service_id,
                created_at__gte=start_date,
                created_at__lte=end_date,
            ).order_by("created_at")

            if not reviews.exists() or reviews.count() < 5:
                result = {
                    "prediction": None,
                    "confidence": 0,
                    "message": "Not enough data for prediction",
                }
                # Cache the result for 15 minutes even when there's not enough data
                cache.set(cache_key, result, 900)  # 15 minutes
                return result

            # Prepare data for linear regression
            # Group by day and calculate daily average sentiment
            from django.db.models import TruncDay

            daily_data = (
                reviews.annotate(day=TruncDay("created_at"))
                .values("day")
                .annotate(avg_polarity=Avg("sentiment_polarity"))
                .order_by("day")
            )

            if len(daily_data) < 3:
                result = {
                    "prediction": None,
                    "confidence": 0,
                    "message": "Not enough data points for prediction",
                }
                # Cache the result for 15 minutes even when there's not enough data
                cache.set(cache_key, result, 900)  # 15 minutes
                return result

            # Prepare X (days) and y (sentiment) arrays
            X = []
            y = []
            base_date = daily_data[0]["day"]

            for item in daily_data:
                days_since_start = (item["day"] - base_date).days
                X.append([days_since_start])
                y.append(item["avg_polarity"])

            # Train linear regression model
            model = LinearRegression()
            model.fit(X, y)

            # Predict future sentiment
            last_day = X[-1][0]
            future_day = last_day + days_ahead
            predicted_sentiment = model.predict([[future_day]])[0]

            # Calculate confidence (R^2 score)
            confidence = model.score(X, y)

            # Ensure sentiment is within bounds
            predicted_sentiment = max(-1.0, min(1.0, predicted_sentiment))

            result = {
                "prediction": round(predicted_sentiment, 3),
                "confidence": round(confidence, 3),
                "trend": (
                    "improving"
                    if predicted_sentiment > y[-1]
                    else "declining" if predicted_sentiment < y[-1] else "stable"
                ),
                "days_ahead": days_ahead,
            }

            # Cache the result for 15 minutes
            cache.set(cache_key, result, 900)  # 15 minutes

            return result
        except Exception as e:
            logger.error(
                f"Error predicting sentiment trend for service {service_id}: {e}",
            )
            result = {
                "prediction": None,
                "confidence": 0,
                "message": "Error in prediction",
            }
            # Cache the error result for 5 minutes to prevent repeated failures
            cache.set(cache_key, result, 300)  # 5 minutes
            return result

    @staticmethod
    def get_service_insights(service_id):
        """Get comprehensive insights for a service.

        Args:
            service_id (int): Service ID

        Returns:
            dict: Comprehensive insights

        """
        # Get basic sentiment stats
        sentiment_stats = ReviewAnalyticsService.get_service_sentiment_stats(service_id)

        # Get trend data
        trend_data = ReviewAnalyticsService.get_sentiment_trend(service_id, days=30)

        # Get prediction
        prediction = ReviewAnalyticsService.predict_sentiment_trend(service_id)

        # Calculate additional metrics
        reviews = Review.objects.filter(service_id=service_id)
        total_reviews = reviews.count()

        if total_reviews == 0:
            return {
                "sentiment_stats": sentiment_stats,
                "trend_data": trend_data,
                "prediction": prediction,
                "insights": {
                    "review_volume_trend": "no_data",
                    "sentiment_health": "no_data",
                    "flagged_reviews": 0,
                },
            }

        # Calculate review volume trend
        from django.utils import timezone

        # Compare last week to previous week
        now = timezone.now()
        last_week_start = now - timedelta(days=7)
        previous_week_start = now - timedelta(days=14)

        last_week_count = reviews.filter(
            created_at__gte=last_week_start,
            created_at__lte=now,
        ).count()

        previous_week_count = reviews.filter(
            created_at__gte=previous_week_start,
            created_at__lt=last_week_start,
        ).count()

        if previous_week_count > 0:
            volume_change = (
                (last_week_count - previous_week_count) / previous_week_count
            ) * 100
            volume_trend = (
                "increasing"
                if volume_change > 0
                else "decreasing" if volume_change < 0 else "stable"
            )
        else:
            volume_trend = "increasing" if last_week_count > 0 else "no_change"

        # Calculate sentiment health
        avg_polarity = sentiment_stats["average_sentiment_polarity"]
        if avg_polarity > 0.3:
            sentiment_health = "positive"
        elif avg_polarity > 0:
            sentiment_health = "slightly_positive"
        elif avg_polarity > -0.3:
            sentiment_health = "neutral"
        else:
            sentiment_health = "negative"

        # Get flagged reviews count
        flagged_count = reviews.filter(is_flagged=True).count()

        return {
            "sentiment_stats": sentiment_stats,
            "trend_data": trend_data,
            "prediction": prediction,
            "insights": {
                "review_volume_trend": volume_trend,
                "sentiment_health": sentiment_health,
                "flagged_reviews": flagged_count,
            },
        }
