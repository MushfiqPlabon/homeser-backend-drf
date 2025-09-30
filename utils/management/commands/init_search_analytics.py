# utils/management/commands/init_search_analytics.py
# Management command to initialize search analytics

import logging

from django.core.management.base import BaseCommand
from django.db import transaction

from utils.models import PopularSearch, SearchAnalytics

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Initialize search analytics tables and populate with sample data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing data before initializing",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Initializing search analytics..."))

        if options["clear"]:
            self.stdout.write("Clearing existing data...")
            SearchAnalytics.objects.all().delete()
            PopularSearch.objects.all().delete()

        # Create sample popular searches
        sample_searches = [
            {"query": "plumbing", "language": "en", "search_count": 150},
            {"query": "cleaning", "language": "en", "search_count": 120},
            {"query": "electrician", "language": "en", "search_count": 95},
            {"query": "carpentry", "language": "en", "search_count": 80},
            {"query": "painting", "language": "en", "search_count": 70},
        ]

        created_count = 0
        for search_data in sample_searches:
            try:
                with transaction.atomic():
                    PopularSearch.objects.get_or_create(
                        query=search_data["query"],
                        language=search_data["language"],
                        defaults={"search_count": search_data["search_count"]},
                    )
                created_count += 1
            except Exception as e:
                logger.error(
                    f"Error creating popular search '{search_data['query']}': {e}",
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully initialized search analytics. Created {created_count} popular searches.",
            ),
        )
