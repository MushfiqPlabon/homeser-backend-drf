from django.urls import path

from . import consumers

websocket_urlpatterns = [
    path("ws/orders/", consumers.OrderUpdatesConsumer.as_asgi(), name="order-updates"),
    path(
        "ws/notifications/",
        consumers.NotificationConsumer.as_asgi(),
        name="notifications",
    ),
    path(
        "ws/payments/",
        consumers.PaymentUpdatesConsumer.as_asgi(),
        name="payment-updates",
    ),
]
