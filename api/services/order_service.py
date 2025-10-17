# api/services/order_service.py
# Simplified service for handling order-related operations

import logging

from django.shortcuts import get_object_or_404
from django_fsm import can_proceed  # Add this import

from orders.models import Order
from utils.email.email_service import EmailService

from ..utils.websocket_utils import send_order_update
from .base_service import log_service_method  # Add this import
from .base_service import BaseService

logger = logging.getLogger(__name__)


class OrderService(BaseService):
    """Simplified service class for handling order-related operations"""

    model = Order

    @classmethod
    @log_service_method
    def get_user_orders(cls, user, admin_mode=False):
        """Get orders for a specific user.

        Args:
            user (User): User whose orders to retrieve
            admin_mode (bool): Whether to enforce admin permissions

        Returns:
            QuerySet: Order queryset

        Raises:
            PermissionError: If user is not authorized to view orders

        """
        # Check if user is authenticated
        if not user.is_authenticated:
            # Return empty queryset for anonymous users
            return Order.objects.none()

        # Check if user is admin when in admin mode
        if admin_mode:
            cls._require_staff_permission(user)

        return (
            Order.objects.filter(user=user)
            .select_related("user")
            .prefetch_related("items__service__category")
            .order_by("-created")
        )

    @classmethod
    @log_service_method
    def get_order_detail(cls, order_id, user):
        """Get detailed information for a specific order.

        Args:
            order_id (int): ID of the order
            user (User): User requesting the order (for permission check)

        Returns:
            Order: Order instance

        """
        order = get_object_or_404(Order, id=order_id)

        # Check if user has permission to view this order
        cls._common_permission_check(order, user, "view")

    @classmethod
    @log_service_method
    def update_order_status(cls, order_id, status, user):
        """Update the status of an order using simplified state machine transitions.

        Args:
            order_id (int): ID of the order to update
            status (str): New status
            user (User): User updating the order

        Returns:
            Order: Updated order instance

        """
        order = get_object_or_404(Order, id=order_id)

        # Check if user has permission to update order status
        cls._common_permission_check(order, user, "change")

        # Store old status for notifications
        old_status = order.status

        # Use simplified state machine transitions based on the requested status
        try:
            transition_map = {
                "pending": order.submit,
                "processing": order.process,
                "confirmed": order.confirm,
                "cancelled": order.cancel,
                "refunded": order.refund,
                "on_hold": order.hold,
                "disputed": order.dispute,
                "delivered": order.complete,  # Assuming delivered leads to completed
                "completed": order.complete,
            }

            transition_func = transition_map.get(status)

            if transition_func:
                if not can_proceed(transition_func):
                    raise ValueError(
                        f"Cannot transition order from '{order.status}' to '{status}'."
                    )
                transition_func()
            else:
                valid_statuses = [choice[0] for choice in Order.STATUS_CHOICES]
                if status in valid_statuses:
                    # This case should ideally not be reached if all transitions are mapped
                    # But as a safeguard, if it's a valid status but no transition, raise error
                    raise ValueError(
                        f"No explicit transition defined for status '{status}'."
                    )
                else:
                    raise ValueError(
                        f"Invalid status '{status}'. Valid statuses are: {', '.join(valid_statuses)}."
                    )

            order.save()

            # Send email notification if status changed
            if old_status != order.status:
                try:
                    # Send different emails based on status change
                    if status == "pending":
                        EmailService.send_order_confirmation_email(order)
                    elif status == "completed":
                        # You could send a delivery confirmation email here
                        pass
                except Exception as e:
                    # Log the error but don't fail the operation
                    print(f"Failed to send order status update email: {e}")

                # Send WebSocket notification for order status change
                try:
                    send_order_update(
                        order.user.id,
                        order.id,
                        order.status,
                        f"Order #{order.id} status updated to {order.status}",
                    )
                except Exception as e:
                    # Log the error but don't fail the operation
                    logger.error(
                        f"Failed to send WebSocket notification for order {order.id}: {e}"
                    )

            return order
        except Exception as e:
            raise ValueError(f"Cannot transition order to {status}: {e!s}")

    @classmethod
    @log_service_method
    def create_order_from_cart(cls, cart_data, customer_data):
        """Create an order from a cart.

        Args:
            cart_data (dict): Cart data (dictionary representation) to convert to order
            customer_data (dict): Customer information

        Returns:
            Order: Created order instance

        """
        # Validate customer data
        from utils.validation_utils import validate_text_length

        # Validate name
        try:
            name = customer_data.get("name")
            if not name:
                raise ValueError("Customer name is required")
            name = validate_text_length(
                name,
                min_length=1,
                max_length=100,
                field_name="Customer name",
            )
        except Exception as e:
            raise ValueError(f"Invalid customer name: {e!s}")

        # Validate address
        try:
            address = customer_data.get("address")
            if not address:
                raise ValueError("Customer address is required")
            address = validate_text_length(
                address,
                min_length=1,
                max_length=500,
                field_name="Customer address",
            )
        except Exception as e:
            raise ValueError(f"Invalid customer address: {e!s}")

        # Validate phone
        try:
            phone = customer_data.get("phone")
            if not phone:
                raise ValueError("Customer phone is required")
            phone = validate_text_length(
                phone,
                min_length=1,
                max_length=20,
                field_name="Customer phone",
            )
        except Exception as e:
            raise ValueError(f"Invalid customer phone: {e!s}")

        # Extract validated data
        name = customer_data.get("name")
        address = customer_data.get("address")
        phone = customer_data.get("phone")
        payment_method = customer_data.get("payment_method", "sslcommerz")

        # Retrieve the actual Order instance from the database
        # Assuming cart_data has an 'id' field for the draft order
        if not cart_data.get("id"):
            raise ValueError("Cart data must contain an 'id' for the draft order.")

        order = Order.objects.get(id=cart_data["id"])

        # Update order with customer details
        logger.debug(f"Before update: order.customer_name = '{order.customer_name}'")
        order.customer_name = name
        order.customer_address = address
        order.customer_phone = phone
        order.payment_method = payment_method
        logger.debug(
            f"After update: order.customer_name = '{order.customer_name}' (should be '{name}')"
        )

        # Use simplified state machine transition to set payment status to paid
        # This should always succeed from 'unpaid' to 'paid'
        if not can_proceed(order.pay):
            raise ValueError(
                f"Cannot transition cart payment status from '{order.payment_status}' to 'paid'."
            )
        order.pay()

        # Use simplified state machine transition to set status to pending
        # This should always succeed from 'draft' to 'pending'
        if not can_proceed(order.submit):
            raise ValueError(
                f"Cannot transition cart status from '{order.status}' to 'pending'."
            )
        order.submit()

        order.save()  # This save is crucial
        logger.debug(f"After save: order.customer_name = '{order.customer_name}'")

        # Send WebSocket notification for new order
        try:
            send_order_update(
                order.user.id,
                order.id,
                order.status,
                f"New order #{order.id} created successfully",
            )
        except Exception as e:
            # Log the error but don't fail the operation
            logger.error(
                f"Failed to send WebSocket notification for new order {order.id}: {e}"
            )

        return order

    @classmethod
    @log_service_method
    def update_payment_status(cls, order_id, payment_status, user):
        """Update the payment status of an order using simplified state machine transitions.

        Args:
            order_id (int): ID of the order to update
            payment_status (str): New payment status
            user (User): User updating the order

        Returns:
            Order: Updated order instance

        """
        # Check if user has permission to update order status
        order = get_object_or_404(Order, id=order_id)

        # Check if user has permission to update order status
        cls._common_permission_check(order, user, "change")

        # Store old payment status for notifications
        old_payment_status = order.payment_status

        # Use simplified state machine transitions based on the requested payment status
        try:
            payment_transition_map = {
                "paid": order.pay,
                "refunded": order.refund_payment,
                "partially_refunded": order.partial_refund_payment,
                "disputed": order.dispute_payment,
            }

            payment_transition_func = payment_transition_map.get(payment_status)

            if payment_transition_func:
                if not can_proceed(payment_transition_func):
                    raise ValueError(
                        f"Cannot transition payment status from '{order.payment_status}' to '{payment_status}'."
                    )
                payment_transition_func()
            else:
                valid_payment_statuses = [
                    choice[0] for choice in Order.PAYMENT_STATUS_CHOICES
                ]
                if payment_status in valid_payment_statuses:
                    raise ValueError(
                        f"No explicit payment transition defined for status '{payment_status}'."
                    )
                else:
                    raise ValueError(
                        f"Invalid payment status '{payment_status}'. Valid statuses are: {', '.join(valid_payment_statuses)}."
                    )

            order.save()

            # Send email notification if payment status changed to paid
            if old_payment_status != "paid" and payment_status == "paid":
                try:
                    EmailService.send_payment_confirmation_email(order)
                except Exception as e:
                    # Log the error but don't fail the operation
                    print(f"Failed to send payment confirmation email: {e}")

                # Send WebSocket notification for payment status change
                try:
                    from ..utils.websocket_utils import send_payment_update

                    send_payment_update(
                        order.user.id,
                        order.id,
                        payment_status,
                        f"Payment for order #{order.id} updated to {payment_status}",
                    )
                except Exception as e:
                    # Log the error but don't fail the operation
                    logger.error(
                        f"Failed to send WebSocket payment notification for order {order.id}: {e}"
                    )

            return order
        except Exception as e:
            raise ValueError(
                f"Cannot transition payment status to {payment_status}: {e!s}",
            )
