# api/views/password_reset_views.py
# Password reset functionality for the HomeSer platform

import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

User = get_user_model()
logger = logging.getLogger(__name__)


class PasswordResetRequestSerializer(serializers.Serializer):
    """Serializer for password reset request"""

    email = serializers.EmailField()

    def validate_email(self, value):
        """Check if user with this email exists"""
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("No user found with this email address.")
        return value


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for password reset confirmation"""

    uidb64 = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(min_length=8)
    confirm_password = serializers.CharField()

    def validate(self, attrs):
        """Validate password reset data"""
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError("Passwords don't match.")

        # Validate token
        try:
            uid = force_str(urlsafe_base64_decode(attrs["uidb64"]))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise serializers.ValidationError("Invalid reset link.")

        if not default_token_generator.check_token(user, attrs["token"]):
            raise serializers.ValidationError("Invalid or expired reset link.")

        attrs["user"] = user
        return attrs


class PasswordResetValidateTokenSerializer(serializers.Serializer):
    """Serializer for password reset token validation"""
    
    uidb64 = serializers.CharField()
    token = serializers.CharField()


@extend_schema(
    request=PasswordResetRequestSerializer,
    responses={200: {"type": "object", "properties": {"message": {"type": "string"}, "success": {"type": "boolean"}}}},
)
class PasswordResetRequestView(APIView):
    """Request password reset via email"""
    
    permission_classes = [permissions.AllowAny]
    serializer_class = PasswordResetRequestSerializer

    def post(self, request):
        """Request password reset via email"""
        serializer = self.serializer_class(data=request.data)

        if serializer.is_valid():
            email = serializer.validated_data["email"]

            try:
                user = User.objects.get(email=email)

                # Generate reset token
                token = default_token_generator.make_token(user)
                uidb64 = urlsafe_base64_encode(force_bytes(user.pk))

                # Create reset URL
                reset_url = f"{settings.FRONTEND_URL}/reset-password/{uidb64}/{token}/"

                # Prepare email context
                context = {
                    "user": user,
                    "reset_url": reset_url,
                    "site_name": "HomeSer",
                }

                # Send email
                subject = "Password Reset Request - HomeSer"
                message = render_to_string("emails/password_reset.html", context)

                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    html_message=message,
                    fail_silently=False,
                )

                logger.info(f"Password reset email sent to {email}")

                return Response(
                    {
                        "message": "Password reset email has been sent to your email address.",
                        "success": True,
                    },
                    status=status.HTTP_200_OK,
                )

            except User.DoesNotExist:
                # For security, don't reveal if email exists or not
                return Response(
                    {
                        "message": "If an account with this email exists, a password reset email has been sent.",
                        "success": True,
                    },
                    status=status.HTTP_200_OK,
                )

            except Exception as e:
                logger.error(f"Error sending password reset email: {e!s}")
                return Response(
                    {
                        "error": "Failed to send password reset email. Please try again later.",
                        "success": False,
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    request=PasswordResetConfirmSerializer,
    responses={200: {"type": "object", "properties": {"message": {"type": "string"}, "success": {"type": "boolean"}}}},
)
class PasswordResetConfirmView(APIView):
    """Confirm password reset with token"""
    
    permission_classes = [permissions.AllowAny]
    serializer_class = PasswordResetConfirmSerializer

    def post(self, request):
        """Confirm password reset with token"""
        serializer = self.serializer_class(data=request.data)

        if serializer.is_valid():
            try:
                user = serializer.validated_data["user"]
                new_password = serializer.validated_data["new_password"]

                # Set new password
                user.set_password(new_password)
                user.save()

                logger.info(f"Password reset completed for user {user.email}")

                return Response(
                    {
                        "message": "Password has been reset successfully. You can now login with your new password.",
                        "success": True,
                    },
                    status=status.HTTP_200_OK,
                )

            except Exception as e:
                logger.error(f"Error resetting password: {e!s}")
                return Response(
                    {
                        "error": "Failed to reset password. Please try again.",
                        "success": False,
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    request=PasswordResetValidateTokenSerializer,
    responses={200: {"type": "object", "properties": {"valid": {"type": "boolean"}, "email": {"type": "string"}, "error": {"type": "string"}}}},
)
class PasswordResetValidateTokenView(APIView):
    """Validate password reset token without resetting password"""
    
    permission_classes = [permissions.AllowAny]
    serializer_class = PasswordResetValidateTokenSerializer

    def post(self, request):
        """Validate password reset token without resetting password"""
        serializer = self.serializer_class(data=request.data)
        
        if serializer.is_valid():
            uidb64 = serializer.validated_data["uidb64"]
            token = serializer.validated_data["token"]
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        if not uidb64 or not token:
            return Response(
                {"valid": False, "error": "Missing required parameters."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Decode user ID
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)

            # Check token validity
            if default_token_generator.check_token(user, token):
                return Response(
                    {"valid": True, "email": user.email}, status=status.HTTP_200_OK,
                )
            return Response(
                {"valid": False, "error": "Invalid or expired reset link."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response(
                {"valid": False, "error": "Invalid reset link."},
                status=status.HTTP_400_BAD_REQUEST,
            )
