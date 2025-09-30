"""Consolidated permissions package for the HomeSer backend.
This package brings together all permission-related functionality in one place for better organization and reuse.
"""

# Import all necessary permission classes and utilities
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from drf_spectacular.utils import extend_schema_view
from guardian.models import GroupObjectPermission, UserObjectPermission
from guardian.shortcuts import (
    assign_perm,
    get_groups_with_perms,
    get_objects_for_user,
    get_perms,
    get_perms_for_model,
    get_users_with_perms,
    remove_perm,
)
from rest_framework import permissions

from utils.response_utils import format_error_response

# Get user model
User = get_user_model()


class BasePermission(permissions.BasePermission):
    """Abstract base permission class with common functionality.
    """

    def has_permission(self, request, view):
        """Check if user has general permission to access the view.

        Args:
            request: HTTP request
            view: View instance

        Returns:
            bool: True if user has permission, False otherwise

        """
        # Default implementation - can be overridden by subclasses
        return True

    def has_object_permission(self, request, view, obj):
        """Check if user has permission to access a specific object.

        Args:
            request: HTTP request
            view: View instance
            obj: Model instance

        Returns:
            bool: True if user has permission, False otherwise

        """
        # Default implementation - can be overridden by subclasses
        return True


class IsOwnerOrReadOnly(BasePermission):
    """Permission that allows owners to edit their own objects, but allows read-only access to others.
    """

    def has_object_permission(self, request, view, obj):
        """Check if user has permission to access a specific object.

        Args:
            request: HTTP request
            view: View instance
            obj: Model instance

        Returns:
            bool: True if user has permission, False otherwise

        """
        # Read permissions are allowed for any request
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner of the object
        return obj.user == request.user


class IsStaffOrReadOnly(BasePermission):
    """Permission that allows staff members to edit objects, but allows read-only access to others.
    """

    def has_permission(self, request, view):
        """Check if user has general permission to access the view.

        Args:
            request: HTTP request
            view: View instance

        Returns:
            bool: True if user has permission, False otherwise

        """
        # Read permissions are allowed for any request
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to staff members
        return request.user and request.user.is_staff


class UniversalObjectPermission(BasePermission):
    """Universal object permission class that checks Django-Guardian permissions.
    """

    def has_permission(self, request, view):
        """Check if user has general permission to access the view.
        Unauthenticated users are denied access by default.

        Args:
            request: HTTP request
            view: View instance

        Returns:
            bool: True if user has permission, False otherwise

        """
        # Return False for unauthenticated users
        if not request.user or not request.user.is_authenticated:
            return False

        # Authenticated users are allowed by default
        # Specific object-level permissions are handled in has_object_permission
        return True

    def has_object_permission(self, request, view, obj):
        """Check if user has permission to access a specific object using Django-Guardian.

        Args:
            request: HTTP request
            view: View instance
            obj: Model instance

        Returns:
            bool: True if user has permission, False otherwise

        """
        # Allow staff members to access all objects
        if request.user.is_staff:
            return True

        # Allow access to object owner
        if hasattr(obj, "user") and obj.user == request.user:
            return True

        # Determine the appropriate permission based on the action
        # Check if this is a viewset action
        if hasattr(view, "action"):
            action = view.action
            if action in ["list", "retrieve"]:
                permission_codename = "view"
            elif action in ["create"]:
                permission_codename = "add"
            elif action in ["update", "partial_update"]:
                permission_codename = "change"
            elif action == "destroy":
                permission_codename = "delete"
            else:
                # Default to view permission for other actions
                permission_codename = "view"
        # For non-viewset views, determine permission based on HTTP method
        elif request.method in ["GET"]:
            permission_codename = "view"
        elif request.method in ["POST"]:
            permission_codename = "add"
        elif request.method in ["PUT", "PATCH"]:
            permission_codename = "change"
        elif request.method == "DELETE":
            permission_codename = "delete"
        else:
            permission_codename = "view"

        # Get app label and model name
        app_label = obj._meta.app_label
        model_name = obj._meta.model_name.lower()

        # Format the full permission codename
        full_permission = f"{app_label}.{permission_codename}_{model_name}"

        return request.user.has_perm(full_permission, obj)


