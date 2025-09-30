from rest_framework import serializers

from .models import Payment, PaymentLog


class PaymentSerializer(serializers.ModelSerializer):
    """Serializer for Payment model"""

    class Meta:
        model = Payment
        fields = (
            "id",
            "order",
            "transaction_id",
            "session_key",
            "gateway_response",
            "validation_response",
            "amount",
            "currency",
            "status",
            "val_id",
            "bank_tran_id",
            "card_type",
            "card_no",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
            "transaction_id",
            "session_key",
            "gateway_response",
            "validation_response",
            "val_id",
            "bank_tran_id",
            "card_type",
            "card_no",
        )

    def validate_amount(self, value):
        """Validate that amount is positive"""
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero")
        return value

    def validate_currency(self, value):
        """Validate currency code format"""
        if len(value) != 3:
            raise serializers.ValidationError("Currency must be a 3-letter code")
        return value.upper()


class PaymentLogSerializer(serializers.ModelSerializer):
    """Serializer for PaymentLog model"""

    class Meta:
        model = PaymentLog
        fields = (
            "id",
            "payment",
            "action",
            "data",
            "created_at",
        )
        read_only_fields = (
            "id",
            "created_at",
            "data",
        )

    def validate_action(self, value):
        """Validate action field"""
        if len(value) < 1:
            raise serializers.ValidationError("Action cannot be empty")
        if len(value) > 50:
            raise serializers.ValidationError("Action cannot exceed 50 characters")
        return value


class PaymentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating Payment model"""

    class Meta:
        model = Payment
        fields = (
            "order",
            "amount",
            "currency",
        )

    def validate_amount(self, value):
        """Validate that amount is positive"""
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero")
        return value

    def validate_currency(self, value):
        """Validate currency code format"""
        if len(value) != 3:
            raise serializers.ValidationError("Currency must be a 3-letter code")
        return value.upper()


class PaymentUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating Payment model"""

    class Meta:
        model = Payment
        fields = ("status",)

    def validate_status(self, value):
        """Validate status is one of the allowed choices"""
        allowed_statuses = [
            "pending",
            "processing",
            "completed",
            "failed",
            "cancelled",
            "refunded",
        ]
        if value not in allowed_statuses:
            raise serializers.ValidationError(
                f"Status must be one of: {', '.join(allowed_statuses)}",
            )
        return value


class PaymentLogCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating PaymentLog model"""

    class Meta:
        model = PaymentLog
        fields = (
            "payment",
            "action",
            "data",
        )

    def validate_action(self, value):
        """Validate action field"""
        if len(value) < 1:
            raise serializers.ValidationError("Action cannot be empty")
        if len(value) > 50:
            raise serializers.ValidationError("Action cannot exceed 50 characters")
        return value


class PaymentRefundSerializer(serializers.Serializer):
    """Serializer for refunding a payment"""

    refund_amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False,
    )
    reason = serializers.CharField(max_length=500, required=False, default="")

    def validate_refund_amount(self, value):
        """Validate refund amount is positive if provided"""
        if value is not None and value <= 0:
            raise serializers.ValidationError("Refund amount must be greater than zero")
        return value


class PaymentDisputeSerializer(serializers.Serializer):
    """Serializer for disputing a payment"""

    dispute_reason = serializers.CharField(max_length=1000, required=True)

    def validate_dispute_reason(self, value):
        """Validate dispute reason is not empty"""
        if not value.strip():
            raise serializers.ValidationError("Dispute reason cannot be empty")
        return value


class PaymentAnalyticsSerializer(serializers.Serializer):
    """Serializer for payment analytics data"""

    period = serializers.DictField()
    summary = serializers.DictField()
    status_breakdown = serializers.ListField()
    currency_breakdown = serializers.ListField()
    daily_trend = serializers.ListField()
    method_breakdown = serializers.ListField()
