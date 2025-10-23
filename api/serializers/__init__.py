"""Consolidated serializers package for the HomeSer backend.
This package brings together common serializer functionality in one place for better organization and reuse.
"""

# Import all necessary serializer classes and utilities
# Import Django utilities
from django.contrib.auth import authenticate, get_user_model
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import OpenApiTypes, extend_schema_field
from rest_framework import serializers
from rest_framework.fields import (BooleanField, CharField, ChoiceField,
                                   DateTimeField, DecimalField, EmailField,
                                   FileField, ImageField, IntegerField,
                                   SlugField, URLField)
from rest_framework.validators import UniqueTogetherValidator, UniqueValidator

# Import model classes
from accounts.models import UserProfile
from orders.models import Order, OrderItem
from services.models import Review, Service, ServiceCategory

# Get user model
User = get_user_model()


# Base serializer classes for common functionality
class BaseSerializer(serializers.ModelSerializer):
    """Abstract base serializer with common functionality."""

    def get_calculated_field(self, obj, field_name, fallback_field=None, default=None):
        """Generic method to get calculated fields with fallback logic.

        Args:
            obj: The model instance
            field_name (str): Name of the field to retrieve
            fallback_field (str): Fallback field name if primary field is not found
            default: Default value if field is not found

        Returns:
            Field value or default

        """
        # First, try to get from precomputed rating aggregation
        if hasattr(obj, "rating_aggregation") and obj.rating_aggregation:
            if hasattr(obj.rating_aggregation, field_name):
                return getattr(obj.rating_aggregation, field_name)

        # Then try annotated values from queryset
        annotated_field = f"{field_name}_val"
        if hasattr(obj, annotated_field):
            return getattr(obj, annotated_field)

        # Try fallback field if specified
        if fallback_field and hasattr(obj, fallback_field):
            return getattr(obj, fallback_field)

        # Fallback: If the field was not pre-calculated, calculate it directly from the model's property
        if hasattr(obj, field_name):
            return getattr(obj, field_name)

        return default


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration with password confirmation.

    Fields:
    - username: Unique identifier for the user account
    - email: Email address for account verification and communication
    - password: Account password (minimum 8 characters, requires uppercase, lowercase, number, and special character)
    - password_confirm: Confirmation of the password
    - first_name: User's first name (optional)
    - last_name: User's last name (optional)
    """

    password = serializers.CharField(
        write_only=True,
        min_length=8,
        help_text="Enter a strong password with at least 8 characters, including uppercase, lowercase, number, and special character",
    )
    password_confirm = serializers.CharField(
        write_only=True,
        help_text="Confirm your password by entering it again",
    )

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "password",
            "password_confirm",
            "first_name",
            "last_name",
        )

    def validate_password(self, value):
        """Validate password strength requirements."""
        if len(value) < 8:
            raise serializers.ValidationError(
                "Password must be at least 8 characters long"
            )

        # Check for uppercase letter
        if not any(char.isupper() for char in value):
            raise serializers.ValidationError(
                "Password must contain at least one uppercase letter"
            )

        # Check for lowercase letter
        if not any(char.islower() for char in value):
            raise serializers.ValidationError(
                "Password must contain at least one lowercase letter"
            )

        # Check for digit
        if not any(char.isdigit() for char in value):
            raise serializers.ValidationError(
                "Password must contain at least one digit"
            )

        # Check for special character
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        if not any(char in special_chars for char in value):
            raise serializers.ValidationError(
                "Password must contain at least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?)"
            )

        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError("Passwords don't match")
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        user = User.objects.create_user(**validated_data)
        # Create user profile
        UserProfile.objects.create(user=user)
        return user


class UserLoginSerializer(serializers.Serializer):
    """Serializer for user login.

    Fields:
    - username: User's username or email address
    - password: User's account password
    """

    username = serializers.CharField(help_text="Enter your username or email address")
    password = serializers.CharField(help_text="Enter your account password")

    def validate(self, attrs):
        username = attrs.get("username")
        password = attrs.get("password")

        if username and password:
            # Attempt authentication first with the provided username.
            # If that fails, try to find a user by email and then authenticate with their actual username.
            # This allows users to log in using either their username or email address.
            user = authenticate(username=username, password=password)
            if not user:
                # Try with email
                try:
                    user_obj = User.objects.get(email=username)
                    user = authenticate(username=user_obj.username, password=password)
                except User.DoesNotExist:
                    pass

            if not user:
                raise serializers.ValidationError("Invalid credentials")

            if not user.is_active:
                raise serializers.ValidationError("User account is disabled")

            attrs["user"] = user
            return attrs
        raise serializers.ValidationError("Must include username and password")


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user details.

    Fields:
    - id: Unique identifier for the user (read-only)
    - username: Unique identifier for the user account
    - email: Email address associated with the account
    - first_name: User's first name
    - last_name: User's last name
    - is_staff: Whether the user has staff permissions (read-only)
    - roles: List of roles assigned to the user (read-only)
    """

    roles = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "is_staff",
            "roles",
        )
        read_only_fields = ("id", "is_staff", "roles")

    def get_roles(self, obj):
        return [group.name for group in obj.groups.all()]


