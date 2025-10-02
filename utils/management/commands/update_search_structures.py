# utils/management/commands/update_search_structures.py
# Management command to update search data structures when services change

import logging

from django.core.management.base import BaseCommand

from services.models import Service
from utils.advanced_data_structures import (
    service_bloom_filter,
    service_hash_table,
    service_name_trie,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Update search data structures when services are modified"

    def add_arguments(self, parser):
        parser.add_argument(
            "--service-id",
            type=int,
            help="Specific service ID to update (default: update all)",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Updating search data structures..."))

        try:
            # If a specific service ID is provided
            if options["service_id"]:
                services = Service.objects.filter(
                    id=options["service_id"],
                    is_active=True,
                )
                if not services.exists():
                    self.stdout.write(
                        self.style.ERROR(
                            f"Service with ID {options['service_id']} not found",
                        ),
                    )
                    return
            else:
                # Update all services
                services = Service.objects.filter(is_active=True)

            updated_count = 0
            for service in services:
                # Update hash table
                service_data = {
                    "id": service.id,
                    "name": service.name,
                    "description": service.description,
                    "price": float(service.price),
                    "image_url": service.image_url,
                    "avg_rating": float(service.avg_rating),
                    "review_count": service.review_count,
                }
                service_hash_table.set(service.id, service_data)

                # Update bloom filter
                service_bloom_filter.add(service.id)

                # Update trie
                service_name_trie.update_service_data(
                    service.name,
                    {
                        "id": service.id,
                        "description": service.short_desc,
                        "price": float(service.price),
                        "avg_rating": float(service.avg_rating)
                        if service.avg_rating
                        else 0.0,
                    },
                )

                updated_count += 1

            # Save trie to cache
            service_name_trie.save_to_cache()

            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully updated search structures for {updated_count} services.",
                ),
            )
        except Exception as e:
            logger.error(f"Error updating search structures: {e}")
            self.stdout.write(
                self.style.ERROR(f"Error updating search structures: {e}"),
            )
