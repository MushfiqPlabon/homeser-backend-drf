from django.core.management.base import BaseCommand
from services.models import ServiceCategory, Service
from accounts.models import UserProfile
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = "Loads sample data for services, categories, and admin profile."

    def handle(self, *args, **options):
        User = get_user_model()

        # Create service categories
        categories_data = [
            {"name": "Cleaning", "description": "Home and office cleaning services"},
            {"name": "Plumbing", "description": "Plumbing repair and installation"},
            {"name": "Electrical", "description": "Electrical repair and installation"},
            {"name": "Gardening", "description": "Garden maintenance and landscaping"},
            {"name": "Painting", "description": "Interior and exterior painting"},
        ]

        self.stdout.write(self.style.SUCCESS("Creating service categories..."))
        for cat_data in categories_data:
            category, created = ServiceCategory.objects.get_or_create(
                name=cat_data["name"], defaults={"description": cat_data["description"]}
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f"Created category: {category.name}")
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f"Category already exists: {category.name}")
                )

        # Create sample services
        services_data = [
            {
                "name": "House Deep Cleaning",
                "category": "Cleaning",
                "price": 2500,
                "short_desc": "Complete house cleaning service",
            },
            {
                "name": "Bathroom Cleaning",
                "category": "Cleaning",
                "price": 800,
                "short_desc": "Thorough bathroom cleaning",
            },
            {
                "name": "Pipe Repair",
                "category": "Plumbing",
                "price": 1200,
                "short_desc": "Fix leaky pipes and faucets",
            },
            {
                "name": "Toilet Installation",
                "category": "Plumbing",
                "price": 3000,
                "short_desc": "Install new toilet fixtures",
            },
            {
                "name": "Wiring Repair",
                "category": "Electrical",
                "price": 1500,
                "short_desc": "Fix electrical wiring issues",
            },
            {
                "name": "Garden Maintenance",
                "category": "Gardening",
                "price": 2000,
                "short_desc": "Regular garden upkeep",
            },
            {
                "name": "Wall Painting",
                "category": "Painting",
                "price": 5000,
                "short_desc": "Interior wall painting service",
            },
        ]

        self.stdout.write(self.style.SUCCESS("Creating sample services..."))
        for service_data in services_data:
            try:
                category = ServiceCategory.objects.get(name=service_data["category"])
                service, created = Service.objects.get_or_create(
                    name=service_data["name"],
                    defaults={
                        "category": category,
                        "price": service_data["price"],
                        "short_desc": service_data["short_desc"],
                        "description": f"Professional {service_data['name'].lower()} service. High quality work guaranteed.",
                    },
                )
                if created:
                    self.stdout.write(
                        self.style.SUCCESS(f"Created service: {service.name}")
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f"Service already exists: {service.name}")
                    )
            except ServiceCategory.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(
                        f"Category {service_data['category']} not found for service {service_data['name']}"
                    )
                )

        # Create profile for admin user
        self.stdout.write(self.style.SUCCESS("Creating admin user profile..."))
        try:
            admin_user = User.objects.get(email="admin@example.com")
            profile, created = UserProfile.objects.get_or_create(
                user=admin_user, defaults={"bio": "System Administrator"}
            )
            if created:
                self.stdout.write(self.style.SUCCESS("Admin user profile created."))
            else:
                self.stdout.write(
                    self.style.WARNING("Admin user profile already exists.")
                )
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(
                    "Admin user (admin@example.com) not found. Please create superuser first."
                )
            )

        self.stdout.write(self.style.SUCCESS("Sample data loaded successfully!"))
