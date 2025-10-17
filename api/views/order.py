from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response

from orders.models import Order

from ..serializers import CheckoutSerializer, OrderSerializer
from ..services.cart_service import CartService
from ..services.order_service import OrderService
from ..services.payment_service import PaymentService
from ..unified_base_views import (UnifiedBaseGenericView,
                                  UnifiedBaseReadOnlyViewSet,
                                  UnifiedBaseViewSet)


class UserOrderViewSet(UnifiedBaseReadOnlyViewSet):
    """User order management endpoints"""

    serializer_class = OrderSerializer
    service_class = OrderService
    model_class = Order

    def get_permissions(self):
        """Set custom permissions based on request method"""
        from ..permissions import UniversalObjectPermission

        if self.request.method in ["PUT", "PATCH", "DELETE"]:
            return [permissions.IsAuthenticated(), UniversalObjectPermission()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        """Return only orders belonging to the current user"""
        return self.get_service().get_user_orders(self.request.user)


class CheckoutView(UnifiedBaseGenericView, generics.CreateAPIView):
    """Checkout and create payment session with lock-free cart sync"""

    serializer_class = CheckoutSerializer
    service_class = CartService

    def get_permissions(self):
        """Set custom permissions for this view"""
        from ..permissions import UniversalObjectPermission

        return [permissions.IsAuthenticated(), UniversalObjectPermission()]

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """Checkout and create payment session with unified services"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            # Use CartService to get cart data (dictionary) from Redis or database
            cart_data = self.get_service().get_cart(request.user)

            if not cart_data or not cart_data.get("id"):
                return Response(
                    {"detail": "No cart found"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Retrieve the actual Order instance from the database using the ID from cart_data
            order_instance = Order.objects.get(id=cart_data["id"])

            if not order_instance.items.exists():
                return Response(
                    {"detail": "Cart is empty"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Use OrderService to create order from cart (pass the cart_data dictionary)
            order = OrderService.create_order_from_cart(
                cart_data,
                serializer.validated_data,
            )

            # Use PaymentService to create payment session
            result = PaymentService.create_payment_session(
                order,
                serializer.validated_data,
            )

            return Response(result)

        except Order.DoesNotExist:
            return Response(
                {"detail": "No cart found"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AdminOrderViewSet(UnifiedBaseViewSet):
    """Admin order management endpoints"""

    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = (
        Order.objects.all().select_related("user").prefetch_related("items__service")
    )
    http_method_names = ["get", "put", "patch"]  # Exclude POST, DELETE methods
    service_class = OrderService

    def get_queryset(self):
        """Only staff users can access this endpoint"""
        # Permission checking is handled in the service layer
        return self.get_service().get_user_orders(self.request.user)

    def get_object(self):
        """Get a specific order by ID"""
        # Permission checking is handled in the service layer
        order_id = self.kwargs.get("pk")
        return get_object_or_404(Order, id=order_id)


class AdminOrderStatusUpdateView(UnifiedBaseGenericView, generics.UpdateAPIView):
    """Admin order status update endpoint"""

    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    service_class = OrderService
    model_class = Order

    def get_permissions(self):
        """Set custom permissions for this view"""
        from ..permissions import UniversalObjectPermission

        return [permissions.IsAuthenticated(), UniversalObjectPermission()]

    def get_object(self):
        """Get a specific order by ID"""
        # Permission checking is handled in the service layer
        order_id = self.kwargs.get("pk")
        return get_object_or_404(Order, id=order_id)

    def update(self, request, *args, **kwargs):
        """Update order status"""
        order = self.get_object()
        status = request.data.get("status")

        if not status:
            return Response(
                {"detail": "Status is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Use OrderService to update order status
            updated_order = self.get_service().update_order_status(
                order.id,
                status,
                request.user,
            )

            serializer = self.get_serializer(updated_order)
            return Response(serializer.data)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
