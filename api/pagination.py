from rest_framework.pagination import CursorPagination


class ServiceCursorPagination(CursorPagination):
    """Custom cursor pagination for services that orders by created_at field.
    """

    ordering = "-created_at"
    page_size = 20
