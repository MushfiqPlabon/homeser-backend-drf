import logging
from typing import Any

from rest_framework import generics, permissions, status
from rest_framework.response import Response

from ..serializers import (CartAddSerializer, CartRemoveSerializer,
                           OrderSerializer)
from ..services.cart_service import CartService
from ..unified_base_views import UnifiedBaseGenericView

logger = logging.getLogger(__name__)


class CartView(UnifiedBaseGenericView, generics.RetrieveAPIView):
    """Get user's cart using smart prefetching and O(1) operations"""

    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    service_class = CartService

    def get_object(self) -> Any:
        """Get cart with optimized database queries"""
        from orders.models import Order

        # Get or create a draft order for the user
        order, created = Order.objects.get_or_create(
            user=self.request.user,
            _status="draft",
            defaults={
                "_payment_status": "unpaid",
                "customer_name": getattr(self.request.user, "first_name", "")
                or self.request.user.username,
                "customer_address": "",
                "subtotal": 0,
                "tax": 0,
                "total": 0,
            },
        )

        # Prefetch related items and services for performance
        return (
            Order.objects.select_related("user")
            .prefetch_related("items__service__category")
            .get(id=order.id)
        )


class AddToCartView(UnifiedBaseGenericView):
    """Add service to cart using O(1) hash map operations"""

    serializer_class = CartAddSerializer
    permission_classes = [permissions.IsAuthenticated]
    service_class = CartService

    def post(self, request, *args, **kwargs) -> Response:
        """Add service to cart with optimized performance"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service_id = serializer.validated_data["service_id"]
        quantity = serializer.validated_data["qty"]

        try:
            order = self.get_service().add_to_cart(
                user=request.user,
                service_id=service_id,
                quantity=quantity,
            )

            # Handle both dict (Redis) and Order (DB) responses
            if isinstance(order, dict):
                return Response(order)
            else:
                serializer = OrderSerializer(order)
                return Response(serializer.data)

        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error adding to cart: {e}")
            return Response(
                {"detail": "Failed to add item to cart"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class RemoveFromCartView(UnifiedBaseGenericView):
    """Remove service from cart using O(1) hash map operations"""

    serializer_class = CartRemoveSerializer
    permission_classes = [permissions.IsAuthenticated]
    service_class = CartService

    def post(self, request, *args, **kwargs) -> Response:
        """Remove service from cart with optimized performance"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service_id = serializer.validated_data["service_id"]

        try:
            order = self.get_service().remove_from_cart(
                user=request.user,
                service_id=service_id,
            )

            # Handle both dict (Redis) and Order (DB) responses
            if isinstance(order, dict):
                return Response(order)
            else:
                serializer = OrderSerializer(order)
                return Response(serializer.data)

        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error removing from cart: {e}")
            return Response(
                {"detail": "Failed to remove item from cart"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class UpdateCartItemQuantityView(UnifiedBaseGenericView):
    """Update cart item quantity using O(1) hash map operations"""

    serializer_class = CartAddSerializer
    permission_classes = [permissions.IsAuthenticated]
    service_class = CartService

    def post(self, request, *args, **kwargs) -> Response:
        """Update cart item quantity with optimized performance"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service_id = serializer.validated_data["service_id"]
        quantity = serializer.validated_data["qty"]

        try:
            order = self.get_service().update_cart_item_quantity(
                user=request.user,
                service_id=service_id,
                quantity=quantity,
            )

            # Handle both dict (Redis) and Order (DB) responses
            if isinstance(order, dict):
                return Response(order)
            else:
                serializer = OrderSerializer(order)
                return Response(serializer.data)

        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error updating cart quantity: {e}")
            return Response(
                {"detail": "Failed to update cart item quantity"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
