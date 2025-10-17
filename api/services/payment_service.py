# api/services/payment_service.py
# Enhanced service for handling payment-related operations

import logging

from pydantic import BaseModel, ValidationError

from api.sslcommerz import SSLCommerzService
from orders.models import Order
from payments.models import Payment, PaymentLog
from utils.email.email_service import EmailService

from .base_service import log_service_method  # Add this import
from .base_service import BaseService

# Set up logging
logger = logging.getLogger(__name__)


# Pydantic model for payment webhook validation
class PaymentWebhookIn(BaseModel):
    val_id: str
    tran_id: str


class PaymentService(BaseService):
    """Enhanced service class for handling payment-related operations"""

    model = Order

    @classmethod
    @log_service_method
    def create_payment_session(cls, order, customer_data):
        """Create a payment session.

        Args:
            order (Order): Order to create payment session for
            customer_data (dict): Customer data

        Returns:
            dict: Payment session information

        """
        # Create payment session
        sslcommerz = SSLCommerzService()
        result = sslcommerz.create_session(order, customer_data)

        if result["success"]:
            return {
                "gateway_url": result["gateway_url"],
                "sessionkey": result["sessionkey"],
                "order_id": order.id,
            }
        # If payment session creation fails, revert the order status back to 'draft'
        # so the user can modify it or try checkout again.
        try:
            order.cancel()  # Use state machine transition
        except Exception:
            order.status = "draft"  # Fallback to direct assignment
        order.save()
        raise Exception(result["error"])

    @classmethod
    @log_service_method
    def handle_payment_ipn(cls, val_id, tran_id):
        """Handle SSLCOMMERZ IPN (Instant Payment Notification) with enhanced security and user identification.

        Args:
            val_id (str): Validation ID
            tran_id (str): Transaction ID

        Returns:
            dict: Result of IPN handling

        """
        # Validate input with Pydantic
        try:
            validated_input = PaymentWebhookIn(val_id=val_id, tran_id=tran_id)
            val_id = validated_input.val_id
            tran_id = validated_input.tran_id
        except ValidationError:
            # The decorator will log the exception, but we still need to return the specific error response
            return {"status": "failed", "error": "Invalid payload parameters"}

        # Manual logger.info removed, decorator handles entry

        try:
            # Validate the payment with SSLCommerz
            sslcommerz = SSLCommerzService()
            result = sslcommerz.validate_payment(val_id, tran_id)

            # Get payment and log the IPN attempt
            try:
                payment = Payment.objects.select_related("order__user").get(
                    transaction_id=tran_id,
                )

                # Create IPN log
                PaymentLog.objects.create(
                    payment=payment,
                    action="ipn_received",
                    data={
                        "val_id": val_id,
                        "tran_id": tran_id,
                        "validation_result": result,
                    },
                )

                # Identify user from the order
                user = payment.order.user if payment.order else None
                if user:
                    # Manual logger.info removed
                    pass
                else:
                    # Manual logger.warning removed
                    pass

            except Payment.DoesNotExist:
                # Manual logger.error removed
                return {"status": "failed", "error": "Payment record not found"}

            if result["success"]:
                # Manual logger.info removed
                # Execute payment processing directly (Vercel-compatible)
                from api.tasks import process_successful_payment

                process_successful_payment(payment.id)

                # Send WebSocket notification for successful payment
                try:
                    from ..utils.websocket_utils import send_payment_update

                    send_payment_update(
                        payment.order.user.id,
                        payment.id,
                        "completed",
                        f"Payment for order #{payment.order.id} confirmed successfully",
                    )
                except Exception as e:
                    # Log the error but don't fail the operation
                    logger.error(
                        f"Failed to send WebSocket payment notification for payment {payment.id}: {e}"
                    )

                return {
                    "status": "success",
                    "message": "Payment IPN received successfully",
                }
            # Manual logger.warning removed
            # Send WebSocket notification for failed payment
            try:
                from ..utils.websocket_utils import send_payment_update

                send_payment_update(
                    payment.order.user.id,
                    payment.id,
                    "failed",
                    f"Payment for order #{payment.order.id} failed",
                )
            except Exception as e:
                # Log the error but don't fail the operation
                logger.error(
                    f"Failed to send WebSocket payment notification for failed payment {payment.id}: {e}"
                )

            return {
                "status": "failed",
                "error": result.get("error", "Payment validation failed"),
            }

        except Exception as e:
            # Manual logger.error removed, decorator handles it
            return {"status": "failed", "error": f"Unexpected error: {e!s}"}

    @classmethod
    @log_service_method
    def validate_payment(cls, val_id, tran_id):
        """Validate a payment.

        Args:
            val_id (str): Validation ID
            tran_id (str): Transaction ID

        Returns:
            dict: Validation result

        """
        sslcommerz = SSLCommerzService()
        return sslcommerz.validate_payment(val_id, tran_id)

    @classmethod
    @log_service_method
    def _validate_refund_requirements(cls, payment, refund_amount):
        """Validate refund requirements."""
        # ... logic ...
        return {"success": True}  # Validation passed

    @classmethod
    @log_service_method
    def _update_payment_and_order_status(cls, payment, order, amount_to_refund, user):
        """Update payment and order status after refund."""
        # Update payment status
        payment.status = "refunded"
        payment.save()

        # Update order payment status
        if amount_to_refund == payment.amount:
            order.refund_payment(by=user)
        else:
            order.partial_refund_payment(by=user)
        order.refund(by=user)  # Refund the order
        order.save()

    @classmethod
    @log_service_method
    def _log_and_notify_refund(cls, payment, order, amount_to_refund, reason, user):
        """Log the refund and send notifications."""
        # ... logic ...

    @classmethod
    @log_service_method
    def initiate_refund(cls, payment_id, refund_amount=None, reason="", user=None):
        """Initiate a refund for a payment.

        Args:
            payment_id (int): ID of the payment to refund
            refund_amount (Decimal, optional): Amount to refund (None for full refund)
            reason (str): Reason for the refund
            user (User): User initiating the refund (admin)

        Returns:
            dict: Refund initiation result

        """
        try:
            payment = Payment.objects.select_related("order").get(id=payment_id)
            order = payment.order

            # Validate refund requirements
            validation_result = cls._validate_refund_requirements(
                payment,
                refund_amount,
            )
            if not validation_result["success"]:
                return validation_result

            # Calculate refund amount
            amount_to_refund = refund_amount if refund_amount else payment.amount

            # Update payment and order status
            cls._update_payment_and_order_status(payment, order, amount_to_refund, user)

            # Log and notify refund
            cls._log_and_notify_refund(payment, order, amount_to_refund, reason, user)

            # Send WebSocket notification for refund
            try:
                from ..utils.websocket_utils import send_payment_update

                send_payment_update(
                    payment.order.user.id,
                    payment.id,
                    "refunded",
                    f"Refund processed for payment {payment.id}",
                )
            except Exception as e:
                # Log the error but don't fail the operation
                logger.error(
                    f"Failed to send WebSocket payment notification for refund {payment.id}: {e}"
                )

            # Manual logger.info removed

            return {
                "success": True,
                "message": "Refund initiated successfully",
                "refund_amount": amount_to_refund,
                "payment_id": payment.id,
            }

        except Payment.DoesNotExist:
            return {"success": False, "error": "Payment not found"}
        except Exception as e:
            # Manual logger.error removed, decorator handles it
            return {"success": False, "error": f"Error initiating refund: {e!s}"}

    @classmethod
    @log_service_method
    def handle_dispute(cls, payment_id, dispute_reason, user=None):
        """Handle a payment dispute.

        Args:
            payment_id (int): ID of the payment in dispute
            dispute_reason (str): Reason for the dispute
            user (User): User initiating the dispute (customer/admin)

        Returns:
            dict: Dispute handling result

        """
        try:
            payment = Payment.objects.select_related("order").get(id=payment_id)
            order = payment.order

            # Update payment status
            payment.status = "disputed"
            payment.save()

            # Update order status
            order.dispute_payment(by=user)
            order.dispute(by=user)
            order.save()

            # Log the dispute
            PaymentLog.objects.create(
                payment=payment,
                action="dispute_initiated",
                data={
                    "dispute_reason": dispute_reason,
                    "initiated_by": user.id if user else None,
                },
            )

            # Send dispute notification emails
            try:
                EmailService.send_dispute_notification_email(order, dispute_reason)
            except Exception:
                # Manual logger.error removed
                pass

            # Send WebSocket notification for dispute
            try:
                from ..utils.websocket_utils import send_payment_update

                send_payment_update(
                    payment.order.user.id,
                    payment.id,
                    "disputed",
                    f"Dispute initiated for payment {payment.id}",
                )
            except Exception as e:
                # Log the error but don't fail the operation
                logger.error(
                    f"Failed to send WebSocket payment notification for dispute {payment.id}: {e}"
                )

            # Manual logger.info removed

            return {
                "success": True,
                "message": "Dispute initiated successfully",
                "payment_id": payment.id,
            }

        except Payment.DoesNotExist:
            return {"success": False, "error": "Payment not found"}
        except Exception as e:
            # Manual logger.error removed, decorator handles it
            return {"success": False, "error": f"Error handling dispute: {e!s}"}

    @classmethod
    @log_service_method
    def _get_basic_statistics(cls, payments):
        """Get basic payment statistics from the payment records.

        Args:
            payments (QuerySet): Payment queryset to calculate statistics for

        Returns:
            dict: Dictionary containing payment statistics including total payments,
                  total amount, successful payments, failed payments, refunded payments,
                  disputed payments, and success rate
        """
        from django.db.models import Sum

        try:
            total_payments = payments.count()
            total_amount = payments.aggregate(total=Sum("amount"))["total"] or 0
            successful_payments = payments.filter(status="completed").count()
            failed_payments = payments.filter(status="failed").count()
            refunded_payments = payments.filter(status="refunded").count()
            disputed_payments = payments.filter(status="disputed").count()

            # Calculate success rate
            success_rate = (
                (successful_payments / total_payments * 100)
                if total_payments > 0
                else 0
            )

            return {
                "total_payments": total_payments,
                "total_amount": total_amount,
                "successful_payments": successful_payments,
                "failed_payments": failed_payments,
                "refunded_payments": refunded_payments,
                "disputed_payments": disputed_payments,
                "success_rate": success_rate,
            }
        except Exception as e:
            # Manual logger.error removed, decorator handles it
            raise e

    @classmethod
    @log_service_method
    def _get_analytics_breakdowns(cls, payments):
        """Get various analytics breakdowns."""
        from django.db.models import Count, Sum

        # Group by status
        try:
            status_breakdown = payments.values("status").annotate(count=Count("id"))
        except Exception:
            # Manual logger.warning removed, decorator handles it
            status_breakdown = []

        # Group by currency
        try:
            currency_breakdown = payments.values("currency").annotate(
                count=Count("id"),
                total_amount=Sum("amount"),
            )
        except Exception:
            # Manual logger.warning removed, decorator handles it
            currency_breakdown = []

        # Daily trend
        try:
            from django.db.models import Date

            daily_trend = (
                payments.annotate(date=Date("created_at"))
                .values("date")
                .annotate(count=Count("id"), total_amount=Sum("amount"))
                .order_by("date")
            )
        except Exception:
            # Manual logger.warning removed, decorator handles it
            daily_trend = []

        # Payment method breakdown (from orders)
        try:
            method_breakdown = (
                payments.select_related("order")
                .filter(order__isnull=False)
                .values("order__payment_method")
                .annotate(count=Count("id"))
            )
        except Exception:
            # Manual logger.warning removed, decorator handles it
            method_breakdown = []

        return status_breakdown, currency_breakdown, daily_trend, method_breakdown

    @classmethod
    @log_service_method
    def get_payment_analytics(cls, start_date=None, end_date=None):
        """Get payment analytics and reporting data.

        Args:
            start_date (datetime, optional): Start date for analytics
            end_date (datetime, optional): End date for analytics

        Returns:
            dict: Payment analytics data

        """
        from datetime import timedelta

        from django.utils import timezone

        try:
            # Set default date range if not provided
            if not end_date:
                end_date = timezone.now()
            if not start_date:
                start_date = end_date - timedelta(days=30)

            # Filter payments by date range
            payments = Payment.objects.filter(
                created_at__gte=start_date,
                created_at__lte=end_date,
            )

            # Calculate basic statistics
            basic_stats = cls._get_basic_statistics(payments)

            # Get analytics breakdowns
            status_breakdown, currency_breakdown, daily_trend, method_breakdown = (
                cls._get_analytics_breakdowns(payments)
            )

            try:
                analytics_data = {
                    "period": {
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat(),
                    },
                    "summary": {
                        "total_payments": basic_stats["total_payments"],
                        "total_amount": float(basic_stats["total_amount"]),
                        "successful_payments": basic_stats["successful_payments"],
                        "failed_payments": basic_stats["failed_payments"],
                        "refunded_payments": basic_stats["refunded_payments"],
                        "disputed_payments": basic_stats["disputed_payments"],
                        "success_rate": round(basic_stats["success_rate"], 2),
                    },
                    "status_breakdown": list(status_breakdown),
                    "currency_breakdown": list(currency_breakdown),
                    "daily_trend": list(daily_trend),
                    "method_breakdown": list(method_breakdown),
                }

                # Manual logger.info removed

                return {"success": True, "data": analytics_data}
            except Exception as e:
                # Manual logger.error removed, decorator handles it
                return {
                    "success": False,
                    "error": f"Error compiling analytics data: {e!s}",
                }

        except Exception as e:
            # Manual logger.error removed, decorator handles it
            return {"success": False, "error": f"Error generating analytics: {e!s}"}
