# utils/management/commands/populate_advanced_structures.py
# Management command to populate advanced data structures

from django.core.management.base import BaseCommand

from utils.populate_advanced_structures import run_population


class Command(BaseCommand):
    help = "Populate advanced data structures with initial data"

    def handle(self, *args, **options):
        self.stdout.write("Populating advanced data structures...")

        try:
            run_population()
            self.stdout.write(
                self.style.SUCCESS("Successfully populated advanced data structures"),
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error populating advanced data structures: {e}"),
            )
