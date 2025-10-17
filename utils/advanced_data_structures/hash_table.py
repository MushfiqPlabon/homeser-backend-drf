# utils/advanced_data_structures/hash_table.py
# Hash table implementation for O(1) lookups in critical paths

import hashlib
import logging
from typing import Any

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class ServiceHashTable:
    """Hash table implementation for fast service lookups.
    Simplified implementation focusing on core functionality.
    """

    def __init__(self, cache_prefix: str = "service_hash"):
        self.cache_prefix = cache_prefix
        self.cache_timeout = getattr(settings, "CACHE_TTL", 900)  # Default 15 minutes

    def _get_cache_key(self, key: str) -> str:
        """Generate a cache key using hash to ensure consistent length."""
        key_hash = hashlib.md5(str(key).encode()).hexdigest()
        return f"{self.cache_prefix}:{key_hash}"

    def set(self, key: str, value: Any, timeout: int | None = None) -> bool:
        """Set a key-value pair in the hash table.

        Args:
            key: The key to store the value under
            value: The value to store
            timeout: Cache timeout in seconds (defaults to settings.CACHE_TTL)

        Returns:
            bool: True if successful

        """
        try:
            cache_key = self._get_cache_key(key)
            # Store in cache with timeout
            cache.set(cache_key, value, timeout or self.cache_timeout)
            return True
        except Exception as e:
            logger.error(f"Error setting hash table value for key '{key}': {e}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the hash table.

        Args:
            key: The key to retrieve
            default: Default value if key not found

        Returns:
            The value if found, otherwise default

        """
        try:
            cache_key = self._get_cache_key(key)
            return cache.get(cache_key, default)
        except Exception as e:
            logger.error(f"Error getting hash table value for key '{key}': {e}")
            return default

    def delete(self, key: str) -> bool:
        """Delete a key from the hash table.

        Args:
            key: The key to delete

        Returns:
            bool: True if successful

        """
        try:
            cache_key = self._get_cache_key(key)
            cache.delete(cache_key)
            return True
        except Exception as e:
            logger.error(f"Error deleting hash table value for key '{key}': {e}")
            return False

    def update_service_data(self, key: str, service_data: dict) -> bool:
        """Update the data for a service in the hash table.

        Args:
            key: The service ID
            service_data: Updated service data

        Returns:
            bool: True if successful

        """
        try:
            return self.set(key, service_data)
        except Exception as e:
            logger.error(f"Error updating service data for key '{key}': {e}")
            return False

    def batch_get(self, keys: list[str]) -> dict:
        """Get multiple values from the hash table efficiently.

        Args:
            keys: List of keys to retrieve

        Returns:
            dict: Dictionary of key-value pairs

        """
        try:
            # Create cache keys for all requested keys
            cache_keys = {self._get_cache_key(key): key for key in keys}
            # Get all values from cache
            cached_values = cache.get_many(list(cache_keys.keys()))
            # Map back to original keys
            result = {}
            for cache_key, value in cached_values.items():
                original_key = cache_keys[cache_key]
                result[original_key] = value
            return result
        except Exception as e:
            logger.error(f"Error in batch get: {e}")
            # Fallback to individual gets
            result = {}
            for key in keys:
                result[key] = self.get(key)
            return result

    def bulk_load_services(self, services: list) -> bool:
        """Bulk load services into the hash table for O(1) access.

        Args:
            services: List of service objects to load

        Returns:
            bool: True if successful

        """
        try:
            # Create a dictionary of service data for bulk loading
            service_data = {}
            for service in services:
                service_id = str(getattr(service, "id", None))
                if service_id:
                    # Prepare service data for caching
                    service_data[service_id] = {
                        "id": service.id,
                        "name": getattr(service, "name", ""),
                        "description": getattr(service, "description", ""),
                        "price": str(getattr(service, "price", "0.00")),
                        "is_active": getattr(service, "is_active", True),
                        "category_id": getattr(
                            getattr(service, "category", None), "id", None
                        ),
                        "avg_rating": str(getattr(service, "avg_rating", "0.0")),
                        "review_count": getattr(service, "review_count", 0),
                    }

            # Create cache keys for all services
            cache_entries = {}
            for service_id, data in service_data.items():
                cache_key = self._get_cache_key(service_id)
                cache_entries[cache_key] = data

            # Bulk set all cache entries
            cache.set_many(cache_entries, self.cache_timeout)
            return True
        except Exception as e:
            logger.error(f"Error bulk loading services: {e}")
            return False

    def get_stats(self) -> dict:
        """Get statistics about the hash table."""
        return {
            "cache_prefix": self.cache_prefix,
            "cache_timeout": self.cache_timeout,
        }


class OrderHashTable:
    """Hash table implementation for fast order lookups."""

    def __init__(self, cache_prefix: str = "order_hash"):
        self.cache_prefix = cache_prefix
        self.cache_timeout = getattr(settings, "CACHE_TTL", 900)  # Default 15 minutes

    def _get_cache_key(self, key: str) -> str:
        """Generate a cache key using hash to ensure consistent length."""
        key_hash = hashlib.md5(str(key).encode()).hexdigest()
        return f"{self.cache_prefix}:{key_hash}"

    def set(self, key: str, value: Any, timeout: int | None = None) -> bool:
        """Set a key-value pair in the hash table.

        Args:
            key: The key to store the value under
            value: The value to store
            timeout: Cache timeout in seconds (defaults to settings.CACHE_TTL)

        Returns:
            bool: True if successful

        """
        try:
            cache_key = self._get_cache_key(key)
            # Store in cache with timeout
            cache.set(cache_key, value, timeout or self.cache_timeout)
            return True
        except Exception as e:
            logger.error(f"Error setting order hash table value for key '{key}': {e}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the hash table.

        Args:
            key: The key to retrieve
            default: Default value if key not found

        Returns:
            The value if found, otherwise default

        """
        try:
            cache_key = self._get_cache_key(key)
            return cache.get(cache_key, default)
        except Exception as e:
            logger.error(f"Error getting order hash table value for key '{key}': {e}")
            return default

    def delete(self, key: str) -> bool:
        """Delete a key from the hash table.

        Args:
            key: The key to delete

        Returns:
            bool: True if successful

        """
        try:
            cache_key = self._get_cache_key(key)
            cache.delete(cache_key)
            return True
        except Exception as e:
            logger.error(f"Error deleting order hash table value for key '{key}': {e}")
            return False

    def update_order_data(self, key: str, order_data: dict) -> bool:
        """Update the data for an order in the hash table.

        Args:
            key: The order ID
            order_data: Updated order data

        Returns:
            bool: True if successful

        """
        try:
            return self.set(key, order_data)
        except Exception as e:
            logger.error(f"Error updating order data for key '{key}': {e}")
            return False

    def batch_get(self, keys: list[str]) -> dict:
        """Get multiple values from the hash table efficiently.

        Args:
            keys: List of keys to retrieve

        Returns:
            dict: Dictionary of key-value pairs

        """
        try:
            # Create cache keys for all requested keys
            cache_keys = {self._get_cache_key(key): key for key in keys}
            # Get all values from cache
            cached_values = cache.get_many(list(cache_keys.keys()))
            # Map back to original keys
            result = {}
            for cache_key, value in cached_values.items():
                original_key = cache_keys[cache_key]
                result[original_key] = value
            return result
        except Exception as e:
            logger.error(f"Error in order batch get: {e}")
            # Fallback to individual gets
            result = {}
            for key in keys:
                result[key] = self.get(key)
            return result

    def bulk_load_orders(self, orders: list) -> bool:
        """Bulk load orders into the hash table for O(1) access.

        Args:
            orders: List of order objects to load

        Returns:
            bool: True if successful

        """
        try:
            # Create a dictionary of order data for bulk loading
            order_data = {}
            for order in orders:
                order_id = str(getattr(order, "id", None))
                if order_id:
                    # Prepare order data for caching
                    order_data[order_id] = {
                        "id": order.id,
                        "order_id": getattr(order, "order_id", ""),
                        "status": getattr(order, "status", ""),
                        "payment_status": getattr(order, "payment_status", ""),
                        "customer_name": getattr(order, "customer_name", ""),
                        "customer_address": getattr(order, "customer_address", ""),
                        "customer_phone": getattr(order, "customer_phone", ""),
                        "total": str(getattr(order, "total", "0.00")),
                        "user_id": getattr(getattr(order, "user", None), "id", None),
                        "created": str(getattr(order, "created", "")),
                        "modified": str(getattr(order, "modified", "")),
                    }

            # Create cache keys for all orders
            cache_entries = {}
            for order_id, data in order_data.items():
                cache_key = self._get_cache_key(order_id)
                cache_entries[cache_key] = data

            # Bulk set all cache entries
            cache.set_many(cache_entries, self.cache_timeout)
            return True
        except Exception as e:
            logger.error(f"Error bulk loading orders: {e}")
            return False

    def get_stats(self) -> dict:
        """Get statistics about the hash table."""
        return {
            "cache_prefix": self.cache_prefix,
            "cache_timeout": self.cache_timeout,
        }


# Global instance for service lookups
service_hash_table = ServiceHashTable("homeser_services")

# Global instance for order lookups
order_hash_table = OrderHashTable("homeser_orders")
