# api/services/permission_service.py
# Specialized service base class for permission-based operations

from abc import ABC, abstractmethod

from .base_service import BaseService


class BasePermission(ABC):
    """Abstract base class for permissions."""

    @abstractmethod
    def check_permission(self, user, instance=None):
        """Check if user has permission.

        Args:
            user: The user to check permissions for
            instance: The instance to check permissions on (optional)

        Returns:
            bool: True if user has permission, False otherwise

        Raises:
            PermissionError: If user doesn't have permission

        """


class OwnerPermission(BasePermission):
    """Permission that checks if user is the owner of the instance."""

    def check_permission(self, user, instance=None):
        """Check if user is the owner of the instance.

        Args:
            user: The user to check permissions for
            instance: The instance to check ownership of

        Returns:
            bool: True if user is owner, False otherwise

        """
        if not user or not instance:
            return False

        # Check for direct ownership (user is the owner)
        return bool(hasattr(instance, "user") and instance.user == user)


class StaffPermission(BasePermission):
    """Permission that checks if user is staff/admin."""

    def check_permission(self, user, instance=None):
        """Check if user is staff/admin.

        Args:
            user: The user to check permissions for
            instance: The instance (not used for this permission)

        Returns:
            bool: True if user is staff, False otherwise

        """
        if not user:
            return False

        return user.is_staff


class ModelPermission(BasePermission):
    """Permission that checks Django model-level permissions."""

    def __init__(self, action):
        """Initialize the model permission.

        Args:
            action (str): The action to check (view, change, delete, etc.)

        """
        self.action = action

    def check_permission(self, user, instance=None):
        """Check if user has the specified model permission.

        Args:
            user: The user to check permissions for
            instance: The instance to check permissions on

        Returns:
            bool: True if user has permission, False otherwise

        """
        if not user or not instance:
            return False

        model = instance.__class__
        app_label = model._meta.app_label
        model_name = model.__name__.lower()
        permission_codename = f"{self.action}_{model_name}"

        return user.has_perm(f"{app_label}.{permission_codename}", instance)


class CompositePermission(BasePermission):
    """Composite permission that combines multiple permissions using logical operators."""

    def __init__(self):
        """Initialize the composite permission."""
        self.permissions = []
        self.operator = "and"  # 'and' or 'or'

    def add_permission(self, permission):
        """Add a permission to the composite.

        Args:
            permission (BasePermission): The permission to add

        """
        self.permissions.append(permission)
        return self

    def set_operator(self, operator):
        """Set the logical operator for combining permissions.

        Args:
            operator (str): 'and' or 'or'

        """
        self.operator = operator
        return self

    def check_permission(self, user, instance=None):
        """Check if user has all/any of the permissions based on the operator.

        Args:
            user: The user to check permissions for
            instance: The instance to check permissions on

        Returns:
            bool: True if user has required permissions, False otherwise

        """
        if not self.permissions:
            return True

        if self.operator == "and":
            return all(
                perm.check_permission(user, instance) for perm in self.permissions
            )
        # operator == 'or'
        return any(perm.check_permission(user, instance) for perm in self.permissions)


class PermissionService(BaseService):
    """Base service class for operations with specific permission requirements"""

    required_permissions = []

    @classmethod
    def _check_permissions(cls, user, instance=None):
        """Check if user has required permissions"""
        if not user:
            raise PermissionError("Authentication required")

        # Create a composite permission for all required permissions
        composite_perm = CompositePermission()

        # Add staff permission (admins can do everything)
        staff_perm = StaffPermission()
        if staff_perm.check_permission(user):
            return True

        # Add specific permissions
        for perm_name in cls.required_permissions:
            model_perm = ModelPermission(perm_name)
            composite_perm.add_permission(model_perm)

        # Add owner permission as an alternative
        owner_perm = OwnerPermission()
        owner_composite = CompositePermission().set_operator("or")
        owner_composite.add_permission(composite_perm)
        owner_composite.add_permission(owner_perm)

        if not owner_composite.check_permission(user, instance):
            model_name = cls.get_model().__name__.lower()
            raise PermissionError(
                f"You don't have permission to {', '.join(cls.required_permissions)} this {model_name}",
            )

        return True


class PermissionFactory:
    """Factory for creating different types of permissions."""

    @staticmethod
    def create_permission(permission_type, **kwargs):
        """Create a permission of the specified type.

        Args:
            permission_type (str): Type of permission to create
            **kwargs: Additional arguments for the permission

        Returns:
            BasePermission: The created permission

        """
        if permission_type == "owner":
            return OwnerPermission()
        if permission_type == "staff":
            return StaffPermission()
        if permission_type == "model":
            return ModelPermission(kwargs.get("action", "view"))
        if permission_type == "composite":
            return CompositePermission()
        raise ValueError(f"Unknown permission type: {permission_type}")
