from django.db import models

from homeser.base_models import BaseModel


class Favorite(BaseModel):
    """User favorites for services"""

    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="favorites"
    )
    service = models.ForeignKey(
        "services.Service", on_delete=models.CASCADE, related_name="favorited_by"
    )

    class Meta:
        unique_together = ("user", "service")
        ordering = ["-created"]

    def __str__(self):
        return f"{self.user.email} - {self.service.name}"
