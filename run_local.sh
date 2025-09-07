#!/bin/bash

echo "Setting up Homeser Backend..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Run migrations
echo "Running migrations..."
python manage.py makemigrations
python manage.py migrate

# Create superuser if it doesn't exist
echo "Creating admin user..."
python manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(email='admin@example.com').exists():
    User.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='adminpass',
        first_name='Admin',
        last_name='User'
    )
    print('Admin user created: admin@example.com / adminpass')
else:
    print('Admin user already exists')
EOF

# Load sample data
echo "Loading sample data..."
python manage.py shell << EOF
from services.models import ServiceCategory, Service
from accounts.models import UserProfile
from django.contrib.auth import get_user_model

User = get_user_model()

# Create service categories
categories_data = [
    {'name': 'Cleaning', 'description': 'Home and office cleaning services'},
    {'name': 'Plumbing', 'description': 'Plumbing repair and installation'},
    {'name': 'Electrical', 'description': 'Electrical repair and installation'},
    {'name': 'Gardening', 'description': 'Garden maintenance and landscaping'},
    {'name': 'Painting', 'description': 'Interior and exterior painting'},
]

for cat_data in categories_data:
    category, created = ServiceCategory.objects.get_or_create(
        name=cat_data['name'],
        defaults={'description': cat_data['description']}
    )
    if created:
        print(f'Created category: {category.name}')

# Create sample services
services_data = [
    {'name': 'House Deep Cleaning', 'category': 'Cleaning', 'price': 2500, 'short_desc': 'Complete house cleaning service'},
    {'name': 'Bathroom Cleaning', 'category': 'Cleaning', 'price': 800, 'short_desc': 'Thorough bathroom cleaning'},
    {'name': 'Pipe Repair', 'category': 'Plumbing', 'price': 1200, 'short_desc': 'Fix leaky pipes and faucets'},
    {'name': 'Toilet Installation', 'category': 'Plumbing', 'price': 3000, 'short_desc': 'Install new toilet fixtures'},
    {'name': 'Wiring Repair', 'category': 'Electrical', 'price': 1500, 'short_desc': 'Fix electrical wiring issues'},
    {'name': 'Garden Maintenance', 'category': 'Gardening', 'price': 2000, 'short_desc': 'Regular garden upkeep'},
    {'name': 'Wall Painting', 'category': 'Painting', 'price': 5000, 'short_desc': 'Interior wall painting service'},
]

for service_data in services_data:
    try:
        category = ServiceCategory.objects.get(name=service_data['category'])
        service, created = Service.objects.get_or_create(
            name=service_data['name'],
            defaults={
                'category': category,
                'price': service_data['price'],
                'short_desc': service_data['short_desc'],
                'description': f"Professional {service_data['name'].lower()} service. High quality work guaranteed."
            }
        )
        if created:
            print(f'Created service: {service.name}')
    except ServiceCategory.DoesNotExist:
        print(f'Category {service_data["category"]} not found')

# Create profile for admin user
admin_user = User.objects.get(email='admin@example.com')
profile, created = UserProfile.objects.get_or_create(
    user=admin_user,
    defaults={'bio': 'System Administrator'}
)

print('Sample data loaded successfully!')
EOF

echo "Starting development server..."
python manage.py runserver