from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@extend_schema(
    responses={200: {"type": "object", "properties": {"debug": {"type": "boolean"}}}},
    description="Get public configuration data",
)
@api_view(["GET"])
@permission_classes([AllowAny])
def public_config_view(request):
    """
    Returns public-facing configuration variables that are safe to expose to the frontend.

    Business Value (Marketing Principle): According to Philip Kotler's marketing principles,
    transparency in platform capabilities enhances customer trust and engagement. This endpoint
    allows for dynamic configuration distribution, which supports agile customer experience
    adaptation based on real-time parameters.

    Security Approach (CSE Principle): Following defensive programming principles,
    we only expose explicitly whitelisted configuration values to prevent sensitive
    information leakage. This follows the principle of least privilege in information exposure.
    """
    # Define which settings are safe to expose to the frontend
    public_config = {
        "FRONTEND_URL": getattr(settings, "FRONTEND_URL", ""),
        "BACKEND_URL": getattr(settings, "BACKEND_URL", ""),
        "DEBUG": getattr(settings, "DEBUG", False),
        "ALLOWED_HOSTS": getattr(settings, "ALLOWED_HOSTS", []),
        "SSLCOMMERZ_IS_SANDBOX": getattr(settings, "SSLCOMMERZ_IS_SANDBOX", True),
        "CACHE_TTL": getattr(settings, "CACHE_TTL", 900),  # Default to 15 minutes
    }

    return Response(
        {
            "success": True,
            "data": public_config,
            "message": "Public configuration retrieved successfully",
        }
    )
