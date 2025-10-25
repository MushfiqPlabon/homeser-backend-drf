# utils/populate_advanced_structures.py
# Service to populate advanced data structures with initial data

import logging

from django.db.models import Avg

from services.models import Service
from utils.advanced_data_structures import (service_bloom_filter,
                                            service_hash_table,
                                            service_name_trie,
                                            service_rating_segment_tree)

logger = logging.getLogger(__name__)


def populate_service_hash_table(batch_size=1000):
    """Populate the service hash table with all active services using batch processing to optimize memory usage."""
    try:
        # Get the count first
        total_services = Service.objects.filter(is_active=True).count()
        logger.info(
            f"Starting to populate service hash table with {total_services} services",
        )

        # Process services in batches to minimize memory usage
        offset = 0
        processed_count = 0

        while offset < total_services:
            services_batch = (
                Service.objects.filter(is_active=True)
                .annotate(avg_rating_val=Avg("reviews__rating"))
                .order_by("id")[offset : offset + batch_size]
            )

            if not services_batch:
                break

            for service in services_batch:
                service_data = {
                    "id": service.id,
                    "name": service.name,
                    "description": service.description,
                    "price": float(service.price),
                    "image_url": service.image_url,
                    "avg_rating": (
                        float(service.avg_rating_val) if service.avg_rating_val else 0.0
                    ),
                    "review_count": service.review_count,
                }
                service_hash_table.set(service.id, service_data)

            processed_count += len(services_batch)
            logger.info(
                f"Processed {processed_count}/{total_services} services for hash table",
            )

            offset += batch_size

        logger.info(
            f"Successfully populated service hash table with {processed_count} services",
        )
        return True
    except Exception as e:
        logger.error(f"Error populating service hash table: {e}")
        return False


def populate_service_bloom_filter(batch_size=10000):
    """Populate the service Bloom filter with all service IDs using batch processing to optimize memory usage."""
    try:
        total_service_ids = Service.objects.filter(is_active=True).count()
        logger.info(
            f"Starting to populate service Bloom filter with {total_service_ids} service IDs",
        )

        # Process service IDs in batches to minimize memory usage
        offset = 0
        processed_count = 0

        while offset < total_service_ids:
            service_ids_batch = list(
                Service.objects.filter(is_active=True)
                .order_by("id")
                .values_list("id", flat=True)[offset : offset + batch_size],
            )

            if not service_ids_batch:
                break

            # Use the available add method instead of bulk_add
            for service_id in service_ids_batch:
                service_bloom_filter.add(service_id)

            processed_count += len(service_ids_batch)
            logger.info(
                f"Processed {processed_count}/{total_service_ids} service IDs for Bloom filter",
            )

            offset += batch_size

        logger.info(
            f"Successfully populated service Bloom filter with {processed_count} service IDs",
        )
        return True
    except Exception as e:
        logger.error(f"Error populating service Bloom filter: {e}")
        return False


def populate_service_name_trie():
    """Populate the service name trie with all service names."""
    try:
        # Get all active services
        services = Service.objects.filter(is_active=True).only("id", "name")

        # Insert each service name into the trie
        for service in services:
            service_name_trie.insert(service.name, {"id": service.id})

        logger.info(
            f"Successfully populated service name trie with {len(services)} service names"
        )
        return True
    except Exception as e:
        logger.error(f"Error populating service name trie: {e}")
        return False


def populate_service_rating_segment_tree():
    """Populate the service rating segment tree with service ratings."""
    try:
        # Get all active services with their ratings using the annotated field
        services = (
            Service.objects.filter(is_active=True)
            .annotate(avg_rating_val=Avg("reviews__rating"))
            .only("id")
        )

        # Create a list of ratings for the segment tree
        ratings_data = []
        for service in services:
            # Use the annotated value or 0 if no reviews
            rating = (
                float(service.avg_rating_val)
                if service.avg_rating_val is not None
                else 0.0
            )
            ratings_data.append(rating)

        # Update the segment tree with the ratings data
        service_rating_segment_tree.data = ratings_data

        logger.info(
            f"Successfully populated service rating segment tree with {len(ratings_data)} service ratings"
        )
        return True
    except Exception as e:
        logger.error(f"Error populating service rating segment tree: {e}")
        return False


def populate_all_advanced_structures():
    """Populate all advanced data structures."""
    logger.info("Starting population of advanced data structures")

    success_count = 0
    total_count = 4

    if populate_service_hash_table():
        success_count += 1

    if populate_service_bloom_filter():
        success_count += 1

    if populate_service_name_trie():
        success_count += 1

    if populate_service_rating_segment_tree():
        success_count += 1

    logger.info(
        f"Completed population of advanced data structures: "
        f"{success_count}/{total_count} successful",
    )

    return success_count == total_count


# Management command to run this function
def run_population():
    """Run the population function."""
    if populate_all_advanced_structures():
        print("Successfully populated all advanced data structures")
    else:
        print("Some errors occurred while populating advanced data structures")
