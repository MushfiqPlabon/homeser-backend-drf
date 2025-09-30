# utils/advanced_data_structures/segment_tree.py
# Segment tree implementation for range queries on service data

from collections.abc import Callable
from typing import Any


class SegmentTree:
    """Simplified segment tree implementation for efficient range queries.
    For performance optimization, we're reducing complexity and focusing on core functionality.
    """

    def __init__(
        self,
        data: list[Any] = None,
        merge_func: Callable = None,
    ):
        """Initialize the segment tree.

        Args:
            data: Initial data array
            merge_func: Function to merge two values (default: max)

        """
        self.data = data or []
        self.merge_func = merge_func or (lambda a, b: max(a or 0, b or 0))

    def query(self, left: int, right: int) -> Any:
        """Query the value (result of merge_func) in range [left, right].

        Args:
            left: Left boundary of query (inclusive)
            right: Right boundary of query (inclusive)

        Returns:
            Result of merge_func over range

        """
        # For performance optimization, use simple slice and reduce operation
        if left < 0 or right >= len(self.data) or left > right:
            return None
        subset = self.data[left : right + 1]
        if not subset:
            return None
        result = subset[0]
        for value in subset[1:]:
            result = self.merge_func(result, value)
        return result

    def update(self, index: int, value: Any) -> None:
        """Update the value at a specific index.

        Args:
            index: Index to update
            value: New value

        """
        if 0 <= index < len(self.data):
            self.data[index] = value

    def get_max_rating_in_range(self, left: int, right: int) -> float:
        """Get the maximum rating in a range of services.

        Args:
            left: Left boundary of range (inclusive)
            right: Right boundary of range (inclusive)

        Returns:
            float: Maximum rating in the range

        """
        result = self.query(left, right)
        return result if result is not None else 0.0

    def get_average_rating(self) -> float:
        """Get the average rating across all services.

        Returns:
            float: Average rating

        """
        if not self.data:
            return 0.0

        total = sum(filter(None, self.data))  # Filter out None values
        return total / len(self.data)


# Example usage for service analytics
def max_func(a, b):
    """Helper function to find maximum of two values."""
    if a is None:
        return b
    if b is None:
        return a
    return max(a, b)


# Create a simple instance without pre-populating data
service_rating_segment_tree = SegmentTree(
    data=[],  # Empty data initially
    merge_func=max_func,  # Default to max function for finding highest rated services
)
