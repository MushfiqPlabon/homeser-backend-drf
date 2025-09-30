# utils/models.py
# Models for the utils package

from django.db import models
from django.utils import timezone


class SearchAnalytics(models.Model):
    """Model to track search analytics data."""

    query = models.CharField(max_length=255, db_index=True)
    language = models.CharField(max_length=10, default="en", db_index=True)
    results_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["query", "language"]),
            models.Index(fields=["created_at", "language"]),
        ]

    def __str__(self):
        return f"Search: {self.query} ({self.language}) - {self.results_count} results"


class PopularSearch(models.Model):
    """Model to track popular search queries."""

    query = models.CharField(max_length=255, db_index=True)
    language = models.CharField(max_length=10, default="en", db_index=True)
    search_count = models.IntegerField(default=1)
    last_searched = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-search_count"]
        indexes = [
            models.Index(fields=["query", "language"]),
            models.Index(fields=["search_count"]),
            models.Index(fields=["last_searched"]),
        ]
        unique_together = ["query", "language"]

    def __str__(self):
        return f"Popular Search: {self.query} ({self.language}) - {self.search_count} times"
