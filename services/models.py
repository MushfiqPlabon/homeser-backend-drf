from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Optional

from cloudinary.models import CloudinaryField
from django.conf import settings
from django.db import models
from django.db.models.base import ModelBase
from django_lifecycle import (AFTER_CREATE, AFTER_DELETE, AFTER_UPDATE,
                              LifecycleModel, hook)
from model_utils.managers import QueryManager

from homeser.base_models import BaseModel, BaseReview, NamedSluggedModel
from utils.validation import (validate_image_aspect_ratio,
                              validate_image_file_extension,
                              validate_image_file_size,
                              validate_positive_price, validate_text_length)


def validate_service_description(value):
    return validate_text_length(
        value,
        min_length=20,
        max_length=2000,
        field_name="Description",
    )


def validate_service_short_desc(value):
    return validate_text_length(
        value,
        min_length=10,
        max_length=300,
        field_name="Short description",
    )


def validate_base_service_short_desc(value):
    return validate_text_length(
        value,
        min_length=10,
        max_length=300,
        field_name="Short description",
    )


def validate_base_service_description(value):
    return validate_text_length(
        value,
        min_length=20,
        max_length=2000,
        field_name="Description",
    )


class ServiceCategory(NamedSluggedModel):
    """Service categories like Cleaning, Plumbing, etc."""

    description = models.TextField(blank=True)
    icon = CloudinaryField("image", blank=True, null=True)

    objects = QueryManager()

    class Meta:
        verbose_name_plural = "Service Categories"


