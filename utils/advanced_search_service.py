# utils/advanced_search_service.py
# Service to demonstrate advanced search using PostgreSQL full-text search (Vercel-compatible)

import logging
from collections import Counter
from datetime import timedelta

from django.core.cache import cache
from django.db import transaction
from django.db.models import Avg, Count, Q
from django.utils import timezone

from services.models import Service

from .models import PopularSearch, SearchAnalytics

logger = logging.getLogger(__name__)

# Constants for search analytics
SEARCH_ANALYTICS_CACHE_KEY = "search_analytics"
SEARCH_ANALYTICS_CACHE_TIMEOUT = 3600  # 1 hour
POPULAR_SEARCHES_CACHE_KEY = "popular_searches"
POPULAR_SEARCHES_CACHE_TIMEOUT = 86400  # 24 hours
MAX_POPULAR_SEARCHES = 100

# Supported languages for multi-language search
SUPPORTED_LANGUAGES = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "ru": "Russian",
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "ar": "Arabic",
    "hi": "Hindi",
}

# Language-specific stop words (simplified example)
STOP_WORDS = {
    "en": {
        "the",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "by",
    },
    "es": {"el", "la", "y", "o", "pero", "en", "de", "a", "para", "con", "por"},
    "fr": {
        "le",
        "la",
        "et",
        "ou",
        "mais",
        "dans",
        "sur",
        "à",
        "pour",
        "de",
        "avec",
        "par",
    },
}


