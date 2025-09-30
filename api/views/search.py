from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework import generics, permissions, serializers, status
from rest_framework.response import Response

from utils.advanced_search_service import AdvancedSearchService

from ..unified_base_views import (
    UnifiedBaseGenericView,
)


class AdvancedSearchView(UnifiedBaseGenericView):
    """Advanced search endpoint using our data structures."""

    permission_classes = [permissions.AllowAny]
    service_class = AdvancedSearchService

    @extend_schema(
        summary="Advanced service search",
        description="Search for services using advanced data structures for improved performance.",
        parameters=[
            OpenApiParameter(
                name="q", description="Search query", required=True, type=str,
            ),
            OpenApiParameter(
                name="limit",
                description="Maximum number of results",
                required=False,
                type=int,
            ),
            OpenApiParameter(
                name="language",
                description="Language code for search (e.g., 'en', 'es', 'fr')",
                required=False,
                type=str,
            ),
        ],
        responses={200: OpenApiTypes.OBJECT},
    )
    def get(self, request, *args, **kwargs):
        """Handle advanced search requests."""
        query = request.query_params.get("q", "")
        limit = request.query_params.get("limit", 20)
        language = request.query_params.get("language", "en")

        if not query:
            return Response(
                {"error": "Query parameter 'q' is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            limit = int(limit)
        except (ValueError, TypeError):
            limit = 20

        # Use our advanced search service
        results = self.get_service().search_services(query, limit, language)

        return Response(
            {
                "query": query,
                "language": language,
                "results": results,
                "count": len(results),
            },
        )


class SearchAnalyticsView(UnifiedBaseGenericView, generics.RetrieveAPIView):
    """Get search analytics statistics."""

    permission_classes = [permissions.IsAuthenticated]
    
    class SearchAnalyticsSerializer(serializers.Serializer):
        statistics = serializers.DictField()
    
    serializer_class = SearchAnalyticsSerializer

    def get(self, request, *args, **kwargs):
        """Get search analytics statistics."""
        # Only admin users can access search analytics
        if not request.user.is_staff:
            return Response(
                {"detail": "Only admin users can access search analytics"},
                status=status.HTTP_403_FORBIDDEN,
            )

        days = request.query_params.get("days", 30)
        try:
            days = int(days)
        except (ValueError, TypeError):
            days = 30

        # Get search statistics
        stats = AdvancedSearchService.get_search_analytics(days=days)

        return Response({"statistics": stats})


class PopularSearchesView(UnifiedBaseGenericView, generics.ListAPIView):
    """Get popular search queries."""

    permission_classes = [permissions.AllowAny]
    
    class PopularSearchesSerializer(serializers.Serializer):
        popular_searches = serializers.ListField(child=serializers.CharField())
        count = serializers.IntegerField()
    
    serializer_class = PopularSearchesSerializer

    def list(self, request, *args, **kwargs):
        """Get popular search queries."""
        limit = request.query_params.get("limit", 10)
        try:
            limit = int(limit)
        except (ValueError, TypeError):
            limit = 10

        # Get popular searches
        popular_searches = AdvancedSearchService.get_popular_searches(limit=limit)

        return Response(
            {"popular_searches": popular_searches, "count": len(popular_searches)},
        )
