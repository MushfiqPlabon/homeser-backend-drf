# utils/error_tracking_middleware.py
# Django middleware for error tracking and logging

import json
import logging
import time
import traceback
from datetime import datetime, timedelta

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class ErrorTrackingMiddleware(MiddlewareMixin):
    """
    Middleware for tracking and logging errors in Django applications.
    Provides comprehensive error context and integrates with existing logging.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)

    def process_request(self, request):
        """Process incoming request and set up tracking context."""
        request._error_tracking_start_time = time.time()
        request._error_tracking_context = {
            "method": request.method,
            "path": request.path,
            "user_agent": request.META.get("HTTP_USER_AGENT", ""),
            "remote_addr": self.get_client_ip(request),
            "user_id": (
                getattr(request.user, "id", None)
                if hasattr(request, "user") and request.user.is_authenticated
                else None
            ),
            "session_key": (
                request.session.session_key if hasattr(request, "session") else None
            ),
            "timestamp": datetime.now().isoformat(),
        }

    def process_exception(self, request, exception):
        """Process unhandled exceptions and log them with context."""
        try:
            error_data = self.build_error_data(request, exception)
            self.log_error(error_data)
            self.cache_error(error_data)

            # Return JSON response for API endpoints
            if request.path.startswith("/api/"):
                return JsonResponse(
                    {
                        "success": False,
                        "error": {
                            "code": "INTERNAL_ERROR",
                            "message": "An internal server error occurred",
                            "details": str(exception) if settings.DEBUG else None,
                        },
                        "timestamp": datetime.now().isoformat(),
                    },
                    status=500,
                )

        except Exception as e:
            # Fallback logging if error tracking itself fails
            logger.error(f"Error in error tracking middleware: {e}")
            logger.error(f"Original exception: {exception}")

        return None  # Let Django handle the exception normally

    def process_response(self, request, response):
        """Process response and track performance metrics."""
        if hasattr(request, "_error_tracking_start_time"):
            duration = time.time() - request._error_tracking_start_time

            # Track slow requests
            if duration > 5.0:  # 5 second threshold
                self.log_performance_issue(request, duration, response.status_code)

            # Track error responses
            if response.status_code >= 400:
                self.log_error_response(request, response, duration)

        return response

    def build_error_data(self, request, exception):
        """Build comprehensive error data for logging."""
        context = getattr(request, "_error_tracking_context", {})

        error_data = {
            "type": "server_error",
            "exception_type": type(exception).__name__,
            "message": str(exception),
            "traceback": traceback.format_exc(),
            "request_context": context,
            "request_data": self.get_request_data(request),
            "timestamp": datetime.now().isoformat(),
        }

        # Add performance context if available
        if hasattr(request, "_error_tracking_start_time"):
            error_data["duration"] = time.time() - request._error_tracking_start_time

        return error_data

    def get_request_data(self, request):
        """Safely extract request data for logging."""
        try:
            data = {}

            # GET parameters
            if request.GET:
                data["get_params"] = dict(request.GET)

            # POST data (be careful with sensitive data)
            if request.method in ["POST", "PUT", "PATCH"] and hasattr(request, "body"):
                try:
                    if request.content_type == "application/json":
                        body_data = json.loads(request.body.decode("utf-8"))
                        # Filter out sensitive fields
                        filtered_data = self.filter_sensitive_data(body_data)
                        data["body"] = filtered_data
                    elif request.POST:
                        # Filter out sensitive fields from POST data
                        filtered_post = self.filter_sensitive_data(dict(request.POST))
                        data["post_params"] = filtered_post
                except (json.JSONDecodeError, UnicodeDecodeError):
                    data["body"] = "<Unable to decode request body>"

            # Headers (filter sensitive ones)
            headers = {}
            for key, value in request.META.items():
                if key.startswith("HTTP_") and key not in [
                    "HTTP_AUTHORIZATION",
                    "HTTP_COOKIE",
                ]:
                    headers[key] = value
            data["headers"] = headers

            return data
        except Exception as e:
            logger.warning(f"Failed to extract request data: {e}")
            return {"error": "Failed to extract request data"}

    def filter_sensitive_data(self, data):
        """Filter out sensitive data from request data."""
        if not isinstance(data, dict):
            return data

        sensitive_fields = [
            "password",
            "token",
            "secret",
            "key",
            "authorization",
            "csrf_token",
            "csrfmiddlewaretoken",
            "api_key",
        ]

        filtered = {}
        for key, value in data.items():
            if any(sensitive in key.lower() for sensitive in sensitive_fields):
                filtered[key] = "<FILTERED>"
            elif isinstance(value, dict):
                filtered[key] = self.filter_sensitive_data(value)
            else:
                filtered[key] = value

        return filtered

    def get_client_ip(self, request):
        """Get client IP address from request."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip

    def log_error(self, error_data):
        """Log error data using Django's logging system."""
        logger.error(
            f"Server Error: {error_data['exception_type']} - {error_data['message']}",
            extra={
                "error_data": error_data,
                "user_id": error_data["request_context"].get("user_id"),
                "path": error_data["request_context"].get("path"),
                "method": error_data["request_context"].get("method"),
            },
        )

    def log_performance_issue(self, request, duration, status_code):
        """Log performance issues."""
        context = getattr(request, "_error_tracking_context", {})

        performance_data = {
            "type": "performance_issue",
            "duration": duration,
            "status_code": status_code,
            "threshold": 5.0,
            "request_context": context,
            "timestamp": datetime.now().isoformat(),
        }

        logger.warning(
            f"Slow Request: {context.get('method')} {context.get('path')} took {duration:.2f}s",
            extra={"performance_data": performance_data},
        )

        self.cache_error(performance_data)

    def log_error_response(self, request, response, duration):
        """Log error responses (4xx, 5xx)."""
        context = getattr(request, "_error_tracking_context", {})

        error_response_data = {
            "type": "error_response",
            "status_code": response.status_code,
            "duration": duration,
            "request_context": context,
            "timestamp": datetime.now().isoformat(),
        }

        # Try to get response content for API errors
        if request.path.startswith("/api/") and hasattr(response, "content"):
            try:
                content = response.content.decode("utf-8")
                if len(content) < 1000:  # Only log short responses
                    error_response_data["response_content"] = content
            except UnicodeDecodeError:
                pass

        logger.warning(
            f"Error Response: {response.status_code} for {context.get('method')} {context.get('path')}",
            extra={"error_response_data": error_response_data},
        )

    def cache_error(self, error_data):
        """Cache error data for analytics (free tier approach)."""
        try:
            # Use cache to store recent errors for analytics
            cache_key = f"error_tracking:{datetime.now().strftime('%Y-%m-%d-%H')}"

            # Get existing errors for this hour
            cached_errors = cache.get(cache_key, [])

            # Add new error (limit to 100 errors per hour to prevent memory issues)
            if len(cached_errors) < 100:
                cached_errors.append(
                    {
                        "type": error_data["type"],
                        "message": error_data.get("message", ""),
                        "path": error_data.get("request_context", {}).get("path", ""),
                        "user_id": error_data.get("request_context", {}).get("user_id"),
                        "timestamp": error_data["timestamp"],
                        "status_code": error_data.get("status_code"),
                        "duration": error_data.get("duration"),
                    }
                )

                # Cache for 24 hours
                cache.set(cache_key, cached_errors, 86400)

        except Exception as e:
            logger.warning(f"Failed to cache error data: {e}")


