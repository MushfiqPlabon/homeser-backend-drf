from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from services.models import Service


class ToggleServiceAvailabilityView(APIView):
    """Toggle service availability"""

    permission_classes = [IsAuthenticated]

    def patch(self, request, service_id):
        try:
            service = Service.objects.get(id=service_id, owner=request.user)
        except Service.DoesNotExist:
            return Response(
                {"error": "Service not found"}, status=status.HTTP_404_NOT_FOUND
            )

        service.is_active = not service.is_active
        service.save()

        return Response(
            {
                "message": f"Service {'activated' if service.is_active else 'deactivated'}",
                "is_active": service.is_active,
            }
        )
