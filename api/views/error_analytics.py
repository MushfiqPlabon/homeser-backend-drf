# api/views/error_analytics.py
# API endpoints for error analytics and monitoring

import logging
from datetime import datetime

from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes

from utils.error_tracking_middleware import (clear_error_cache,
                                             get_error_analytics)
from utils.response_utils import format_error_response, format_success_response

logger = logging.getLogger(__name__)


@method_decorator(staff_member_required, name="dispatch")
class ErrorAnalyticsView(View):
    """
    View for retrieving error analytics data.
    Only accessible to staff members.
    """

    def get(self, request):
        """Get error analytics for the specified time period."""
        try:
            # Get query parameters
            hours = int(request.GET.get("hours", 24))
            hours = min(hours, 168)  # Limit to 1 week maximum

            # Get analytics data
            analytics = get_error_analytics(hours)

            return JsonResponse(
                {
                    "success": True,
                    "data": analytics,
                    "timestamp": datetime.now().isoformat(),
                }
            )

        except ValueError:
            return JsonResponse(
                {
                    "success": False,
                    "error": {
                        "code": "INVALID_PARAMETER",
                        "message": "Invalid hours parameter",
                    },
                },
                status=400,
            )
        except Exception as e:
            logger.error(f"Error retrieving analytics: {e}")
            return JsonResponse(
                {
                    "success": False,
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "Failed to retrieve error analytics",
                    },
                },
                status=500,
            )


@api_view(["POST"])
@permission_classes([permissions.IsAdminUser])
def clear_error_analytics(request):
    """
    Clear all cached error analytics data.
    Only accessible to admin users.
    """
    try:
        success = clear_error_cache()

        if success:
            return format_success_response(
                message="Error analytics data cleared successfully"
            )
        else:
            return format_error_response(
                error_code="CLEAR_FAILED",
                message="Failed to clear error analytics data",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    except Exception as e:
        logger.error(f"Error clearing analytics: {e}")
        return format_error_response(
            error_code="INTERNAL_ERROR",
            message="An error occurred while clearing analytics data",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([permissions.IsAdminUser])
def error_summary(request):
    """
    Get a summary of recent errors for dashboard display.
    """
    try:
        # Get recent analytics
        analytics = get_error_analytics(24)  # Last 24 hours

        # Calculate summary metrics
        total_errors = analytics["total_errors"]
        error_rate = total_errors / 24 if total_errors > 0 else 0  # Errors per hour

        # Get most common error types
        top_error_types = sorted(
            analytics["errors_by_type"].items(), key=lambda x: x[1], reverse=True
        )[:5]

        # Get most problematic endpoints
        top_error_endpoints = sorted(
            analytics["errors_by_endpoint"].items(), key=lambda x: x[1], reverse=True
        )[:5]

        # Calculate error trend (compare with previous 24 hours)
        previous_analytics = get_error_analytics(48)
        previous_24h_errors = previous_analytics["total_errors"] - total_errors

        trend = "stable"
        if total_errors > previous_24h_errors * 1.2:
            trend = "increasing"
        elif total_errors < previous_24h_errors * 0.8:
            trend = "decreasing"

        summary = {
            "total_errors_24h": total_errors,
            "error_rate_per_hour": round(error_rate, 2),
            "trend": trend,
            "top_error_types": [
                {"type": error_type, "count": count}
                for error_type, count in top_error_types
            ],
            "top_error_endpoints": [
                {"endpoint": endpoint, "count": count}
                for endpoint, count in top_error_endpoints
            ],
            "status_code_distribution": analytics["errors_by_status"],
            "last_updated": datetime.now().isoformat(),
        }

        return format_success_response(
            data=summary, message="Error summary retrieved successfully"
        )

    except Exception as e:
        logger.error(f"Error retrieving error summary: {e}")
        return format_error_response(
            error_code="INTERNAL_ERROR",
            message="Failed to retrieve error summary",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([permissions.IsAdminUser])
def health_check(request):
    """
    Health check endpoint that includes error rate information.
    """
    try:
        # Get recent error analytics
        analytics = get_error_analytics(1)  # Last hour
        recent_errors = analytics["total_errors"]

        # Determine health status based on error rate
        if recent_errors == 0:
            health_status = "healthy"
        elif recent_errors <= 5:
            health_status = "warning"
        else:
            health_status = "critical"

        # Check for specific error patterns
        alerts = []
        if recent_errors > 10:
            alerts.append(
                {
                    "type": "high_error_rate",
                    "message": f"High error rate detected: {recent_errors} errors in the last hour",
                    "severity": "high",
                }
            )

        # Check for 5xx errors specifically
        server_errors = sum(
            count
            for status_code, count in analytics["errors_by_status"].items()
            if status_code.startswith("5")
        )

        if server_errors > 0:
            alerts.append(
                {
                    "type": "server_errors",
                    "message": f"{server_errors} server errors detected in the last hour",
                    "severity": "high" if server_errors > 5 else "medium",
                }
            )

        health_data = {
            "status": health_status,
            "timestamp": datetime.now().isoformat(),
            "metrics": {
                "errors_last_hour": recent_errors,
                "server_errors_last_hour": server_errors,
                "error_rate_per_minute": round(recent_errors / 60, 2),
            },
            "alerts": alerts,
        }

        return format_success_response(
            data=health_data, message="Health check completed"
        )

    except Exception as e:
        logger.error(f"Error in health check: {e}")
        return format_error_response(
            error_code="HEALTH_CHECK_FAILED",
            message="Health check failed",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def report_client_error(request):
    """
    Endpoint for clients to report JavaScript errors and other client-side issues.
    """
    try:
        error_data = request.data

        # Validate required fields
        required_fields = ["type", "message", "timestamp"]
        missing_fields = [field for field in required_fields if field not in error_data]

        if missing_fields:
            return format_error_response(
                error_code="MISSING_FIELDS",
                message=f"Missing required fields: {', '.join(missing_fields)}",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Log the client error
        logger.error(
            f"Client Error: {error_data['type']} - {error_data['message']}",
            extra={
                "client_error_data": {
                    **error_data,
                    "user_id": (
                        request.user.id if request.user.is_authenticated else None
                    ),
                    "user_agent": request.META.get("HTTP_USER_AGENT", ""),
                    "remote_addr": request.META.get("REMOTE_ADDR", ""),
                    "server_timestamp": datetime.now().isoformat(),
                }
            },
        )

        return format_success_response(message="Client error reported successfully")

    except Exception as e:
        logger.error(f"Error reporting client error: {e}")
        return format_error_response(
            error_code="REPORT_FAILED",
            message="Failed to report client error",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