class ErrorAnalyticsMiddleware(MiddlewareMixin):
    """
    Lightweight middleware for error analytics and rate limiting.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)

    def process_response(self, request, response):
        """Track error rates and implement basic rate limiting."""
        if response.status_code >= 400:
            self.track_error_rate(request, response.status_code)

            # Implement basic rate limiting for error responses
            if response.status_code == 429:
                self.handle_rate_limit(request)

        return response

    def track_error_rate(self, request, status_code):
        """Track error rates by endpoint and user."""
        try:
            # Track by endpoint
            endpoint_key = f"error_rate:endpoint:{request.path}:{datetime.now().strftime('%Y-%m-%d-%H')}"
            cache.set(endpoint_key, cache.get(endpoint_key, 0) + 1, 3600)

            # Track by user if authenticated
            if hasattr(request, "user") and request.user.is_authenticated:
                user_key = f"error_rate:user:{request.user.id}:{datetime.now().strftime('%Y-%m-%d-%H')}"
                cache.set(user_key, cache.get(user_key, 0) + 1, 3600)

            # Track by status code
            status_key = f"error_rate:status:{status_code}:{datetime.now().strftime('%Y-%m-%d-%H')}"
            cache.set(status_key, cache.get(status_key, 0) + 1, 3600)

        except Exception as e:
            logger.warning(f"Failed to track error rate: {e}")

    def handle_rate_limit(self, request):
        """Handle rate limiting scenarios."""
        try:
            # Log rate limiting events
            logger.warning(
                f"Rate limit exceeded for {self.get_client_ip(request)} on {request.path}",
                extra={
                    "rate_limit_event": {
                        "ip": self.get_client_ip(request),
                        "path": request.path,
                        "user_id": (
                            getattr(request.user, "id", None)
                            if hasattr(request, "user")
                            and request.user.is_authenticated
                            else None
                        ),
                        "timestamp": datetime.now().isoformat(),
                    }
                },
            )
        except Exception as e:
            logger.warning(f"Failed to handle rate limit logging: {e}")

    def get_client_ip(self, request):
        """Get client IP address from request."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip


