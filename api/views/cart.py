from typing import Any

from rest_framework import generics, permissions, status
from rest_framework.response import Response

from ..serializers import (CartAddSerializer, CartRemoveSerializer,
                           OrderSerializer)
from ..services.cart_service import CartService
from ..unified_base_views import UnifiedBaseGenericView


class CartView(UnifiedBaseGenericView, generics.RetrieveAPIView):
    """Get user's cart using smart prefetching and O(1) operations"""

    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    service_class = CartService

    def get_object(self) -> Any:
        """Get cart with optimized database queries"""
        cart_service = self.get_service()
        cart = cart_service.get_cart(self.request.user)

        # If cart has ID, get from database with prefetch
        if cart_id := cart.get("id"):
            try:
                from orders.models import Order

                return (
                    Order.objects.select_related("user")
                    .prefetch_related("items__service__category")
                    .get(id=cart_id)
                )
            except Order.DoesNotExist:
                pass

        # Create new cart if none exists
        from orders.models import Order

        return Order.objects.create(
            user=self.request.user,
            _status="draft",
            _payment_status="unpaid",
            customer_name=getattr(self.request.user, "first_name", "")
            or self.request.user.username,
            customer_address="",
            subtotal=0,
            tax=0,
            total=0,
        )


class AddToCartView(UnifiedBaseGenericView):
    """Add service to cart using O(1) hash map operations"""

    serializer_class = CartAddSerializer
    service_class = CartService

    def get_permissions(self):
        from ..permissions import UniversalObjectPermission

        return [permissions.IsAuthenticated(), UniversalObjectPermission()]

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
        except Exception:
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
        except Exception:
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

        if quantity <= 0:
            return Response(
                {"detail": "Quantity must be greater than 0"},
                status=status.HTTP_400_BAD_REQUEST,
            )

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
        except Exception:
            return Response(
                {"detail": "Failed to update cart item quantity"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
