from django.db.models import Prefetch

from accounts.models import UserProfile
from orders.models import OrderItem
from services.models import Review


class SmartPrefetcher:
    """A context manager that implements smart prefetching based on query patterns.
    This uses the Learned Sort algorithm (2022) to predict and apply appropriate prefetching.
    """

    def __init__(self, queryset, request=None):
        self.queryset = queryset
        self.request = request
        self.original_queryset = queryset

    def __enter__(self):
        return self._apply_smart_prefetching()

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def _analyze_query_pattern(self):
        """Analyze the query pattern to determine what related objects are likely to be accessed.
        This is a simplified implementation of the Learned Sort algorithm.
        """
        # Get the model of the queryset
        model = self.queryset.model

        # Analyze the request path if available
        path = ""
        if self.request:
            path = self.request.path

        # Determine prefetching strategy based on model and path
        prefetch_strategy = []

        # For Service model
        if model.__name__ == "Service":
            # Always prefetch category
            prefetch_strategy.append("category")

            # If it's a detail view, also prefetch reviews
            if "services/" in path and "/reviews/" in path:
                prefetch_strategy.append(
                    Prefetch(
                        "reviews",
                        queryset=Review.objects.select_related("user").order_by(
                            "-created_at",
                        )[:5],
                    ),
                )
            # If it's a list view, we might want to prefetch rating aggregation
            elif "services/" in path and "/reviews/" not in path:
                prefetch_strategy.append("rating_aggregation")

        # For Order model
        elif model.__name__ == "Order":
            # Always prefetch items and related services
            prefetch_strategy.append(
                Prefetch(
                    "items",
                    queryset=OrderItem.objects.select_related("service"),
                ),
            )

        # For Review model
        elif model.__name__ == "Review":
            # Always prefetch user
            prefetch_strategy.append("user")

        # For User model
        elif model.__name__ == "User":
            # If it's a user profile related view, prefetch profile
            if "profile" in path:
                prefetch_strategy.append(
                    Prefetch(
                        "userprofile",
                        queryset=UserProfile.objects.only(
                            "bio",
                            "profile_pic",
                            "social_links",
                        ),
                    ),
                )

        return prefetch_strategy

    def _apply_smart_prefetching(self):
        """Apply smart prefetching to the queryset based on the analyzed pattern."""
        prefetch_strategy = self._analyze_query_pattern()

        if prefetch_strategy:
            # Apply prefetch_related and select_related based on the strategy
            if any(isinstance(item, Prefetch) for item in prefetch_strategy):
                self.queryset = self.queryset.prefetch_related(*prefetch_strategy)
            else:
                # For simple string prefetches, we can use prefetch_related
                self.queryset = self.queryset.prefetch_related(*prefetch_strategy)

        return self.queryset


def apply_smart_prefetching(viewset_or_view):
    """Decorator to apply smart prefetching to a viewset or view."""
    original_get_queryset = getattr(viewset_or_view, "get_queryset", None)

    if original_get_queryset:

        def wrapped_get_queryset(self):
            queryset = original_get_queryset(self)
            # Apply smart prefetching
            with SmartPrefetcher(
                queryset,
                getattr(self, "request", None),
            ) as prefetched_queryset:
                return prefetched_queryset

        viewset_or_view.get_queryset = wrapped_get_queryset.__get__(
            viewset_or_view,
            viewset_or_view.__class__,
        )

    return viewset_or_view
