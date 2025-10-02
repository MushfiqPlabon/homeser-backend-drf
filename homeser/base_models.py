from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.text import slugify
from model_utils.managers import QueryManager
from model_utils.models import TimeStampedModel


class BaseModel(TimeStampedModel, models.Model):
    """Abstract base model with common fields and functionality"""

    objects = QueryManager()

    class Meta:
        abstract = True

    def __str__(self):
        # Generic string representation
        if hasattr(self, "name"):
            return self.name
        if hasattr(self, "title"):
            return self.title
        return f"{self.__class__.__name__} #{self.pk}"

    def save(self, *args, **kwargs):
        """Override save to add generic functionality if needed."""
        super().save(*args, **kwargs)


class SluggedModel(TimeStampedModel, models.Model):
    """Abstract base model with auto-generated slug field"""

    slug = models.SlugField(unique=True, blank=True)

    objects = QueryManager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        # Auto-generate slug from name field if not provided
        if not self.slug and hasattr(self, "name"):
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class NamedSluggedModel(TimeStampedModel, models.Model):
    """Abstract base model with name and slug fields"""

    name = models.CharField(max_length=200, db_index=True)
    slug = models.SlugField(unique=True, blank=True)

    objects = QueryManager()

    class Meta:
        abstract = True

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Auto-generate slug from name field if not provided
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class BaseReview(TimeStampedModel, models.Model):
    """Abstract base model for reviews with sentiment analysis"""

    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, db_index=True)
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        db_index=True,
    )
    text = models.TextField()
    # Sentiment analysis fields
    sentiment_polarity = models.FloatField(default=0.0, db_index=True)
    sentiment_subjectivity = models.FloatField(default=0.0)
    sentiment_label = models.CharField(max_length=20, default="neutral", db_index=True)
    # Moderation fields
    is_flagged = models.BooleanField(default=False, db_index=True)
    flagged_reason = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        abstract = True
        ordering = ["-created", "-modified"]

    def save(self, *args, **kwargs):
        # Perform sentiment analysis before saving
        if self.text:
            try:
                from utils.sentiment_analysis import SentimentAnalysisService

                sentiment = SentimentAnalysisService.analyze_sentiment(self.text)
                self.sentiment_polarity = sentiment["polarity"]
                self.sentiment_subjectivity = sentiment["subjectivity"]
                self.sentiment_label = sentiment["sentiment"]

                # Automatically flag reviews with very negative sentiment
                if self.sentiment_polarity < -0.6:
                    self.is_flagged = True
                    self.flagged_reason = "Very negative sentiment detected"
            except Exception as e:
                import logging

                logger = logging.getLogger(__name__)
                logger.error(
                    f"Error performing sentiment analysis for review {self.id if self.id else 'new'}: {e}",
                )
                # Set default values in case of error
                self.sentiment_polarity = 0.0
                self.sentiment_subjectivity = 0.0
                self.sentiment_label = "neutral"
        super().save(*args, **kwargs)


class ServiceType(models.TextChoices):
    """Choices for different service types"""

    STANDARD = "standard", "Standard Service"
    PREMIUM = "premium", "Premium Service"
    CUSTOM = "custom", "Custom Service"


class OrderType(models.TextChoices):
    """Choices for different order types"""

    STANDARD = "standard", "Standard Order"
    EXPRESS = "express", "Express Order"
    SCHEDULED = "scheduled", "Scheduled Order"
