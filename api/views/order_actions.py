from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from orders.models import Order


class CancelOrderView(APIView):
    """Cancel pending order"""

    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id, user=request.user)
        except Order.DoesNotExist:
            return Response(
                {"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND
            )

        if order.status not in ["pending", "confirmed"]:
            return Response(
                {"error": "Only pending/confirmed orders can be cancelled"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        order.status = "cancelled"
        order.save()

        return Response(
            {"message": "Order cancelled successfully", "status": order.status}
        )


class RequestRefundView(APIView):
    """Request refund for completed order"""

    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id, user=request.user)
        except Order.DoesNotExist:
            return Response(
                {"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND
            )

        if order.status != "completed":
            return Response(
                {"error": "Only completed orders can be refunded"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        reason = request.data.get("reason", "")
        if not reason:
            return Response(
                {"error": "Refund reason required"}, status=status.HTTP_400_BAD_REQUEST
            )

        order.status = "refunded"
        order.save()

        return Response(
            {"message": "Refund requested successfully", "status": order.status}
        )
