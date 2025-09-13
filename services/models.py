from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from cloudinary.models import CloudinaryField
from django.utils.text import slugify

User = get_user_model()


class ServiceCategory(models.Model):
    """Service categories like Cleaning, Plumbing, etc."""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)
    icon = CloudinaryField("image", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Service Categories"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Service(models.Model):
    """Individual services offered"""

    name = models.CharField(max_length=200, db_index=True)
    slug = models.SlugField(unique=True, blank=True)
    category = models.ForeignKey(
        ServiceCategory, on_delete=models.CASCADE, related_name="services"
    )
    short_desc = models.CharField(max_length=300)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2, db_index=True)
    image = models.ImageField(upload_to="services/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def avg_rating(self):
        """Calculate average rating for this service"""
        # Prioritize pre-calculated (annotated) value from queryset for efficiency.
        # This avoids an extra database query if the value is already available.
        if hasattr(self, "avg_rating_val") and self.avg_rating_val is not None:
            return round(self.avg_rating_val, 1)
        # Fallback: If not annotated, perform a database query to calculate.
        # This is less efficient, especially in list views.
        reviews = self.reviews.all()
        if reviews:
            return round(sum(review.rating for review in reviews) / len(reviews), 1)
        return 0

    @property
    def review_count(self):
        """Count of reviews for this service"""
        # Prioritize pre-calculated (annotated) value from queryset for efficiency.
        # This avoids an extra database query if the value is already available.
        if hasattr(self, "review_count_val") and self.review_count_val is not None:
            return self.review_count_val
        # Fallback: If not annotated, perform a database query to count.
        # This is less efficient, especially in list views.
        return self.reviews.count()

    @property
    def image_url(self):
        """Get image URL for API responses"""
        if self.image:
            return self.image.url
        return None

    def __str__(self):
        return self.name


class Review(models.Model):
    """Customer reviews for services"""

    service = models.ForeignKey(
        Service, on_delete=models.CASCADE, related_name="reviews"
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reviews")
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("service", "user")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.service.name} ({self.rating}/5)"
