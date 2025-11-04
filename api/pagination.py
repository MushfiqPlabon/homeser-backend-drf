from rest_framework.pagination import CursorPagination


class OptimizedServiceCursorPagination(CursorPagination):
    """Optimized cursor pagination for services that works with multiple ordering fields."""

    # Default ordering field that matches the model's default ordering
    ordering = "-created"
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class ServiceCursorPagination(OptimizedServiceCursorPagination):
    """Alias for backward compatibility"""