class Service(LifecycleModel, NamedSluggedModel):
    """Individual services offered"""

    # Remove name field as it's now in NamedSluggedModel
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="services",
        db_index=True,
    )
    category = models.ForeignKey(
        ServiceCategory,
        on_delete=models.CASCADE,
        related_name="services",
        db_index=True,
    )

    short_desc = models.CharField(
        max_length=300,
        db_index=True,
        validators=[validate_service_short_desc],
    )
    description = models.TextField(
        validators=[validate_service_description],
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        db_index=True,
        validators=[validate_positive_price],
    )
    image = models.ImageField(
        upload_to="services/",
        blank=True,
        null=True,
        validators=[
            validate_image_file_extension,
            validate_image_file_size,
            validate_image_aspect_ratio,
        ],
    )
    is_active = models.BooleanField(default=True, db_index=True)

    # Cached ratings to optimize queries and reduce JOINs
    cached_avg_rating = models.DecimalField(
        max_digits=3, decimal_places=2, default=0, db_index=True
    )
    cached_rating_count = models.PositiveIntegerField(default=0, db_index=True)

    objects = QueryManager()

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["category", "is_active"]),
            models.Index(fields=["price", "is_active"]),
            models.Index(fields=["name", "category"]),  # for name+category searches
            models.Index(
                fields=["is_active", "created"],
            ),  # for active services ordered by creation date
            models.Index(
                fields=["price", "category", "is_active"],
            ),  # for complex price/category queries
            models.Index(
                fields=["is_active", "name"]
            ),  # for active services sorted by name
            models.Index(
                fields=["is_active", "price"]
            ),  # for active services sorted by price
            # Indexes for cached ratings
            models.Index(
                fields=["cached_avg_rating", "is_active"]
            ),  # for rating-based queries
            models.Index(
                fields=["cached_rating_count", "is_active"]
            ),  # for popularity queries
            models.Index(
                fields=["is_active", "cached_avg_rating"]
            ),  # for active services sorted by rating
            models.Index(
                fields=["is_active", "cached_rating_count"]
            ),  # for active services sorted by popularity
        ]

    # Remove __str__ method as it's now in NamedSluggedModel

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)



    @property
    def avg_rating(self):
        """Get the average rating for this service."""
        # Use cached value for O(1) access
        return float(self.cached_avg_rating) if self.cached_avg_rating is not None else 0

    @property
    def review_count(self):
        """Get the number of reviews for this service."""
        # Use cached value for O(1) access
        return self.cached_rating_count or 0

    @property
    def image_url(self) -> str | None:
        """Get the URL of the service image if it exists."""
        if self.image:
            return self.image.url
        return None

    image_url.fget.__annotations__["return"] = Optional[str]

    def update_rating_cache(self):
        """Public method to refresh rating cache"""
        # Refresh cache by calling the update method
        self.update_rating_aggregation()
        # Return the updated ratings
        return self.avg_rating

    def save(self, *args, **kwargs):
        """Save the service and update aggregated ratings."""
        # Validation is handled by field validators, so we just call the parent save
        super().save(*args, **kwargs)

        # For Vercel compatibility, we're not using MeiliSearch
        # PostgreSQL full-text search will automatically work with the updated data
        # The search functionality will use database queries instead of a search index

    def delete(self, *args, **kwargs):
        """Delete the service."""
        # For Vercel compatibility, we're not using MeiliSearch
        # Call the parent delete method directly
        return super().delete(*args, **kwargs)

    def update_rating_aggregation(self):
        """Update the ServiceRatingAggregation and cached ratings."""
        try:
            # Ensure the service instance is properly saved before proceeding
            if not self.pk:
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(
                    f"Service {self} does not have a primary key yet, skipping rating aggregation update"
                )
                return

            from django.db.models import Avg, Count

            # Calculate the new average and count
            aggregation = Review.objects.filter(service=self).aggregate(
                avg_rating=Avg("rating"),
                count=Count("id"),
            )

            # Update the cached fields on the service itself for O(1) access
            new_avg_rating = (
                float(aggregation["avg_rating"])
                if aggregation["avg_rating"] is not None
                else 0
            )
            new_rating_count = aggregation["count"] or 0
            
            # Use direct DB update to bypass model lifecycle hooks and prevent recursion
            self.__class__.objects.filter(pk=self.pk).update(
                cached_avg_rating=new_avg_rating,
                cached_rating_count=new_rating_count
            )
            
            # Update the in-memory instance to reflect the changes
            self.cached_avg_rating = new_avg_rating
            self.cached_rating_count = new_rating_count

            # Get or create the ServiceRatingAggregation object
            rating_aggregation, created = (
                ServiceRatingAggregation.objects.get_or_create(
                    service=self,
                    defaults={
                        "average": new_avg_rating,  # Use the new values
                        "count": new_rating_count,
                    },
                )
            )

            # If it already existed, update it
            if not created:
                rating_aggregation.average = new_avg_rating
                rating_aggregation.count = new_rating_count
                rating_aggregation.save()

            # Use django-cachalot for automatic cache invalidation
            from cachalot.api import invalidate as cachalot_invalidate

            # Invalidate cache for the specific service and related data
            cachalot_invalidate("services.Service")
            cachalot_invalidate("services.Review")
        except Exception as e:
            # Log the error but don't prevent the operation from completing
            import logging

            logger = logging.getLogger(__name__)
            logger.error(
                f"Error updating rating aggregation for service {self.id}: {e}"
            )

    @hook(AFTER_CREATE)
    @hook(AFTER_UPDATE)
    @hook(AFTER_DELETE)
    def update_rating_aggregation_hook(self):
        """Hook method that triggers the rating aggregation update."""
        self.update_rating_aggregation()

    @hook(AFTER_CREATE)
    def update_advanced_data_structures_on_create(self):
        """Update advanced data structures when a service is created."""
        from cachalot.api import invalidate as cachalot_invalidate

        # Use django-cachalot for automatic cache invalidation
        cachalot_invalidate(Service)

        # Also update our advanced data structures
        try:
            # Import here to avoid circular imports
            from utils.advanced_data_structures import (service_bloom_filter,
                                                        service_hash_table,
                                                        service_name_trie)

            # Update individual data structures for the service
            service_data = {
                "id": self.id,
                "name": self.name,
                "description": self.description,
                "price": float(self.price),
                "image_url": self.image_url,
                "avg_rating": float(self.avg_rating) or 0,
                "review_count": self.review_count or 0,
            }

            # Update hash table
            service_hash_table.update_service_data(self.id, service_data)

            # Update bloom filter to include this new service
            service_bloom_filter.add(self.id)

            # Update trie
            service_name_trie.update_service_data(
                self.name,
                {
                    "id": self.id,
                    "description": getattr(self, "short_desc", ""),
                    "price": float(self.price),
                    "avg_rating": float(self.avg_rating) if self.avg_rating else 0.0,
                },
            )

            # Note: For segment tree, we would need to know the index of the service
            # This is more complex and would require maintaining a mapping
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(
                f"Error updating advanced data structures for service {self.id}: {e}",
            )

    @hook(AFTER_UPDATE)
    def update_advanced_data_structures_on_update(self):
        """Update advanced data structures when a service is updated."""
        from cachalot.api import invalidate as cachalot_invalidate

        # Use django-cachalot for automatic cache invalidation
        cachalot_invalidate(Service)

        # Also update our advanced data structures
        try:
            # Import here to avoid circular imports
            from utils.advanced_data_structures import (service_hash_table,
                                                        service_name_trie)

            # Update individual data structures for the service
            service_data = {
                "id": self.id,
                "name": self.name,
                "description": self.description,
                "price": float(self.price),
                "image_url": self.image_url,
                "avg_rating": float(self.avg_rating) or 0,
                "review_count": self.review_count or 0,
            }

            # Update hash table
            service_hash_table.update_service_data(self.id, service_data)

            # Update trie
            service_name_trie.update_service_data(
                self.name,
                {
                    "id": self.id,
                    "description": getattr(self, "short_desc", ""),
                    "price": float(self.price),
                    "avg_rating": float(self.avg_rating) if self.avg_rating else 0.0,
                },
            )

            # Note: For segment tree, we would need to know the index of the service
            # This is more complex and would require maintaining a mapping
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(
                f"Error updating advanced data structures for service {self.id}: {e}",
            )

    @hook(AFTER_DELETE)
    def update_advanced_data_structures_on_delete(self):
        """Handle advanced data structures when a service is deleted."""
        from cachalot.api import invalidate as cachalot_invalidate

        # Use django-cachalot for automatic cache invalidation
        cachalot_invalidate(Service)

        # For deleted services, we primarily need to update cache invalidation
        # Bloom filter doesn't need explicit removal (false positives are acceptable)
        # Hash table and trie entries might need to be removed, but this is complex after deletion
        try:
            # Import here to avoid circular imports
            from utils.advanced_data_structures import service_hash_table

            # Remove from hash table if possible (using the ID before it's gone)
            service_hash_table.delete(self.id)
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(
                f"Error handling advanced data structures for deleted service {self.id}: {e}",
            )


