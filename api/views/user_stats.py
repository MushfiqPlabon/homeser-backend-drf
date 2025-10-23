from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from orders.models import Order
from services.models import Favorite, Review


class UserStatsView(APIView):
    """Get user statistics"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        orders_count = Order.objects.filter(user=user).count()
        reviews_count = Review.objects.filter(user=user).count()
        favorites_count = Favorite.objects.filter(user=user).count()

        return Response(
            {
                "orders": orders_count,
                "reviews": reviews_count,
                "favorites": favorites_count,
            }
        )


class ChangePasswordView(APIView):
    """Change user password"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        old_password = request.data.get("old_password")
        new_password = request.data.get("new_password")

        if not old_password or not new_password:
            return Response(
                {"error": "Both old and new passwords required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not user.check_password(old_password):
            return Response(
                {"error": "Incorrect old password"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            validate_password(new_password, user)
        except ValidationError as e:
            return Response(
                {"error": list(e.messages)}, status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(new_password)
        user.save()
        update_session_auth_hash(request, user)

        return Response({"message": "Password changed successfully"})
