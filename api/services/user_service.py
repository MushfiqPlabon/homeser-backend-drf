# api/services/user_service.py
# Unified service for handling user-related operations

from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import get_object_or_404
from guardian.shortcuts import assign_perm

from accounts.models import UserProfile
from utils.email.email_service import EmailService

from .base_service import BaseService

from .base_service import log_service_method # Add this import

User = get_user_model()


class UserService(BaseService):
    """Service class for handling user-related operations"""

    model = User

    @classmethod
    @log_service_method
    def get_users(cls, user=None, admin_mode=False):
        """Get all users (admin only).

        Args:
            user (User): User requesting the users (must be admin)
            admin_mode (bool): Whether to enforce admin permissions

        Returns:
            QuerySet: User queryset

        Raises:
            PermissionError: If user is not admin and admin_mode is True

        """
        # Check if user is admin when in admin mode
        if admin_mode:
            cls._require_staff_permission(user)

        return User.objects.all()

    @classmethod
    @log_service_method
    def get_user_detail(cls, user_id):
        """Get detailed information for a specific user.

        Args:
            user_id (int): ID of the user

        Returns:
            User: User instance

        """
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None

    @classmethod
    @log_service_method
    def create_user(cls, data):
        """Create a new user.

        Args:
            data (dict): User data

        Returns:
            User: Created user instance

        """
        # Validate user data
        from utils.validation_utils import validate_email_format, validate_text_length

        # Validate username
        try:
            username = data.get("username")
            if not username:
                raise ValueError("Username is required")
            username = validate_text_length(
                username, min_length=1, max_length=150, field_name="Username",
            )
        except Exception as e:
            raise ValueError(f"Invalid username: {e!s}")

        # Validate email
        try:
            email = data.get("email")
            if not email:
                raise ValueError("Email is required")
            email = validate_email_format(email)
        except Exception as e:
            raise ValueError(f"Invalid email: {e!s}")

        # Validate password
        try:
            password = data.get("password")
            if not password:
                raise ValueError("Password is required")
            if len(password) < 8:
                raise ValueError("Password must be at least 8 characters long")
        except Exception as e:
            raise ValueError(f"Invalid password: {e!s}")

        # Validate first name
        try:
            first_name = data.get("first_name")
            if not first_name:
                raise ValueError("First name is required")
            first_name = validate_text_length(
                first_name, min_length=1, max_length=30, field_name="First name",
            )
        except Exception as e:
            raise ValueError(f"Invalid first name: {e!s}")

        # Validate last name
        try:
            last_name = data.get("last_name")
            if not last_name:
                raise ValueError("Last name is required")
            last_name = validate_text_length(
                last_name, min_length=1, max_length=30, field_name="Last name",
            )
        except Exception as e:
            raise ValueError(f"Invalid last name: {e!s}")

        # Create user
        with transaction.atomic():
            user = User.objects.create_user(
                username=data["username"],
                email=data["email"],
                password=data["password"],
                first_name=data["first_name"],
                last_name=data["last_name"],
            )

            # Create user profile
            UserProfile.objects.create(user=user)

            # Assign basic permissions to the user
            assign_perm("accounts.view_user", user, user)
            assign_perm("accounts.change_user", user, user)

            # Send welcome email
            try:
                EmailService.send_welcome_email(user)
            except Exception as e:
                # Log the error but don't fail user creation
                print(f"Failed to send welcome email: {e}")

            return user

    @classmethod
    @log_service_method
    def update_user(cls, user_id, data, requesting_user):
        """Update an existing user.

        Args:
            user_id (int): ID of the user to update
            data (dict): Updated user data
            requesting_user (User): User making the request

        Returns:
            User: Updated user instance

        """
        # Check permissions
        user = get_object_or_404(User, id=user_id)
        cls._common_permission_check(user, requesting_user, "change")

        # Validate user data
        from utils.validation_utils import validate_email_format, validate_text_length

        # Validate first name if provided
        if data.get("first_name"):
            try:
                first_name = validate_text_length(
                    data["first_name"],
                    min_length=1,
                    max_length=30,
                    field_name="First name",
                )
                data["first_name"] = first_name
            except Exception as e:
                raise ValueError(f"Invalid first name: {e!s}")

        # Validate last name if provided
        if data.get("last_name"):
            try:
                last_name = validate_text_length(
                    data["last_name"],
                    min_length=1,
                    max_length=30,
                    field_name="Last name",
                )
                data["last_name"] = last_name
            except Exception as e:
                raise ValueError(f"Invalid last name: {e!s}")

        # Validate email if provided
        if data.get("email"):
            try:
                email = validate_email_format(data["email"])
                data["email"] = email
            except Exception as e:
                raise ValueError(f"Invalid email: {e!s}")

        # Update fields if provided
        if "first_name" in data:
            user.first_name = data["first_name"]

        if "last_name" in data:
            user.last_name = data["last_name"]

        if "email" in data:
            user.email = data["email"]

        # Save user
        user.save()

        return user

    @classmethod
    @log_service_method
    def delete_user(cls, user_id, requesting_user):
        """Delete a user.

        Args:
            user_id (int): ID of the user to delete
            requesting_user (User): User making the request

        Returns:
            bool: True if successful

        """
        # Check permissions
        if requesting_user.id == user_id:
            raise ValueError("You cannot delete your own account")

        # Use common permission check for delete operation
        user = get_object_or_404(User, id=user_id)
        cls._common_permission_check(user, requesting_user, "delete")

        # Delete user
        user.delete()

        return True

    @classmethod
    @log_service_method
    def promote_user_to_admin(cls, user_id, requesting_user):
        """Promote a user to admin (staff) role.

        Args:
            user_id (int): ID of the user to promote
            requesting_user (User): User making the request (must be admin)

        Returns:
            User: Promoted user instance

        """
        # Check permissions - admin promotion requires admin privileges
        cls._require_staff_permission(requesting_user)

        user = get_object_or_404(User, id=user_id)

        # Promote user
        user.is_staff = True
        user.save()

        return user

    @classmethod
    @log_service_method
    def get_user_profile(cls, user):
        """Get user profile.

        Args:
            user (User): User whose profile to retrieve

        Returns:
            UserProfile: User profile instance

        """
        profile, created = UserProfile.objects.select_related("user").get_or_create(
            user=user,
        )
        return profile

    @classmethod
    @log_service_method
    def update_user_profile(cls, user, data):
        """Update user profile.

        Args:
            user (User): User whose profile to update
            data (dict): Updated profile data

        Returns:
            UserProfile: Updated profile instance

        """
        profile = cls.get_user_profile(user)

        # Validate profile data
        from utils.validation_utils import validate_phone_number, validate_text_length

        # Validate bio if provided
        if data.get("bio"):
            try:
                bio = validate_text_length(
                    data["bio"], min_length=0, max_length=500, field_name="Bio",
                )
                data["bio"] = bio
            except Exception as e:
                raise ValueError(f"Invalid bio: {e!s}")

        # Validate phone if provided
        if data.get("phone"):
            try:
                phone = validate_phone_number(data["phone"])
                data["phone"] = phone
            except Exception as e:
                raise ValueError(f"Invalid phone: {e!s}")

        # Validate address if provided
        if data.get("address"):
            try:
                address = validate_text_length(
                    data["address"], min_length=0, max_length=200, field_name="Address",
                )
                data["address"] = address
            except Exception as e:
                raise ValueError(f"Invalid address: {e!s}")

        # Update fields if provided
        if "bio" in data:
            profile.bio = data["bio"]

        if "phone" in data:
            profile.phone = data["phone"]

        if "address" in data:
            profile.address = data["address"]

        # Save profile
        profile.save()

        return profile
