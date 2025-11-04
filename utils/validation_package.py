"""Consolidated validation package for the HomeSer backend.
This package brings together all validation logic in one place for better organization and reuse.
"""

# Import Django built-in validators for convenience
from django.core.exceptions import ValidationError
from django.core.validators import (EmailValidator, MaxLengthValidator,
                                    MaxValueValidator, MinLengthValidator,
                                    MinValueValidator, RegexValidator,
                                    URLValidator)

# Import all validation utilities from the centralized module
from utils.validation import (validate_email_format,
                              validate_image_aspect_ratio,
                              validate_image_dimensions,
                              validate_image_file_extension,
                              validate_image_file_size, validate_name,
                              validate_phone, validate_positive_price,
                              validate_rating, validate_text_length)

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
