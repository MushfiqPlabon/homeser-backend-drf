from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from accounts.models import UserProfile
from services.models import Service, Review
from orders.models import Order, OrderItem
from payments.models import Payment

from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer, UserSerializer,
    UserProfileSerializer, ServiceSerializer, ReviewSerializer,
    OrderSerializer, CheckoutSerializer, CartAddSerializer, 
    CartRemoveSerializer, AdminPromoteSerializer
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
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': UserSerializer(user).data,
            'access': str(refresh.access_token),
            'refresh': str(refresh)
        }, status=status.HTTP_201_CREATED)


class LoginView(generics.GenericAPIView):
    """User login endpoint"""
    serializer_class = UserLoginSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data
        })


class ProfileView(generics.RetrieveUpdateAPIView):
    """User profile endpoint"""
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        profile, created = UserProfile.objects.get_or_create(user=self.request.user)
        return profile


class ServiceListView(generics.ListAPIView):
    """List all services with optional ordering"""
    queryset = Service.objects.filter(is_active=True)
    serializer_class = ServiceSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()
        ordering = self.request.query_params.get('ordering')
        
        if ordering == '-avg_rating':
            # Custom ordering by average rating
            services = list(queryset)
            services.sort(key=lambda x: x.avg_rating, reverse=True)
            return services
        
        return queryset


class ServiceDetailView(generics.RetrieveAPIView):
    """Service detail with reviews"""
    queryset = Service.objects.filter(is_active=True)
    serializer_class = ServiceSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'id'

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        
        # Get recent reviews
        reviews = Review.objects.filter(service=instance)[:5]
        reviews_data = ReviewSerializer(reviews, many=True).data
        
        data = serializer.data
        data['recent_reviews'] = reviews_data
        
        return Response(data)


class ServiceReviewsView(generics.ListCreateAPIView):
    """List and create reviews for a service"""
    serializer_class = ReviewSerializer

    def get_queryset(self):
        service_id = self.kwargs['service_id']
        return Review.objects.filter(service_id=service_id)

    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def perform_create(self, serializer):
        service_id = self.kwargs['service_id']
        service = get_object_or_404(Service, id=service_id)
        
        # Check if user has purchased this service
        user_orders = Order.objects.filter(
            user=self.request.user,
            status='confirmed',
            payment_status='paid',
            items__service=service
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
        cart, created = Order.objects.get_or_create(
            user=self.request.user,
            status='cart'
        )
        return cart


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def add_to_cart(request):
    """Add service to cart"""
    serializer = CartAddSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    service_id = serializer.validated_data['service_id']
    quantity = serializer.validated_data['qty']
    
    service = get_object_or_404(Service, id=service_id, is_active=True)
    
    # Get or create cart
    cart, created = Order.objects.get_or_create(
        user=request.user,
        status='cart'
    )
    
    # Add or update cart item
    cart_item, created = OrderItem.objects.get_or_create(
        order=cart,
        service=service,
        defaults={'quantity': quantity, 'price': service.price}
    )
    
    if not created:
        cart_item.quantity += quantity
        cart_item.save()
    
    return Response(OrderSerializer(cart).data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def remove_from_cart(request):
    """Remove service from cart"""
    serializer = CartRemoveSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    service_id = serializer.validated_data['service_id']
    
    try:
        cart = Order.objects.get(user=request.user, status='cart')
        cart_item = OrderItem.objects.get(order=cart, service_id=service_id)
        cart_item.delete()
    except (Order.DoesNotExist, OrderItem.DoesNotExist):
        pass
    
    # Get updated cart
    cart, created = Order.objects.get_or_create(
        user=request.user,
        status='cart'
    )
    
    return Response(OrderSerializer(cart).data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def checkout(request):
    """Checkout and create payment session"""
    serializer = CheckoutSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    try:
        cart = Order.objects.get(user=request.user, status='cart')
        if not cart.items.exists():
            return Response(
                {'error': 'Cart is empty'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update order with customer details
        cart.customer_name = serializer.validated_data['name']
        cart.customer_address = serializer.validated_data['address']
        cart.customer_phone = serializer.validated_data['phone']
        cart.payment_method = serializer.validated_data['payment_method']
        cart.status = 'pending'
        cart.save()
        
        # Create payment session
        sslcommerz = SSLCommerzService()
        result = sslcommerz.create_session(cart, serializer.validated_data)
        
        if result['success']:
            return Response({
                'gateway_url': result['gateway_url'],
                'sessionkey': result['sessionkey'],
                'order_id': cart.id
            })
        else:
            cart.status = 'cart'  # Revert to cart status
            cart.save()
            return Response(
                {'error': result['error']}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
    except Order.DoesNotExist:
        return Response(
            {'error': 'No cart found'}, 
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
@csrf_exempt
def payment_ipn(request):
    """Handle SSLCOMMERZ IPN (Instant Payment Notification)"""
    val_id = request.POST.get('val_id')
    tran_id = request.POST.get('tran_id')
    
    if val_id and tran_id:
        sslcommerz = SSLCommerzService()
        result = sslcommerz.validate_payment(val_id, tran_id)
        
        if result['success']:
            return Response({'status': 'success'})
    
    return Response({'status': 'failed'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def admin_promote_user(request):
    """Promote user to admin (staff) - only admins can do this"""
    if not request.user.is_staff:
        return Response(
            {'error': 'Only admins can promote users'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = AdminPromoteSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    user_id = serializer.validated_data['user_id']
    user = get_object_or_404(User, id=user_id)
    
    user.is_staff = True
    user.save()
    
    return Response({
        'message': f'User {user.get_full_name()} has been promoted to admin',
        'user': UserSerializer(user).data
    })