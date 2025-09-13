from django.contrib import admin
from .models import Payment, PaymentLog


class PaymentLogInline(admin.TabularInline):
    model = PaymentLog
    extra = 0
    readonly_fields = ("action", "data", "created_at")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("transaction_id", "order", "amount", "status", "created_at")
    list_filter = ("status", "currency", "created_at")
    search_fields = ("transaction_id", "order__order_id", "val_id")
    readonly_fields = ("created_at", "updated_at")
    inlines = [PaymentLogInline]


@admin.register(PaymentLog)
class PaymentLogAdmin(admin.ModelAdmin):
    list_display = ("payment", "action", "created_at")
    list_filter = ("action", "created_at")
    readonly_fields = ("payment", "action", "data", "created_at")
