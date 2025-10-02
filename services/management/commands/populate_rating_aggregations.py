from django.core.management.base import BaseCommand
from django.db.models import Avg, Count

from services.models import Review, Service, ServiceRatingAggregation


class Command(BaseCommand):
    help = "Populate ServiceRatingAggregation table with initial data"

    def handle(self, *args, **options):
        self.stdout.write("Populating ServiceRatingAggregation table...")

        # Get all services
        services = Service.objects.all()

        for service in services:
            # Calculate the average and count
            aggregation = Review.objects.filter(service=service).aggregate(
                avg_rating=Avg("rating"),
                count=Count("id"),
            )

            # Create or update the ServiceRatingAggregation object
            ServiceRatingAggregation.objects.update_or_create(
                service=service,
                defaults={
                    "average": aggregation["avg_rating"] or 0,
                    "count": aggregation["count"] or 0,
                },
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully populated ServiceRatingAggregation for {services.count()} services",
            ),
        )
