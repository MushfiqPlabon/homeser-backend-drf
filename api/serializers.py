from rest_framework import serializers
from django.contrib.auth import get_user_model, authenticate
from accounts.models import UserProfile
from services.models import Service, ServiceCategory, Review
from orders.models import Order, OrderItem

User = get_user_model()


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "password",
            "password_confirm",
            "first_name",
            "last_name",
        )

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError("Passwords don't match")
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        user = User.objects.create_user(**validated_data)
        # Create user profile
        UserProfile.objects.create(user=user)
        return user


class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

    def validate(self, attrs):
        username = attrs.get("username")
        password = attrs.get("password")

        if username and password:
            # Attempt authentication first with the provided username.
            # If that fails, try to find a user by email and then authenticate with their actual username.
            # This allows users to log in using either their username or email address.
            user = authenticate(username=username, password=password)
            if not user:
                # Try with email
                try:
                    user_obj = User.objects.get(email=username)
                    user = authenticate(username=user_obj.username, password=password)
                except User.DoesNotExist:
                    pass

            if not user:
                raise serializers.ValidationError("Invalid credentials")

            if not user.is_active:
                raise serializers.ValidationError("User account is disabled")

            attrs["user"] = user
            return attrs
        else:
            raise serializers.ValidationError("Must include username and password")


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name", "is_staff")
        read_only_fields = ("id", "is_staff")


class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    profile_pic_url = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = (
            "user",
            "bio",
            "profile_pic",
            "profile_pic_url",
            "social_links",
            "phone",
            "address",
        )

    def get_profile_pic_url(self, obj):
        if obj.profile_pic:
            return obj.profile_pic.url
        return None


class ServiceCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceCategory
        fields = ("id", "name", "slug", "description")


class ServiceSerializer(serializers.ModelSerializer):
    category = ServiceCategorySerializer(read_only=True)
    avg_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    image_url = serializers.ReadOnlyField()

    class Meta:
        model = Service
        fields = (
            "id",
            "slug",
            "name",
            "category",
            "short_desc",
            "description",
            "price",
            "image_url",
            "avg_rating",
            "review_count",
            "is_active",
        )

    def get_avg_rating(self, obj):
        # This method prioritizes pre-calculated (annotated) average rating from the queryset.
        # This is more efficient as it avoids N+1 queries.
        if hasattr(obj, "avg_rating_val"):
            return round(obj.avg_rating_val, 1) if obj.avg_rating_val else 0
        # Fallback: If the average rating was not pre-calculated (e.g., when fetching a single service),
        # calculate it directly from the model's property. This is less efficient for lists.
        return obj.avg_rating

    def get_review_count(self, obj):
        # This method prioritizes pre-calculated (annotated) review count from the queryset.
        # This is more efficient as it avoids N+1 queries.
        if hasattr(obj, "review_count_val"):
            return obj.review_count_val
        # Fallback: If the review count was not pre-calculated, calculate it directly from the model's property.
        return obj.review_count


class ReviewSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = ("id", "user", "user_name", "rating", "text", "created_at")
        read_only_fields = ("user", "created_at")

    def get_user_name(self, obj):
        return obj.user.get_full_name()

    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError("Rating must be between 1 and 5")
        return value


class OrderItemSerializer(serializers.ModelSerializer):
    service = ServiceSerializer(read_only=True)
    total_price = serializers.ReadOnlyField()

    class Meta:
        model = OrderItem
        fields = ("id", "service", "quantity", "price", "total_price")


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    order_id = serializers.ReadOnlyField()

    class Meta:
        model = Order
        fields = (
            "id",
            "order_id",
            "status",
            "payment_status",
            "customer_name",
            "customer_address",
            "customer_phone",
            "subtotal",
            "tax",
            "total",
            "items",
            "created_at",
        )
        read_only_fields = ("subtotal", "tax", "total", "created_at")


class CheckoutSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    address = serializers.CharField()
    phone = serializers.CharField(max_length=20)
    payment_method = serializers.CharField(default="sslcommerz")


class CartAddSerializer(serializers.Serializer):
    service_id = serializers.IntegerField()
    qty = serializers.IntegerField(min_value=1, default=1)


class CartRemoveSerializer(serializers.Serializer):
    service_id = serializers.IntegerField()

    def validate_service_id(self, value):
        try:
            Service.objects.get(id=value)
        except Service.DoesNotExist:
            raise serializers.ValidationError("Service not found")
        return value


class AdminPromoteSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()

    def validate_user_id(self, value):
        try:
            User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found")
        return value
