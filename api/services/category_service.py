# api/services/category_service.py
# Unified service for handling category-related operations

from services.models import ServiceCategory

from .abstract_service import AbstractService
from .base_service import BaseService


from .base_service import log_service_method # Add this import


class CategoryService(BaseService, AbstractService):
    """Service class for handling category-related operations"""

    model = ServiceCategory

    @classmethod
    @log_service_method
    def get_categories(cls):
        """Get all service categories.

        Returns:
            QuerySet: ServiceCategory queryset

        """
        return cls.get_all()

    @classmethod
    @log_service_method
    def get_category_detail(cls, category_id):
        """Get detailed information for a specific category.

        Args:
            category_id (int): ID of the category

        Returns:
            ServiceCategory: Category instance

        """
        return cls.get_by_id(category_id)

    @classmethod
    @log_service_method
    def get_detail(cls, obj_id, user=None):
        """Get detailed information for a specific category (AbstractService implementation).

        Args:
            obj_id (int): ID of the category
            user (User): User requesting the category

        Returns:
            ServiceCategory: Category instance

        """
        return cls.get_category_detail(obj_id)

    @classmethod
    @log_service_method
    def create_category(cls, data, user):
        """Create a new category.

        Args:
            data (dict): Category data
            user (User): User creating the category

        Returns:
            ServiceCategory: Created category instance

        """
        # Validate that user is admin
        cls._require_staff_permission(user)

        # Validate category data
        from utils.validation_utils import validate_text_length

        # Validate name
        try:
            name = data.get("name")
            if not name:
                raise ValueError("Category name is required")
            name = validate_text_length(
                name, min_length=1, max_length=100, field_name="Category name",
            )
        except Exception as e:
            raise ValueError(f"Invalid category name: {e!s}")

        # Validate description if provided
        if data.get("description"):
            try:
                description = validate_text_length(
                    data["description"],
                    min_length=0,
                    max_length=500,
                    field_name="Category description",
                )
                data["description"] = description
            except Exception as e:
                raise ValueError(f"Invalid category description: {e!s}")

        # Create category
        category_data = {
            "name": data["name"],
            "description": data.get("description", ""),
        }
        # Icon handling would be done separately

        return cls.create(category_data, user)

    @classmethod
    @log_service_method
    def create_obj(cls, data, user=None):
        """Create a new category (AbstractService implementation).

        Args:
            data (dict): Category data
            user (User): User creating the category

        Returns:
            ServiceCategory: Created category instance

        """
        return cls.create_category(data, user)

    @classmethod
    @log_service_method
    def update_category(cls, category_id, data, user):
        """Update an existing category.

        Args:
            category_id (int): ID of the category to update
            data (dict): Updated category data
            user (User): User updating the category

        Returns:
            ServiceCategory: Updated category instance

        """
        # Validate that user is admin
        cls._require_staff_permission(user)

        # Validate category data
        from utils.validation_utils import validate_text_length

        # Validate name if provided
        if data.get("name"):
            try:
                name = validate_text_length(
                    data["name"],
                    min_length=1,
                    max_length=100,
                    field_name="Category name",
                )
                data["name"] = name
            except Exception as e:
                raise ValueError(f"Invalid category name: {e!s}")

        # Validate description if provided
        if data.get("description"):
            try:
                description = validate_text_length(
                    data["description"],
                    min_length=0,
                    max_length=500,
                    field_name="Category description",
                )
                data["description"] = description
            except Exception as e:
                raise ValueError(f"Invalid category description: {e!s}")

        # Update category
        return cls.update(category_id, data, user)

    @classmethod
    @log_service_method
    def update_obj(cls, obj_id, data, user=None):
        """Update an existing category (AbstractService implementation).

        Args:
            obj_id (int): ID of the category to update
            data (dict): Updated category data
            user (User): User updating the category

        Returns:
            ServiceCategory: Updated category instance

        """
        return cls.update_category(obj_id, data, user)

    @classmethod
    @log_service_method
    def delete_category(cls, category_id, user):
        """Delete a category.

        Args:
            category_id (int): ID of the category to delete
            user (User): User deleting the category

        Returns:
            bool: True if successful

        """
        # Validate that user is admin
        cls._require_staff_permission(user)

        return cls.delete(category_id, user)

    @classmethod
    @log_service_method
    def delete_obj(cls, obj_id, user=None):
        """Delete a category (AbstractService implementation).

        Args:
            obj_id (int): ID of the category to delete
            user (User): User deleting the category

        Returns:
            bool: True if successful

        """
        return cls.delete_category(obj_id, user)
