import pusher
from django.conf import settings

pusher_client = pusher.Pusher(
    app_id=settings.PUSHER_APP_ID,
    key=settings.PUSHER_KEY,
    secret=settings.PUSHER_SECRET,
    cluster=settings.PUSHER_CLUSTER,
    ssl=True,
)


def send_order_update(user_id, order_id, status, message="Order status updated"):
    channel = f"user_{user_id}"
    event = "order_update"
    data = {"order_id": order_id, "status": status, "message": message}
    pusher_client.trigger(channel, event, data)


def send_payment_update(user_id, payment_id, status, message="Payment status updated"):
    channel = f"user_{user_id}"
    event = "payment_update"
    data = {"payment_id": payment_id, "status": status, "message": message}
    pusher_client.trigger(channel, event, data)


def send_notification(user_id, message, notification_type="general"):
    channel = f"user_{user_id}"
    event = "notification"
    data = {"message": message, "notification_type": notification_type}
    pusher_client.trigger(channel, event, data)
