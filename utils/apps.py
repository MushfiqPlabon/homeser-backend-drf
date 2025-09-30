# utils/apps.py
# App configuration for the utils package

from django.apps import AppConfig
from django.conf import settings


class UtilsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "utils"

    def ready(self):
        # Import here to avoid circular imports
        import utils.populate_advanced_structures
        import utils.signals  # Import signals

        # Only populate structures in production or when explicitly requested
        if not settings.DEBUG or getattr(
            settings, "POPULATE_ADVANCED_STRUCTURES_ON_STARTUP", False,
        ):
            try:
                utils.populate_advanced_structures.populate_all_advanced_structures()
            except Exception as e:
                # Log error but don't crash the application
                import logging

                logger = logging.getLogger(__name__)
                logger.error(f"Error populating advanced structures on startup: {e}")