class AdvancedSearchService:
    """Service for advanced search operations using PostgreSQL full-text search (Vercel-compatible)."""

    @staticmethod
    def get_postgresql_search_results(query, limit=20):
        """Get search results using PostgreSQL full-text search.

        Args:
            query (str): Search query
            limit (int): Maximum number of results

        Returns:
            QuerySet: Search results

        """
        # Import PostgreSQL-specific functions for full-text search
        try:
            from django.contrib.postgres.search import (
                SearchQuery,
                SearchRank,
                SearchVector,
            )

            # Create a search query
            search_query = SearchQuery(query)

            # Create a search vector combining multiple fields
            search_vector = (
                SearchVector("name", weight="A")
                + SearchVector("short_desc", weight="B")
                + SearchVector("description", weight="C")
            )

            # Perform the search with ranking
            results = (
                Service.objects.annotate(
                    search=search_vector,
                    rank=SearchRank(search_vector, search_query),
                )
                .filter(search=search_query, is_active=True)
                .order_by("-rank")[:limit]
            )

            return results
        except Exception as e:
            # Fallback to standard database search if PostgreSQL full-text search is not available
            logger.warning(
                f"PostgreSQL full-text search not available, using fallback: {e}",
            )
            return Service.objects.filter(
                Q(name__icontains=query)
                | Q(short_desc__icontains=query)
                | Q(description__icontains=query),
                is_active=True,
            ).annotate(
                review_count_val=Count("reviews"),
                avg_rating_val=Avg("reviews__rating"),
            )[:limit]

    @staticmethod
    def fast_service_lookup(service_id):
        """Fast lookup of service by ID using database.

        Args:
            service_id (int): Service ID to look up

        Returns:
            dict: Service data or None if not found

        """
        try:
            # Direct database lookup with proper prefetching to prevent N+1 queries
            service = (
                Service.objects.select_related("category")
                .prefetch_related("rating_aggregation")
                .get(id=service_id, is_active=True)
            )
            return {
                "id": service.id,
                "name": service.name,
                "description": service.description,
                "price": float(service.price),
                "image_url": service.image_url,
                "avg_rating": float(service.avg_rating),
                "review_count": service.review_count,
            }
        except Service.DoesNotExist:
            logger.warning(f"Service with id {service_id} not found")
            return None
        except Exception as e:
            logger.error(f"Error in fast_service_lookup for service {service_id}: {e}")
            return None

    @staticmethod
    def autocomplete_service_names(prefix, limit=10, language="en"):
        """Autocomplete service names using database search.

        Args:
            prefix (str): Prefix to search for
            limit (int): Maximum number of results
            language (str): Language code for search

        Returns:
            list: List of matching service names with data

        """
        try:
            # Validate language
            if language not in SUPPORTED_LANGUAGES:
                language = "en"  # Default to English

            # Direct database search using istartswith for prefix matching
            # Use proper prefetching to prevent N+1 queries when accessing ratings
            services = (
                Service.objects.select_related("category")
                .prefetch_related("rating_aggregation")
                .filter(name__istartswith=prefix, is_active=True)[:limit]
            )

            results = [
                {
                    "word": service.name.lower(),
                    "data": {
                        "id": service.id,
                        "description": service.short_desc,
                        "price": float(service.price),
                        "avg_rating": float(service.avg_rating)
                        if service.avg_rating
                        else 0.0,
                    },
                }
                for service in services
            ]
            return results
        except Exception as e:
            logger.error(
                f"Error in autocomplete_service_names for prefix '{prefix}': {e}",
            )
            # Fallback to a more general search in case istartswith fails
            try:
                services = (
                    Service.objects.select_related("category")
                    .prefetch_related("rating_aggregation")
                    .filter(
                        name__icontains=prefix,
                        is_active=True,
                    )[:limit]
                )

                results = []
                for service in services:
                    results.append(
                        {
                            "word": service.name.lower(),
                            "data": {
                                "id": service.id,
                                "description": service.short_desc,
                                "price": float(service.price),
                                "avg_rating": float(service.avg_rating)
                                if service.avg_rating
                                else 0.0,
                            },
                        },
                    )
                return results
            except Exception as db_e:
                logger.error(f"Error in fallback database search: {db_e}")
                return []

    @staticmethod
    def _track_search_query(
        query: str,
        language: str = "en",
        results_count: int = 0,
    ) -> None:
        """Track search queries for analytics.

        Args:
            query (str): The search query
            language (str): Language of the search
            results_count (int): Number of results returned

        """
        try:
            # Track in database
            with transaction.atomic():
                # Update or create search analytics record
                SearchAnalytics.objects.create(
                    query=query[:255],  # Truncate to max length
                    language=language,
                    results_count=results_count,
                )

                # Update popular search
                popular_search, created = PopularSearch.objects.get_or_create(
                    query=query[:255],  # Truncate to max length
                    language=language,
                    defaults={"search_count": 1, "last_searched": timezone.now()},
                )

                if not created:
                    popular_search.search_count += 1
                    popular_search.last_searched = timezone.now()
                    popular_search.save()

                # Keep only top popular searches
                if PopularSearch.objects.count() > MAX_POPULAR_SEARCHES * 2:
                    # Delete least popular searches, keeping only top MAX_POPULAR_SEARCHES
                    excess_searches = PopularSearch.objects.order_by("search_count")[
                        : PopularSearch.objects.count() - MAX_POPULAR_SEARCHES
                    ]
                    for search in excess_searches:
                        search.delete()

            # Track in cache for faster access
            # Track popular searches
            popular_searches = cache.get(POPULAR_SEARCHES_CACHE_KEY, {})
            search_key = f"{query.lower()}|{language}"

            if search_key in popular_searches:
                popular_searches[search_key]["count"] += 1
                popular_searches[search_key]["last_searched"] = (
                    timezone.now().isoformat()
                )
            else:
                popular_searches[search_key] = {
                    "query": query,
                    "language": language,
                    "count": 1,
                    "last_searched": timezone.now().isoformat(),
                    "results_count": results_count,
                }

            # Keep only top searches
            if len(popular_searches) > MAX_POPULAR_SEARCHES * 2:
                # Sort by count and keep top MAX_POPULAR_SEARCHES
                sorted_searches = sorted(
                    popular_searches.items(),
                    key=lambda x: x[1]["count"],
                    reverse=True,
                )
                popular_searches = dict(sorted_searches[:MAX_POPULAR_SEARCHES])

            cache.set(
                POPULAR_SEARCHES_CACHE_KEY,
                popular_searches,
                POPULAR_SEARCHES_CACHE_TIMEOUT,
            )

            # Track search analytics
            search_analytics = cache.get(
                SEARCH_ANALYTICS_CACHE_KEY,
                {
                    "total_searches": 0,
                    "total_results": 0,
                    "no_results_searches": 0,
                    "searches_by_language": {},
                    "searches_by_hour": {},
                    "popular_queries": Counter(),
                },
            )

            # Update counters
            search_analytics["total_searches"] += 1
            search_analytics["total_results"] += results_count
            if results_count == 0:
                search_analytics["no_results_searches"] += 1

            # Update language stats
            if language not in search_analytics["searches_by_language"]:
                search_analytics["searches_by_language"][language] = 0
            search_analytics["searches_by_language"][language] += 1

            # Update hourly stats
            current_hour = timezone.now().hour
            if current_hour not in search_analytics["searches_by_hour"]:
                search_analytics["searches_by_hour"][current_hour] = 0
            search_analytics["searches_by_hour"][current_hour] += 1

            # Update popular queries (keep top 50)
            search_analytics["popular_queries"][query.lower()] += 1
            if len(search_analytics["popular_queries"]) > 50:
                search_analytics["popular_queries"] = Counter(
                    dict(search_analytics["popular_queries"].most_common(50)),
                )

            cache.set(
                SEARCH_ANALYTICS_CACHE_KEY,
                search_analytics,
                SEARCH_ANALYTICS_CACHE_TIMEOUT,
            )
        except Exception as e:
            logger.error(f"Error tracking search query '{query}': {e}")

    @staticmethod
    def _preprocess_query(query: str, language: str = "en") -> str:
        """Preprocess search query for better matching.

        Args:
            query (str): Raw search query
            language (str): Language of the query

        Returns:
            str: Preprocessed query

        """
        # Convert to lowercase
        query = query.lower().strip()

        # Remove extra whitespace
        query = " ".join(query.split())

        # Remove stop words for the language if available
        if language in STOP_WORDS:
            words = query.split()
            filtered_words = [
                word for word in words if word not in STOP_WORDS[language]
            ]
            query = " ".join(filtered_words)

        return query

    @staticmethod
    def _multi_language_search(
        query: str,
        language: str = "en",
        limit: int = 20,
    ) -> list[dict]:
        """Perform search in a specific language.

        Args:
            query (str): Search query
            language (str): Language code
            limit (int): Maximum number of results

        Returns:
            list: List of matching services

        """
        try:
            # Preprocess query
            processed_query = AdvancedSearchService._preprocess_query(query, language)

            # For multi-language search, we would ideally have language-specific fields
            # For now, we'll search in the available fields
            services = Service.objects.filter(
                Q(name__icontains=processed_query)
                | Q(short_desc__icontains=processed_query)
                | Q(description__icontains=processed_query),
                is_active=True,
            ).annotate(
                review_count_val=Count("reviews"),
                avg_rating_val=Avg("reviews__rating"),
            )[:limit]

            results = [
                {
                    "id": service.id,
                    "name": service.name,
                    "description": service.short_desc,
                    "price": float(service.price),
                    "avg_rating": float(service.avg_rating_val)
                    if service.avg_rating_val
                    else 0.0,
                    "review_count": service.review_count_val,
                    "language": language,  # In a real implementation, this would be from the service data
                }
                for service in services
            ]

            return results
        except Exception as e:
            logger.error(
                f"Error in multi-language search for query '{query}' in language '{language}': {e}",
            )
            return []

    @staticmethod
    def search_services(query, limit=20, language="en"):
        """Search services using PostgreSQL full-text search (Vercel-compatible).

        Args:
            query (str): Search query
            limit (int): Maximum number of results
            language (str): Language code for search

        Returns:
            list: List of matching services

        """
        try:
            # Validate language
            if language not in SUPPORTED_LANGUAGES:
                language = "en"  # Default to English

            # Preprocess query
            processed_query = AdvancedSearchService._preprocess_query(query, language)

            # Get search results using PostgreSQL full-text search
            services = AdvancedSearchService.get_postgresql_search_results(
                processed_query,
                limit,
            )

            results = []
            for service in services:
                # Handle both full-text search results and fallback results
                if (
                    hasattr(service, "avg_rating_val")
                    and service.avg_rating_val is not None
                ):
                    avg_rating = float(service.avg_rating_val)
                    review_count = service.review_count_val
                else:
                    avg_rating = (
                        float(service.avg_rating) if service.avg_rating else 0.0
                    )
                    review_count = service.review_count

                results.append(
                    {
                        "id": service.id,
                        "name": service.name,
                        "description": service.short_desc,
                        "price": float(service.price),
                        "avg_rating": avg_rating,
                        "review_count": review_count,
                    },
                )

            # Track search with results count
            AdvancedSearchService._track_search_query(query, language, len(results))
            return results
        except Exception as e:
            logger.error(f"Error in search_services for query '{query}': {e}")
            # Track failed search
            AdvancedSearchService._track_search_query(query, language, 0)

            # Fallback to database search
            try:
                services = Service.objects.filter(
                    Q(name__icontains=query)
                    | Q(short_desc__icontains=query)
                    | Q(description__icontains=query),
                    is_active=True,
                ).annotate(
                    review_count_val=Count("reviews"),
                    avg_rating_val=Avg("reviews__rating"),
                )[:limit]

                results = []
                for service in services:
                    results.append(
                        {
                            "id": service.id,
                            "name": service.name,
                            "description": service.short_desc,
                            "price": float(service.price),
                            "avg_rating": float(service.avg_rating_val)
                            if service.avg_rating_val
                            else 0.0,
                            "review_count": service.review_count_val,
                        },
                    )

                return results
            except Exception as db_e:
                logger.error(f"Error in fallback database search: {db_e}")
                return []

    @staticmethod
    def get_search_analytics(days: int = 30) -> dict:
        """Get search analytics data.

        Args:
            days (int): Number of days to analyze

        Returns:
            dict: Search analytics data

        """
        try:
            # Calculate date range
            end_date = timezone.now()
            start_date = end_date - timedelta(days=days)

            # Get database analytics
            search_stats = SearchAnalytics.objects.filter(
                created_at__gte=start_date,
                created_at__lte=end_date,
            ).aggregate(
                total_searches=Count("id"),
                total_results=Avg("results_count"),
                no_results_searches=Count("id", filter=Q(results_count=0)),
            )

            # Get language distribution
            language_stats = (
                SearchAnalytics.objects.filter(
                    created_at__gte=start_date,
                    created_at__lte=end_date,
                )
                .values("language")
                .annotate(count=Count("id"))
                .order_by("-count")
            )

            # Get hourly distribution
            hourly_stats = (
                SearchAnalytics.objects.filter(
                    created_at__gte=start_date,
                    created_at__lte=end_date,
                )
                .extra(select={"hour": "EXTRACT(hour FROM created_at)"})
                .values("hour")
                .annotate(count=Count("id"))
                .order_by("hour")
            )

            # Get popular searches from database
            popular_searches_db = PopularSearch.objects.all()[:10]

            # Get cached analytics for additional data
            cached_analytics = cache.get(
                SEARCH_ANALYTICS_CACHE_KEY,
                {
                    "total_searches": 0,
                    "total_results": 0,
                    "no_results_searches": 0,
                    "searches_by_language": {},
                    "searches_by_hour": {},
                    "popular_queries": Counter(),
                },
            )

            # Calculate additional metrics
            total_searches = search_stats["total_searches"] or 0
            no_results_searches = search_stats["no_results_searches"] or 0

            success_rate = (
                ((total_searches - no_results_searches) / total_searches * 100)
                if total_searches > 0
                else 0
            )

            avg_results_per_search = search_stats["total_results"] or 0

            # Format language stats
            language_distribution = {
                item["language"]: item["count"] for item in language_stats
            }

            # Format hourly stats
            hourly_distribution = {
                int(item["hour"]): item["count"] for item in hourly_stats
            }

            # Get popular searches from cache
            popular_searches_cache = cache.get(POPULAR_SEARCHES_CACHE_KEY, {})

            # Get top 10 popular searches from cache
            top_searches_cache = sorted(
                popular_searches_cache.items(),
                key=lambda x: x[1]["count"],
                reverse=True,
            )[:10]

            return {
                "total_searches": total_searches,
                "no_results_searches": no_results_searches,
                "success_rate": round(success_rate, 2),
                "avg_results_per_search": round(avg_results_per_search, 2),
                "searches_by_language": language_distribution,
                "searches_by_hour": hourly_distribution,
                "top_popular_searches": [
                    {
                        "query": item[1]["query"],
                        "language": item[1]["language"],
                        "count": item[1]["count"],
                        "last_searched": item[1]["last_searched"],
                        "results_count": item[1]["results_count"],
                    }
                    for item in top_searches_cache
                ],
                "top_popular_searches_db": [
                    {
                        "query": item.query,
                        "language": item.language,
                        "count": item.search_count,
                        "last_searched": item.last_searched.isoformat()
                        if item.last_searched
                        else None,
                    }
                    for item in popular_searches_db
                ],
                "top_queries": dict(
                    cached_analytics["popular_queries"].most_common(10),
                ),
            }
        except Exception as e:
            logger.error(f"Error getting search analytics: {e}")
            return {"error": "Failed to retrieve search analytics"}

    @staticmethod
    def get_popular_searches(limit: int = 10) -> list[dict]:
        """Get popular search queries.

        Args:
            limit (int): Maximum number of results

        Returns:
            list: List of popular searches

        """
        try:
            # Try to get from database first
            popular_searches_db = PopularSearch.objects.all()[:limit]

            if popular_searches_db.exists():
                return [
                    {
                        "query": item.query,
                        "language": item.language,
                        "count": item.search_count,
                        "last_searched": item.last_searched.isoformat()
                        if item.last_searched
                        else None,
                    }
                    for item in popular_searches_db
                ]

            # Fallback to cache
            popular_searches = cache.get(POPULAR_SEARCHES_CACHE_KEY, {})

            # Sort by count and return top results
            sorted_searches = sorted(
                popular_searches.items(),
                key=lambda x: x[1]["count"],
                reverse=True,
            )[:limit]

            return [
                {
                    "query": item[1]["query"],
                    "language": item[1]["language"],
                    "count": item[1]["count"],
                    "last_searched": item[1]["last_searched"],
                    "results_count": item[1]["results_count"],
                }
                for item in sorted_searches
            ]
        except Exception as e:
            logger.error(f"Error getting popular searches: {e}")
            return []

    @staticmethod
    def clear_search_analytics() -> bool:
        """Clear search analytics data.

        Returns:
            bool: True if successful

        """
        try:
            cache.delete(SEARCH_ANALYTICS_CACHE_KEY)
            cache.delete(POPULAR_SEARCHES_CACHE_KEY)
            return True
        except Exception as e:
            logger.error(f"Error clearing search analytics: {e}")
            return False
