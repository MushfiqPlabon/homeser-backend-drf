# api/__init__.py
# Make sure the utils module is accessible

# Expose utils module
from . import utils  # noqa: F401

default_app_config = "api.apps.ApiConfig"
