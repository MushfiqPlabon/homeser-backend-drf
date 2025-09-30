from rest_framework import generics, permissions, status
from rest_framework.response import Response

from orders.models import Order

from ..serializers import (
    CartAddSerializer,
    CartRemoveSerializer,
    OrderSerializer,
)
from ..services.cart_service import CartService
from ..smart_prefetch import SmartPrefetcher
from ..unified_base_views import (
    UnifiedBaseGenericView,
)


class CartView(UnifiedBaseGenericView, generics.RetrieveAPIView):
    """Get user's cart using smart prefetching"""

    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    service_class = CartService

    def get_object(self):
        # Use CartService to get cart
        cart = self.get_service().get_cart(self.request.user)

        # Check if cart has an ID (it should for authenticated users)
        cart_id = cart.get('id') 
        if cart_id is None:
            # For cases where no cart exists, create an empty one or return None
            # This shouldn't normally happen for authenticated users since get_cart
            # should create a draft order for them, but we'll handle it safely
            from orders.models import Order
            # Create a new draft order for this user
            order = Order.objects.create(
                user=self.request.user,
                _status="draft",
                _payment_status="unpaid",
                customer_name=getattr(self.request.user, 'first_name', '') or self.request.user.username,
                customer_address="",  # Will be filled during checkout
                subtotal=0,
                tax=0,
                total=0
            )
            cart_id = order.id

        # Use smart prefetching
        base_queryset = Order.objects.filter(id=cart_id)
        with SmartPrefetcher(base_queryset, self.request) as queryset:
            return (
                queryset.select_related("user")
                .prefetch_related("items__service__category")
                .only(
                    "id",
                    "user__id",
                    "status",
                    "payment_status",
                    "customer_name",
                    "customer_address",
                    "customer_phone",
                    "payment_method",
                    "transaction_id",
                    "subtotal",
                    "tax",
                    "total",
                    "created_at",
                    "updated_at",
                    "items__id",
                    "items__service__id",
                    "items__service__name",
                    "items__service__slug",
                    "items__service__price",
                    "items__service__image",
                    "items__service__category__id",
                    "items__service__category__name",
                    "items__quantity",
                    "items__price",
                    "items__created_at",
                )
                .first()
            )


class AddToCartView(UnifiedBaseGenericView):
    """Add service to cart using lock-free implementation"""

    serializer_class = CartAddSerializer
    service_class = CartService

    def get_permissions(self):
        """Set custom permissions for this view"""
        from ..permissions import UniversalObjectPermission

        return [permissions.IsAuthenticated(), UniversalObjectPermission()]

    def post(self, request, *args, **kwargs):
        """Add service to cart using CartService"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service_id = serializer.validated_data["service_id"]
        quantity = serializer.validated_data["qty"]

        try:
            # Use CartService to add item to cart
            order = self.get_service().add_to_cart(
                user=request.user, service_id=service_id, quantity=quantity,
            )

            # Return updated cart
            serializer = OrderSerializer(order)
            return Response(serializer.data)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class RemoveFromCartView(UnifiedBaseGenericView):
    """Remove service from cart using lock-free implementation"""

    serializer_class = CartRemoveSerializer
    permission_classes = [permissions.IsAuthenticated]
    service_class = CartService

    def post(self, request, *args, **kwargs):
        """Remove service from cart using CartService"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service_id = serializer.validated_data["service_id"]

        try:
            # Use CartService to remove item from cart
            order = self.get_service().remove_from_cart(
                user=request.user, service_id=service_id,
            )

            # Return updated cart
            serializer = OrderSerializer(order)
            return Response(serializer.data)
        except Exception:
            return Response(
                {"detail": "Failed to remove item from cart"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class UpdateCartItemQuantityView(UnifiedBaseGenericView):
    """Update cart item quantity using lock-free implementation"""

    serializer_class = CartAddSerializer  # Reusing CartAddSerializer
    permission_classes = [permissions.IsAuthenticated]
    service_class = CartService

    def post(self, request, *args, **kwargs):
        """Update cart item quantity using CartService"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service_id = serializer.validated_data["service_id"]
        quantity = serializer.validated_data["qty"]

        # Validate quantity
        if quantity <= 0:
            return Response(
                {"detail": "Quantity must be greater than 0"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Use CartService to update item quantity in cart
            order = self.get_service().update_cart_item_quantity(
                user=request.user, service_id=service_id, quantity=quantity,
            )

            # Return updated cart
            serializer = OrderSerializer(order)
            return Response(serializer.data)
        except Exception:
            return Response(
                {"detail": "Failed to update cart item quantity"},
                status=status.HTTP_400_BAD_REQUEST,
            )
