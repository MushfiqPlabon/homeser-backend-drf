"""
Test suite for services app models
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from services.models import Review, Service, ServiceCategory

UserModel = get_user_model()


class ServicesModelsTestCase(TestCase):
    """Test cases for services app models"""

    def test_service_category_model(self):
        """Test ServiceCategory model functionality"""
        # Create a service category
        category = ServiceCategory.objects.create(
            name="Cleaning Services",
            description="Professional cleaning services for homes and offices",
        )

        # Verify category was created correctly
        self.assertEqual(category.name, "Cleaning Services")
        self.assertEqual(
            category.description, "Professional cleaning services for homes and offices"
        )

    def test_service_model_creation(self):
        """Test Service model creation and basic functionality"""
        # Create a user for the service provider
        user = UserModel.objects.create_user(
            username="serviceprovider",
            email="provider@example.com",
            password="testpass123",
        )

        # Create a service category
        category = ServiceCategory.objects.create(
            name="Home Cleaning", description="Professional home cleaning services"
        )

        # Create a service
        service = Service.objects.create(
            name="Deep House Cleaning",
            short_desc="Comprehensive deep cleaning service",
            description="A thorough deep cleaning service for your entire home",
            category=category,
            owner=user,
            price=Decimal("100.00"),
        )

        self.assertEqual(service.name, "Deep House Cleaning")
        self.assertEqual(service.category, category)
        self.assertEqual(service.owner, user)
        self.assertEqual(service.price, Decimal("100.00"))
        self.assertTrue(service.is_active)

    def test_service_rating_properties(self):
        """Test service rating properties"""
        user = UserModel.objects.create_user(
            username="ratingprovider",
            email="rating@example.com",
            password="testpass123",
        )

        category = ServiceCategory.objects.create(
            name="Rating Test Category", description="Category for rating testing"
        )

        service = Service.objects.create(
            name="Rating Test Service",
            short_desc="Service for rating testing",
            description="A service to test rating functionality",
            category=category,
            owner=user,
            price=Decimal("100.00"),
        )

        # Test default rating values
        self.assertEqual(service.avg_rating, 0)
        self.assertEqual(service.review_count, 0)

    def test_service_image_url_property(self):
        """Test service image URL property"""
        user = UserModel.objects.create_user(
            username="imageprovider", email="image@example.com", password="testpass123"
        )

        category = ServiceCategory.objects.create(
            name="Image Test Category", description="Category for image testing"
        )

        service = Service.objects.create(
            name="Image Test Service",
            short_desc="Service for image testing",
            description="A service to test image functionality",
            category=category,
            owner=user,
            price=Decimal("75.00"),
        )

        # Test image URL when no image is set
        self.assertIsNone(service.image_url)

    def test_review_model_creation(self):
        """Test Review model creation and functionality"""
        # Create users
        provider = UserModel.objects.create_user(
            username="reviewprovider",
            email="reviewprovider@example.com",
            password="testpass123",
        )

        customer = UserModel.objects.create_user(
            username="reviewcustomer",
            email="reviewcustomer@example.com",
            password="testpass123",
        )

        # Create service
        category = ServiceCategory.objects.create(
            name="Review Test Category", description="Category for review testing"
        )

        service = Service.objects.create(
            name="Review Test Service",
            short_desc="Service for review testing",
            description="A service to test review functionality",
            category=category,
            owner=provider,
            price=Decimal("75.00"),
        )

        # Create review
        review = Review.objects.create(
            service=service,
            user=customer,
            rating=5,
            comment="Excellent service, highly recommended!",
        )

        self.assertEqual(review.service, service)
        self.assertEqual(review.user, customer)
        self.assertEqual(review.rating, 5)
        self.assertEqual(review.comment, "Excellent service, highly recommended!")

    def test_service_rating_cache_update(self):
        """Test service rating cache update functionality"""
        user = UserModel.objects.create_user(
            username="cacheprovider", email="cache@example.com", password="testpass123"
        )

        category = ServiceCategory.objects.create(
            name="Cache Test Category", description="Category for cache testing"
        )

        service = Service.objects.create(
            name="Cache Test Service",
            short_desc="Service for cache testing",
            description="A service to test cache functionality",
            category=category,
            owner=user,
            price=Decimal("50.00"),
        )

        # Test rating cache update
        rating = service.update_rating_cache()
        self.assertEqual(rating, 0)  # No reviews yet

    def test_service_string_representation(self):
        """Test service string representation"""
        user = UserModel.objects.create_user(
            username="stringprovider",
            email="string@example.com",
            password="testpass123",
        )

        category = ServiceCategory.objects.create(
            name="String Test Category", description="Category for string testing"
        )

        service = Service.objects.create(
            name="String Test Service",
            short_desc="Service for string testing",
            description="A service to test string representation",
            category=category,
            owner=user,
            price=Decimal("25.00"),
        )

        self.assertEqual(str(service), "String Test Service")

    def test_service_category_string_representation(self):
        """Test service category string representation"""
        category = ServiceCategory.objects.create(
            name="Category String Test",
            description="Testing category string representation",
        )

        self.assertEqual(str(category), "Category String Test")
