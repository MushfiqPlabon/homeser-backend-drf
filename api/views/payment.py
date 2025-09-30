from django.views.decorators.csrf import csrf_exempt
from rest_framework import permissions, serializers, status
from rest_framework.response import Response

from ..services.payment_service import PaymentService
from ..unified_base_views import (
    UnifiedBaseGenericView,
)


class PaymentIPNView(UnifiedBaseGenericView):
    """Handle SSLCOMMERZ IPN (Instant Payment Notification) and clear cart from Redis"""

    permission_classes = [permissions.AllowAny]
    service_class = PaymentService
    
    class IPNSerializer(serializers.Serializer):
        """Serializer for IPN requests"""
        val_id = serializers.CharField(required=False)
        tran_id = serializers.CharField(required=False)
        
        # Add all the fields that SSLCOMMERZ typically sends
        amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
        store_amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
        bank_tran_id = serializers.CharField(required=False)
        card_type = serializers.CharField(required=False)
        card_no = serializers.CharField(required=False)
        currency_type = serializers.CharField(required=False)
        currency_amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
        issuer_bank = serializers.CharField(required=False)
        issuer_country = serializers.CharField(required=False)
        tran_date = serializers.CharField(required=False)
        emi_inst_status = serializers.CharField(required=False)
        account_details = serializers.CharField(required=False)
    
    serializer_class = IPNSerializer

    @csrf_exempt  # CSRF protection is exempted because this is an external callback (IPN)
    # from the payment gateway, which does not send CSRF tokens.
    def post(self, request, *args, **kwargs):
        """Handle SSLCOMMERZ IPN (Instant Payment Notification) and clear cart from Redis"""
        val_id = request.POST.get("val_id")
        tran_id = request.POST.get("tran_id")

        # Use PaymentService to handle IPN
        result = self.get_service().handle_payment_ipn(val_id, tran_id)
        return Response(result)


class PaymentAnalyticsView(UnifiedBaseGenericView):
    """Get payment analytics and reporting data"""

    permission_classes = [permissions.IsAuthenticated]
    service_class = PaymentService
    
    class PaymentAnalyticsSerializer(serializers.Serializer):
        """Serializer for payment analytics response"""
        success = serializers.BooleanField()
        data = serializers.DictField()
        message = serializers.CharField()
    
    serializer_class = PaymentAnalyticsSerializer

    def get(self, request, *args, **kwargs):
        """Handle analytics data retrieval"""
        # Check if user is admin
        self.get_service()._require_staff_permission(request.user)

        # Get date range from query parameters
        days = request.query_params.get("days", 30)
        try:
            days = int(days)
        except ValueError:
            days = 30

        from datetime import timedelta

        from django.utils import timezone

        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)

        result = self.get_service().get_payment_analytics(start_date, end_date)

        if result["success"]:
            return Response(
                {
                    "success": True,
                    "data": result["data"],
                    "message": "Payment analytics retrieved successfully",
                },
                status=status.HTTP_200_OK,
            )
        return Response(
            {"success": False, "message": result["error"]},
            status=status.HTTP_400_BAD_REQUEST,
        )


class PaymentRefundView(UnifiedBaseGenericView):
    """Initiate a refund for a payment"""

    permission_classes = [permissions.IsAuthenticated]
    service_class = PaymentService
    
    class RefundSerializer(serializers.Serializer):
        """Serializer for refund requests"""
        refund_amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)
        reason = serializers.CharField(max_length=200, required=False, default="")
    
    serializer_class = RefundSerializer

    def post(self, request, *args, **kwargs):
        """Handle refund initiation"""
        # Check if user is admin
        if not request.user.is_staff:
            return Response(
                {"success": False, "message": "Only admin users can initiate refunds"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Get payment ID from URL
        payment_id = self.kwargs.get("payment_id")

        # Get refund data from request
        refund_amount = request.data.get("refund_amount")
        reason = request.data.get("reason", "")

        result = self.get_service().initiate_refund(
            payment_id=payment_id,
            refund_amount=refund_amount,
            reason=reason,
            user=request.user,
        )

        if result["success"]:
            return Response(
                {
                    "success": True,
                    "data": result,
                    "message": "Refund initiated successfully",
                },
                status=status.HTTP_200_OK,
            )
        return Response(
            {"success": False, "message": result["error"]},
            status=status.HTTP_400_BAD_REQUEST,
        )


class PaymentDisputeView(UnifiedBaseGenericView):
    """Initiate a dispute for a payment"""

    permission_classes = [permissions.IsAuthenticated]
    service_class = PaymentService
    
    class DisputeSerializer(serializers.Serializer):
        """Serializer for dispute requests"""
        dispute_reason = serializers.CharField(max_length=500)
    
    serializer_class = DisputeSerializer

    def post(self, request, *args, **kwargs):
        """Handle dispute initiation"""
        # Get payment ID from URL
        payment_id = self.kwargs.get("payment_id")

        # Get dispute reason from request
        dispute_reason = request.data.get("dispute_reason")

        if not dispute_reason:
            return Response(
                {"success": False, "message": "Dispute reason is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = self.get_service().handle_dispute(
            payment_id=payment_id, dispute_reason=dispute_reason, user=request.user,
        )

        if result["success"]:
            return Response(
                {
                    "success": True,
                    "data": result,
                    "message": "Dispute initiated successfully",
                },
                status=status.HTTP_200_OK,
            )
        return Response(
            {"success": False, "message": result["error"]},
            status=status.HTTP_400_BAD_REQUEST,
        )
