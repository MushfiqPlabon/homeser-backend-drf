"""Consolidated validation package for the HomeSer backend.
This package brings together all validation logic in one place for better organization and reuse.
"""

# Import all validation utilities
from utils.validation_utils import (validate_email_format, validate_name,
                                    validate_phone, validate_positive_price,
                                    validate_rating, validate_text_length)

# Import all service-specific validators (if they exist)
try:
    from services.validators import (validate_image_aspect_ratio,
                                     validate_image_dimensions,
                                     validate_image_file_extension,
                                     validate_image_file_size)
except ImportError:
    # Define placeholder functions if the import fails
    import os

    from django.core.exceptions import ValidationError

    def validate_image_file_extension(value):
        """Validate image file extension
        Args:
            value: File object to validate
        Raises:
            ValidationError: If file extension is not allowed
        """
        allowed_extensions = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
        ext = os.path.splitext(value.name)[1].lower()
        if ext not in allowed_extensions:
            raise ValidationError(
                f"File extension {ext} is not allowed. Allowed extensions are: {', '.join(allowed_extensions)}",
            )

    def validate_image_file_size(value):
        """Validate image file size
        Args:
            value: File object to validate
        Raises:
            ValidationError: If file size exceeds limit
        """
        max_size = 5 * 1024 * 1024  # 5MB in bytes
        if value.size > max_size:
            raise ValidationError(
                "File size is too large. Maximum allowed size is 5MB.",
            )

    def validate_image_dimensions(value):
        """Validate image dimensions
        Args:
            value: File object to validate
        Raises:
            ValidationError: If image dimensions are not within allowed range
        """
        from PIL import Image

        try:
            img = Image.open(value)
        except Exception:
            raise ValidationError("File is not a valid image or is corrupted.")

        max_width, max_height = 4000, 4000  # Maximum dimensions
        min_width, min_height = 10, 10  # Minimum dimensions
        if img.width < min_width or img.height < min_height:
            raise ValidationError(
                f"Image dimensions are too small. Minimum allowed dimensions are {min_width}x{min_height}.",
            )
        if img.width > max_width or img.height > max_height:
            raise ValidationError(
                f"Image dimensions are too large. Maximum allowed dimensions are {max_width}x{max_height}.",
            )

    def validate_image_aspect_ratio(value):
        """Validate image aspect ratio
        Args:
            value: File object to validate
        Raises:
            ValidationError: If aspect ratio is not within allowed range
        """
        from PIL import Image

        try:
            img = Image.open(value)
        except Exception:
            raise ValidationError("File is not a valid image or is corrupted.")

        # Check if aspect ratio is between 1:3 and 3:1 (landscape or portrait, but not extremely narrow)
        aspect_ratio = img.width / img.height
        if aspect_ratio < 1 / 3 or aspect_ratio > 3:
            raise ValidationError(
                f"Image aspect ratio {aspect_ratio:.2f} is not allowed. Allowed aspect ratios are between 1:3 and 3:1.",
            )


# Import Django built-in validators for convenience
# Import Django ValidationError for consistent error handling
from django.core.exceptions import ValidationError
from django.core.validators import (EmailValidator, MaxLengthValidator,
                                    MaxValueValidator, MinLengthValidator,
                                    MinValueValidator, RegexValidator,
                                    URLValidator)

# Re-export commonly used validators with more descriptive names
validate_min_value = MinValueValidator
validate_max_value = MaxValueValidator
validate_email = EmailValidator
validate_url = URLValidator
validate_regex = RegexValidator
validate_max_length = MaxLengthValidator
validate_min_length = MinLengthValidator


# Create combined validation functions for common use cases
def validate_user_name(value, field_name="Name"):
    """Validate user name with standard rules.

    Args:
        value: Name to validate
        field_name: Name of the field for error messages

    Returns:
        str: Validated name

    Raises:
        ValidationError: If name is invalid

    """
    return validate_name(value, min_length=1, max_length=30, field_name=field_name)


def validate_service_name(value, field_name="Service Name"):
    """Validate service name with standard rules.

    Args:
        value: Service name to validate
        field_name: Name of the field for error messages

    Returns:
        str: Validated service name

    Raises:
        ValidationError: If service name is invalid

    """
    return validate_name(value, min_length=3, max_length=200, field_name=field_name)


def validate_review_text(value, field_name="Review Text"):
    """Validate review text with standard rules.

    Args:
        value: Review text to validate
        field_name: Name of the field for error messages

    Returns:
        str: Validated review text

    Raises:
        ValidationError: If review text is invalid

    """
    return validate_text_length(
        value,
        min_length=10,
        max_length=500,
        field_name=field_name,
    )


def validate_service_description(value, field_name="Description"):
    """Validate service description with standard rules.

    Args:
        value: Description to validate
        field_name: Name of the field for error messages

    Returns:
        str: Validated description

    Raises:
        ValidationError: If description is invalid

    """
    return validate_text_length(
        value,
        min_length=10,
        max_length=2000,
        field_name=field_name,
    )


def validate_service_short_description(value, field_name="Short Description"):
    """Validate service short description with standard rules.

    Args:
        value: Short description to validate
        field_name: Name of the field for error messages

    Returns:
        str: Validated short description

    Raises:
        ValidationError: If short description is invalid

    """
    return validate_text_length(
        value,
        min_length=10,
        max_length=300,
        field_name=field_name,
    )


# Create a validation service class for complex validation scenarios
# Export all validation functions for convenience
__all__ = [
    # Basic validation functions
    "validate_email_format",
    "validate_name",
    "validate_phone",
    "validate_positive_price",
    "validate_text_length",
    "validate_rating",
    # Image validation functions
    "validate_image_file_extension",
    "validate_image_file_size",
    "validate_image_dimensions",
    "validate_image_aspect_ratio",
    # Django built-in validators
    "MinValueValidator",
    "MaxValueValidator",
    "EmailValidator",
    "URLValidator",
    "RegexValidator",
    "MaxLengthValidator",
    "MinLengthValidator",
    # Convenience re-exports
    "validate_min_value",
    "validate_max_value",
    "validate_email",
    "validate_url",
    "validate_regex",
    "validate_max_length",
    "validate_min_length",
    # Combined validation functions
    "validate_user_name",
    "validate_service_name",
    "validate_review_text",
    "validate_service_description",
    "validate_service_short_description",
    # Error handling
    "ValidationError",
]
