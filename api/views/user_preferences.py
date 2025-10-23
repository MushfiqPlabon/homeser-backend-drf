from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import UserProfile


class UserPreferencesView(APIView):
    """Get and update user preferences"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        preferences = (
            profile.social_links if isinstance(profile.social_links, dict) else {}
        )
        return Response(
            {
                "email_notifications": preferences.get("email_notifications", True),
                "sms_notifications": preferences.get("sms_notifications", False),
            }
        )

    def patch(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        preferences = (
            profile.social_links if isinstance(profile.social_links, dict) else {}
        )

        if "email_notifications" in request.data:
            preferences["email_notifications"] = request.data["email_notifications"]
        if "sms_notifications" in request.data:
            preferences["sms_notifications"] = request.data["sms_notifications"]

        profile.social_links = preferences
        profile.save()

        return Response({"message": "Preferences updated successfully"})
