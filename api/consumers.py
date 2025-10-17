import json

from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model

User = get_user_model()


class OrderUpdatesConsumer(AsyncWebsocketConsumer):
    """
    Consumer for real-time order updates.

    This consumer handles WebSocket connections for order status updates,
    allowing real-time notifications when order status changes.
    """

    async def connect(self):
        # Get user from scope
        user = self.scope.get("user", None)

        if user is not None and user.is_authenticated:
            # Add user to their own order group
            self.user_id = user.id
            self.group_name = f"user_{self.user_id}_orders"

            # Join the user's order group
            await self.channel_layer.group_add(self.group_name, self.channel_name)

            await self.accept()
        else:
            await self.close()

    async def disconnect(self, close_code):
        # Remove user from order group
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_type = text_data_json.get("type", "")

        if message_type == "request_order_updates":
            # User is requesting to subscribe to specific order updates
            order_id = text_data_json.get("order_id")
            if order_id:
                order_group_name = f"order_{order_id}"
                await self.channel_layer.group_add(order_group_name, self.channel_name)

                # Send confirmation to WebSocket
                await self.send(
                    text_data=json.dumps(
                        {
                            "message": f"Subscribed to order {order_id} updates",
                            "order_id": order_id,
                        }
                    )
                )

    # Receive message from room group (for order updates)
    async def order_status_update(self, event):
        # Send order update to WebSocket
        await self.send(
            text_data=json.dumps(
                {
                    "type": "order_status_update",
                    "order_id": event["order_id"],
                    "status": event["status"],
                    "message": event["message"],
                    "timestamp": event["timestamp"],
                }
            )
        )

    # Receive message from room group (for general notifications)
    async def order_notification(self, event):
        # Send notification to WebSocket
        await self.send(
            text_data=json.dumps(
                {
                    "type": "order_notification",
                    "message": event["message"],
                    "timestamp": event["timestamp"],
                }
            )
        )


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    Consumer for general notifications.

    This consumer handles WebSocket connections for various notifications
    like new reviews, system messages, etc.
    """

    async def connect(self):
        user = self.scope.get("user", None)

        if user is not None and user.is_authenticated:
            # Add user to their notification group
            self.user_id = user.id
            self.group_name = f"user_{self.user_id}_notifications"

            await self.channel_layer.group_add(self.group_name, self.channel_name)

            await self.accept()
        else:
            await self.close()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)

        # Process any commands from the client if needed
        message = text_data_json.get("message", "")

        # Echo back the message to confirm communication
        await self.send(text_data=json.dumps({"message": f"Received: {message}"}))

    # Receive notification from other parts of the system
    async def notification_message(self, event):
        # Send notification to WebSocket
        await self.send(
            text_data=json.dumps(
                {
                    "type": "notification",
                    "message": event["message"],
                    "timestamp": event["timestamp"],
                }
            )
        )


class PaymentUpdatesConsumer(AsyncWebsocketConsumer):
    """
    Consumer for real-time payment updates.

    This consumer handles WebSocket connections for payment status updates,
    allowing real-time notifications when payment status changes.
    """

    async def connect(self):
        user = self.scope.get("user", None)

        if user is not None and user.is_authenticated:
            # Add user to their payment group
            self.user_id = user.id
            self.group_name = f"user_{self.user_id}_payments"

            await self.channel_layer.group_add(self.group_name, self.channel_name)

            await self.accept()
        else:
            await self.close()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)

        # Process any commands from the client if needed
        message = text_data_json.get("message", "")

        # Echo back the message to confirm communication
        await self.send(text_data=json.dumps({"message": f"Received: {message}"}))

    # Receive payment update from other parts of the system
    async def payment_status_update(self, event):
        # Send payment update to WebSocket
        await self.send(
            text_data=json.dumps(
                {
                    "type": "payment_status_update",
                    "payment_id": event["payment_id"],
                    "status": event["status"],
                    "message": event["message"],
                    "timestamp": event["timestamp"],
                }
            )
        )
