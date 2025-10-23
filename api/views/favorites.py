"""
Favorites Views - Wishlist & Remarketing

CSE: Simple CRUD operations, optimized queries
BBA: Favorites = purchase intent signal = remarketing opportunity

BUSINESS IMPACT: Favorites = future sales pipeline, remarketing targets
CITATION: Kotler (2016): "Wishlist data enables targeted campaigns"
"""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from services.models import Favorite, Service


class FavoritesView(APIView):
    """List user favorites"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        favorites = Favorite.objects.filter(user=request.user).select_related("service")
        data = [
            {
                "id": fav.id,
                "service": {
                    "id": fav.service.id,
                    "name": fav.service.name,
                    "price": str(fav.service.price),
                    "image_url": fav.service.image.url if fav.service.image else None,
                    "avg_rating": (
                        float(fav.service.avg_rating)
                        if hasattr(fav.service, "avg_rating")
                        else 0
                    ),
                },
                "created": fav.created.isoformat(),
            }
            for fav in favorites
        ]
        return Response(data)


class AddFavoriteView(APIView):
    """Add service to favorites"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        service_id = request.data.get("service_id")
        if not service_id:
            return Response(
                {"error": "service_id required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            service = Service.objects.get(id=service_id)
        except Service.DoesNotExist:
            return Response(
                {"error": "Service not found"}, status=status.HTTP_404_NOT_FOUND
            )

        favorite, created = Favorite.objects.get_or_create(
            user=request.user, service=service
        )
        return Response(
            {"message": "Added to favorites", "created": created},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class RemoveFavoriteView(APIView):
    """Remove service from favorites"""

    permission_classes = [IsAuthenticated]

    def delete(self, request, service_id):
        try:
            favorite = Favorite.objects.get(user=request.user, service_id=service_id)
            favorite.delete()
            return Response(
                {"message": "Removed from favorites"}, status=status.HTTP_200_OK
            )
        except Favorite.DoesNotExist:
            return Response(
                {"error": "Favorite not found"}, status=status.HTTP_404_NOT_FOUND
            )
