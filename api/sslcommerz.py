import logging
import uuid
from decimal import Decimal

from django.conf import settings
from sslcommerz_python_api import SSLCSession

from payments.models import Payment, PaymentLog

# Set up logging
logger = logging.getLogger(__name__)


class SSLCommerzService:
    """Service class for SSLCOMMERZ payment gateway integration with enhanced security"""

    def __init__(self):
        self.store_id = settings.SSLCOMMERZ_STORE_ID
        self.store_pass = settings.SSLCOMMERZ_STORE_PASS
        self.is_sandbox = getattr(settings, "SSLCOMMERZ_IS_SANDBOX", True)

        # Initialize the SSLCSession object
        self.sslcommerz_session = SSLCSession(
            sslc_is_sandbox=self.is_sandbox,
            sslc_store_id=self.store_id,
            sslc_store_pass=self.store_pass,
        )
        # Set URLs once during initialization
        self.sslcommerz_session.set_urls(
            success_url=f"{settings.BACKEND_URL}/api/payments/success/",
            fail_url=f"{settings.BACKEND_URL}/api/payments/fail/",
            cancel_url=f"{settings.BACKEND_URL}/api/payments/cancel/",
            ipn_url=f"{settings.BACKEND_URL}/api/payments/ipn/",
        )

    def create_session(self, order, customer_data):
        """Create payment session with SSLCOMMERZ with enhanced security"""
        # Generate a unique transaction ID for SSLCOMMERZ.
        # It combines a prefix, the internal order ID, and a short UUID for uniqueness.
        tran_id = f"homeser_{order.order_id}_{uuid.uuid4().hex[:8]}"

        try:
            # Set product integration details
            self.sslcommerz_session.set_product_integration(
                # Convert total amount to Decimal from string to ensure precise financial calculations
                # and avoid floating-point inaccuracies.
                total_amount=Decimal(str(order.total)),
                currency="BDT",
                product_category="service",
                product_name="HomeSer Service",  # Generic name
                num_of_item=order.items.count(),  # Number of items in order
                shipping_method="NO",  # Assuming no physical shipping
                product_profile="general",
            )

            # Set customer information
            self.sslcommerz_session.set_customer_info(
                name=customer_data.get("name", order.user.get_full_name()),
                email=order.user.email,
                address1=customer_data.get("address", ""),
                address2="",  # Assuming no address2
                city="Dhaka",  # Default city
                postcode="1000",  # Default postcode
                country="Bangladesh",  # Default country
                phone=customer_data.get("phone", ""),
            )

            # Initiate the payment session
            result = self.sslcommerz_session.init_payment()

            # Create payment record
            payment = Payment.objects.create(
                order=order,
                transaction_id=tran_id,
                amount=order.total,
                gateway_response=result,
            )

            # Log the session creation
            PaymentLog.objects.create(
                payment=payment, action="session_created", data=result,
            )

            if result.get("status") == "SUCCESS":
                payment.session_key = result.get("sessionkey", "")
                payment.save()

                logger.info(
                    f"Payment session created successfully for order {order.id}",
                )

                return {
                    "success": True,
                    "gateway_url": result.get("GatewayPageURL"),
                    "sessionkey": result.get("sessionkey"),
                    "transaction_id": tran_id,
                }
            logger.warning(
                f"Payment session creation failed for order {order.id}: {result.get('failedreason')}",
            )
            return {
                "success": False,
                "error": result.get(
                    "failedreason", "Payment session creation failed",
                ),
            }

        except Exception as e:
            logger.error(f"Payment gateway error for order {order.id}: {e!s}")
            # Log the error
            PaymentLog.objects.create(
                payment=payment if "payment" in locals() else None,
                action="session_error",
                data={"error": str(e)},
            )
            return {"success": False, "error": f"Payment gateway error: {e!s}"}

    def validate_payment(self, val_id, tran_id):
        """Validate payment with SSLCOMMERZ with enhanced security validation"""
        try:
            # Validate the payment
            validation_response = self.sslcommerz_session.validate_payment(
                val_id=val_id, tran_id=tran_id,
            )

            # Find payment record
            try:
                payment = Payment.objects.select_related("order").get(
                    transaction_id=tran_id,
                )
                payment.validation_response = validation_response
                payment.val_id = val_id

                # Log validation
                PaymentLog.objects.create(
                    payment=payment,
                    action="validation_response",
                    data=validation_response,
                )

                # Security validation checks
                # 1. Check if validation status is valid
                if validation_response.get("status") != "VALID":
                    logger.warning(
                        f"Payment validation failed for transaction {tran_id}: Invalid status",
                    )
                    payment.status = "failed"
                    payment.save()
                    return {
                        "success": False,
                        "error": "Payment validation failed - invalid status",
                    }

                # 2. Check if transaction ID matches
                if validation_response.get("tran_id") != tran_id:
                    logger.warning(
                        f"Payment validation failed for transaction {tran_id}: Transaction ID mismatch",
                    )
                    payment.status = "failed"
                    payment.save()
                    return {
                        "success": False,
                        "error": "Payment validation failed - transaction ID mismatch",
                    }

                # 3. Check if amount matches
                validation_amount = Decimal(str(validation_response.get("amount", 0)))
                payment_amount = Decimal(str(payment.amount))
                if validation_amount != payment_amount:
                    logger.warning(
                        f"Payment validation failed for transaction {tran_id}: Amount mismatch ({validation_amount} vs {payment_amount})",
                    )
                    payment.status = "failed"
                    payment.save()
                    return {
                        "success": False,
                        "error": "Payment validation failed - amount mismatch",
                    }

                # 4. Check if currency matches
                if validation_response.get("currency") != payment.currency:
                    logger.warning(
                        f"Payment validation failed for transaction {tran_id}: Currency mismatch",
                    )
                    payment.status = "failed"
                    payment.save()
                    return {
                        "success": False,
                        "error": "Payment validation failed - currency mismatch",
                    }

                # All validations passed
                payment.status = "completed"
                payment.bank_tran_id = validation_response.get("bank_tran_id", "")
                payment.card_type = validation_response.get("card_type", "")
                payment.card_no = validation_response.get("card_no", "")
                payment.save()

                # Update order status
                order = payment.order
                order.payment_status = "paid"
                order.status = "confirmed"
                order.transaction_id = tran_id
                order.save()

                logger.info(f"Payment validation successful for transaction {tran_id}")

                return {"success": True, "payment": payment, "order": order}

            except Payment.DoesNotExist:
                logger.error(f"Payment record not found for transaction {tran_id}")
                return {"success": False, "error": "Payment record not found"}

        except Exception as e:
            logger.error(f"Payment validation error for transaction {tran_id}: {e!s}")
            return {"success": False, "error": f"Validation error: {e!s}"}
