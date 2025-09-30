# api/services/service_service.py
# Simplified service for handling service-related operations

import logging
import time

from django.db import transaction

# Import pydantic for validation
from pydantic import BaseModel, ValidationError, field_validator

from services.models import Review, Service, ServiceRatingAggregation

from .base_service import BaseService

logger = logging.getLogger(__name__)


# Pydantic validation models
class ServiceUpdateIn(BaseModel):
    name: str | None = None
    short_desc: str | None = None
    description: str | None = None
    price: float | None = None
    category: int | None = None
    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        if v is not None and (len(v) < 1 or len(v) > 200):
            raise ValueError("Service name must be between 1 and 200 characters")
        return v

    @field_validator("short_desc")
    @classmethod
    def validate_short_desc(cls, v):
        if v is not None and (len(v) < 10 or len(v) > 300):
            raise ValueError("Short description must be between 10 and 300 characters")
        return v

    @field_validator("description")
    @classmethod
    def validate_description(cls, v):
        if v is not None and (len(v) < 20 or len(v) > 5000):
            raise ValueError("Description must be between 20 and 5000 characters")
        return v

    @field_validator("price")
    @classmethod
    def validate_price(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Price must be positive")
        return v

    @field_validator("is_active")
    @classmethod
    def validate_is_active(cls, v):
        if v is not None and not isinstance(v, bool):
            raise ValueError("Active status must be a boolean value")
        return v


def timing_decorator(func):
    """Decorator to measure execution time of functions"""

    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        logger.info(
            f"{func.__module__}.{func.__name__} executed in {execution_time:.4f} seconds",
        )

        # Add performance metrics to monitoring
        try:
            from utils.monitoring import record_performance_metric

            record_performance_metric(
                f"{func.__module__}.{func.__name__}",
                execution_time,
                {"args_count": len(args), "kwargs_count": len(kwargs)},
            )
        except Exception:
            pass  # Don't fail if monitoring is not available

        return result

    return wrapper


class ServiceService(BaseService):
    """Simplified service class for handling service-related operations"""

    model = Service

    @classmethod
    @timing_decorator
    def get_services(cls, user=None, admin_mode=False):
        """Get all services with optional admin mode.

        Args:
            user (User): User requesting services
            admin_mode (bool): Whether to enforce admin permissions

        Returns:
            QuerySet: Service queryset

        """
        logger.info(
            f"Getting services - admin_mode: {admin_mode}, user: {user.id if user else 'anonymous'}",
        )

        # Check if user is admin when in admin mode
        if admin_mode:
            cls._require_staff_permission(user)

        # Start with base queryset and optimize with select_related and prefetch_related
        queryset = (
            cls.get_model()
            .objects.select_related("category")
            .prefetch_related(
                "rating_aggregation",
                "reviews",  # Prefetch reviews if needed
            )
        )

        # Apply filters based on admin mode
        if not admin_mode:
            queryset = queryset.filter(is_active=True)

        logger.info(f"Retrieved {queryset.count()} services")
        return queryset

    @classmethod
    @timing_decorator
    def get_service_detail(cls, service_id):
        """Get detailed information for a specific service.

        Args:
            service_id (int): ID of the service

        Returns:
            Service: Service instance with annotations

        """
        logger.info(f"Getting service detail for service_id: {service_id}")

        try:
            # Get service with precomputed aggregations from ServiceRatingAggregation
            # This is more efficient than calculating on-the-fly
            # Optimize with select_related for category and prefetch_related for related data
            service = (
                cls.get_model()
                .objects.select_related("category")
                .prefetch_related(
                    "rating_aggregation",  # Use precomputed aggregation
                    "reviews__user",  # Prefetch user information with reviews
                    "orders",  # Prefetch related orders if needed
                )
                .filter(id=service_id, is_active=True)
                .first()
            )

            if service:
                logger.info(f"Successfully retrieved service: {service.name}")
            else:
                logger.warning(f"Service not found or inactive: {service_id}")

            return service
        except cls.get_model().DoesNotExist:
            logger.error(f"Service not found: {service_id}")
            return None

    @classmethod
    @timing_decorator
    def create_service(cls, data, user):
        """Create a new service.

        Args:
            data (dict): Service data
            user (User): User creating the service

        Returns:
            Service: Created service instance

        """
        logger.info(f"Creating new service by user: {user.id}")

        # Validate that user is admin
        cls._require_staff_permission(user)

        # Validate service data
        from utils.validation_utils import validate_positive_price, validate_text_length

        # Validate name
        try:
            name = data.get("name")
            if not name:
                raise ValueError("Service name is required")
            name = validate_text_length(
                name, min_length=1, max_length=200, field_name="Service name",
            )
        except Exception as e:
            logger.error(f"Invalid service name: {e!s}")
            raise ValueError(f"Invalid service name: {e!s}")

        # Validate short description
        try:
            short_desc = data.get("short_desc")
            if not short_desc:
                raise ValueError("Short description is required")
            short_desc = validate_text_length(
                short_desc,
                min_length=10,
                max_length=300,
                field_name="Short description",
            )
        except Exception as e:
            logger.error(f"Invalid short description: {e!s}")
            raise ValueError(f"Invalid short description: {e!s}")

        # Validate description
        try:
            description = data.get("description")
            if not description:
                raise ValueError("Description is required")
            description = validate_text_length(
                description, min_length=20, max_length=5000, field_name="Description",
            )
        except Exception as e:
            logger.error(f"Invalid description: {e!s}")
            raise ValueError(f"Invalid description: {e!s}")

        # Validate price
        try:
            price = data.get("price")
            if price is None:
                raise ValueError("Price is required")
            price = validate_positive_price(price)
        except Exception as e:
            logger.error(f"Invalid price: {e!s}")
            raise ValueError(f"Invalid price: {e!s}")

        # Validate category
        if "category" not in data or not data["category"]:
            logger.error("Category is required")
            raise ValueError("Category is required")

        # Create service data
        service_data = {
            "name": data["name"],
            "short_desc": data["short_desc"],
            "description": data["description"],
            "price": data["price"],
            "category_id": data["category"],
        }
        # Image handling would be done separately

        # Use the base service create method
        with transaction.atomic():
            instance = cls.get_model().objects.create(**service_data)

            # Create initial rating aggregation
            ServiceRatingAggregation.objects.create(
                service=instance, average=0, count=0,
            )

            # Assign object-level permissions using django-guardian
            # Allow the creator to view, change, and delete the service
            cls._assign_permissions(instance, user)

            logger.info(
                f"Successfully created service: {instance.name} (ID: {instance.id})",
            )

            return instance

    @classmethod
    @timing_decorator
    def update_service(cls, service_id, data, user):
        """Update an existing service.

        Args:
            service_id (int): ID of the service to update
            data (dict): Updated service data
            user (User): User updating the service

        Returns:
            Service: Updated service instance

        """
        logger.info(f"Updating service {service_id} by user: {user.id}")
        service = cls.get_or_404(service_id)

        # Check if user has permission to update this service
        cls._common_permission_check(service, user, "change")

        # Validate the input data using Pydantic model
        try:
            service_update = ServiceUpdateIn(
                **{k: v for k, v in data.items() if v is not None},
            )
        except ValidationError as e:
            logger.error(f"Invalid service data: {e!s}")
            raise ValueError(f"Invalid service data: {e!s}")

        # Update fields if provided
        for field, value in service_update.model_dump(exclude_unset=True).items():
            if field == "category":
                service.category_id = value
            else:
                setattr(service, field, value)

        # Save service
        service.save()
        logger.info(f"Successfully updated service: {service.name} (ID: {service.id})")

        return service

    @classmethod
    @timing_decorator
    def delete_service(cls, service_id, user):
        """Delete a service.

        Args:
            service_id (int): ID of the service to delete
            user (User): User deleting the service

        Returns:
            bool: True if successful

        """
        logger.info(f"Deleting service {service_id} by user: {user.id}")
        service = cls.get_or_404(service_id)

        # Check if user has permission to delete this service
        cls._common_permission_check(service, user, "delete")

        # Delete service
        service.delete()
        logger.info(f"Successfully deleted service ID: {service_id}")

        return True

    @classmethod
    @timing_decorator
    def get_service_reviews(cls, service_id):
        """Get reviews for a specific service.

        Args:
            service_id (int): ID of the service

        Returns:
            QuerySet: Reviews queryset

        """
        logger.info(f"Getting reviews for service {service_id}")
        reviews = (
            Review.objects.filter(service_id=service_id)
            .select_related("user")
            .prefetch_related(
                "user__profile",  # Prefetch user profile if needed
            )
        )
        logger.info(f"Retrieved {reviews.count()} reviews for service {service_id}")
        return reviews

    @classmethod
    @timing_decorator
    def create_service_review(cls, service_id, user, rating, text):
        """Create a review for a service.

        Args:
            service_id (int): ID of the service
            user (User): User creating the review
            rating (int): Rating (1-5)
            text (str): Review text

        Returns:
            Review: Created review instance

        Raises:
            ValueError: If validation fails
            Exception: If creation fails

        """
        try:
            from orders.models import Order
            from utils.email.email_service import EmailService

            # Validate service exists and is active
            try:
                service = cls.get_model().objects.get(id=service_id, is_active=True)
            except cls.get_model().DoesNotExist:
                logger.warning(
                    f"Attempt to review inactive or non-existent service {service_id}",
                )
                from rest_framework.serializers import ValidationError

                raise ValidationError("Service not found or not active")

            # Validate that user has purchased the service
            user_orders = Order.objects.filter(
                user=user,
                _status="confirmed",
                _payment_status="paid",
                items__service=service,
            )

            if not user_orders.exists():
                logger.warning(
                    f"User {user.id} attempted to review service {service_id} without purchase",
                )
                from rest_framework.serializers import ValidationError

                raise ValidationError(
                    "You can only review services you have purchased and received",
                )

            # Validate rating and text
            validation_data = {"rating": rating, "text": text}

            # Validate rating
            from utils.validation_utils import validate_rating

            try:
                validation_data["rating"] = validate_rating(validation_data["rating"])
            except Exception as e:
                logger.error(f"Invalid rating: {e!s}")
                from rest_framework.serializers import ValidationError

                raise ValidationError(f"Invalid rating: {e!s}")

            # Validate text length
            from utils.validation_utils import validate_text_length

            try:
                validation_data["text"] = validate_text_length(
                    validation_data["text"],
                    min_length=1,
                    max_length=1000,
                    field_name="Review text",
                )
            except Exception as e:
                logger.error(f"Invalid review text: {e!s}")
                from rest_framework.serializers import ValidationError

                raise ValidationError(f"Invalid review text: {e!s}")

            # Create review
            with transaction.atomic():
                review, created = Review.objects.get_or_create(
                    service=service,
                    user=user,
                    defaults={
                        "rating": validation_data["rating"],
                        "text": validation_data["text"],
                    },
                )

                if not created:
                    # Update existing review
                    review.rating = validation_data["rating"]
                    review.text = validation_data["text"]
                    review.save()

                # Send review notification email
                if created:
                    try:
                        EmailService.send_review_notification_email(review)
                    except Exception as e:
                        # Log the error but don't fail the operation
                        logger.error(f"Failed to send review notification email: {e}")

                logger.info(
                    f"Review {'created' if created else 'updated'} for service {service_id} by user {user.id}",
                )

                return review
        except Exception as e:
            logger.error(
                f"Error creating/updating review for service {service_id} by user {user.id}: {e}",
            )
            raise
