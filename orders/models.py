import logging
import uuid
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import models
from django_fsm import FSMField, can_proceed, transition
from guardian.shortcuts import assign_perm
from model_utils.managers import QueryManager

from homeser.base_models import BaseModel, OrderType
from services.models import Service
from utils.validation_package import validate_min_value

User = get_user_model()

# Set up logging
logger = logging.getLogger(__name__)


class BaseOrderItem(models.Model):
    """Abstract base model for order items with common functionality"""

    quantity = models.PositiveIntegerField(validators=[validate_min_value(1)])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    # Keep the price field for backward compatibility with existing database schema
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    objects = QueryManager()

    class Meta:
        abstract = True

    @property
    def total_price(self):
        """Calculate total price for this item"""
        # Use unit_price if available, otherwise fall back to price
        unit_price = self.unit_price if self.unit_price is not None else self.price
        return unit_price * self.quantity

    def clean(self):
        """Validate model fields"""
        from django.core.exceptions import ValidationError

        if self.quantity <= 0:
            raise ValidationError("Quantity must be greater than zero")

        if self.unit_price < 0:
            raise ValidationError("Price cannot be negative")

        super().clean()

    def save(self, *args, **kwargs):
        """Override save to ensure data integrity"""
        self.full_clean()
        super().save(*args, **kwargs)


