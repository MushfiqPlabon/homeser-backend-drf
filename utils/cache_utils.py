import logging

from cachalot.api import invalidate as cachalot_invalidate
from django.db.models import Avg, Count

from services.models import Service

# Configure logger
logger = logging.getLogger(__name__)


def get_cached_data_with_fallback(key, data_generator_func, timeout=None):
    """Get data from cache with fallback to generator function.
    This function now relies on django-cachalot for automatic ORM query caching.

    Args:
        key: Cache key (for compatibility, not used by cachalot)
        data_generator_func: Function that generates the data if not cached
        timeout: Cache timeout in seconds (not used by cachalot)

    Returns:
        Generated data (cachalot handles caching automatically)

    """
    # With django-cachalot, we just execute the function normally
    # since cachalot automatically caches ORM queries
    return data_generator_func()


def invalidate_cache_for_instance(obj):
    """Invalidate cache for a specific data entity using django-cachalot.
    This replaces the complex custom dependency tracking system.

    Args:
        obj (Model instance): The data entity that has changed

    """
    try:
        # Use django-cachalot's invalidate function to clear cached queries for this object
        cachalot_invalidate(obj)
    except Exception as e:
        logger.error(f"Error invalidating cache for instance {obj}: {e}")


def get_service_data(service_id):
    """Retrieve service data. With django-cachalot, ORM queries are automatically cached.

    Args:
        service_id (int): ID of the service to retrieve

    Returns:
        Service: Service instance with annotations

    """
    try:
        # Get service with annotations - django-cachalot will automatically cache this query
        service = (
            Service.objects.filter(id=service_id, is_active=True)
            .annotate(
                avg_rating_val=Avg("reviews__rating"),
                review_count_val=Count("reviews"),
            )
            .first()
        )
        return service
    except Service.DoesNotExist:
        return None


def invalidate_service_cache(service_id):
    """Invalidate cache for a specific service using django-cachalot.

    Args:
        service_id (int): The ID of the service to invalidate cache for

    """
    try:
        # Use django-cachalot's invalidate function for the Service model
        cachalot_invalidate(Service, pk=service_id)
        # Also invalidate related models that might be affected
        from services.models import Review

        cachalot_invalidate(Review, service_id=service_id)
    except Exception as e:
        logger.error(f"Error invalidating service cache for service {service_id}: {e}")


def invalidate_service_list_cache():
    """Invalidate cache for service list data using django-cachalot.
    """
    try:
        # Use django-cachalot's invalidate function for the Service model
        cachalot_invalidate(Service)
    except Exception as e:
        logger.error(f"Error invalidating service list cache: {e}")


def invalidate_all_service_cache():
    """Invalidate all service-related cache using django-cachalot.
    """
    try:
        # Invalidate service model and related models
        cachalot_invalidate(Service)

        # Invalidate related models
        from services.models import Review

        cachalot_invalidate(Review)
    except Exception as e:
        logger.error(f"Error invalidating all service cache: {e}")
