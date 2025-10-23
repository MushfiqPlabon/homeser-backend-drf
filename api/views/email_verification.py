# api/views/email_verification.py
# View for email verification endpoints

from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.http import urlsafe_base64_decode
from rest_framework import permissions, status
from rest_framework.response import Response

from ..unified_base_views import UnifiedBaseGenericView

User = get_user_model()


class EmailVerificationView(UnifiedBaseGenericView):
    """
    API endpoint for email verification.

    This endpoint handles email verification requests from users who click
    verification links in their email. It verifies the verification token
    and marks the user's email as verified.
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        """
        Handle email verification GET requests.

        Args:
            request: HTTP request object
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments including uidb64 and token

        Returns:
            Response: Success or error response

        """
        try:
            # Extract uidb64 and token from URL parameters
            uidb64 = kwargs.get("uidb64")
            token = kwargs.get("token")

            if not uidb64 or not token:
                return Response(
                    {
                        "success": False,
                        "message": "Invalid verification link",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Decode user ID
            try:
                uid = urlsafe_base64_decode(uidb64).decode()
                user = User.objects.get(pk=uid)
            except (TypeError, ValueError, OverflowError, User.DoesNotExist):
                return Response(
                    {
                        "success": False,
                        "message": "Invalid verification link",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Verify the token using the new method
            if user.verification_token != token:
                return Response(
                    {
                        "success": False,
                        "message": "Invalid verification token",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Check if token has expired using the new method
            if user.is_email_verification_expired():
                return Response(
                    {
                        "success": False,
                        "message": "Verification token has expired. Please request a new verification email.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Mark email as verified using the new method
            user.verify_email()

            return Response(
                {
                    "success": True,
                    "message": "Email verified successfully. You can now use all platform features.",
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": "Email verification failed. Please try again.",
                    "error": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ResendVerificationEmailView(UnifiedBaseGenericView):
    """
    API endpoint for resending email verification.

    This endpoint allows users to request a new verification email
    if they didn't receive the original or if it expired.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        """
        Handle resend verification email POST requests.

        Args:
            request: HTTP request object
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments

        Returns:
            Response: Success or error response

        """
        try:
            user = request.user

            # Check if email is already verified
            if user.email_verified:
                return Response(
                    {
                        "success": True,
                        "message": "Your email is already verified",
                    },
                    status=status.HTTP_200_OK,
                )

            # Check if a verification email was recently sent (within 5 minutes)
            if user.verification_sent_at:
                time_since_last = timezone.now() - user.verification_sent_at
                if time_since_last < timezone.timedelta(minutes=5):
                    return Response(
                        {
                            "success": False,
                            "message": "Verification email already sent recently. Please check your inbox or wait 5 minutes before requesting another.",
                        },
                        status=status.HTTP_429_TOO_MANY_REQUESTS,
                    )

            # Generate new verification token using the new method
            user.generate_verification_token()

            # Send verification email
            from django.conf import settings
            # Construct verification URL
            from django.utils.http import urlsafe_base64_encode

            from utils.email.email_service import EmailService

            uidb64 = urlsafe_base64_encode(str(user.pk).encode())
            verification_url = f"{settings.FRONTEND_URL}/verify-email/{uidb64}/{user.verification_token}/"

            # Send the email
            email_sent = EmailService.send_account_verification_email(
                user, verification_url
            )

            if email_sent:
                return Response(
                    {
                        "success": True,
                        "message": "Verification email sent successfully. Please check your inbox.",
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {
                        "success": False,
                        "message": "Failed to send verification email. Please try again later.",
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": "Failed to resend verification email. Please try again.",
                    "error": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
