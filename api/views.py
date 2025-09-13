from rest_framework import generics, status, permissions, serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.db.models import Avg, Count
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.core.cache import cache
from django.conf import settings

from accounts.models import UserProfile
from services.models import Service, Review
from orders.models import Order, OrderItem

from .serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    UserSerializer,
    UserProfileSerializer,
    ServiceSerializer,
    ReviewSerializer,
    OrderSerializer,
    CheckoutSerializer,
    CartAddSerializer,
    CartRemoveSerializer,
    AdminPromoteSerializer,
)
from .sslcommerz import SSLCommerzService

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """User registration endpoint"""

    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Generate JWT (JSON Web Token) tokens for the newly registered user.
        # 'refresh' token is used to obtain new 'access' tokens after they expire.
        # 'access' token is used for authenticating subsequent API requests.
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "user": UserSerializer(user).data,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(generics.GenericAPIView):
    """User login endpoint"""

    serializer_class = UserLoginSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        # Generate JWT (JSON Web Token) tokens for the authenticated user.
        # 'refresh' token is used to obtain new 'access' tokens after they expire.
        # 'access' token is used for authenticating subsequent API requests.
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserSerializer(user).data,
            }
        )


class ProfileView(generics.RetrieveUpdateAPIView):
    """User profile endpoint"""

    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        profile, created = UserProfile.objects.select_related("user").get_or_create(
            user=self.request.user
        )
        return profile


class ServiceListView(generics.ListAPIView):
    """List all services with optional ordering"""

    serializer_class = ServiceSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        # Debug information
        print("=== ServiceListView Debug Info ===")
        print(f"Request method: {self.request.method}")
        print(f"Request path: {self.request.path}")
        print(f"Query params: {self.request.query_params}")

        # Check database directly with more details
        from django.db import connection

        print(f"Database connection: {connection.settings_dict['NAME']}")

        total_services = Service.objects.count()
        active_services = Service.objects.filter(is_active=True).count()
        print(f"Total services in DB: {total_services}")
        print(f"Active services in DB: {active_services}")

        # Let's also check what services actually exist
        if total_services > 0:
            services = Service.objects.all()[:3]  # Get first 3 services
            for service in services:
                print(
                    f"Service: {service.name} (ID: {service.id}, Active: {service.is_active})"
                )

        # Create cache key based on ordering and page parameters
        ordering = self.request.query_params.get("ordering", "default")
        page = self.request.query_params.get("page", 1)
        cache_key = f"services_list_{ordering}_page_{page}"
        print(f"Cache key: {cache_key}")

        # Try to get cached result
        cached_queryset = cache.get(cache_key)
        print(f"Cached result: {cached_queryset is not None}")
        if cached_queryset is not None:
            # If we have a cached queryset, make sure it's evaluated
            if isinstance(cached_queryset, list):
                print(f"Returning cached list with {len(cached_queryset)} items")
                return cached_queryset
            result_list = list(cached_queryset)
            print(
                f"Returning cached queryset converted to list with {len(result_list)} items"
            )
            return result_list

        # Optimize queryset with annotations for avg_rating and review_count
        queryset = (
            Service.objects.filter(is_active=True)
            .select_related("category")
            .annotate(
                avg_rating_val=Avg("reviews__rating"), review_count_val=Count("reviews")
            )
        )

        if ordering == "-avg_rating":
            # Efficient database-level ordering
            queryset = queryset.order_by("-avg_rating_val")
        elif ordering == "price":
            queryset = queryset.order_by("price")
        elif ordering == "-price":
            queryset = queryset.order_by("-price")
        elif ordering == "name":
            queryset = queryset.order_by("name")
        else:
            # Default ordering (by creation date)
            queryset = queryset.order_by("-created_at")

        # Convert to list to ensure it's serializable and cache the result for 15 minutes
        result_list = list(queryset)
        print(f"Created new result list with {len(result_list)} items")
        if len(result_list) > 0:
            for service in result_list[:3]:  # Show first 3 services
                print(f"Result service: {service.name} (ID: {service.id})")
        cache.set(cache_key, result_list, timeout=settings.CACHE_TTL)
        print(f"Cached result with key: {cache_key}")

        return result_list


class ServiceDetailView(generics.RetrieveAPIView):
    """Service detail with reviews"""

    serializer_class = ServiceSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = "id"

    def get_queryset(self):
        # Optimize queryset with annotations
        return (
            Service.objects.filter(is_active=True)
            .select_related("category")
            .annotate(
                avg_rating_val=Avg("reviews__rating"), review_count_val=Count("reviews")
            )
        )

    def retrieve(self, request, *args, **kwargs):
        # Create cache key based on service id
        service_id = self.kwargs["id"]
        cache_key = f"service_detail_{service_id}"

        # Try to get cached result
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)

        instance = self.get_object()
        serializer = self.get_serializer(instance)

        # Get recent reviews
        reviews = Review.objects.filter(service=instance).select_related("user")[:5]
        reviews_data = ReviewSerializer(reviews, many=True).data

        data = serializer.data
        data["recent_reviews"] = reviews_data

        # Cache the result for 15 minutes
        cache.set(cache_key, data, timeout=settings.CACHE_TTL)

        return Response(data)