class Favorite(BaseModel):
    """User favorites for services"""

    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="favorites"
    )
    service = models.ForeignKey(
        "Service", on_delete=models.CASCADE, related_name="favorited_by"
    )

    class Meta:
        unique_together = ("user", "service")
        ordering = ["-created"]

    def __str__(self):
        return f"{self.user.email} - {self.service.name}"


class Review(BaseReview):
    """Customer reviews for services with sentiment analysis"""

    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name="reviews",
        db_index=True,
    )
    # user, rating, text, sentiment_polarity, sentiment_subjectivity, sentiment_label,
    # is_flagged, flagged_reason, created, modified are inherited from BaseReview

    objects = QueryManager()

    class Meta(BaseReview.Meta):
        unique_together = ("service", "user")
        # Remove ordering as it's defined in BaseReview.Meta

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.service.name} ({self.rating}/5)"

    def save(self, *args, **kwargs):
        # Call parent save method for sentiment analysis
        super().save(*args, **kwargs)

    @hook(AFTER_CREATE)
    @hook(AFTER_UPDATE)
    @hook(AFTER_DELETE)
    def update_service_rating(self):
        """Update the service rating when a review is created, updated, or deleted."""
        # Trigger the service's rating aggregation update
        # We call it directly on the service instance
        self.service.update_rating_aggregation()


class ServiceRatingAggregation(models.Model):
    """Precomputed rating aggregations for services"""

    service = models.OneToOneField(
        Service,
        on_delete=models.CASCADE,
        related_name="rating_aggregation",
    )
    average = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    count = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    objects = QueryManager()

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["average"], name="rating_aggr_average_idx"),
            models.Index(fields=["updated_at"], name="rating_aggr_updated_at_idx"),
            models.Index(
                fields=["average", "updated_at"], name="rating_aggr_avg_updated_idx"
            ),
        ]

    def __str__(self):
        return f"{self.service.name} - Avg: {self.average}, Count: {self.count}"


