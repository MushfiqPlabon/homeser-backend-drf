#!/usr/bin/env python
"""
Script to populate the database with all demo data for demonstration purposes
Updated to meet current validation requirements while preserving original functionality
"""

import os
import sys
from pathlib import Path

# Add the project to the path
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

# Clear any conflicting environment variables
for var in ["dbname", "user", "password", "host", "port"]:
    if var in os.environ:
        del os.environ[var]

# Set the Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "homeser.settings")

import django  # noqa: E402


def populate_all_demo_data():
    django.setup()

    from accounts.models import User, UserProfile
    from orders.models import Order, OrderItem
    from services.models import (Review, Service, ServiceCategory,
                                 ServiceRatingAggregation)

    print("Populating all demo data...")

    # Create admin user with proper password validation
    admin_data = {
        "username": "admin",
        "email": "admin@example.com",
        "password": "AdminPass123!",  # Updated to meet validation requirements
        "first_name": "Admin",
        "last_name": "User",
        "is_staff": True,
        "is_superuser": True,
    }

    admin_user, created = User.objects.get_or_create(
        email=admin_data["email"],
        defaults={
            "username": admin_data["username"],
            "first_name": admin_data["first_name"],
            "last_name": admin_data["last_name"],
            "is_staff": True,
            "is_superuser": True,
        },
    )
    if created:
        admin_user.set_password(admin_data["password"])
        admin_user.save()
        # Create user profile
        UserProfile.objects.get_or_create(
            user=admin_user, defaults={"bio": "Demo admin profile"}
        )
        print(f"Created admin user: {admin_data['email']}")
    else:
        print(f"Admin user already exists: {admin_data['email']}")

    from django.contrib.auth.models import Group

    # Create groups
    admin_group, _ = Group.objects.get_or_create(name="admin")
    provider_group, _ = Group.objects.get_or_create(name="service_provider")
    customer_group, _ = Group.objects.get_or_create(name="customer")

    # Assign admin user to admin group
    admin_user.groups.add(admin_group)

    # Create regular users from credentials.txt with updated passwords
    regular_users_data = [
        {
            "username": "rahman_khan",
            "email": "rahman@example.com",
            "password": "Rahman123!",  # Updated password
            "first_name": "Rahman",
            "last_name": "Khan",
            "group": "service_provider",
        },
        {
            "username": "akterara_begum",
            "email": "aktera@example.com",
            "password": "Aktera123!",  # Updated password
            "first_name": "Aktera",
            "last_name": "Begum",
            "group": "customer",
        },
        {
            "username": "ahmed_hossain",
            "email": "ahmedh@example.com",
            "password": "Ahmed123!",  # Updated password
            "first_name": "Ahmed",
            "last_name": "Hossain",
            "group": "service_provider",
        },
        {
            "username": "nasrin_akhter",
            "email": "nasrin@example.com",
            "password": "Nasrin123!",  # Updated password
            "first_name": "Nasrin",
            "last_name": "Akhter",
            "group": "customer",
        },
        {
            "username": "islam_chowdhury",
            "email": "islamc@example.com",
            "password": "Islam123!",  # Updated password
            "first_name": "Islam",
            "last_name": "Chowdhury",
            "group": "customer",
        },
        {
            "username": "tania_akter",
            "email": "tania@example.com",
            "password": "Tania123!",  # Updated password
            "first_name": "Tania",
            "last_name": "Akter",
            "group": "customer",
        },
        {
            "username": "karim_miah",
            "email": "karim@example.com",
            "password": "Karim123!",  # Updated password
            "first_name": "Karim",
            "last_name": "Miah",
            "group": "service_provider",
        },
        {
            "username": "farida_yasmin",
            "email": "farida@example.com",
            "password": "Farida123!",  # Updated password
            "first_name": "Farida",
            "last_name": "Yasmin",
            "group": "customer",
        },
        {
            "username": "mahmud_hasan",
            "email": "mahmud@example.com",
            "password": "Mahmud123!",  # Updated password
            "first_name": "Mahmud",
            "last_name": "Hasan",
            "group": "customer",
        },
        {
            "username": "sheuli_rani",
            "email": "sheuli@example.com",
            "password": "Sheuli123!",  # Updated password
            "first_name": "Sheuli",
            "last_name": "Rani",
            "group": "customer",
        },
    ]

    for user_data in regular_users_data:
        user, created = User.objects.get_or_create(
            email=user_data["email"],
            defaults={
                "username": user_data["username"],
                "first_name": user_data["first_name"],
                "last_name": user_data["last_name"],
            },
        )
        if created:
            user.set_password(user_data["password"])
            user.save()
            # Create user profile
            UserProfile.objects.get_or_create(
                user=user, defaults={"bio": f"Demo user profile for {user.first_name}"}
            )
            print(f"Created user: {user_data['email']}")

        # Assign user to group
        if user_data["group"] == "service_provider":
            user.groups.add(provider_group)
        else:
            user.groups.add(customer_group)

    # Create service categories
    categories_data = [
        {
            "name": "Cleaning",
            "description": "Professional cleaning services for homes and offices",
        },
        {"name": "Plumbing", "description": "Plumbing repairs and installations"},
        {"name": "Electrical", "description": "Electrical repairs and installations"},
        {"name": "AC Repair", "description": "Air conditioning repair and maintenance"},
        {
            "name": "Furniture Assembly",
            "description": "Professional furniture assembly services",
        },
        {
            "name": "Pest Control",
            "description": "Pest control and extermination services",
        },
        {"name": "Gardening", "description": "Lawn care and gardening services"},
        {"name": "Painting", "description": "Interior and exterior painting services"},
    ]

    created_categories = []
    for cat_data in categories_data:
        category, created = ServiceCategory.objects.get_or_create(
            name=cat_data["name"], defaults={"description": cat_data["description"]}
        )
        created_categories.append(category)
        if created:
            print(f"Created category: {cat_data['name']}")
        else:
            print(f"Category already exists: {cat_data['name']}")

    # Create sample services with proper owner assignment
    services_data = [
        {
            "name": "Home Deep Cleaning",
            "category": created_categories[0],
            "short_desc": "Thorough deep cleaning of your home",
            "description": "Professional deep cleaning service including all rooms, kitchen, bathrooms, and common areas. Includes dusting, vacuuming, mopping, and sanitizing.",
            "price": 2500.00,  # BDT
        },
        {
            "name": "Office Cleaning",
            "category": created_categories[0],
            "short_desc": "Professional office cleaning service",
            "description": "Regular office cleaning including desks, common areas, restrooms, and kitchenettes. Vacuuming, dusting, and sanitizing of all surfaces.",
            "price": 2000.00,  # BDT
        },
        {
            "name": "Bathroom Deep Clean",
            "category": created_categories[0],
            "short_desc": "Specialized bathroom deep cleaning",
            "description": "Deep cleaning of bathroom including toilet, shower, tub, sink, mirrors, and all surfaces. Sanitizing and disinfecting included.",
            "price": 1200.00,  # BDT
        },
        {
            "name": "Leak Repair",
            "category": created_categories[1],
            "short_desc": "Fix water leaks in pipes and fixtures",
            "description": "Professional repair of water leaks in pipes, faucets, and fixtures. Includes inspection, repair, and testing to ensure no further leaks.",
            "price": 800.00,  # BDT
        },
        {
            "name": "Drain Unblocking",
            "category": created_categories[1],
            "short_desc": "Unblock clogged drains",
            "description": "Professional drain cleaning service to unblock clogged sinks, toilets, showers, and bathtubs. Includes use of specialized equipment.",
            "price": 600.00,  # BDT
        },
        {
            "name": "Electrical Wiring",
            "category": created_categories[2],
            "short_desc": "Residential electrical wiring service",
            "description": "Professional electrical wiring installation and repair. Includes outlets, switches, lighting, and electrical panel work.",
            "price": 1500.00,  # BDT
        },
        {
            "name": "Light Installation",
            "category": created_categories[2],
            "short_desc": "Ceiling and wall light installation",
            "description": "Professional installation of ceiling lights, wall sconces, and other lighting fixtures. Includes wiring and testing.",
            "price": 700.00,  # BDT
        },
        {
            "name": "AC Service",
            "category": created_categories[3],
            "short_desc": "Air conditioning maintenance service",
            "description": "Regular AC maintenance including cleaning, filter replacement, and performance check. Improves efficiency and extends unit life.",
            "price": 1800.00,  # BDT
        },
        {
            "name": "AC Repair",
            "category": created_categories[3],
            "short_desc": "Air conditioning repair",
            "description": "Professional AC repair service for cooling issues, leaks, and mechanical problems. Includes diagnosis and repair.",
            "price": 2500.00,  # BDT
        },
        {
            "name": "Furniture Assembly",
            "category": created_categories[4],
            "short_desc": "Professional furniture assembly service",
            "description": "Professional furniture assembly service for all types of furniture including beds, cabinets, bookshelves, and more. Includes all tools and expertise.",
            "price": 1000.00,  # BDT
        },
    ]

    created_services = []
    # Get admin user as default owner for services
    default_owner = User.objects.get(email="admin@example.com")

    for service_data in services_data:
        service, created = Service.objects.get_or_create(
            name=service_data["name"],
            category=service_data["category"],
            defaults={
                "short_desc": service_data["short_desc"],
                "description": service_data["description"],
                "price": service_data["price"],
                "owner": default_owner,  # Assign owner for the service
                "is_active": True,
            },
        )
        created_services.append(service)
        if created:
            print(f"Created service: {service_data['name']}")
        else:
            print(f"Service already exists: {service_data['name']}")

    # Sample review data
    review_texts = [
        "Excellent service! The technician was professional and completed the job on time.",
        "Very satisfied with the quality of work. Will definitely hire again.",
        "Good value for money. The service exceeded my expectations.",
        "The service was okay, but took longer than expected.",
        "Not bad, but there's room for improvement in attention to detail.",
        "Outstanding work! Highly recommend this service to others.",
        "Professional and courteous staff. Great experience overall.",
        "The service was decent, met my basic requirements.",
        "Impressed with the quick response time and quality of work.",
        "Satisfactory service, though communication could be better.",
    ]

    # Get users for review creation
    users = list(User.objects.all()[:5])  # Get first 5 users
    review_count = 0

    # Create sample orders for users to enable reviews
    order_count = 0

    # Create orders for users purchasing services, then create reviews
    for i, service in enumerate(
        created_services
    ):  # Create orders for all services, if needed for reviews
        user = users[i % len(users)]  # Rotate through users

        # Get or create the draft order for the user
        order, _ = Order.objects.get_or_create(
            user=user,
            _status="draft",
            defaults={
                "customer_name": f"{user.first_name} {user.last_name}",
                "customer_address": "Dhaka, Bangladesh",
                "customer_phone": "123-456-7890",
            },
        )

        # Add the service as an order item
        OrderItem.objects.create(
            order=order,
            service=service,
            quantity=1,
            unit_price=service.price,
        )

        print(f"Created order for user '{user.username}' for service '{service.name}'")
        order_count += 1

    print(f"Successfully created {order_count} demo orders to enable reviews!")

    # Create more reviews by iterating through services multiple times
    for i in range(
        len(created_services) * 2
    ):  # Create approximately 2 reviews per service
        service_idx = i % len(created_services)
        service = created_services[service_idx]
        user = users[i % len(users)]  # Rotate through users

        # Check if user has ordered this service before creating a review
        user_orders = Order.objects.filter(
            user=user,
            items__service=service,
        )

        if user_orders.exists():
            # User has purchased this service, so they can leave a review
            try:
                review, created = Review.objects.get_or_create(
                    service=service,
                    user=user,
                    defaults={
                        "rating": (
                            4 if i % 3 == 0 else 5
                        ),  # Mostly 5-star reviews with some 4-star
                        "text": review_texts[i % len(review_texts)],
                    },
                )
                if created:
                    print(
                        f"Created review for service '{service.name}' by user '{user.username}'"
                    )
                    review_count += 1
                else:
                    print(
                        f"Review already exists for service '{service.name}' by user '{user.username}'"
                    )
            except Exception as e:
                print(f"Error creating review for service {service.id}: {e}")
                continue
        else:
            # Create an order for this user-service combination to allow review
            order = Order.objects.create(
                user=user,
                customer_name=f"{user.first_name} {user.last_name}",
                customer_address="Dhaka, Bangladesh",
                customer_phone="123-456-7890",
            )

            # Add the service as an order item
            OrderItem.objects.create(
                order=order,
                service=service,
                quantity=1,
                unit_price=service.price,
            )

            # Now create the review
            try:
                review, created = Review.objects.get_or_create(
                    service=service,
                    user=user,
                    defaults={
                        "rating": 4 if i % 3 == 0 else 5,
                        "text": review_texts[i % len(review_texts)],
                    },
                )
                if created:
                    print(
                        f"Created review for service '{service.name}' by user '{user.username}'"
                    )
                    review_count += 1
                else:
                    print(
                        f"Review already exists for service '{service.name}' by user '{user.username}'"
                    )
            except Exception as e:
                print(f"Error creating review for service {service.id}: {e}")
                continue

    print(f"Successfully created {review_count} demo reviews!")

    # Recalculate rating aggregations for all services to ensure counts are accurate
    from django.db.models import Avg, Count

    for service in created_services:
        # Calculate average rating and count from all reviews for this service
        aggregation_data = Review.objects.filter(service=service).aggregate(
            avg_rating=Avg("rating"),
            count=Count("id"),
        )

        # Get or create the ServiceRatingAggregation object
        rating_aggregation, created = ServiceRatingAggregation.objects.get_or_create(
            service=service,
            defaults={
                "average": (
                    float(aggregation_data["avg_rating"])
                    if aggregation_data["avg_rating"] is not None
                    else 0
                ),
                "count": aggregation_data["count"] or 0,
            },
        )

        # If it already existed, update it
        if not created:
            rating_aggregation.average = (
                float(aggregation_data["avg_rating"])
                if aggregation_data["avg_rating"] is not None
                else 0
            )
            rating_aggregation.count = aggregation_data["count"] or 0
            rating_aggregation.save()

        print(
            f"Updated rating aggregation for service '{service.name}': avg={rating_aggregation.average}, count={rating_aggregation.count}"
        )

    print("\nDemo data population completed!")
    print("\nCredentials from credentials.txt are now active in the system:")
    print("- Admin: admin@example.com / AdminPass123!")
    print(
        "- Regular users: [username]@[email] / [Updated Password with validation] as listed above"
    )


if __name__ == "__main__":
    populate_all_demo_data()