class ServiceReviewsView(generics.ListCreateAPIView):
    """List and create reviews for a service"""

    serializer_class = ReviewSerializer

    def get_queryset(self):
        service_id = self.kwargs["service_id"]
        return Review.objects.filter(service_id=service_id)

    def get_permissions(self):
        if self.request.method == "POST":
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def perform_create(self, serializer):
        service_id = self.kwargs["service_id"]
        service = get_object_or_404(Service, id=service_id)

        # Business Logic: A user can only review a service if they have
        # successfully purchased it and the order is confirmed and paid.
        # Additionally, the service must still be active.
        if not service.is_active:
            raise serializers.ValidationError("You can only review active services.")

        user_orders = Order.objects.filter(
            user=self.request.user,
            status="confirmed",
            payment_status="paid",
            items__service=service,
        )

        if not user_orders.exists():
            raise serializers.ValidationError(
                "You can only review services you have purchased and received."
            )

        serializer.save(user=self.request.user, service=service)


class CartView(generics.RetrieveAPIView):
    """Get user's cart"""

    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        cart, created = Order.objects.prefetch_related("items__service").get_or_create(
            user=self.request.user, status="cart"
        )
        return cart


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def add_to_cart(request):
    """Add service to cart"""
    serializer = CartAddSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    service_id = serializer.validated_data["service_id"]
    quantity = serializer.validated_data["qty"]

    service = get_object_or_404(Service, id=service_id, is_active=True)

    # Get or create cart
    cart, created = Order.objects.prefetch_related("items__service").get_or_create(
        user=request.user, status="cart"
    )

    # Add or update cart item
    cart_item, created = OrderItem.objects.get_or_create(
        order=cart,
        service=service,
        defaults={"quantity": quantity, "price": service.price},
    )

    if not created:
        cart_item.quantity += quantity
        cart_item.save()

    return Response(OrderSerializer(cart).data)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def remove_from_cart(request):
    """Remove service from cart"""
    serializer = CartRemoveSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    service_id = serializer.validated_data["service_id"]

    try:
        cart = Order.objects.get(user=request.user, status="cart")
        cart_item = OrderItem.objects.get(order=cart, service_id=service_id)
        cart_item.delete()
    except (Order.DoesNotExist, OrderItem.DoesNotExist):
        pass

    # Get updated cart
    cart, created = Order.objects.prefetch_related("items__service").get_or_create(
        user=request.user, status="cart"
    )

    return Response(OrderSerializer(cart).data)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
@transaction.atomic  # Add this decorator
def checkout(request):
    """Checkout and create payment session"""
    serializer = CheckoutSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        cart = Order.objects.get(user=request.user, status="cart")
        if not cart.items.exists():
            return Response(
                {"error": "Cart is empty"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Update order with customer details
        cart.customer_name = serializer.validated_data["name"]
        cart.customer_address = serializer.validated_data["address"]
        cart.customer_phone = serializer.validated_data["phone"]
        cart.payment_method = serializer.validated_data["payment_method"]
        cart.status = "pending"
        cart.save()

        # Create payment session
        sslcommerz = SSLCommerzService()
        result = sslcommerz.create_session(cart, serializer.validated_data)

        if result["success"]:
            return Response(
                {
                    "gateway_url": result["gateway_url"],
                    "sessionkey": result["sessionkey"],
                    "order_id": cart.id,
                }
            )
        else:
            # If payment session creation fails, revert the order status back to 'cart'
            # so the user can modify it or try checkout again.
            cart.status = "cart"  # Revert to cart status
            cart.save()
            return Response(
                {"error": result["error"]}, status=status.HTTP_400_BAD_REQUEST
            )

    except Order.DoesNotExist:
        return Response({"error": "No cart found"}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
@csrf_exempt  # CSRF protection is exempted because this is an external callback (IPN)
# from the payment gateway, which does not send CSRF tokens.
def payment_ipn(request):
    """Handle SSLCOMMERZ IPN (Instant Payment Notification)"""
    val_id = request.POST.get("val_id")
    tran_id = request.POST.get("tran_id")

    if val_id and tran_id:
        sslcommerz = SSLCommerzService()
        result = sslcommerz.validate_payment(val_id, tran_id)

        if result["success"]:
            return Response({"status": "success"})

    return Response({"status": "failed"}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def admin_promote_user(request):
    """Promote user to admin (staff) - only admins can do this"""
    if not request.user.is_staff:
        return Response(
            {"error": "Only admins can promote users"}, status=status.HTTP_403_FORBIDDEN
        )

    serializer = AdminPromoteSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    user_id = serializer.validated_data["user_id"]
    user = get_object_or_404(User, id=user_id)

    user.is_staff = True
    user.save()

    return Response(
        {
            "message": f"User {user.get_full_name()} has been promoted to admin",
            "user": UserSerializer(user).data,
        }
    )
