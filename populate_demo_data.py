#!/usr/bin/env python
"""
Script to populate the database with demo data for demonstration purposes
"""
import os
import sys
from pathlib import Path

# Add the project to the path
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

# Set the Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'homeser.settings')

import django
from django.contrib.auth import get_user_model
from django.core.management import execute_from_command_line

def populate_demo_data():
    django.setup()
    
    from services.models import ServiceCategory, Service
    from accounts.models import User
    from orders.models import Order, OrderItem
    
    User = get_user_model()
    
    print("Populating demo data...")
    
    # Create admin user
    admin_data = {
        'username': 'admin',
        'email': 'admin@example.com',
        'password': 'adminpass',
        'first_name': 'Admin',
        'last_name': 'User',
        'is_staff': True,
        'is_superuser': True
    }
    
    admin_user, created = User.objects.get_or_create(
        email=admin_data['email'],
        defaults={
            'username': admin_data['username'],
            'first_name': admin_data['first_name'],
            'last_name': admin_data['last_name'],
            'is_staff': True,
            'is_superuser': True
        }
    )
    if created:
        admin_user.set_password(admin_data['password'])
        admin_user.save()
        print(f"Created admin user: {admin_data['email']}")
    else:
        print(f"Admin user already exists: {admin_data['email']}")
    
    # Create regular users from credentials.txt
    regular_users_data = [
        {
            'username': 'rahman_khan',
            'email': 'rahman@example.com',
            'password': 'rahman123',
            'first_name': 'Rahman',
            'last_name': 'Khan'
        },
        {
            'username': 'akterara_begum',
            'email': 'aktera@example.com',
            'password': 'aktera123',
            'first_name': 'Aktera',
            'last_name': 'Begum'
        },
        {
            'username': 'ahmed_hossain',
            'email': 'ahmedh@example.com',
            'password': 'ahmed123',
            'first_name': 'Ahmed',
            'last_name': 'Hossain'
        },
        {
            'username': 'nasrin_akhter',
            'email': 'nasrin@example.com',
            'password': 'nasrin123',
            'first_name': 'Nasrin',
            'last_name': 'Akhter'
        },
        {
            'username': 'islam_chowdhury',
            'email': 'islamc@example.com',
            'password': 'islam123',
            'first_name': 'Islam',
            'last_name': 'Chowdhury'
        },
        {
            'username': 'tania_akter',
            'email': 'tania@example.com',
            'password': 'tania123',
            'first_name': 'Tania',
            'last_name': 'Akter'
        },
        {
            'username': 'karim_miah',
            'email': 'karim@example.com',
            'password': 'karim123',
            'first_name': 'Karim',
            'last_name': 'Miah'
        },
        {
            'username': 'farida_yasmin',
            'email': 'farida@example.com',
            'password': 'farida123',
            'first_name': 'Farida',
            'last_name': 'Yasmin'
        },
        {
            'username': 'mahmud_hasan',
            'email': 'mahmud@example.com',
            'password': 'mahmud123',
            'first_name': 'Mahmud',
            'last_name': 'Hasan'
        },
        {
            'username': 'sheuli_rani',
            'email': 'sheuli@example.com',
            'password': 'sheuli123',
            'first_name': 'Sheuli',
            'last_name': 'Rani'
        }
    ]
    
    for user_data in regular_users_data:
        user, created = User.objects.get_or_create(
            email=user_data['email'],
            defaults={
                'username': user_data['username'],
                'first_name': user_data['first_name'],
                'last_name': user_data['last_name']
            }
        )
        if created:
            user.set_password(user_data['password'])
            user.save()
            print(f"Created user: {user_data['email']}")
        else:
            print(f"User already exists: {user_data['email']}")
    
    # Create service categories
    categories_data = [
        {'name': 'Cleaning', 'description': 'Professional cleaning services for homes and offices'},
        {'name': 'Plumbing', 'description': 'Plumbing repairs and installations'},
        {'name': 'Electrical', 'description': 'Electrical repairs and installations'},
        {'name': 'AC Repair', 'description': 'Air conditioning repair and maintenance'},
        {'name': 'Furniture Assembly', 'description': 'Professional furniture assembly services'},
        {'name': 'Pest Control', 'description': 'Pest control and extermination services'},
        {'name': 'Gardening', 'description': 'Lawn care and gardening services'},
        {'name': 'Painting', 'description': 'Interior and exterior painting services'}
    ]
    
    created_categories = []
    for cat_data in categories_data:
        category, created = ServiceCategory.objects.get_or_create(
            name=cat_data['name'],
            defaults={'description': cat_data['description']}
        )
        created_categories.append(category)
        if created:
            print(f"Created category: {cat_data['name']}")
        else:
            print(f"Category already exists: {cat_data['name']}")
    
    # Create sample services
    services_data = [
        {
            'name': 'Home Deep Cleaning',
            'category': created_categories[0],
            'short_desc': 'Thorough deep cleaning of your home',
            'description': 'Professional deep cleaning service including all rooms, kitchen, bathrooms, and common areas. Includes dusting, vacuuming, mopping, and sanitizing.',
            'price': 150.00
        },
        {
            'name': 'Office Cleaning',
            'category': created_categories[0],
            'short_desc': 'Professional office cleaning service',
            'description': 'Regular office cleaning including desks, common areas, restrooms, and kitchenettes. Vacuuming, dusting, and sanitizing of all surfaces.',
            'price': 120.00
        },
        {
            'name': 'Bathroom Deep Clean',
            'category': created_categories[0],
            'short_desc': 'Specialized bathroom deep cleaning',
            'description': 'Deep cleaning of bathroom including toilet, shower, tub, sink, mirrors, and all surfaces. Sanitizing and disinfecting included.',
            'price': 80.00
        },
        {
            'name': 'Leak Repair',
            'category': created_categories[1],
            'short_desc': 'Fix water leaks in pipes and fixtures',
            'description': 'Professional repair of water leaks in pipes, faucets, and fixtures. Includes inspection, repair, and testing to ensure no further leaks.',
            'price': 75.00
        },
        {
            'name': 'Drain Unblocking',
            'category': created_categories[1],
            'short_desc': 'Unblock clogged drains',
            'description': 'Professional drain cleaning service to unblock clogged sinks, toilets, showers, and bathtubs. Includes use of specialized equipment.',
            'price': 65.00
        },
        {
            'name': 'Electrical Wiring',
            'category': created_categories[2],
            'short_desc': 'Residential electrical wiring service',
            'description': 'Professional electrical wiring installation and repair. Includes outlets, switches, lighting, and electrical panel work.',
            'price': 100.00
        },
        {
            'name': 'Light Installation',
            'category': created_categories[2],
            'short_desc': 'Ceiling and wall light installation',
            'description': 'Professional installation of ceiling lights, wall sconces, and other lighting fixtures. Includes wiring and testing.',
            'price': 50.00
        },
        {
            'name': 'AC Service',
            'category': created_categories[3],
            'short_desc': 'Air conditioning maintenance service',
            'description': 'Regular AC maintenance including cleaning, filter replacement, and performance check. Improves efficiency and extends unit life.',
            'price': 90.00
        },
        {
            'name': 'AC Repair',
            'category': created_categories[3],
            'short_desc': 'Air conditioning repair',
            'description': 'Professional AC repair service for cooling issues, leaks, and mechanical problems. Includes diagnosis and repair.',
            'price': 120.00
        },
        {
            'name': 'Ikea Furniture Assembly',
            'category': created_categories[4],
            'short_desc': 'Assembly of Ikea furniture',
            'description': 'Professional assembly of Ikea furniture including beds, cabinets, bookshelves, and more. Includes all tools and expertise.',
            'price': 85.00
        }
    ]
    
    for service_data in services_data:
        service, created = Service.objects.get_or_create(
            name=service_data['name'],
            category=service_data['category'],
            defaults={
                'short_desc': service_data['short_desc'],
                'description': service_data['description'],
                'price': service_data['price']
            }
        )
        if created:
            print(f"Created service: {service_data['name']}")
        else:
            print(f"Service already exists: {service_data['name']}")
    
    print("Demo data population completed!")
    print("\nCredentials from credentials.txt are now active in the system:")
    print("- Admin: admin@example.com / adminpass")
    print("- Regular users: [username]@[email] / [password] as listed in credentials.txt")

if __name__ == "__main__":
    populate_demo_data()