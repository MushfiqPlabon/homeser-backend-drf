"""Base service classes for the HomeSer backend.
This module provides standardized base classes for all service implementations.
Consolidated from previous separate files to eliminate redundancy.
"""

import logging
from functools import wraps

from django.conf import settings  # Added this import
from django.db import transaction
from django.shortcuts import get_object_or_404
from guardian.shortcuts import assign_perm

logger = logging.getLogger(__name__)


def log_service_method(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        cls_name = (
            args[0].__name__
            if isinstance(args[0], type)
            else args[0].__class__.__name__
        )
        method_name = func.__name__
        logger.info(
            f"Entering {cls_name}.{method_name} with args: {args[1:]}, kwargs: {kwargs}"
        )
        try:
            result = func(*args, **kwargs)
            logger.info(f"Exiting {cls_name}.{method_name} successfully.")
            return result
        except Exception as e:
            logger.error(
                f"Exiting {cls_name}.{method_name} with error: {e}", exc_info=True
            )
            raise

    return wrapper


class BaseService:
    """Base service class with common functionality for all services."""

    model = None  # Should be overridden by subclasses
    cache_timeout = getattr(settings, "CACHE_TTL", 300)  # Default 5 minutes

    @classmethod
    def get_model(cls):
        """Get the model class."""
        if cls.model is None:
            raise NotImplementedError("model must be set in subclass")
        return cls.model

    @classmethod
    def _require_staff_permission(cls, user):
        """Helper method to check if the user is staff. Raises PermissionError if not."""
        if user is None or not user.is_authenticated or not user.is_staff:
            raise PermissionError(
                "Only staff users have permission to perform this action."
            )

    @classmethod
    def get_all(cls):
        """Get all instances of the model.

        Returns:
            QuerySet: QuerySet of model instances

        """
        return cls.get_model().objects.all()

    @classmethod
    def get_by_id(cls, obj_id):
        """Get an instance by ID.

        Args:
            obj_id (int): ID of the object

        Returns:
            Model instance or None

        """
        try:
            return cls.get_model().objects.get(id=obj_id)
        except cls.get_model().DoesNotExist:
            return None

    @classmethod
    def get_or_404(cls, obj_id):
        """Get an instance by ID or raise 404.

        Args:
            obj_id (int): ID of the object

        Returns:
            Model instance

        """
        return get_object_or_404(cls.get_model(), id=obj_id)

    @classmethod
    def create(cls, data, user=None):
        """Create a new instance.

        Args:
            data (dict): Data for the new instance
            user (User): User creating the instance

        Returns:
            Model instance

        Raises:
            Exception: If creation fails

        """
        try:
            with transaction.atomic():
                instance = cls.get_model().objects.create(**data)
                cls._assign_permissions(instance, user)
                return instance
        except Exception:
            raise

    @classmethod
    def update(cls, obj_id, data, user=None):
        """Update an existing instance.

        Args:
            obj_id (int): ID of the object to update
            data (dict): Updated data
            user (User): User updating the instance

        Returns:
            Model instance

        Raises:
            Exception: If update fails

        """
        try:
            instance = cls.get_or_404(obj_id)
            cls._common_permission_check(instance, user, "change")

            # Update fields
            for key, value in data.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)

            instance.save()
            return instance
        except Exception:
            raise

    @classmethod
    def delete(cls, obj_id, user=None):
        """Delete an instance.

        Args:
            obj_id (int): ID of the object to delete
            user (User): User deleting the instance

        Returns:
            bool: True if successful

        Raises:
            Exception: If deletion fails

        """
        try:
            instance = cls.get_or_404(obj_id)
            cls._common_permission_check(instance, user, "delete")

            instance.delete()
            return True
        except Exception:
            raise

    @classmethod
    def _common_validation(cls, data, validation_rules):
        """Common validation method for all service operations.

        Args:
            data (dict): Data to validate
            validation_rules (dict): Validation rules

        Raises:
            ValueError: If validation fails

        """
        # Perform validation based on the provided rules
        for field, rules in validation_rules.items():
            if field in data:
                value = data[field]
                if "required" in rules and rules["required"] and not value:
                    raise ValueError(f"{field} is required")
                if "type" in rules and not isinstance(value, rules["type"]):
                    raise TypeError(f"{field} must be of type {rules['type'].__name__}")
                if "min_length" in rules and len(value) < rules["min_length"]:
                    raise ValueError(
                        f"{field} must have at least {rules['min_length']} characters"
                    )
                if "max_length" in rules and len(value) > rules["max_length"]:
                    raise ValueError(
                        f"{field} must have at most {rules['max_length']} characters"
                    )

    @classmethod
    def _common_permission_check(cls, instance, user, action):
        """Standardized permission checking for all service operations.

        Args:
            instance: Model instance
            user (User): User performing the action
            action (str): Action to perform (view, change, delete)

        Raises:
            PermissionError: If user doesn't have permission

        """
        if user is None:
            return  # No permission check if no user provided

        app_label = cls.get_model()._meta.app_label
        model_name = cls.get_model().__name__.lower()
        permission_codename = f"{action}_{model_name}"

        # Check for direct ownership (user is the owner)
        # This handles both the 'user' field (for reviews) and 'owner' field (for services)
        if hasattr(instance, "owner") and instance.owner == user:
            return
        elif hasattr(instance, "user") and instance.user == user:
            return

        # Check django-guardian permissions
        has_perm = (
            user.has_perm(f"{app_label}.{permission_codename}", instance)
            or user.is_staff
        )

        if not has_perm:
            raise PermissionError(
                f"You don't have permission to {action} this {model_name}",
            )

    @classmethod
    def _assign_permissions(cls, instance, user):
        """Assign object-level permissions to the user and set ownership.

        Args:
            instance: Model instance
            user (User): User to assign permissions to

        """
        if user is None:
            return

        app_label = cls.get_model()._meta.app_label
        model_name = cls.get_model().__name__.lower()

        # Set ownership if the model has an owner field
        if hasattr(instance, "owner"):
            instance.owner = user
            instance.save(update_fields=["owner"])

        # Assign basic permissions
        permissions = ["view", "change", "delete"]
        for perm in permissions:
            try:
                assign_perm(f"{app_label}.{perm}_{model_name}", user, instance)
            except Exception:
                # Log error but don't fail
                pass