class Order(BaseModel):
    """Order model with full state machine implementation"""

    # Comprehensive status choices with all business-critical states
    STATUS_CHOICES = [
        ("draft", "Draft"),  # Initial state, order in cart
        ("pending", "Pending"),  # Submitted but not yet paid
        ("confirmed", "Confirmed"),  # Payment received, awaiting processing
        ("processing", "Processing"),  # Being prepared/processed
        ("shipped", "Shipped"),  # Sent to customer
        ("delivered", "Delivered"),  # Received by customer
        ("completed", "Completed"),  # Final successful state
        ("cancelled", "Cancelled"),  # Cancelled before completion
        ("refunded", "Refunded"),  # Completed order refunded
        ("on_hold", "On Hold"),  # Temporarily paused
        ("disputed", "Disputed"),  # Customer dispute initiated
    ]

    # Comprehensive payment status choices
    PAYMENT_STATUS_CHOICES = [
        ("unpaid", "Unpaid"),  # Initial state
        ("pending", "Pending"),  # Payment initiated but not confirmed
        ("paid", "Paid"),  # Payment confirmed
        ("partially_refuned", "Partially Refuned"),  # Partial refund issued
        ("refunded", "Refunded"),  # Full refund issued
        ("failed", "Failed"),  # Payment attempt failed
        ("disputed", "Disputed"),  # Payment in dispute
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="orders", db_index=True,
    )
    _status = FSMField(
        choices=STATUS_CHOICES, default="draft", db_column="status", db_index=True,
    )
    _payment_status = FSMField(
        choices=PAYMENT_STATUS_CHOICES,
        default="unpaid",
        protected=True,
        db_column="payment_status",
        db_index=True,
    )
    customer_name = models.CharField(max_length=100)
    customer_address = models.TextField()
    customer_phone = models.CharField(max_length=20, blank=True)
    _subtotal = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00"), db_column="subtotal",
    )
    _tax = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00"), db_column="tax",
    )
    _total = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00"), db_column="total",
    )
    order_id = models.CharField(max_length=50, unique=True, db_index=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __str__(self):
        return f"Order {self.order_id} - {self.status}"

    @property
    def status(self):
        """Get the order status"""
        return self._status

    def _is_valid_status_transition(self, value):
        """Check if the status transition is valid."""
        return value in self._STATE_TRANSITIONS.get(self._status, [])

    def _execute_status_transition(self, value):
        """Execute the appropriate status transition."""
        transition_methods = {
            "pending": self.submit,
            "processing": self.process,
            "completed": self.complete,
            "cancelled": self.cancel,
            "refunded": self.refund,
            "on_hold": self.hold,
            "disputed": self.dispute,
        }

        method = transition_methods.get(value)
        if method:
            method()

    @status.setter
    def status(self, value):
        """Set the order status directly during object initialization"""
        # Only allow direct assignment during object initialization
        if not self.pk:  # During object creation
            # Use __dict__ to bypass FSM protections during initialization
            self.__dict__["_status"] = value
        # For existing objects, only allow FSM transitions
        elif self._is_valid_status_transition(value):
            self._execute_status_transition(value)

    @property
    def payment_status(self):
        """Get the payment status"""
        return self._payment_status

    def _is_valid_payment_transition(self, value):
        """Check if the payment status transition is valid."""
        transitions = {
            "paid": ["unpaid"],
            "refunded": ["paid"],
            "partially_refunded": ["paid"],
            "disputed": ["paid", "partially_refunded"],
        }
        return self._payment_status in transitions.get(value, [])

    def _execute_payment_transition(self, value):
        """Execute the appropriate payment transition."""
        transition_methods = {
            "paid": self.pay,
            "refunded": self.refund_payment,
            "partially_refunded": self.partial_refund_payment,
            "disputed": self.dispute_payment,
        }
        method = transition_methods.get(value)
        if method:
            method()

    @payment_status.setter
    def payment_status(self, value):
        """Set the payment status directly during object initialization"""
        # Only allow direct assignment during object initialization
        if not self.pk:  # During object creation
            # Use __dict__ to bypass FSM protections during initialization
            self.__dict__["_payment_status"] = value
        # For existing objects, only allow FSM transitions
        elif self._is_valid_payment_transition(value):
            self._execute_payment_transition(value)

    @property
    def subtotal(self):
        """Get the subtotal"""
        return self._subtotal

    @subtotal.setter
    def subtotal(self, value):
        """Set the subtotal"""
        self._subtotal = value

    @property
    def tax(self):
        """Get the tax amount"""
        return self._tax

    @tax.setter
    def tax(self, value):
        """Set the tax amount"""
        self._tax = value

    @property
    def total(self):
        """Get the total amount"""
        return self._total

    @total.setter
    def total(self, value):
        """Set the total amount"""
        self._total = value

    def _calculate_totals(self):
        """Calculate order totals"""
        # Use prefetch_related when calling this method to avoid N+1 queries
        # Alternatively, use aggregation to calculate in the database
        from django.db.models import DecimalField, F, Sum

        # Calculate subtotal using database aggregation to avoid N+1 queries
        item_totals = self.items.aggregate(
            subtotal=Sum(F("quantity") * F("price"), output_field=DecimalField()),
        )
        subtotal = item_totals["subtotal"] or Decimal("0.00")

        self._subtotal = subtotal
        self._tax = subtotal * Decimal("0.15")  # 15% tax
        self._total = self._subtotal + self._tax

    # State transition matrix configuration
    _STATE_TRANSITIONS = {
        "draft": ["pending", "cancelled"],
        "pending": ["processing", "confirmed", "cancelled"],
        "confirmed": ["processing"],
        "processing": ["completed", "on_hold", "cancelled"],
        "on_hold": ["processing", "cancelled"],
        "completed": ["refunded", "disputed"],
        "cancelled": [],
        "refunded": ["disputed"],
        "disputed": [],
    }

    def can_transition_to(self, target_status):
        """Check if order can transition to target status using configuration-driven approach"""
        if target_status not in self._STATE_TRANSITIONS.get(self.status, []):
            return False

        # Get the appropriate transition method for this target
        transition_methods = {
            "pending": self.submit,
            "processing": self.process,
            "confirmed": self.confirm,
            "completed": self.complete,
            "cancelled": self.cancel,
            "refunded": self.refund,
            "on_hold": self.hold,
            "disputed": self.dispute,
        }

        method = transition_methods.get(target_status)
        if method:
            return can_proceed(method)

        return False

    @transition(field=_status, source="draft", target="pending")
    def submit(self):
        """Submit the order"""
        logger.info(f"Order {self.order_id} submitted")

    @transition(field=_status, source=["pending", "confirmed"], target="processing")
    def process(self):
        """Process the order"""
        logger.info(f"Order {self.order_id} processing")

    @transition(field=_status, source="pending", target="confirmed")
    def confirm(self):
        """Confirm the order (payment received, awaiting processing)"""
        logger.info(f"Order {self.order_id} confirmed")

    @transition(
        field=_status, source=["draft", "pending", "processing"], target="cancelled",
    )
    def cancel(self):
        """Cancel the order"""
        logger.info(f"Order {self.order_id} cancelled")

    @transition(field=_status, source=["completed"], target="refunded")
    def refund(self):
        """Refund the order"""
        logger.info(f"Order {self.order_id} refunded")

    @transition(field=_status, source=["processing"], target="on_hold")
    def hold(self):
        """Put order on hold"""
        logger.info(f"Order {self.order_id} on hold")

    @transition(field=_status, source=["completed", "refunded"], target="disputed")
    def dispute(self):
        """Dispute the order"""
        logger.info(f"Order {self.order_id} disputed")

    @transition(field=_payment_status, source="unpaid", target="paid")
    def pay(self):
        """Mark payment as paid"""
        logger.info(f"Order {self.order_id} payment marked as paid")

    @transition(field=_payment_status, source="paid", target="refunded")
    def refund_payment(self):
        """Refund the payment"""
        logger.info(f"Order {self.order_id} payment refunded")

    @transition(field=_payment_status, source="paid", target="partially_refunded")
    def partial_refund_payment(self):
        """Partially refund the payment"""
        logger.info(f"Order {self.order_id} payment partially refunded")

    @transition(
        field=_payment_status, source=["paid", "partially_refunded"], target="disputed",
    )
    def dispute_payment(self):
        """Dispute the payment"""
        logger.info(f"Order {self.order_id} payment disputed")

    def set_payment_paid(self):
        """Helper method to set payment status to paid"""
        if self._payment_status != "paid":
            self.pay()

    class Meta:
        indexes = [
            models.Index(fields=["user", "_status"]),  # for user+status queries
            models.Index(fields=["_status", "created"]),  # for status+date queries
            models.Index(
                fields=["_payment_status", "_status"],
            ),  # for payment+status queries
            models.Index(fields=["created"]),  # for date-based queries
        ]

    def save(self, *args, **kwargs):
        """Save the order and assign default permissions."""
        # Generate order_id if it's a new order
        if not self.order_id:
            self.order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"

        # Calculate totals before saving (only for updates, not create)
        if self.pk:
            self._calculate_totals()

        is_new = self.pk is None
        super().save(*args, **kwargs)

        # Assign default permissions for new orders
        if is_new and self.user:
            # Assign owner permissions
            assign_perm("orders.change_order", self.user, self)
            assign_perm("orders.view_order", self.user, self)


class OrderItem(BaseOrderItem):
    """Order item model"""

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    # unit_price is inherited from BaseOrderItem

    def __str__(self):
        return f"{self.service.name} (x{self.quantity})"


class StandardOrder(Order):
    """Standard order implementation"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    class Meta:
        proxy = True  # Using proxy model for polymorphism

    def calculate_delivery_time(self):
        """Calculate standard delivery time (5-7 business days)"""
        from datetime import datetime, timedelta

        return datetime.now() + timedelta(days=7)


class ExpressOrder(Order):
    """Express order with faster delivery"""

    express_fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("100.00"),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    class Meta:
        verbose_name = "Express Order"
        verbose_name_plural = "Express Orders"

    def calculate_delivery_time(self):
        """Calculate express delivery time (1-2 business days)"""
        from datetime import datetime, timedelta

        return datetime.now() + timedelta(days=2)

    def get_total(self):
        """Get total including express fee"""
        return self.total + self.express_fee


class ScheduledOrder(Order):
    """Scheduled order for future delivery"""

    scheduled_date = models.DateTimeField()
    reminder_sent = models.BooleanField(default=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    class Meta:
        verbose_name = "Scheduled Order"
        verbose_name_plural = "Scheduled Orders"

    def calculate_delivery_time(self):
        """Scheduled delivery time"""
        return self.scheduled_date

    def send_reminder(self):
        """Send reminder for scheduled order"""
        if not self.reminder_sent:
            # Implementation for sending reminder
            self.reminder_sent = True
            self.save()


class OrderFactory:
    """Factory for creating different types of orders"""

    @staticmethod
    def create_order(order_type, **kwargs):
        """Create an order of the specified type"""
        if order_type == OrderType.STANDARD:
            return StandardOrder(**kwargs)
        if order_type == OrderType.EXPRESS:
            return ExpressOrder(**kwargs)
        if order_type == OrderType.SCHEDULED:
            return ScheduledOrder(**kwargs)
        raise ValueError(f"Unknown order type: {order_type}")
