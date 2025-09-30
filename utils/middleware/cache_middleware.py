# utils/middleware/cache_middleware.py
# Middleware for advanced caching strategies

import time

from django.core.cache import cache
from django.utils.deprecation import MiddlewareMixin

from utils.advanced_data_structures import service_bloom_filter


class AdvancedCacheMiddleware(MiddlewareMixin):
    """Middleware for advanced caching strategies.
    Implements cache warming and monitoring.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)

    def process_request(self, request):
        # Add timing to request for performance monitoring
        request.start_time = time.time()

        # Check if this is a service request and if service exists in Bloom filter
        if request.path.startswith("/api/services/"):
            # Extract service ID from path if present
            path_parts = request.path.strip("/").split("/")
            if len(path_parts) >= 3 and path_parts[1] == "services":
                try:
                    service_id = int(path_parts[2])
                    # If service doesn't exist in Bloom filter, we can return early
                    if not service_bloom_filter.check(service_id):
                        # Note: We don't return here as we want to let the view handle the 404
                        pass
                except (ValueError, IndexError):
                    pass

    def process_response(self, request, response):
        # Calculate response time
        if hasattr(request, "start_time"):
            response_time = time.time() - request.start_time
            # Store response time in cache for monitoring
            cache_key = f"response_time:{request.path}"
            cache.set(cache_key, response_time, timeout=300)  # Store for 5 minutes

        return response