class ServiceOperationStrategy:
    """Abstract base class for service operation strategies."""

    def execute(self, service_class, *args, **kwargs):
        """Execute the service operation.

        Args:
            service_class: The service class to operate on
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Result of the operation

        """
        raise NotImplementedError


class CreateStrategy(ServiceOperationStrategy):
    """Strategy for creating instances."""

    def execute(self, service_class, data, user=None):
        """Create a new instance.

        Args:
            service_class: The service class to operate on
            data (dict): Data for the new instance
            user (User): User creating the instance

        Returns:
            Model instance

        """
        return service_class.create(data, user)


class UpdateStrategy(ServiceOperationStrategy):
    """Strategy for updating instances."""

    def execute(self, service_class, obj_id, data, user=None):
        """Update an existing instance.

        Args:
            service_class: The service class to operate on
            obj_id (int): ID of the object to update
            data (dict): Updated data
            user (User): User updating the instance

        Returns:
            Model instance

        """
        return service_class.update(obj_id, data, user)


class DeleteStrategy(ServiceOperationStrategy):
    """Strategy for deleting instances."""

    def execute(self, service_class, obj_id, user=None):
        """Delete an instance.

        Args:
            service_class: The service class to operate on
            obj_id (int): ID of the object to delete
            user (User): User deleting the instance

        Returns:
            bool: True if successful

        """
        return service_class.delete(obj_id, user)


class ServiceContext:
    """Context class for service operation strategies."""

    def __init__(self, strategy: ServiceOperationStrategy):
        """Initialize the context with a strategy.

        Args:
            strategy (ServiceOperationStrategy): The strategy to use

        """
        self._strategy = strategy

    def set_strategy(self, strategy: ServiceOperationStrategy):
        """Change the strategy.

        Args:
            strategy (ServiceOperationStrategy): The new strategy to use

        """
        self._strategy = strategy

    def execute_operation(self, service_class, *args, **kwargs):
        """Execute the operation using the current strategy.

        Args:
            service_class: The service class to operate on
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Result of the operation

        """
        return self._strategy.execute(service_class, *args, **kwargs)


class PermissionService(BaseService):
    """Base service class for operations with specific permission requirements"""

    required_permissions = []

    @classmethod
    def _check_permissions(cls, user, instance=None):
        """Check if user has required permissions"""
        if not user or not user.is_authenticated:
            raise PermissionError("Authentication required")

        # Check if user is admin
        if user.is_staff:
            return True

        # Check specific permissions
        model_name = cls.get_model().__name__.lower()
        app_label = cls.get_model()._meta.app_label

        for perm in cls.required_permissions:
            permission_codename = f"{perm}_{model_name}"
            if not user.has_perm(f"{app_label}.{permission_codename}", instance):
                raise PermissionError(
                    f"You don't have permission to {perm} this {model_name}",
                )

        return True


class ServiceInterface:
    """Interface for all service classes to ensure consistent API."""

    @classmethod
    def create(cls, data, user=None):
        """Create a new instance."""
        raise NotImplementedError

    @classmethod
    def retrieve(cls, obj_id):
        """Retrieve an instance by ID."""
        raise NotImplementedError

    @classmethod
    def update(cls, obj_id, data, user=None):
        """Update an existing instance."""
        raise NotImplementedError

    @classmethod
    def delete(cls, obj_id, user=None):
        """Delete an instance."""
        raise NotImplementedError

    @classmethod
    def list(cls, filters=None):
        """List instances with optional filters."""
        raise NotImplementedError


class CRUDService(ServiceInterface, BaseService):
    """Service class that implements the full CRUD interface."""

    @classmethod
    def create(cls, data, user=None):
        """Create a new instance."""
        return super().create(data, user)

    @classmethod
    def retrieve(cls, obj_id):
        """Retrieve an instance by ID."""
        return cls.get_by_id(obj_id)

    @classmethod
    def update(cls, obj_id, data, user=None):
        """Update an existing instance."""
        return super().update(obj_id, data, user)

    @classmethod
    def delete(cls, obj_id, user=None):
        """Delete an instance."""
        return super().delete(obj_id, user)

    @classmethod
    def list(cls, filters=None):
        """List instances with optional filters."""
        queryset = cls.get_model().objects.all()
        if filters:
            queryset = queryset.filter(**filters)
        return queryset


# Export all classes for convenience
__all__ = [
    "BaseService",
    "CRUDService",
    "CreateStrategy",
    "DeleteStrategy",
    "PermissionService",
    "ServiceContext",
    "ServiceInterface",
    "ServiceOperationStrategy",
    "UpdateStrategy",
]