# Utility functions for error analytics


def get_error_analytics(hours=24):
    """Get error analytics for the specified number of hours."""
    try:
        analytics = {
            "total_errors": 0,
            "errors_by_hour": {},
            "errors_by_type": {},
            "errors_by_endpoint": {},
            "errors_by_status": {},
        }

        now = datetime.now()

        for hour_offset in range(hours):
            hour_key = (now - timedelta(hours=hour_offset)).strftime("%Y-%m-%d-%H")

            # Get cached errors for this hour
            cache_key = f"error_tracking:{hour_key}"
            cached_errors = cache.get(cache_key, [])

            analytics["errors_by_hour"][hour_key] = len(cached_errors)
            analytics["total_errors"] += len(cached_errors)

            # Aggregate by type, endpoint, and status
            for error in cached_errors:
                error_type = error.get("type", "unknown")
                analytics["errors_by_type"][error_type] = (
                    analytics["errors_by_type"].get(error_type, 0) + 1
                )

                endpoint = error.get("path", "unknown")
                analytics["errors_by_endpoint"][endpoint] = (
                    analytics["errors_by_endpoint"].get(endpoint, 0) + 1
                )

                status_code = error.get("status_code")
                if status_code:
                    analytics["errors_by_status"][str(status_code)] = (
                        analytics["errors_by_status"].get(str(status_code), 0) + 1
                    )

        return analytics

    except Exception as e:
        logger.error(f"Failed to get error analytics: {e}")
        return {
            "total_errors": 0,
            "errors_by_hour": {},
            "errors_by_type": {},
            "errors_by_endpoint": {},
            "errors_by_status": {},
            "error": str(e),
        }


def clear_error_cache():
    """Clear all cached error data."""
    try:
        # This is a simplified approach - in production you might want to be more selective
        pass

        # Clear error tracking cache keys
        now = datetime.now()
        for hour_offset in range(48):  # Clear last 48 hours
            hour_key = (now - timedelta(hours=hour_offset)).strftime("%Y-%m-%d-%H")
            cache_key = f"error_tracking:{hour_key}"
            cache.delete(cache_key)

        return True
    except Exception as e:
        logger.error(f"Failed to clear error cache: {e}")
        return False
