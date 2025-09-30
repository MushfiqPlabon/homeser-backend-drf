import logging

from django.conf import settings
from redisbloom.client import Client

logger = logging.getLogger(__name__)


class RedisBloomService:
    """Service to handle RedisBloom operations for probabilistic data structures
    """

    _client = None

    @classmethod
    def get_client(cls):
        """Get or create RedisBloom client
        """
        if cls._client is None:
            try:
                redis_url = getattr(
                    settings, "REDISBLOOM_HOST", "redis://127.0.0.1:6379",
                )
                cls._client = Client(host=redis_url)
            except Exception as e:
                logger.error(f"Failed to create RedisBloom client: {e}")
                return None

        return cls._client

    @classmethod
    def add_to_filter(cls, filter_name, item):
        """Add an item to a Bloom filter

        Args:
            filter_name (str): Name of the Bloom filter
            item (str): Item to add to the filter

        """
        client = cls.get_client()
        if not client:
            return False

        try:
            # Create filter if it doesn't exist (capacity 100000, error rate 0.01)
            try:
                client.reserve(filter_name, 0.01, 100000)
            except Exception:
                # Filter already exists
                pass

            return client.add(filter_name, str(item))
        except Exception as e:
            logger.error(f"Failed to add item to Bloom filter {filter_name}: {e}")
            return False

    @classmethod
    def exists_in_filter(cls, filter_name, item):
        """Check if an item exists in a Bloom filter

        Args:
            filter_name (str): Name of the Bloom filter
            item (str): Item to check in the filter

        Returns:
            bool: True if item possibly exists, False if definitely doesn't exist

        """
        client = cls.get_client()
        if not client:
            return False

        try:
            return client.exists(filter_name, str(item))
        except Exception as e:
            logger.error(f"Failed to check item in Bloom filter {filter_name}: {e}")
            return False

    @classmethod
    def batch_add_to_filter(cls, filter_name, items):
        """Add multiple items to a Bloom filter

        Args:
            filter_name (str): Name of the Bloom filter
            items (list): List of items to add to the filter

        """
        client = cls.get_client()
        if not client:
            return False

        try:
            # Create filter if it doesn't exist (capacity 100000, error rate 0.01)
            try:
                client.reserve(filter_name, 0.01, 100000)
            except Exception:
                # Filter already exists
                pass

            return client.madd(filter_name, *items)
        except Exception as e:
            logger.error(
                f"Failed to batch add items to Bloom filter {filter_name}: {e}",
            )
            return False
