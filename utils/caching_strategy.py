# utils/caching_strategy.py
# Cache warming strategies using django-cachalot

import logging
from datetime import datetime, timedelta

from django.db import models
from django.db.models import Avg, Count

from .cache_utils import get_service_data

# Configure logger
logger = logging.getLogger(__name__)


class CacheWarmingStrategy:
    """Cache warming strategies using django-cachalot.
    With django-cachalot, warming is less critical as queries are cached automatically,
    but we can still warm common queries to improve performance.
    """

    def warm_popular_services(self, service_ids: list[int]) -> bool:
        """Warm cache for popular services by executing common queries.

        Args:
            service_ids: List of popular service IDs

        Returns:
            bool: True if successful

        """
        try:
            # With django-cachalot, we simply execute the queries once to cache them
            for service_id in service_ids:
                _ = get_service_data(service_id)

            return True
        except Exception as e:
            logger.error(f"Error warming popular services: {e}")
            return False

    def warm_service_categories(self) -> bool:
        """Warm cache for service categories by executing common queries.

        Returns:
            bool: True if successful

        """
        try:
            from services.models import ServiceCategory

            # Execute the query to cache the results with django-cachalot
            categories = list(ServiceCategory.objects.all())
            # Access category data to trigger caching
            _ = [
                {
                    "id": category.id,
                    "name": category.name,
                    "description": category.description,
                }
                for category in categories
            ]
            return True
        except Exception as e:
            logger.error(f"Error warming service categories: {e}")
            return False

    def warm_user_cart(self, user_id: int) -> bool:
        """Warm cache for user's cart by executing common queries.

        Args:
            user_id: User ID

        Returns:
            bool: True if successful

        """
        try:
            from orders.models import Order

            # Execute the query to cache the results with django-cachalot
            cart = Order.objects.filter(user_id=user_id, status="cart").first()
            if cart:
                # Access related items to cache them too
                _ = list(cart.items.all())
            return True
        except Exception as e:
            logger.error(f"Error warming user cart: {e}")
            return False

    def warm_user_profile(self, user_id: int) -> bool:
        """Warm cache for user profile data by executing common queries.

        Args:
            user_id: User ID

        Returns:
            bool: True if successful

        """
        try:
            from accounts.models import User

            # Execute the query to cache the results with django-cachalot
            _ = User.objects.select_related("profile").get(id=user_id)
            return True
        except Exception as e:
            logger.error(f"Error warming user profile: {e}")
            return False

    def warm_user_reviews(self, user_id: int) -> bool:
        """Warm cache for user's review data by executing common queries.

        Args:
            user_id: User ID

        Returns:
            bool: True if successful

        """
        try:
            from services.models import Review

            # Execute the query to cache the results with django-cachalot
            reviews = (
                Review.objects.filter(user_id=user_id)
                .select_related("service")
                .order_by("-created_at")
            )
            _ = list(reviews)
            return True
        except Exception as e:
            logger.error(f"Error warming user reviews: {e}")
            return False

    def warm_user_order_history(self, user_id: int) -> bool:
        """Warm cache for user's order history by executing common queries.

        Args:
            user_id: User ID

        Returns:
            bool: True if successful

        """
        try:
            from orders.models import Order

            # Execute the query to cache the results with django-cachalot
            orders = (
                Order.objects.filter(user_id=user_id)
                .exclude(status="cart")
                .order_by("-created_at")
            )
            # Access items to cache related data too
            for order in orders:
                _ = list(order.items.all())
            return True
        except Exception as e:
            logger.error(f"Error warming user order history: {e}")
            return False

    def warm_service_reviews(self, service_id: int) -> bool:
        """Warm cache for service reviews by executing common queries.

        Args:
            service_id: Service ID

        Returns:
            bool: True if successful

        """
        try:
            from services.models import Review, Service

            # Execute the queries to cache the results with django-cachalot
            _ = Service.objects.get(id=service_id)
            reviews = (
                Review.objects.filter(service_id=service_id)
                .select_related("user")
                .order_by("-created_at")[:10]  # Limit to 10 recent reviews
            )
            _ = list(reviews)
            return True
        except Exception as e:
            logger.error(f"Error warming service reviews: {e}")
            return False

    def predict_and_warm_user_cache(self, user_id: int, access_patterns: dict) -> bool:
        """Predictively warm user-related caches based on access patterns.

        Args:
            user_id: User ID
            access_patterns: Dictionary containing user access patterns

        Returns:
            bool: True if successful

        """
        try:
            # Warm user profile (always warm as it's frequently accessed)
            self.warm_user_profile(user_id)

            # Warm user cart if user frequently accesses cart
            if access_patterns.get("cart_access_frequency", 0) > 0.5:
                self.warm_user_cart(user_id)

            # Warm user reviews if user is active in reviewing
            if access_patterns.get("review_activity", 0) > 0.3:
                self.warm_user_reviews(user_id)

            # Warm order history if user frequently checks orders
            if access_patterns.get("order_history_access_frequency", 0) > 0.4:
                self.warm_user_order_history(user_id)

            return True
        except Exception as e:
            logger.error(f"Error in predictive warming for user {user_id}: {e}")
            return False

    def warm_popular_services_by_category(
        self,
        category_id: int,
        limit: int = 10,
    ) -> bool:
        """Warm cache for popular services in a specific category.

        Args:
            category_id: Category ID
            limit: Number of services to warm

        Returns:
            bool: True if successful

        """
        try:
            from services.models import Service

            # Execute the query to cache the results with django-cachalot
            services = (
                Service.objects.filter(category_id=category_id, is_active=True)
                .annotate(
                    review_count_val=Count("reviews"),
                    avg_rating_val=Avg("reviews__rating"),
                )
                .order_by("-review_count_val", "-avg_rating_val")[:limit]
            )
            _ = list(services)
            return True
        except Exception as e:
            logger.error(f"Error warming popular services by category: {e}")
            return False