class UserProfileSerializer(BaseSerializer):
    """Serializer for user profiles with profile picture URL."""

    user = UserSerializer(read_only=True)
    profile_pic_url = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = (
            "user",
            "bio",
            "profile_pic",
            "profile_pic_url",
            "social_links",
            "phone",
            "address",
        )

    @extend_schema_field(OpenApiTypes.URI)
    def get_profile_pic_url(self, obj):
        if obj.profile_pic:
            return obj.profile_pic.url
        return None


class ServiceCategorySerializer(BaseSerializer):
    """Serializer for service categories.

    Fields:
    - id: Unique identifier for the category (read-only)
    - name: Display name of the service category
    - slug: URL-friendly version of the name
    - description: Detailed information about the category
    """

    class Meta:
        model = ServiceCategory
        fields = ("id", "name", "slug", "description")


class ServiceSerializer(BaseSerializer):
    """Serializer for services with rating information.

    Fields:
    - id: Unique identifier for the service (read-only)
    - slug: URL-friendly version of the service name
    - name: Display name of the service
    - category: Associated service category with detailed information
    - short_desc: Brief description of the service
    - description: Detailed information about the service
    - price: Cost of the service
    - image_url: URL to the service image (read-only)
    - avg_rating: Average rating based on user reviews (read-only)
    - review_count: Number of reviews for this service (read-only)
    - is_active: Whether the service is currently available
    """

    category = ServiceCategorySerializer(
        read_only=True,
        help_text="Category details for this service",
    )
    avg_rating = serializers.SerializerMethodField(
        help_text="Average rating calculated from all reviews",
    )
    review_count = serializers.SerializerMethodField(
        help_text="Total number of reviews for this service",
    )
    image_url = serializers.ReadOnlyField(help_text="URL to the service image")

    class Meta:
        model = Service
        fields = (
            "id",
            "slug",
            "name",
            "category",
            "short_desc",
            "description",
            "price",
            "image_url",
            "avg_rating",
            "review_count",
            "is_active",
        )

    @extend_schema_field(OpenApiTypes.FLOAT)
    def get_avg_rating(self, obj):
        """Get the average rating for the service."""
        # First, try to get from precomputed rating aggregation
        if hasattr(obj, "rating_aggregation") and obj.rating_aggregation:
            return (
                round(obj.rating_aggregation.average, 1)
                if obj.rating_aggregation.average
                else 0
            )
        # Then try annotated values from queryset
        if hasattr(obj, "avg_rating_val"):
            return round(obj.avg_rating_val, 1) if obj.avg_rating_val else 0
        # Fallback: If the average rating was not pre-calculated (e.g., when fetching a single service),
        # calculate it directly from the model's property. This is less efficient for lists.
        return obj.avg_rating

    @extend_schema_field(OpenApiTypes.INT)
    def get_review_count(self, obj):
        """Get the number of reviews for the service."""
        # First, try to get from precomputed rating aggregation
        if hasattr(obj, "rating_aggregation") and obj.rating_aggregation:
            return obj.rating_aggregation.count
        # Then try annotated values from queryset
        if hasattr(obj, "review_count_val"):
            return obj.review_count_val
        # Fallback: If the review count was not pre-calculated, calculate it directly from the model's property.
        return obj.review_count


class ReviewSerializer(BaseSerializer):
    """Serializer for reviews with user and service information.

    Fields:
    - id: Unique identifier for the review (read-only)
    - service: ID of the service being reviewed
    - user: ID of the user who wrote the review
    - user_name: Full name of the reviewer (read-only)
    - service_name: Name of the reviewed service (read-only)
    - rating: Rating given to the service (1-5 stars)
    - text: Detailed review text
    - sentiment_polarity: Automated sentiment analysis (read-only)
    - sentiment_subjectivity: Automated subjectivity analysis (read-only)
    - sentiment_label: Positive/Negative/Neutral label (read-only)
    - is_flagged: Whether the review has been flagged for review (read-only)
    - flagged_reason: Reason for flagging (read-only)
    - created_at: Date when the review was created (read-only)
    - created_at_formatted: Formatted creation date (read-only)
    - updated_at: Date when the review was last updated (read-only)
    """

    user_name = serializers.CharField(
        source="user.get_full_name",
        read_only=True,
        help_text="Full name of the user who submitted the review",
    )
    service_name = serializers.CharField(
        source="service.name",
        read_only=True,
        help_text="Name of the service being reviewed",
    )
    created_at_formatted = serializers.DateTimeField(
        source="created",
        read_only=True,
        format="%B %d, %Y",
        help_text="Formatted creation date",
    )

    class Meta:
        model = Review
        fields = [
            "id",
            "service",
            "user",
            "user_name",
            "service_name",
            "rating",
            "text",
            "sentiment_polarity",
            "sentiment_subjectivity",
            "sentiment_label",
            "is_flagged",
            "flagged_reason",
            "created",
            "created_at_formatted",
            "modified",
        ]
        read_only_fields = [
            "service",
            "user",
            "sentiment_polarity",
            "sentiment_subjectivity",
            "sentiment_label",
            "is_flagged",
            "flagged_reason",
            "created",
            "modified",
        ]


