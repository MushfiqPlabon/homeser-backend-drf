"""Consolidated models package for the HomeSer backend.
This package brings together common model functionality in one place for better organization and reuse.
"""

# Import all base model classes
# Import decimal for financial calculations
from decimal import Decimal

from cloudinary.models import CloudinaryField
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.validators import (
    EmailValidator,
    MaxValueValidator,
    MinValueValidator,
    RegexValidator,
)

# Import frequently used Django model fields and utilities
from django.db import models

# Import Django FSM for state machine functionality
from django_fsm import FSMField, transition

# Import third-party model utilities
from guardian.shortcuts import assign_perm

from homeser.base_models import (
    BaseModel,
    BaseReview,
    NamedSluggedModel,
    OrderType,
    ServiceType,
    SluggedModel,
)

# Get user model
User = get_user_model()

# Re-export commonly used validators with more descriptive names
validate_min_value = MinValueValidator
validate_max_value = MaxValueValidator
validate_email_format = EmailValidator
validate_regex_pattern = RegexValidator


# Status tracking using django-fsm (simplified version)
class StatusTrackedModelMixin:
    """Mixin that adds status tracking to models using django-fsm.
    """

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("pending", "Pending"),
        ("active", "Active"),
        ("inactive", "Inactive"),
        ("archived", "Archived"),
    ]

    status = FSMField(choices=STATUS_CHOICES, default="draft", db_index=True)

    class Meta:
        abstract = True

    @transition(field=status, source="draft", target="pending")
    def submit(self):
        """Submit the model instance."""

    @transition(field=status, source="pending", target="active")
    def activate(self):
        """Activate the model instance."""

    @transition(field=status, source="active", target="inactive")
    def deactivate(self):
        """Deactivate the model instance."""


# Export all classes and utilities for convenience
__all__ = [
    # Base model classes
    "BaseModel",
    "SluggedModel",
    "NamedSluggedModel",
    "BaseReview",
    "ServiceType",
    "OrderType",
    # Django model utilities
    "models",
    "get_user_model",
    "MinValueValidator",
    "MaxValueValidator",
    "EmailValidator",
    "RegexValidator",
    "settings",
    # Third-party model utilities
    "assign_perm",
    "CloudinaryField",
    "FSMField",
    "transition",
    # Decimal for financial calculations
    "Decimal",
    # User model
    "User",
    # Re-exported validators
    "validate_min_value",
    "validate_max_value",
    "validate_email_format",
    "validate_regex_pattern",
    # Status tracking mixin
    "StatusTrackedModelMixin",
]
