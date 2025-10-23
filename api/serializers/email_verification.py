# api/serializers/email_verification.py
# Serializers for email verification endpoints

from rest_framework import serializers


class EmailVerificationSerializer(serializers.Serializer):
    """
    Serializer for email verification requests.

    This serializer validates email verification requests that include
    a user ID and verification token.
    """

    uidb64 = serializers.CharField(
        help_text="Base64 encoded user ID",
        required=True,
    )
    token = serializers.CharField(
        help_text="Verification token",
        required=True,
    )

    def validate(self, attrs):
        """
        Validate the email verification request.

        Args:
            attrs (dict): Dictionary of serializer fields

        Returns:
            dict: Validated attributes

        Raises:
            serializers.ValidationError: If validation fails

        """
        # Validation is handled in the view
        return attrs


class ResendVerificationEmailSerializer(serializers.Serializer):
    """
    Serializer for resending verification email requests.

    This serializer validates resend verification email requests.
    Since the user is authenticated, we don't need additional fields.
    """

    # No additional fields needed since user is authenticated
    # and we can get the user from the request context

    def validate(self, attrs):
        """
        Validate the resend verification email request.

        Args:
            attrs (dict): Dictionary of serializer fields

        Returns:
            dict: Validated attributes

        Raises:
            serializers.ValidationError: If validation fails

        """
        # Validation is handled in the view
        return attrs
