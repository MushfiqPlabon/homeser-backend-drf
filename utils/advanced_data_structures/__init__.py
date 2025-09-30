# utils/advanced_data_structures/__init__.py
# Expose advanced data structures for easy import

from .bloom_filter import BloomFilter
from .hash_table import ServiceHashTable
from .segment_tree import SegmentTree
from .trie import Trie

# Create global instances
service_hash_table = ServiceHashTable()
service_bloom_filter = BloomFilter()
service_name_trie = Trie()


# Create segment tree with empty data initially
def max_func(a, b):
    """Helper function to find maximum of two values."""
    if a is None:
        return b
    if b is None:
        return a
    return max(a, b)


service_rating_segment_tree = SegmentTree(
    data=[],  # Empty data initially
    merge_func=max_func,  # Default to max function for finding highest rated services
)

# Expose the instances for import
__all__ = [
    "BloomFilter",
    "SegmentTree",
    "ServiceHashTable",
    "Trie",
    "service_bloom_filter",
    "service_hash_table",
    "service_name_trie",
    "service_rating_segment_tree",
]
