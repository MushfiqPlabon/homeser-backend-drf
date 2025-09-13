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
        "status",
        "payment_status",
        "total",
        "created_at",
    )
    list_filter = ("status", "payment_status", "created_at")
    search_fields = ("order_id", "user__email", "customer_name")
    readonly_fields = (
        "order_id",
        "subtotal",
        "tax",
        "total",
        "created_at",
        "updated_at",
    )
    inlines = [OrderItemInline]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("order", "service", "quantity", "price", "total_price")
    list_filter = ("created_at",)
    readonly_fields = ("total_price",)
