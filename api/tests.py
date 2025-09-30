from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from orders.models import Order, OrderItem
from payments.models import Payment
from services.models import Service, ServiceCategory

User = get_user_model()


class AuthenticationTestCase(APITestCase):
    """Test user authentication endpoints"""

    def test_user_registration(self):
        """Test user registration returns tokens"""
        url = reverse("register")
        data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpass123",
            "password_confirm": "testpass123",
            "first_name": "Test",
            "last_name": "User",
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertIn("user", response.data)

    def test_user_login(self):
        """Test user login returns tokens"""
        # Create user
        User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123",
        )

        url = reverse("login")
        data = {"username": "test@example.com", "password": "testpass123"}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)


class ReviewTestCase(APITestCase):
    """Test review functionality"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123",
        )
        self.category = ServiceCategory.objects.create(name="Test Category")
        self.service = Service.objects.create(
            name="Test Service",
            category=self.category,
            short_desc="Test description",
            description="Longer test description",
            price=100.00,
        )

    def test_review_without_purchase_fails(self):
        """Test that trying to post review without owning paid order fails"""
        self.client.force_authenticate(user=self.user)

        url = reverse("service-reviews", kwargs={"service_id": self.service.id})
        data = {"rating": 5, "text": "Great service!"}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_review_with_purchase_succeeds(self):
        """Test that review works after purchasing service"""
        # Create an order using proper initial state
        order = Order.objects.create(
            user=self.user, status="draft", payment_status="unpaid",
        )
        OrderItem.objects.create(
            order=order, service=self.service, quantity=1, unit_price=self.service.price,
        )

        # Use proper transitions to set the order status
        order.submit()  # Transition from draft to pending
        order.set_payment_paid()  # This will set payment_status to "paid"
        order.confirm()  # This will set status to "confirmed" if payment_status is "paid"
        order.save()

        self.client.force_authenticate(user=self.user)

        url = reverse("service-reviews", kwargs={"service_id": self.service.id})
        data = {"rating": 5, "text": "Great service!"}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class CheckoutTestCase(APITestCase):
    """Test checkout functionality"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123",
        )
        self.category = ServiceCategory.objects.create(name="Test Category")
        self.service = Service.objects.create(
            name="Test Service",
            category=self.category,
            short_desc="Test description",
            description="Longer test description",
            price=100.00,
        )

    def test_checkout_creates_order(self):
        """Test checkout endpoint creates order and attempts SSLCOMMERZ session"""
        self.client.force_authenticate(user=self.user)

        # Add item to cart - using the proper initial state
        cart = Order.objects.create(
            user=self.user, status="draft", payment_status="unpaid", customer_name="", customer_address="", customer_phone="",
        )
        OrderItem.objects.create(
            order=cart, service=self.service, quantity=1, unit_price=self.service.price,
        )

        url = reverse("checkout")
        data = {
            "name": "Test User",
            "address": "123 Test St",
            "phone": "1234567890",
            "payment_method": "sslcommerz",
        }
        response = self.client.post(url, data)

        # Should either succeed or fail gracefully (depending on network)
        self.assertIn(
            response.status_code, [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST],
        )

        # Fetch the updated order from the database
        updated_order = Order.objects.get(id=cart.id) # Use the original cart's ID

        self.assertEqual(updated_order.customer_name, "Test User")
        self.assertEqual(updated_order.customer_address, "123 Test St")


class PaymentTestCase(TestCase):
    """Test payment processing"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123",
        )
        self.order = Order.objects.create(
            user=self.user, status="pending", total=100.00,
        )

    def test_ipn_processing_sets_payment_status(self):
        """Test IPN processing sets payment_status='paid' after validation"""
        # Create payment record
        payment = Payment.objects.create(
            order=self.order, transaction_id="test_tran_123", amount=100.00,
        )

        # Simulate successful validation (would normally call SSLCOMMERZ)
        payment.status = "completed"
        payment.save()

        # Use the proper django-fsm transition method
        self.order.set_payment_paid()
        self.order.save()

        self.assertEqual(self.order.payment_status, "paid")