class OrderItemSerializer(serializers.ModelSerializer):
    """Serializer for order items with service information."""

    service = ServiceSerializer(read_only=True)
    total_price = serializers.SerializerMethodField(
        help_text="The total price for this order item (quantity * unit_price)"
    )

    class Meta:
        model = OrderItem
        fields = "__all__"
        read_only_fields = ("total_price",)

    @extend_schema_field(OpenApiTypes.NUMBER)
    def get_total_price(self, obj):
        """Method to access the total_price property from the model"""
        return obj.total_price


class OrderSerializer(serializers.ModelSerializer):
    """Serializer for orders with items and status information.

    Fields:
    - id: Unique identifier for the order (read-only)
    - order_id: Human-readable order identifier (read-only)
    - status: Current status of the order (e.g., pending, confirmed, completed)
    - payment_status: Status of payment processing (e.g., pending, completed, failed)
    - customer_name: Name of the customer who placed the order
    - customer_address: Shipping address for the order
    - customer_phone: Contact phone number for the order
    - subtotal: Total cost of items before tax
    - tax: Tax amount calculated for the order
    - total: Final total including items, tax, and any additional fees
    - items: List of order items with service details
    - created: Date and time when the order was created (read-only)
    """

    items = OrderItemSerializer(
        many=True,
        read_only=True,
        help_text="List of items in this order with detailed information",
    )
    order_id = serializers.ReadOnlyField(
        help_text="Unique identifier for the order that can be used for tracking",
    )

    # Add explicit field definitions with type hints for schema generation
    status = serializers.CharField(
        read_only=True,
        help_text="Current status of the order (e.g., pending, confirmed, completed)",
    )
    payment_status = serializers.CharField(
        read_only=True,
        help_text="Status of payment processing (e.g., pending, completed, failed)",
    )
    subtotal = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True,
        help_text="Total cost of items before tax",
    )
    tax = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True,
        help_text="Tax amount calculated for the order",
    )
    total = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True,
        help_text="Final total including items, tax, and any additional fees",
    )

    class Meta:
        model = Order
        fields = (
            "id",
            "order_id",
            "status",
            "payment_status",
            "customer_name",
            "customer_address",
            "customer_phone",
            "subtotal",
            "tax",
            "total",
            "items",
            "created",
        )
        read_only_fields = ("subtotal", "tax", "total", "created")


class EmailAnalyticsSerializer(serializers.Serializer):
    """Serializer for email analytics response"""

    success = serializers.BooleanField()
    data = serializers.DictField()
    message = serializers.CharField()


class SentimentAnalyticsSerializer(serializers.Serializer):
    """Serializer for sentiment analytics response"""

    success = serializers.BooleanField()
    data = serializers.DictField()
    message = serializers.CharField()


class CheckoutSerializer(serializers.Serializer):
    """Serializer for checkout information.

    Fields:
    - name: Full name of the person placing the order
    - address: Complete shipping address for the order
    - phone: Contact phone number for delivery and order updates
    - payment_method: Payment gateway to use (default: sslcommerz)
    """

    name = serializers.CharField(
        max_length=100,
        help_text="Full name of the person placing the order",
    )
    address = serializers.CharField(help_text="Complete shipping address for the order")
    phone = serializers.CharField(
        max_length=20,
        help_text="Contact phone number for delivery and order updates",
    )
    payment_method = serializers.CharField(
        default="sslcommerz",
        help_text="Payment gateway to use for processing the transaction",
    )


class CartAddSerializer(serializers.Serializer):
    """Serializer for adding items to cart.

    Fields:
    - service_id: Unique identifier of the service to add to cart
    - qty: Quantity of the service to add (minimum 1, default 1)
    """

    service_id = serializers.IntegerField(
        help_text="Unique identifier of the service to add to cart",
    )
    qty = serializers.IntegerField(
        min_value=1,
        default=1,
        help_text="Quantity of the service to add (minimum 1, default 1)",
    )


