import logging

from django.db import models
from model_utils.managers import QueryManager

from homeser.base_models import BaseModel
from orders.models import Order

# Set up logging
logger = logging.getLogger(__name__)


class Payment(BaseModel):
    """Payment transaction records with enhanced logging"""

    PAYMENT_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
        ("refunded", "Refunded"),
        ("disputed", "Disputed"),
    ]

    order = models.OneToOneField(
        Order, on_delete=models.CASCADE, related_name="payment",
    )
    transaction_id = models.CharField(max_length=100, unique=True, db_index=True)
    session_key = models.CharField(max_length=200, blank=True)
    gateway_response = models.JSONField(default=dict, blank=True)
    validation_response = models.JSONField(default=dict, blank=True)

    amount = models.DecimalField(max_digits=10, decimal_places=2, db_index=True)
    currency = models.CharField(max_length=3, default="BDT")
    _status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default="pending",
        db_column="status",
        db_index=True,
    )

    # SSLCOMMERZ specific fields
    val_id = models.CharField(max_length=100, blank=True)
    bank_tran_id = models.CharField(max_length=100, blank=True)
    card_type = models.CharField(max_length=50, blank=True)
    card_no = models.CharField(max_length=20, blank=True)

    objects = QueryManager()

    def __str__(self):
        return f"Payment {self.transaction_id} - {self.order.order_id}"

    @property
    def status(self):
        """Get the payment status"""
        return self._status

    @status.setter
    def status(self, value):
        """Set the payment status with validation"""
        if value not in dict(self.PAYMENT_STATUS_CHOICES):
            raise ValueError(f"Invalid status: {value}")

        # Log status changes
        if self.pk and self._status != value:
            logger.info(
                f"Payment {self.transaction_id} status changed from {self._status} to {value}",
            )
        elif not self.pk:
            logger.info(f"New payment created: {self.transaction_id}")

        self._status = value

    class Meta:
        indexes = [
            models.Index(fields=["_status"]),  # for status-based queries
            models.Index(fields=["created"]),  # for date-based queries
            models.Index(fields=["_status", "created"]),  # for status+date queries
        ]

    def save(self, *args, **kwargs):
        """Override save to log status changes"""
        # Validate status before saving
        if self._status not in dict(self.PAYMENT_STATUS_CHOICES):
            raise ValueError(f"Invalid status: {self._status}")

        if self.pk:  # Only for existing objects
            old_instance = Payment.objects.get(pk=self.pk)
            if old_instance._status != self._status:
                logger.info(
                    f"Payment {self.transaction_id} status changed from {old_instance._status} to {self._status}",
                )
        else:
            logger.info(f"New payment created: {self.transaction_id}")

        super().save(*args, **kwargs)

    def process_payment(self):
        """Process payment using SSLCommerz"""
        from api.sslcommerz import SSLCommerzService

        sslcommerz = SSLCommerzService()
        return sslcommerz.create_session(
            self.order,
            {
                "name": self.order.customer_name,
                "address": self.order.customer_address,
                "phone": self.order.customer_phone,
            },
        )

    def validate_payment(self, val_id, tran_id):
        """Validate payment using SSLCommerz"""
        from api.sslcommerz import SSLCommerzService

        sslcommerz = SSLCommerzService()
        return sslcommerz.validate_payment(val_id, tran_id)

    def refund_payment(self, amount=None):
        """Refund payment using SSLCommerz"""
        from api.sslcommerz import SSLCommerzService

        sslcommerz = SSLCommerzService()
        refund_amount = amount if amount else self.amount
        return sslcommerz.refund_payment(self.transaction_id, refund_amount)


class PaymentLog(models.Model):
    """Log all payment-related activities with enhanced data"""

    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name="logs")
    action = models.CharField(
        max_length=50,
    )  # 'session_created', 'ipn_received', 'validated', etc.
    data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.payment.transaction_id} - {self.action}"

    def save(self, *args, **kwargs):
        """Override save to log payment activities"""
        logger.info(
            f"Payment log created: {self.payment.transaction_id} - {self.action}",
        )
        super().save(*args, **kwargs)
