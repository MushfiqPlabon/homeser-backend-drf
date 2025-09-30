from django.db.models import Q
from django_filters import rest_framework as filters

from orders.models import Order
from services.models import Review, Service, ServiceCategory


class ServiceFilter(filters.FilterSet):
    """Filter for Service model"""

    category = filters.NumberFilter(field_name="category__id")
    category_name = filters.CharFilter(
        field_name="category__name", lookup_expr="icontains",
    )
    min_price = filters.NumberFilter(field_name="price", lookup_expr="gte")
    max_price = filters.NumberFilter(field_name="price", lookup_expr="lte")
    is_active = filters.BooleanFilter(field_name="is_active")
    name = filters.CharFilter(field_name="name", lookup_expr="icontains")
    search = filters.CharFilter(method="search_filter")

    class Meta:
        model = Service
        fields = ["category", "min_price", "max_price", "is_active"]

    def search_filter(self, queryset, name, value):
        """Filter services by name or category name"""
        return queryset.filter(
            Q(name__icontains=value)
            | Q(category__name__icontains=value)
            | Q(short_desc__icontains=value)
            | Q(description__icontains=value),
        )


class ServiceCategoryFilter(filters.FilterSet):
    """Filter for ServiceCategory model"""

    name = filters.CharFilter(field_name="name", lookup_expr="icontains")
    search = filters.CharFilter(method="search_filter")

    class Meta:
        model = ServiceCategory
        fields = ["name"]

    def search_filter(self, queryset, name, value):
        """Filter categories by name"""
        return queryset.filter(name__icontains=value)


class OrderFilter(filters.FilterSet):
    """Filter for Order model"""

    user = filters.NumberFilter(field_name="user__id")
    status = filters.CharFilter(field_name="_status")
    payment_status = filters.CharFilter(field_name="_payment_status")
    customer_name = filters.CharFilter(
        field_name="customer_name", lookup_expr="icontains",
    )
    order_id = filters.CharFilter(field_name="order_id", lookup_expr="icontains")
    date_from = filters.DateTimeFilter(field_name="created", lookup_expr="gte")
    date_to = filters.DateTimeFilter(field_name="created", lookup_expr="lte")

    class Meta:
        model = Order
        fields = ["user", "status", "payment_status", "customer_name", "order_id"]


class ReviewFilter(filters.FilterSet):
    """Filter for Review model"""

    service = filters.NumberFilter(field_name="service__id")
    user = filters.NumberFilter(field_name="user__id")
    min_rating = filters.NumberFilter(field_name="rating", lookup_expr="gte")
    max_rating = filters.NumberFilter(field_name="rating", lookup_expr="lte")
    has_text = filters.BooleanFilter(method="has_text_filter")
    date_from = filters.DateTimeFilter(field_name="created", lookup_expr="gte")
    date_to = filters.DateTimeFilter(field_name="created", lookup_expr="lte")

    class Meta:
        model = Review
        fields = ["service", "user", "min_rating", "max_rating"]

    def has_text_filter(self, queryset, name, value):
        """Filter reviews that have/don't have text"""
        if value:
            return queryset.exclude(text="")
        return queryset.filter(text="")