class CartRemoveSerializer(serializers.Serializer):
    """Serializer for removing items from cart.

    Fields:
    - service_id: Unique identifier of the service to remove from cart
    """

    service_id = serializers.IntegerField(
        help_text="Unique identifier of the service to remove from cart",
    )

    def validate_service_id(self, value):
        try:
            Service.objects.get(id=value)
        except Service.DoesNotExist:
            raise serializers.ValidationError("Service not found")
        return value


class AdminPromoteSerializer(serializers.Serializer):
    """Serializer for promoting users to admin.

    Fields:
    - user_id: Unique identifier of the user to promote to admin status
    """

    user_id = serializers.IntegerField(
        help_text="Unique identifier of the user to promote to admin status",
    )

    def validate_user_id(self, value):
        try:
            User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found")
        return value


# Polymorphic serializers for different service types
class PolymorphicServiceSerializer(BaseSerializer):
    """Polymorphic serializer that adapts based on the service type."""

    def to_representation(self, instance):
        """Return the appropriate serializer based on the service type.

        Args:
            instance: The service instance

        Returns:
            Serialized representation

        """
        if hasattr(instance, "service_type"):
            if instance.service_type == "premium":
                return PremiumServiceSerializer(instance, context=self.context).data
            if instance.service_type == "specialized":
                return SpecializedServiceSerializer(instance, context=self.context).data

        # Default to standard service serializer
        return ServiceSerializer(instance, context=self.context).data


class PremiumServiceSerializer(ServiceSerializer):
    """Serializer for premium services with additional fields."""

    class Meta(ServiceSerializer.Meta):
        fields = ServiceSerializer.Meta.fields + (
            "premium_features",
            "discount_percentage",
        )


class SpecializedServiceSerializer(ServiceSerializer):
    """Serializer for specialized services with additional fields."""

    class Meta(ServiceSerializer.Meta):
        fields = ServiceSerializer.Meta.fields + (
            "customization_options",
            "min_price",
        )


# Serializer factory for creating different types of serializers
class SerializerFactory:
    """Factory for creating different types of serializers."""

    SERIALIZER_MAP = {
        "service": ServiceSerializer,
        "premium_service": PremiumServiceSerializer,
        "specialized_service": SpecializedServiceSerializer,
        "user": UserSerializer,
        "user_profile": UserProfileSerializer,
        "review": ReviewSerializer,
        "order": OrderSerializer,
        "order_item": OrderItemSerializer,
    }

    @staticmethod
    def create_serializer(serializer_type, **kwargs):
        """Create a serializer of the specified type.

        Args:
            serializer_type (str): Type of serializer to create
            **kwargs: Additional arguments for the serializer

        Returns:
            Serializer instance

        """
        serializer_class = SerializerFactory.SERIALIZER_MAP.get(serializer_type)
        if not serializer_class:
            raise ValueError(f"Unknown serializer type: {serializer_type}")
        return serializer_class(**kwargs)

    @staticmethod
    def register_serializer(serializer_type, serializer_class):
        """Register a new serializer type.

        Args:
            serializer_type (str): Type identifier for the serializer
            serializer_class: The serializer class to register

        """
        SerializerFactory.SERIALIZER_MAP[serializer_type] = serializer_class


# Export all classes and utilities for convenience
__all__ = [
    # Base serializer classes
    "BaseSerializer",
    "UserRegistrationSerializer",
    "UserLoginSerializer",
    "UserSerializer",
    "UserProfileSerializer",
    "ServiceCategorySerializer",
    "ServiceSerializer",
    "ReviewSerializer",
    "OrderItemSerializer",
    "OrderSerializer",
    "CheckoutSerializer",
    "CartAddSerializer",
    "CartRemoveSerializer",
    "AdminPromoteSerializer",
    # Polymorphic serializers
    "PolymorphicServiceSerializer",
    "PremiumServiceSerializer",
    "SpecializedServiceSerializer",
    # Serializer factory
    "SerializerFactory",
    # DRF serializer classes
    "serializers",
    "CharField",
    "IntegerField",
    "DecimalField",
    "DateTimeField",
    "BooleanField",
    "EmailField",
    "URLField",
    "ChoiceField",
    "SlugField",
    "FileField",
    "ImageField",
    # DRF validators
    "UniqueValidator",
    "UniqueTogetherValidator",
    # DRF Spectacular utilities
    "extend_schema_field",
    "OpenApiTypes",
    # Django utilities
    "get_user_model",
    "ValidationError",
    "_",
    # Model classes
    "User",
    "UserProfile",
    "Service",
    "ServiceCategory",
    "Review",
    "Order",
    "OrderItem",
]
