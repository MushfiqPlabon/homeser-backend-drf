# utils/validation_utils.py
# Validation utilities
# This module exists for organization and provides compatibility with existing code that imports from here
# All validation logic is centralized in utils.validation for DRY principle

from utils.validation import (
    validate_email_format,
    validate_name,
    validate_phone,
    validate_positive_price,
    validate_text_length,
    validate_rating,
    validate_positive_integer,
)

__all__ = [
    "validate_email_format",
    "validate_name", 
    "validate_phone",
    "validate_positive_price",
    "validate_text_length",
    "validate_rating",
    "validate_positive_integer",
]