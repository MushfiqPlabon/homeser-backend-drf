import logging
from decimal import Decimal

from django.db import transaction

from orders.models import Order, OrderItem

# Configure logger
logger = logging.getLogger(__name__)


def sync_cart_to_database(user_id):
    """Synchronize cart from Redis to database (Vercel-compatible synchronous function)."""
    from api.services.cart_service import CartService

    # Get cart from Redis
    cart = CartService.get_cart(user_id)

    if not cart:
        logger.warning(f"No cart found in Redis for user {user_id}")
        return

    # Create or get order
    order, created = Order.objects.get_or_create(
        user_id=user_id,
        _status="cart",  # Use the internal field name
        defaults={
            "customer_name": "",
            "customer_address": "",
            "customer_phone": "",
        },
    )

    try:
        with transaction.atomic():
            # Get existing items
            existing_items = {item.service_id: item for item in order.items.all()}

            # Prepare lists for bulk operations
            items_to_update = []
            items_to_create = []

            for item_data in cart.get("items", []):
                service_id = item_data["service_id"]
                quantity = item_data["quantity"]
                price = Decimal(item_data["price"])

                if service_id in existing_items:
                    # Update existing item
                    item = existing_items[service_id]
                    item.quantity = quantity
                    item.price = price
                    items_to_update.append(item)
                    del existing_items[service_id]
                else:
                    # Schedule item for creation
                    items_to_create.append(
                        OrderItem(
                            order=order,
                            service_id=service_id,
                            quantity=quantity,
                            price=price,
                        ),
                    )

            # Perform bulk updates and creates
            if items_to_update:
                OrderItem.objects.bulk_update(items_to_update, ["quantity", "price"])

            if items_to_create:
                OrderItem.objects.bulk_create(items_to_create)

            # Delete items that are no longer in the cart
            items_to_delete = list(existing_items.values())
            if items_to_delete:
                OrderItem.objects.filter(
                    id__in=[item.id for item in items_to_delete],
                ).delete()

            order.save()

            logger.info(f"Successfully synced cart for user {user_id}")

    except Exception as e:
        logger.error(f"Database error while syncing cart for user {user_id}: {e!s}")
        raise


def process_successful_payment(payment_id):
    """Process successful payments and update order status (Vercel-compatible synchronous function)."""
    from api.services.cart_service import CartService
    from utils.email.email_service import EmailService

    from .utils.websocket_utils import send_order_update, send_payment_update

    try:
        # Get the payment object
        from payments.models import Payment

        payment = Payment.objects.select_related("order__user").get(id=payment_id)
        order = payment.order

        if not order:
            logger.error(f"Order not found for payment {payment_id}")
            return

        # Clear cart from Redis after successful payment
        try:
            CartService.clear_cart(order.user.id)
            logger.info(f"Cart cleared for order {order.id}")
        except Exception as e:
            logger.error(f"Failed to clear cart for order {order.id}: {e}")

        # Additional security validation - check order ownership
        if not order.user:
            logger.error(f"Order {order.id} has no associated user")
            return

        # Use state machine transition to set payment status to paid
        try:
            order.pay()
            order.submit()  # Also submit the order
            logger.info(f"Order {order.id} status updated to paid and submitted")
        except Exception as e:
            logger.error(f"State transition failed for order {order.id}: {e}")
            # Fallback to direct assignment
            order.payment_status = "paid"
            order.status = "pending"
            order.save()

        # Send payment confirmation email
        try:
            EmailService.send_payment_confirmation_email(order)
            logger.info(f"Payment confirmation email sent for order {order.id}")
        except Exception as e:
            logger.error(
                f"Failed to send payment confirmation email for order {order.id}: {e}",
            )

        # Send WebSocket notifications
        try:
            # Send payment status update notification
            send_payment_update(
                order.user.id,
                payment.id,
                "completed",
                f"Payment for order #{order.id} confirmed successfully",
            )

            # Send order status update notification
            send_order_update(
                order.user.id,
                order.id,
                order.status,
                f"Order #{order.id} has been updated to {order.status} status",
            )
        except Exception as e:
            logger.error(
                f"Failed to send WebSocket notifications for order {order.id}: {e}"
            )

    except Exception as e:
        logger.error(f"Error processing successful payment {payment_id}: {e}")
        raise
