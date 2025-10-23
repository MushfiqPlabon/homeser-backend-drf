"""
Test suite for accounts app models
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import (BusinessCustomer, CustomerType,
                             GovernmentCustomer, IndividualCustomer)

UserModel = get_user_model()


class AccountsModelsTestCase(TestCase):
    """Test cases for accounts app models"""

    def test_user_model(self):
        """Test User model creation and basic functionality"""
        # Create a user
        user = UserModel.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            first_name="Test",
            last_name="User",
        )

        self.assertEqual(user.username, "testuser")
        self.assertEqual(user.email, "test@example.com")
        self.assertEqual(user.first_name, "Test")
        self.assertEqual(user.last_name, "User")
        self.assertTrue(user.check_password("testpass123"))

    def test_individual_customer_creation(self):
        """Test IndividualCustomer model creation"""
        user = UserModel.objects.create_user(
            username="individual",
            email="individual@example.com",
            password="testpass123",
        )

        customer = IndividualCustomer.objects.create(
            user=user,
            email="individual@example.com",
            first_name="John",
            last_name="Doe",
            phone="+1234567890",
        )

        self.assertEqual(customer.user, user)
        self.assertEqual(customer.customer_type, CustomerType.INDIVIDUAL)
        self.assertEqual(customer.first_name, "John")
        self.assertEqual(customer.last_name, "Doe")

    def test_business_customer_creation(self):
        """Test BusinessCustomer model creation"""
        user = UserModel.objects.create_user(
            username="business", email="business@example.com", password="testpass123"
        )

        customer = BusinessCustomer.objects.create(
            user=user,
            email="business@example.com",
            business_name="Test Business",
            tax_id="TAX123456",
            business_size="medium",
            employee_count=50,
        )

        self.assertEqual(customer.user, user)
        self.assertEqual(customer.customer_type, CustomerType.BUSINESS)
        self.assertEqual(customer.business_name, "Test Business")
        self.assertEqual(customer.tax_id, "TAX123456")

    def test_government_customer_creation(self):
        """Test GovernmentCustomer model creation"""
        user = UserModel.objects.create_user(
            username="government",
            email="government@example.com",
            password="testpass123",
        )

        customer = GovernmentCustomer.objects.create(
            user=user,
            email="government@example.com",
            government_entity_name="Test Department",
            government_id="GOV123456",
            department="IT Department",
            contact_person="Jane Smith",
            entity_type="federal",
        )

        self.assertEqual(customer.user, user)
        self.assertEqual(customer.customer_type, CustomerType.GOVERNMENT)
        self.assertEqual(customer.government_entity_name, "Test Department")
        self.assertEqual(customer.government_id, "GOV123456")

    def test_customer_discount_rates(self):
        """Test customer discount rate calculations"""
        # Test individual customer
        user1 = UserModel.objects.create_user(
            username="individual_discount",
            email="individual_discount@example.com",
            password="testpass123",
        )

        individual = IndividualCustomer.objects.create(
            user=user1,
            email="individual_discount@example.com",
            first_name="John",
            last_name="Doe",
        )

        self.assertEqual(individual.get_discount_rate(), Decimal("0.0"))

        # Test business customer
        user2 = UserModel.objects.create_user(
            username="business_discount",
            email="business_discount@example.com",
            password="testpass123",
        )

        business = BusinessCustomer.objects.create(
            user=user2,
            email="business_discount@example.com",
            business_name="Test Business",
            tax_id="TAX789",
            business_size="large",
            employee_count=100,
        )

        self.assertEqual(business.get_discount_rate(), Decimal("0.15"))

    def test_customer_service_fee_multipliers(self):
        """Test customer service fee multiplier calculations"""
        user = UserModel.objects.create_user(
            username="fee_test", email="fee_test@example.com", password="testpass123"
        )

        business = BusinessCustomer.objects.create(
            user=user,
            email="fee_test@example.com",
            business_name="Fee Test Business",
            tax_id="TAX999",
            business_size="medium",
            employee_count=25,
        )

        self.assertEqual(business.get_service_fee_multiplier(), Decimal("0.90"))

    def test_customer_profile_retrieval(self):
        """Test getting customer profile from user"""
        user = UserModel.objects.create_user(
            username="profile_test",
            email="profile_test@example.com",
            password="testpass123",
        )

        customer = IndividualCustomer.objects.create(
            user=user,
            email="profile_test@example.com",
            first_name="Profile",
            last_name="Test",
        )

        profile = user.get_customer_profile()
        self.assertEqual(profile, customer)
        self.assertIsInstance(profile, IndividualCustomer)
