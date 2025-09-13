from django.db import models
from django.contrib.auth import get_user_model
from services.models import Service
import uuid
from decimal import Decimal

User = get_user_model()


class Order(models.Model):
    """Order model for handling purchases"""

    STATUS_CHOICES = [
        ("cart", "Cart"),
        ("pending", "Pending Payment"),
        ("confirmed", "Confirmed"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    PAYMENT_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="orders", db_index=True
    )
    order_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="cart", db_index=True
    )
    payment_status = models.CharField(
        max_length=20, choices=PAYMENT_STATUS_CHOICES, default="pending"
    )

    # Customer details for delivery
    customer_name = models.CharField(max_length=100, blank=True)
    customer_address = models.TextField(blank=True)
    customer_phone = models.CharField(max_length=20, blank=True)

    # Payment details
    payment_method = models.CharField(max_length=50, default="sslcommerz")
    transaction_id = models.CharField(max_length=100, blank=True, null=True)

    # Totals
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def calculate_totals(self):
        """Calculate order totals based on items"""
        # Use prefetched items if available to avoid N+1 query issue
        if (
            hasattr(self, "_prefetched_objects_cache")
            and "items" in self._prefetched_objects_cache
        ):
            items = self._prefetched_objects_cache["items"]
            self.subtotal = sum(item.total_price for item in items)
        else:
            # Fallback to database query if items are not prefetched
            self.subtotal = sum(item.total_price for item in self.items.all())
        self.tax = self.subtotal * Decimal("0.05")  # Apply a 5% tax rate
        self.total = self.subtotal + self.tax
        self.save()

    def __str__(self):
        return f"Order {self.order_id} - {self.user.email}"


class OrderItem(models.Model):
    """Individual items in an order"""

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def total_price(self):
        return self.quantity * self.price

    def save(self, *args, **kwargs):
        # Check if we should skip order recalculation
        skip_order_update = kwargs.pop("skip_order_update", False)

        if not self.price:
            self.price = self.service.price
        super().save(*args, **kwargs)

        # Only recalculate order totals if not explicitly skipped
        if not skip_order_update:
            # Important: Recalculate the parent order's totals every time an item is saved
            # to ensure the order's subtotal, tax, and total are always up-to-date.
            self.order.calculate_totals()

    def delete(self, *args, **kwargs):
        # Check if we should skip order recalculation
        skip_order_update = kwargs.pop("skip_order_update", False)

        order = self.order
        super().delete(*args, **kwargs)

        # Only recalculate order totals if not explicitly skipped
        if not skip_order_update:
            # Important: Recalculate the parent order's totals after an item is deleted
            # to ensure the order's subtotal, tax, and total are always up-to-date.
            order.calculate_totals()

    def __str__(self):
        return f"{self.service.name} x {self.quantity}"