# Global instance
cache_warming_strategy = CacheWarmingStrategy()


class ScheduledCacheWarming:
    """Scheduled cache warming tasks that can be run periodically."""

    def __init__(self):
        self.warming_strategy = cache_warming_strategy

    def warm_all_service_categories(self) -> bool:
        """Warm cache for all service categories.
        This should be run periodically to keep category data fresh.

        Returns:
            bool: True if successful

        """
        return self.warming_strategy.warm_service_categories()

    def warm_top_services(self, limit: int = 50) -> bool:
        """Warm cache for top services based on popularity.

        Args:
            limit: Number of top services to warm

        Returns:
            bool: True if successful

        """
        try:
            from services.models import Service

            # Get top services by review count - this query will be cached by django-cachalot
            top_services = (
                Service.objects.filter(is_active=True)
                .annotate(review_count_val=Count("reviews"))
                .order_by("-review_count_val")[:limit]
            )

            service_ids = [service.id for service in top_services]
            return self.warming_strategy.warm_popular_services(service_ids)
        except Exception as e:
            logger.error(f"Error warming top services: {e}")
            return False

    def warm_active_user_profiles(self, limit: int = 100) -> bool:
        """Warm cache for active user profiles.

        Args:
            limit: Number of active users to warm

        Returns:
            bool: True if successful

        """
        try:
            from accounts.models import User

            # Get users with recent orders (active users) - this query will be cached by django-cachalot
            active_users = User.objects.filter(
                orders__created_at__gte=datetime.now() - timedelta(days=30),
            ).distinct()[:limit]

            success_count = 0
            for user in active_users:
                if self.warming_strategy.warm_user_profile(user.id):
                    success_count += 1

            logger.info(
                f"Warmed profiles for {success_count}/{len(active_users)} active users",
            )
            return True
        except Exception as e:
            logger.error(f"Error warming active user profiles: {e}")
            return False

    def warm_service_statistics(self) -> bool:
        """Warm cache for service statistics data.

        Returns:
            bool: True if successful

        """
        try:
            from orders.models import OrderItem
            from services.models import Service, ServiceCategory

            # Execute the queries that will be cached by django-cachalot
            _ = Service.objects.filter(is_active=True).count()

            _ = list(
                ServiceCategory.objects.annotate(
                    service_count=Count(
                        "services",
                        filter=models.Q(services__is_active=True),
                    ),
                ).values("id", "name", "service_count"),
            )

            _ = list(
                OrderItem.objects.values("service_id", "service__name")
                .annotate(order_count=Count("service_id"))
                .order_by("-order_count")[:10],
            )

            return True
        except Exception as e:
            logger.error(f"Error warming service statistics: {e}")
            return False


# Global instance
scheduled_cache_warming = ScheduledCacheWarming()
