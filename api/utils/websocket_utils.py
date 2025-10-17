from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth import get_user_model

User = get_user_model()


def send_order_update(user_id, order_id, status, message="Order status updated"):
    """
    Send order status update notification to a specific user via WebSocket.

    Args:
        user_id (int): ID of the user to notify
        order_id (int): ID of the order that was updated
        status (str): New status of the order
        message (str): Optional message to send with the update
    """
    channel_layer = get_channel_layer()

    # Send to the user's order-specific group
    async_to_sync(channel_layer.group_send)(
        f"user_{user_id}_orders",
        {
            "type": "order_status_update",
            "order_id": order_id,
            "status": status,
            "message": message,
            "timestamp": __import__("datetime").datetime.now().isoformat(),
        },
    )

    # Also send to the specific order group if needed
    async_to_sync(channel_layer.group_send)(
        f"order_{order_id}",
        {
            "type": "order_status_update",
            "order_id": order_id,
            "status": status,
            "message": message,
            "timestamp": __import__("datetime").datetime.now().isoformat(),
        },
    )


def send_payment_update(user_id, payment_id, status, message="Payment status updated"):
    """
    Send payment status update notification to a specific user via WebSocket.

    Args:
        user_id (int): ID of the user to notify
        payment_id (int): ID of the payment that was updated
        status (str): New status of the payment
        message (str): Optional message to send with the update
    """
    channel_layer = get_channel_layer()

    # Send to the user's payment-specific group
    async_to_sync(channel_layer.group_send)(
        f"user_{user_id}_payments",
        {
            "type": "payment_status_update",
            "payment_id": payment_id,
            "status": status,
            "message": message,
            "timestamp": __import__("datetime").datetime.now().isoformat(),
        },
    )


def send_notification(user_id, message, notification_type="general"):
    """
    Send a general notification to a specific user via WebSocket.

    Args:
        user_id (int): ID of the user to notify
        message (str): Message to send
        notification_type (str): Type of notification (e.g., 'review', 'system')
    """
    channel_layer = get_channel_layer()

    # Send to the user's notification-specific group
    async_to_sync(channel_layer.group_send)(
        f"user_{user_id}_notifications",
        {
            "type": "notification_message",
            "message": message,
            "notification_type": notification_type,
            "timestamp": __import__("datetime").datetime.now().isoformat(),
        },
    )
