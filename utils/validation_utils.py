# utils/validation_utils.py
# Shared validation utilities

import re

from django.core.exceptions import ValidationError


def validate_email_format(value):
    """Validate email format"""
    if not re.match(r"[^@]+@[^@]+\.[^@]+", value):
        raise ValidationError("Invalid email format")
    return value


def validate_name(value, min_length=1, max_length=30, field_name="Name"):
    """Validate name format and length"""
    if len(value) < min_length:
        raise ValidationError(
            f"{field_name} must be at least {min_length} characters long",
        )

    if len(value) > max_length:
        raise ValidationError(f"{field_name} cannot exceed {max_length} characters")

    if not re.match(r"^[a-zA-Z\s'-]+$", value):
        raise ValidationError(f"{field_name} contains invalid characters")

    return value


def validate_phone(value):
    """Validate phone number format and length"""
    if not re.match(r"^[\d\s\-\+\(\)]{10,20}$", value):
        raise ValidationError("Invalid phone number format")

    digits_only = re.sub(r"[\s\-\+\(\)]", "", value)
    if len(digits_only) < 10 or len(digits_only) > 15:
        raise ValidationError("Phone number must be between 10 and 15 digits")

    return value


def validate_positive_price(value):
    """Validate that price is positive"""
    if value <= 0:
        raise ValidationError("Price must be greater than zero")
    return value


def validate_text_length(value, min_length=1, max_length=500, field_name="Text"):
    """Validate text length"""
    if len(value) < min_length:
        raise ValidationError(
            f"{field_name} must be at least {min_length} characters long",
        )

    if len(value) > max_length:
        raise ValidationError(f"{field_name} cannot exceed {max_length} characters")

    return value


def validate_rating(value):
    """Validate rating is between 1 and 5"""
    try:
        rating = int(value)
    except (ValueError, TypeError):
        raise ValidationError("Rating must be a number between 1 and 5")

    if rating < 1 or rating > 5:
        raise ValidationError("Rating must be between 1 and 5")

    return rating
