# utils/advanced_data_structures/bloom_filter.py
# Bloom filter implementation for cache penetration protection

import hashlib
import math

from django.core.cache import cache


class BloomFilter:
    """Bloom filter implementation for probabilistic set membership testing.
    Used to reduce database hits for non-existent cache keys.
    Proper implementation using Redis for storage.
    """

    def __init__(
        self,
        capacity: int = 100000,
        error_rate: float = 0.01,
        redis_key: str = "bloom_filter",
    ):
        """Initialize the Bloom filter.

        Args:
            capacity: Expected number of items to store
            error_rate: Desired false positive rate (0.01 = 1%)
            redis_key: Redis key prefix for storing filter data

        """
        self.capacity = capacity
        self.error_rate = error_rate
        self.redis_key = redis_key

        # Calculate optimal number of hash functions and bit array size
        self.bit_array_size = self._optimal_bit_array_size(capacity, error_rate)
        self.num_hashes = self._optimal_num_hashes(capacity, error_rate)

    def _optimal_num_hashes(self, capacity: int, error_rate: float) -> int:
        """Calculate optimal number of hash functions."""
        return int(math.ceil(math.log(2) * self.bit_array_size / capacity))

    def _optimal_bit_array_size(self, capacity: int, error_rate: float) -> int:
        """Calculate optimal bit array size."""
        return int(math.ceil(-capacity * math.log(error_rate) / (math.log(2) ** 2)))

    def _hash(self, item: str | int, seed: int) -> int:
        """Generate a hash for an item with a specific seed."""
        item_str = str(item).encode("utf-8")
        hash_obj = hashlib.md5(item_str + str(seed).encode("utf-8"))
        return int(hash_obj.hexdigest(), 16) % self.bit_array_size

    def _get_bit_positions(self, item: str | int) -> list[int]:
        """Get the positions in the bit array that correspond to the item."""
        positions = []
        for i in range(self.num_hashes):
            positions.append(self._hash(item, i))
        return positions

    def add(self, item: str | int) -> bool:
        """Add an item to the Bloom filter.

        Args:
            item: Item to add

        Returns:
            bool: True if successful

        """
        try:
            bit_positions = self._get_bit_positions(item)

            # Get the current bit array from cache
            bit_array_key = f"{self.redis_key}:bits"
            bit_array = cache.get(bit_array_key, [0] * self.bit_array_size)

            # Set the appropriate bits
            for pos in bit_positions:
                bit_array[pos] = 1

            # Store the updated bit array back to cache
            cache.set(
                bit_array_key, bit_array, timeout=None
            )  # No timeout for bloom filter

            return True
        except Exception:
            # If there's an error, still return True to avoid false negatives
            return True

    def check(self, item: str | int) -> bool:
        """Check if an item might be in the set (probabilistic).

        Args:
            item: Item to check

        Returns:
            bool: True if item might be in set, False if definitely not

        """
        try:
            bit_positions = self._get_bit_positions(item)

            # Get the current bit array from cache
            bit_array_key = f"{self.redis_key}:bits"
            bit_array = cache.get(bit_array_key, [0] * self.bit_array_size)

            # Check if all the corresponding bits are set
            for pos in bit_positions:
                if bit_array[pos] == 0:
                    return False  # Definitely not in the set

            return True  # Might be in the set
        except Exception:
            # If there's an error accessing the bit array, assume the item exists to avoid false negatives
            return True

    def get_stats(self) -> dict:
        """Get statistics about the Bloom filter."""
        return {
            "capacity": self.capacity,
            "error_rate": self.error_rate,
            "num_hashes": self.num_hashes,
            "bit_array_size": self.bit_array_size,
            "redis_key": self.redis_key,
        }


# Global instance for service use
service_bloom_filter = BloomFilter(
    capacity=100000,
    error_rate=0.001,
    redis_key="homeser_service_bloom",
)
