from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from orders.models import Order


class AddOrderNotesView(APIView):
    """Add notes to an order"""

    permission_classes = [IsAuthenticated]

    def patch(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id, user=request.user)
            notes = request.data.get("notes", "")
            # Store notes in a JSON field or text field
            if hasattr(order, "notes"):
                order.notes = notes
                order.save()
            return Response({"message": "Notes added successfully"})
        except Order.DoesNotExist:
            return Response(
                {"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND
            )
