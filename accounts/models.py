from decimal import Decimal

from cloudinary.models import CloudinaryField
from django.contrib.auth.models import AbstractUser, UserManager
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from model_utils.managers import QueryManager

from homeser.base_models import BaseModel


class CustomUserManager(QueryManager, UserManager):
    """Custom user manager that combines caching and user management"""


class User(AbstractUser):
    """Extended User model with additional fields"""

    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "first_name", "last_name"]

    def get_customer_profile(self):
        """Get the customer profile for this user.
        This method checks all customer types and returns the appropriate one.
        """
        for customer_model in [
            IndividualCustomer,
            BusinessCustomer,
            GovernmentCustomer,
        ]:
            try:
                return getattr(self, customer_model.__name__.lower())
            except customer_model.DoesNotExist:
                continue
        return None


class CustomerType(models.TextChoices):
    INDIVIDUAL = "individual", "Individual Customer"
    BUSINESS = "business", "Business Customer"
    GOVERNMENT = "government", "Government Customer"


class BaseCustomer(models.Model):
    """Abstract base model for all customer types with common fields and functionality.
    Implements the polymorphic pattern through inheritance.
    """

    customer_type = models.CharField(max_length=20, choices=CustomerType.choices)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    email = models.EmailField(unique=True, db_index=True)

    objects = QueryManager()

    class Meta:
        abstract = True

    def get_discount_rate(self):
        """Calculate discount rate based on customer type.
        This is an abstract method to be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement get_discount_rate method")

    def get_service_fee_multiplier(self):
        """Calculate service fee multiplier based on customer type.
        This is an abstract method to be implemented by subclasses.
        """
        return Decimal("1.0")  # Default multiplier

    def __str__(self):
        return f"{self.get_customer_type_display()} - {self.email}"


class IndividualCustomer(BaseCustomer):
    """Individual customer implementation with personal details."""

    first_name = models.CharField(max_length=50, db_index=True)
    last_name = models.CharField(max_length=50)
    phone = models.CharField(max_length=20, blank=True, db_index=True)

    class Meta:
        verbose_name = "Individual Customer"
        verbose_name_plural = "Individual Customers"

    def get_discount_rate(self):
        """Individual customers receive no special discount by default."""
        return Decimal("0.0")

    def get_service_fee_multiplier(self):
        """Individual customers pay standard service fees."""
        return Decimal("1.0")

    def save(self, *args, **kwargs):
        self.customer_type = CustomerType.INDIVIDUAL
        super().save(*args, **kwargs)


class BusinessCustomer(BaseCustomer):
    """Business customer implementation with business-specific details."""

    BUSINESS_SIZE_CHOICES = [
        ("small", "Small"),
        ("medium", "Medium"),
        ("large", "Large"),
    ]

    business_name = models.CharField(max_length=100, db_index=True)
    tax_id = models.CharField(max_length=50, unique=True, db_index=True)
    business_size = models.CharField(max_length=20, choices=BUSINESS_SIZE_CHOICES)
    employee_count = models.PositiveIntegerField(default=1)
    annual_revenue = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Business Customer"
        verbose_name_plural = "Business Customers"

    def get_discount_rate(self):
        """Calculate discount rate based on business size."""
        discount_mapping = {
            "small": Decimal("0.05"),
            "medium": Decimal("0.10"),
            "large": Decimal("0.15"),
        }
        return discount_mapping.get(self.business_size, Decimal("0.0"))

    def get_service_fee_multiplier(self):
        """Business customers may get reduced service fees based on size."""
        multiplier_mapping = {
            "small": Decimal("0.95"),
            "medium": Decimal("0.90"),
            "large": Decimal("0.85"),
        }
        return multiplier_mapping.get(self.business_size, Decimal("1.0"))

    def save(self, *args, **kwargs):
        self.customer_type = CustomerType.BUSINESS
        super().save(*args, **kwargs)


class GovernmentCustomer(BaseCustomer):
    """Government customer implementation with government-specific details."""

    government_entity_name = models.CharField(max_length=150, db_index=True)
    government_id = models.CharField(max_length=50, unique=True, db_index=True)
    department = models.CharField(max_length=100)
    contact_person = models.CharField(max_length=100)
    entity_type = models.CharField(
        max_length=50,
        choices=[
            ("federal", "Federal"),
            ("state", "State"),
            ("local", "Local"),
            ("other", "Other"),
        ],
    )

    class Meta:
        verbose_name = "Government Customer"
        verbose_name_plural = "Government Customers"

    def get_discount_rate(self):
        """Government customers receive a standard discount."""
        return Decimal("0.10")

    def get_service_fee_multiplier(self):
        """Government customers typically get reduced service fees."""
        return Decimal("0.80")

    def save(self, *args, **kwargs):
        self.customer_type = CustomerType.GOVERNMENT
        super().save(*args, **kwargs)


class CustomerProfileManager(QueryManager):
    """Custom manager for customer profiles that provides common functionality
    and makes it easy to get the concrete customer type.
    """

    def get_queryset(self):
        return super().get_queryset()

    def individual_customers(self):
        """Get all individual customers"""
        return self.filter(customer_type=CustomerType.INDIVIDUAL)

    def business_customers(self):
        """Get all business customers"""
        return self.filter(customer_type=CustomerType.BUSINESS)

    def government_customers(self):
        """Get all government customers"""
        return self.filter(customer_type=CustomerType.GOVERNMENT)

    def get_by_user(self, user):
        """Get customer profile by user"""
        for customer_model in [
            IndividualCustomer,
            BusinessCustomer,
            GovernmentCustomer,
        ]:
            try:
                return getattr(user, customer_model.__name__.lower())
            except customer_model.DoesNotExist:
                continue
        return None


class CustomerBillingAddress(BaseModel):
    """Billing address for customer profiles.
    Can be associated with any customer type.
    """

    # Generic foreign key to any customer type
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    customer = GenericForeignKey("content_type", "object_id")

    address_line_1 = models.CharField(max_length=255)
    address_line_2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100)
    is_default = models.BooleanField(default=False)

    objects = QueryManager()

    class Meta:
        verbose_name = "Customer Billing Address"
        verbose_name_plural = "Customer Billing Addresses"

    def __str__(self):
        return (
            f"{self.address_line_1}, {self.city}, {self.state} - {self.customer.email}"
        )

    def save(self, *args, **kwargs):
        """Override save to ensure only one default address per customer."""
        if self.is_default:
            # Set all other addresses for this customer as non-default
            CustomerBillingAddress.objects.filter(
                content_type=self.content_type,
                object_id=self.object_id,
                is_default=True,
            ).update(is_default=False)
        super().save(*args, **kwargs)


class CustomerServiceHistory(BaseModel):
    """Service history for customer profiles.
    Tracks all services purchased by customers.
    """

    # Generic foreign key to any customer type
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    customer = GenericForeignKey("content_type", "object_id")

    service = models.CharField(
        max_length=200,
        db_index=True,
    )  # Could be a relation to Service model
    service_cost = models.DecimalField(max_digits=10, decimal_places=2)
    discount_applied = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    final_cost = models.DecimalField(max_digits=10, decimal_places=2)

    objects = QueryManager()

    class Meta:
        verbose_name = "Customer Service History"
        verbose_name_plural = "Customer Service Histories"
        ordering = ["-created"]
        indexes = [
            models.Index(
                fields=["content_type", "object_id"],
            ),  # for generic foreign key queries
            models.Index(
                fields=["created", "content_type", "object_id"],
            ),  # for common date/customer queries
        ]

    def __str__(self):
        return f"{self.service} - {self.created.date()} - {self.customer.email if hasattr(self.customer, 'email') else 'Unknown Customer'}"


class UserProfile(BaseModel):
    """User profile with additional information"""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    bio = models.TextField(max_length=500, blank=True)
    profile_pic = CloudinaryField("image", blank=True, null=True)
    social_links = models.JSONField(default=dict, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)

    objects = QueryManager()

    def __str__(self):
        return f"{self.user.get_full_name()}'s Profile"

    def save(self, *args, **kwargs):
        """Save the profile."""
        super().save(*args, **kwargs)
