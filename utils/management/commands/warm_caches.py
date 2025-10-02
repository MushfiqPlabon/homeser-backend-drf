# utils/management/commands/warm_caches.py
# Management command to warm caches with popular data

import logging
import random

from django.core.management.base import BaseCommand

from accounts.models import User
from services.models import Service
from utils.cache_utils import warm_user_related_cache
from utils.caching_strategy import cache_warming_strategy, scheduled_cache_warming

# Configure logger
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Warm caches with popular data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--popular-services",
            type=int,
            default=10,
            help="Number of popular services to warm (default: 10)",
        )
        parser.add_argument(
            "--all-categories",
            action="store_true",
            help="Warm cache for all service categories",
        )
        parser.add_argument(
            "--random-users",
            type=int,
            default=5,
            help="Number of random users' data to warm (default: 5)",
        )
        parser.add_argument(
            "--user-profiles",
            type=int,
            default=0,
            help="Number of user profiles to warm",
        )
        parser.add_argument(
            "--service-reviews",
            type=int,
            default=0,
            help="Number of service reviews to warm",
        )
        parser.add_argument(
            "--run-scheduled",
            action="store_true",
            help="Run all scheduled cache warming tasks",
        )

    def handle(self, *args, **options):
        self.stdout.write("Starting cache warming process...")

        # Warm popular services
        popular_count = options["popular_services"]
        if popular_count > 0:
            self.stdout.write(
                f"Warming cache for top {popular_count} popular services...",
            )

            # Get popular services (for demo, we'll use random services)
            services = list(
                Service.objects.all()[: popular_count * 2],
            )  # Get more than needed
            if services:
                # Select random services as "popular"
                popular_service_ids = random.sample(
                    [s.id for s in services],
                    min(popular_count, len(services)),
                )

                if cache_warming_strategy.warm_popular_services(popular_service_ids):
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Successfully warmed cache for {len(popular_service_ids)} services",
                        ),
                    )
                else:
                    self.stdout.write(self.style.ERROR("Failed to warm service cache"))
            else:
                self.stdout.write("No services found to warm cache")

        # Warm service categories
        if options["all_categories"]:
            self.stdout.write("Warming cache for service categories...")
            if cache_warming_strategy.warm_service_categories():
                self.stdout.write(
                    self.style.SUCCESS(
                        "Successfully warmed cache for service categories",
                    ),
                )
            else:
                self.stdout.write(self.style.ERROR("Failed to warm category cache"))

        # Warm random user data
        random_users_count = options["random_users"]
        if random_users_count > 0:
            self.stdout.write(f"Warming cache for {random_users_count} random users...")
            users = list(User.objects.all())
            if users:
                # Select random users
                selected_users = random.sample(
                    users,
                    min(random_users_count, len(users)),
                )

                success_count = 0
                for user in selected_users:
                    if warm_user_related_cache(user.id):
                        success_count += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Successfully warmed cache for {success_count}/{len(selected_users)} users",
                    ),
                )
            else:
                self.stdout.write("No users found to warm cache")

        # Warm specific number of user profiles
        user_profiles_count = options["user_profiles"]
        if user_profiles_count > 0:
            self.stdout.write(
                f"Warming cache for {user_profiles_count} user profiles...",
            )
            if scheduled_cache_warming.warm_active_user_profiles(user_profiles_count):
                self.stdout.write(
                    self.style.SUCCESS("Successfully warmed user profiles"),
                )
            else:
                self.stdout.write(self.style.ERROR("Failed to warm user profiles"))

        # Warm service reviews
        service_reviews_count = options["service_reviews"]
        if service_reviews_count > 0:
            self.stdout.write(
                f"Warming cache for reviews of {service_reviews_count} services...",
            )
            services = list(Service.objects.all())
            if services:
                # Select random services
                selected_services = random.sample(
                    services,
                    min(service_reviews_count, len(services)),
                )

                success_count = 0
                for service in selected_services:
                    if cache_warming_strategy.warm_service_reviews(service.id):
                        success_count += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Successfully warmed reviews for {success_count}/{len(selected_services)} services",
                    ),
                )
            else:
                self.stdout.write("No services found to warm reviews cache")

        # Run scheduled cache warming tasks
        if options["run_scheduled"]:
            self.stdout.write("Running all scheduled cache warming tasks...")
            results = scheduled_cache_warming.warm_all_service_categories()
            if results:
                self.stdout.write(
                    self.style.SUCCESS(
                        "Successfully ran scheduled cache warming tasks"
                    ),
                )
            else:
                self.stdout.write(
                    self.style.ERROR("Failed to run scheduled cache warming tasks"),
                )

        self.stdout.write(self.style.SUCCESS("Cache warming process completed"))