# Custom metaclass that properly combines ModelBase and ABC functionality
class ABCModelBase(ModelBase):
    """
    Metaclass that properly combines ModelBase and ABC functionality.
    This allows abstract base classes to work with Django models.
    """

    def __new__(cls, name, bases, namespace, **kwargs):
        # Call the ModelBase.__new__ to handle Django model creation
        result = super().__new__(cls, name, bases, namespace, **kwargs)

        # Apply ABC behavior by initializing ABC on the result class
        ABC.__init__(result)

        return result


class BaseService(NamedSluggedModel, metaclass=ABCModelBase):
    """Abstract base class for all service types with polymorphic behavior"""

    SERVICE_TYPES = [
        ("basic", "Basic Service"),
        ("premium", "Premium Service"),
        ("specialized", "Specialized Service"),
    ]

    service_type = models.CharField(
        max_length=20,
        choices=SERVICE_TYPES,
        default="basic",
    )
    category = models.ForeignKey(
        ServiceCategory,
        on_delete=models.CASCADE,
        related_name="%(class)s_services",
        db_index=True,
    )
    short_desc = models.CharField(
        max_length=300,
        db_index=True,
        validators=[validate_base_service_short_desc],
    )
    description = models.TextField(
        validators=[validate_base_service_description],
    )
    base_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        db_index=True,
        validators=[validate_positive_price],
    )
    is_active = models.BooleanField(default=True, db_index=True)

    objects = QueryManager()

    class Meta:
        abstract = True

    @abstractmethod
    def calculate_price(self):
        """Abstract method to calculate service price - to be implemented by subclasses"""

    def get_service_features(self):
        """Get service features based on type"""
        return []

    def __str__(self):
        return f"{self.name} ({self.get_service_type_display()})"

    def save(self, *args, **kwargs):
        """Validate and format fields before saving."""
        if self.short_desc:
            self.short_desc = validate_text_length(
                self.short_desc,
                min_length=10,
                max_length=300,
                field_name="Short description",
            )
        if self.description:
            self.description = validate_text_length(
                self.description,
                min_length=20,
                max_length=2000,
                field_name="Description",
            )
        if self.base_price:
            self.base_price = validate_positive_price(self.base_price)
        super().save(*args, **kwargs)


class BasicService(BaseService):
    """Basic service with fixed pricing"""

    class Meta:
        db_table = "services_basicservice"

    def calculate_price(self):
        """Basic service has fixed price"""
        return self.base_price

    def get_service_features(self):
        """Basic service features"""
        return ["Standard service", "Basic support"]


class PremiumService(BaseService):
    """Premium service with additional features"""

    priority_support = models.BooleanField(default=False)
    extended_warranty_months = models.IntegerField(default=0)

    class Meta:
        db_table = "services_premiumservice"

    def calculate_price(self):
        """Premium service with additional cost factors"""
        price = self.base_price
        if self.priority_support:
            price += Decimal("100.00")
        if self.extended_warranty_months > 0:
            price += Decimal(str(self.extended_warranty_months * 50))
        return price

    def get_service_features(self):
        """Premium service features"""
        features = ["Priority service", "Extended warranty"]
        if self.priority_support:
            features.append("24/7 Priority support")
        return features


class SpecializedService(BaseService):
    """Specialized service with custom pricing"""

    complexity_factor = models.DecimalField(max_digits=3, decimal_places=2, default=1.0)
    required_equipment_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.0,
    )

    class Meta:
        db_table = "services_specializedservice"

    def calculate_price(self):
        """Specialized service with complexity-based pricing"""
        return self.base_price * self.complexity_factor + self.required_equipment_cost

    def get_service_features(self):
        """Specialized service features"""
        return ["Customized solution", "Specialized equipment", "Expert technician"]


class ServiceFactory:
    """Factory for creating different types of services"""

    @staticmethod
    def create_service(service_type, **kwargs):
        """Create a service of the specified type"""
        if service_type == "basic":
            return BasicService(**kwargs)
        if service_type == "premium":
            return PremiumService(**kwargs)
        if service_type == "specialized":
            return SpecializedService(**kwargs)
        raise ValueError(f"Unknown service type: {service_type}")

    @staticmethod
    def create_from_data(data):
        """Create a service from data dictionary"""
        service_type = data.get("service_type", "basic")
        return ServiceFactory.create_service(service_type, **data)
