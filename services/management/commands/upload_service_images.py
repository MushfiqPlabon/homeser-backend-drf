import os

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand

from services.models import Service


class Command(BaseCommand):
    help = "Uploads sample images to existing services"

    def add_arguments(self, parser):
        parser.add_argument(
            "--image-dir",
            type=str,
            default=os.path.join(
                settings.BASE_DIR,
                "..",
                "homeser-frontend-react",
                "public",
                "images",
            ),
            help="Directory containing service images",
        )

    def handle(self, *args, **options):
        image_dir = options["image_dir"]

        if not os.path.exists(image_dir):
            self.stdout.write(
                self.style.ERROR(f"Image directory does not exist: {image_dir}"),
            )
            return

        # Map service names to image files
        service_image_map = {
            "House Cleaning": "service_cleaning.png",
            "House Deep Cleaning": "service_cleaning.png",
            "Bathroom Cleaning": "service_cleaning.png",
            "Pipe Repair": "service_plumbing.png",
            "Toilet Installation": "service_plumbing.png",
            "Wiring Repair": "service_electrical.png",
            "Garden Maintenance": "service_plumbing.png",  # Using plumbing image as placeholder
            "Wall Painting": "service_cleaning.png",  # Using cleaning image as placeholder
        }

        self.stdout.write(self.style.SUCCESS("Uploading images to services..."))

        for service_name, image_filename in service_image_map.items():
            try:
                service = Service.objects.get(name=service_name)

                # Check if service already has an image
                if (
                    service.image
                    and hasattr(service.image, "name")
                    and service.image.name
                ):
                    self.stdout.write(
                        self.style.WARNING(
                            f"Service '{service_name}' already has an image. Skipping...",
                        ),
                    )
                    continue

                image_path = os.path.join(image_dir, image_filename)

                if not os.path.exists(image_path):
                    self.stdout.write(
                        self.style.WARNING(
                            f"Image file not found: {image_path}. Skipping...",
                        ),
                    )
                    continue

                # Upload image to service
                with open(image_path, "rb") as f:
                    django_file = File(f)
                    service.image.save(image_filename, django_file, save=True)

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Successfully uploaded image to service: {service_name}",
                    ),
                )

            except Service.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f"Service not found: {service_name}"),
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"Error uploading image to service '{service_name}': {e!s}",
                    ),
                )
                import traceback

                self.stdout.write(self.style.ERROR(traceback.format_exc()))

        self.stdout.write(self.style.SUCCESS("Image upload process completed!"))
