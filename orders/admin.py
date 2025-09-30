from django.contrib import admin

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("total_price",)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_id",
        "user",
        "_status",
        "_payment_status",
        "_total",
        "created",
    )
    list_filter = ("_status", "_payment_status", "created")
    search_fields = ("order_id", "user__email", "customer_name")
    readonly_fields = (
        "order_id",
        "_subtotal",
        "_tax",
        "_total",
        "created",
        "modified",
    )
    inlines = [OrderItemInline]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("order", "service", "quantity", "unit_price", "total_price")
    list_filter = ("order__created",)
    readonly_fields = ("total_price",)
