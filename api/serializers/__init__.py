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
# Import centralized validation functions
from utils.validation import (validate_phone, validate_positive_price,
                              validate_rating, validate_text_length)

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
    - password: Account password (minimum 12 characters, requires uppercase, lowercase, number, and special character)
    - password_confirm: Confirmation of the password
    - first_name: User's first name (optional)
    - last_name: User's last name (optional)
    """

    password = serializers.CharField(
        write_only=True,
        min_length=12,  # Increased minimum length for security
        help_text="Enter a strong password with at least 12 characters, including uppercase, lowercase, number, and special character",
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
        extra_kwargs = {
            "username": {
                "min_length": 3,
                "max_length": 150,
                "help_text": "Enter a username between 3 and 150 characters long",
            },
            "email": {
                "help_text": "Enter a valid email address",
            },
            "first_name": {
                "max_length": 150,
                "required": False,
                "help_text": "Enter your first name (optional)",
            },
            "last_name": {
                "max_length": 150,
                "required": False,
                "help_text": "Enter your last name (optional)",
            },
        }

    def validate_username(self, value):
        """Validate username format and length."""
        if not value or not value.strip():
            raise serializers.ValidationError("Username cannot be empty")

        # Ensure username contains only alphanumeric characters and underscores/hyphens
        import re

        if not re.match(r"^[a-zA-Z0-9_-]+$", value):
            raise serializers.ValidationError(
                "Username can only contain alphanumeric characters, hyphens, and underscores"
            )

        # Check if username already exists
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("Username already exists")

        return value

    def validate_email(self, value):
        """Validate email format and ensure it's unique."""
        if not value or not value.strip():
            raise serializers.ValidationError("Email cannot be empty")

        # Check if email already exists
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Email address already registered")

        return value

    def validate_password(self, value):
        """Validate password strength requirements."""
        from django.contrib.auth.password_validation import validate_password

        try:
            # Use Django's built-in password validators defined in settings
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(e.messages)

        # Additional custom validation
        if len(value) < 12:
            raise serializers.ValidationError(
                "Password must be at least 12 characters long for security"
            )

        # Check for common patterns that are easy to guess
        common_patterns = ["123456", "password", "qwerty", "abc123"]
        lower_value = value.lower()
        for pattern in common_patterns:
            if pattern in lower_value:
                raise serializers.ValidationError(
                    f"Password cannot contain common patterns like '{pattern}'"
                )

        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError("Passwords don't match")

        # Optional: Additional validation for first and last name
        if "first_name" in attrs and attrs["first_name"]:
            first_name = attrs["first_name"].strip()
            if len(first_name) < 1 or len(first_name) > 150:
                raise serializers.ValidationError(
                    {"first_name": "First name must be between 1 and 150 characters"}
                )

        if "last_name" in attrs and attrs["last_name"]:
            last_name = attrs["last_name"].strip()
            if len(last_name) < 1 or len(last_name) > 150:
                raise serializers.ValidationError(
                    {"last_name": "Last name must be between 1 and 150 characters"}
                )

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
    - slug: URL-friendly version of the service name (read-only)
    - name: Display name of the service
    - category: Associated service category with detailed information
    - short_desc: Brief description of the service
    - description: Detailed information about the service
    - price: Cost of the service
    - image: Service image (optional)
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
            "image",
            "image_url",
            "avg_rating",
            "review_count",
            "is_active",
        )
        read_only_fields = ("slug", "avg_rating", "review_count", "image_url")

    def validate_name(self, value):
        """Validate service name."""
        if not value or not value.strip():
            raise serializers.ValidationError("Service name cannot be empty")

        # Use centralized validation function for text length
        try:
            validated_value = validate_text_length(
                value.strip(), min_length=3, max_length=100, field_name="Service name"
            )
        except ValidationError as e:
            raise serializers.ValidationError(str(e))

        # Check for potentially harmful characters
        import re

        if re.search(r"[<>{}[\]`]", value):
            raise serializers.ValidationError(
                "Service name contains invalid characters"
            )

        return validated_value

    def validate_short_desc(self, value):
        """Validate short description."""
        if not value or not value.strip():
            raise serializers.ValidationError("Short description cannot be empty")

        # Use centralized validation function for text length
        try:
            validated_value = validate_text_length(
                value.strip(),
                min_length=10,
                max_length=300,
                field_name="Short description",
            )
        except ValidationError as e:
            raise serializers.ValidationError(str(e))

        return validated_value

    def validate_description(self, value):
        """Validate full description."""
        if not value or not value.strip():
            raise serializers.ValidationError("Description cannot be empty")

        # Use centralized validation function for text length
        try:
            validated_value = validate_text_length(
                value.strip(), min_length=20, max_length=2000, field_name="Description"
            )
        except ValidationError as e:
            raise serializers.ValidationError(str(e))

        return validated_value

    def validate_price(self, value):
        """Validate price."""
        if value is None:
            raise serializers.ValidationError("Price is required")

        # Use centralized validation function for positive price
        try:
            validate_positive_price(value)
        except ValidationError as e:
            raise serializers.ValidationError(str(e))

        if value > 1000000:  # Maximum price validation
            raise serializers.ValidationError("Price is too high")

        return value

    def validate_image(self, value):
        """Validate image file."""
        if value:
            # Check file size (max 5MB)
            max_size = 5 * 1024 * 1024
            if value.size > max_size:
                raise serializers.ValidationError("Image size cannot exceed 5MB")

            # Check file format
            import os

            ext = os.path.splitext(value.name)[1].lower()
            valid_extensions = [".jpg", ".jpeg", ".png", ".webp"]
            if ext not in valid_extensions:
                raise serializers.ValidationError(
                    "Only JPG, JPEG, PNG, and WEBP images are allowed"
                )

        return value

    @extend_schema_field(OpenApiTypes.FLOAT)
    def get_avg_rating(self, obj):
        """Get the average rating for the service from cached value."""
        # Use the cached value that's always up-to-date via model signals
        return float(obj.cached_avg_rating)

    @extend_schema_field(OpenApiTypes.INT)
    def get_review_count(self, obj):
        """Get the number of reviews for the service from cached value."""
        # Use the cached value that's always up-to-date via model signals
        return obj.cached_rating_count


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

    def validate_rating(self, value):
        """Validate rating value."""
        if value is None:
            raise serializers.ValidationError("Rating is required")

        # Use centralized validation function
        try:
            validated_value = validate_rating(value)
        except ValidationError as e:
            raise serializers.ValidationError(str(e))

        return validated_value

    def validate_text(self, value):
        """Validate review text."""
        if not value or not value.strip():
            raise serializers.ValidationError("Review text cannot be empty")

        # Use centralized validation function for text length
        try:
            validated_value = validate_text_length(
                value.strip(), min_length=10, max_length=1000, field_name="Review text"
            )
        except ValidationError as e:
            raise serializers.ValidationError(str(e))

        # Check for potentially harmful content (basic check)
        import re

        harmful_patterns = [r"<script", r"javascript:", r"vbscript:", r"on\w+\s*="]
        for pattern in harmful_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                raise serializers.ValidationError(
                    "Review text contains invalid content"
                )

        return validated_value


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
    address = serializers.CharField(
        help_text="Complete shipping address for the order",
        min_length=10,
        max_length=500,
    )
    phone = serializers.CharField(
        max_length=20,
        help_text="Contact phone number for delivery and order updates",
    )
    payment_method = serializers.CharField(
        default="sslcommerz",
        help_text="Payment gateway to use for processing the transaction",
    )

    def validate_name(self, value):
        """Validate customer name."""
        if not value or not value.strip():
            raise serializers.ValidationError("Name is required")

        if len(value.strip()) < 2:
            raise serializers.ValidationError("Name must be at least 2 characters long")

        # Remove extra whitespace
        return " ".join(value.split())

    def validate_address(self, value):
        """Validate address format."""
        if not value or not value.strip():
            raise serializers.ValidationError("Address is required")

        if len(value.strip()) < 10:
            raise serializers.ValidationError(
                "Address must be at least 10 characters long"
            )

        return value.strip()

    def validate_phone(self, value):
        """Validate phone number format."""
        if not value or not value.strip():
            raise serializers.ValidationError("Phone number is required")

        # Use centralized validation function
        try:
            validated_value = validate_phone(value.strip())
        except ValidationError as e:
            raise serializers.ValidationError(str(e))

        # Remove common formatting characters for consistent storage
        import re

        phone_clean = re.sub(r"[\s\-\(\)\+]", "", validated_value)

        # Check if it's a valid phone number (Bangladesh format or international)
        if not re.match(r"^[0-9]{10,15}$", phone_clean):
            raise serializers.ValidationError(
                "Phone number must contain 10-15 digits without special characters"
            )

        return phone_clean

    def validate_payment_method(self, value):
        """Validate payment method."""
        allowed_methods = ["sslcommerz", "cash_on_delivery", "bkash", "nagad"]
        if value not in allowed_methods:
            raise serializers.ValidationError(
                f"Payment method must be one of: {', '.join(allowed_methods)}"
            )

        return value


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

    def validate_service_id(self, value):
        try:
            service = Service.objects.get(id=value)
            if not service.is_active:
                raise serializers.ValidationError("Service is not active")
        except Service.DoesNotExist:
            raise serializers.ValidationError("Service not found")
        return value

    def validate_qty(self, value):
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than 0")
        return value


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
            service = Service.objects.get(id=value)
            if not service.is_active:
                raise serializers.ValidationError("Service is not active")
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
