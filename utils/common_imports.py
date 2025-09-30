"""Common imports module for frequently used imports across the HomeSer backend.
This module reduces import boilerplate and ensures consistent imports across the codebase.
"""

# Django core imports
# Django REST Framework imports
# Django contrib imports
# Third-party package imports
import logging

from django.conf import settings
from django.contrib.auth import get_user_model

# Local imports

# Configure logger
logger = logging.getLogger(__name__)

# Get user model
User = get_user_model()

# Common constants
DEFAULT_CACHE_TIMEOUT = getattr(settings, "CACHE_TTL", 300)  # Default 5 minutes
