from django.core.cache import cache
from django.core.management.base import BaseCommand

from services.models import Service


class Command(BaseCommand):
    help = "Clear service cache keys"

    def handle(self, *args, **options):
        # Clear common cache keys used by ServiceListView
        cache_keys_to_clear = [
            "services_list_default_page_1",
            "services_list_-avg_rating_page_1",
            "services_list_price_page_1",
            "services_list_-price_page_1",
            "services_list_name_page_1",
        ]

        # Also clear any pattern-based keys
        # Note: This is a simplified approach. In production, you might want to use a more sophisticated cache key management.

        for key in cache_keys_to_clear:
            cache.delete(key)
            self.stdout.write(f"Cleared cache key: {key}")

        # Clear all cache as a fallback
        cache.clear()
        self.stdout.write(self.style.SUCCESS("All cache cleared successfully!"))

        # Verify services exist
        service_count = Service.objects.filter(is_active=True).count()
        self.stdout.write(f"Active services in database: {service_count}")