class PermissionService:
    """Service class for managing permissions.
    """

    @staticmethod
    def assign_object_permission(user, permission, obj):
        """Assign an object-level permission to a user.

        Args:
            user (User): User to assign permission to
            permission (str): Permission codename
            obj: Model instance

        Returns:
            bool: True if successful, False otherwise

        """
        try:
            assign_perm(permission, user, obj)
            return True
        except Exception:
            # Log error but don't fail
            return False

    @staticmethod
    def remove_object_permission(user, permission, obj):
        """Remove an object-level permission from a user.

        Args:
            user (User): User to remove permission from
            permission (str): Permission codename
            obj: Model instance

        Returns:
            bool: True if successful, False otherwise

        """
        try:
            remove_perm(permission, user, obj)
            return True
        except Exception:
            # Log error but don't fail
            return False

    @staticmethod
    def get_user_objects_with_permission(user, permission, model_class):
        """Get all objects that a user has a specific permission for.

        Args:
            user (User): User to check permissions for
            permission (str): Permission codename
            model_class: Model class to check objects for

        Returns:
            QuerySet: Objects that user has permission for

        """
        return get_objects_for_user(user, permission, model_class)

    @staticmethod
    def get_object_permissions(obj):
        """Get all permissions for a specific object.

        Args:
            obj: Model instance

        Returns:
            list: Permissions for the object

        """
        return get_perms(obj)

    @staticmethod
    def get_user_permissions_for_object(user, obj):
        """Get all permissions that a user has for a specific object.

        Args:
            user (User): User to check permissions for
            obj: Model instance

        Returns:
            list: Permissions that user has for the object

        """
        return get_perms(user, obj)

    @staticmethod
    def get_users_with_object_permissions(obj):
        """Get all users that have permissions for a specific object.

        Args:
            obj: Model instance

        Returns:
            list: Users with permissions for the object

        """
        return get_users_with_perms(obj)

    @staticmethod
    def get_groups_with_object_permissions(obj):
        """Get all groups that have permissions for a specific object.

        Args:
            obj: Model instance

        Returns:
            list: Groups with permissions for the object

        """
        return get_groups_with_perms(obj)

    @staticmethod
    def validate_permission_data(data):
        """Validate permission data.

        Args:
            data (dict): Permission data to validate

        Returns:
            dict: Validated data

        Raises:
            ValidationError: If data is invalid

        """
        # Validate permission data
        from utils.validation_utils import (
            validate_positive_integer,
            validate_text_length,
        )

        # Validate user_id
        try:
            user_id = data.get("user_id")
            if not user_id:
                raise ValueError("User ID is required")
            user_id = validate_positive_integer(user_id)
            data["user_id"] = user_id
        except Exception as e:
            raise ValueError(f"Invalid user ID: {e!s}")

        # Validate permission
        try:
            permission = data.get("permission")
            if not permission:
                raise ValueError("Permission is required")
            permission = validate_text_length(
                permission, min_length=1, max_length=100, field_name="Permission",
            )
            data["permission"] = permission
        except Exception as e:
            raise ValueError(f"Invalid permission: {e!s}")

        # Validate object_id
        try:
            object_id = data.get("object_id")
            if not object_id:
                raise ValueError("Object ID is required")
            object_id = validate_positive_integer(object_id)
            data["object_id"] = object_id
        except Exception as e:
            raise ValueError(f"Invalid object ID: {e!s}")

        return data


class PermissionFactory:
    """Factory for creating different types of permissions.
    """

    PERMISSION_TYPES = {
        "view": "view",
        "change": "change",
        "delete": "delete",
        "add": "add",
    }

    @staticmethod
    def create_permission(permission_type, model_class, user=None, group=None):
        """Create a permission of the specified type.

        Args:
            permission_type (str): Type of permission to create
            model_class: Model class to create permission for
            user (User): User to assign permission to (optional)
            group (Group): Group to assign permission to (optional)

        Returns:
            Permission: Created permission

        Raises:
            ValueError: If permission type is invalid

        """
        if permission_type not in PermissionFactory.PERMISSION_TYPES:
            raise ValueError(f"Invalid permission type: {permission_type}")

        app_label = model_class._meta.app_label
        model_name = model_class.__name__.lower()
        codename = f"{permission_type}_{model_name}"

        permission, created = Permission.objects.get_or_create(
            codename=codename,
            content_type__app_label=app_label,
            content_type__model=model_name,
            defaults={
                "name": f"Can {permission_type} {model_name}",
                "content_type": model_class._meta.content_type,
            },
        )

        # Assign permission to user or group if specified
        if user:
            user.user_permissions.add(permission)
        elif group:
            group.permissions.add(permission)

        return permission

    @staticmethod
    def create_object_permission(
        permission_type, model_class, obj, user=None, group=None,
    ):
        """Create an object-level permission of the specified type.

        Args:
            permission_type (str): Type of permission to create
            model_class: Model class to create permission for
            obj: Model instance to create permission for
            user (User): User to assign permission to (optional)
            group (Group): Group to assign permission to (optional)

        Returns:
            tuple: (permission, created) where permission is the created permission and created is a boolean

        Raises:
            ValueError: If permission type is invalid

        """
        if permission_type not in PermissionFactory.PERMISSION_TYPES:
            raise ValueError(f"Invalid permission type: {permission_type}")

        app_label = model_class._meta.app_label
        model_name = model_class.__name__.lower()
        codename = f"{permission_type}_{model_name}"

        # Create the base permission if it doesn't exist
        permission, created = Permission.objects.get_or_create(
            codename=codename,
            content_type__app_label=app_label,
            content_type__model=model_name,
            defaults={
                "name": f"Can {permission_type} {model_name}",
                "content_type": model_class._meta.content_type,
            },
        )

        # Assign object-level permission to user or group if specified
        if user:
            assign_perm(permission, user, obj)
        elif group:
            # Note: Group object permissions are not directly supported by Django-Guardian
            # This would need to be implemented differently
            pass

        return permission, created


def is_owner(user, obj):
    """Helper function to check if a user is the owner of an object.

    Args:
        user (User): User to check ownership for
        obj: Model instance to check ownership of

    Returns:
        bool: True if user is owner of the object, False otherwise

    """
    if hasattr(obj, "user"):
        return obj.user == user
    if hasattr(obj, "owner"):
        return obj.owner == user
    return False


# Add GuardianPermission class
# Export all classes and utilities for convenience
__all__ = [
    # Base permission classes
    "BasePermission",
    "IsOwnerOrReadOnly",
    "IsStaffOrReadOnly",
    "UniversalObjectPermission",
    # Permission service
    "PermissionService",
    # Permission factory
    "PermissionFactory",
    # Django permission classes
    "permissions",
    # Django-Guardian utilities
    "assign_perm",
    "remove_perm",
    "get_objects_for_user",
    "get_perms_for_model",
    "get_perms",
    "get_users_with_perms",
    "get_groups_with_perms",
    "UserObjectPermission",
    "GroupObjectPermission",
    # DRF Spectacular utilities
    "extend_schema_view",
    # Utility functions
    "format_error_response",
    # Model classes
    "User",
    "Permission",
]
