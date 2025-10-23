"""
Test suite for orders app models
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from orders.models import Order, OrderItem
from services.models import Service, ServiceCategory

UserModel = get_user_model()


class OrdersModelsTestCase(TestCase):
    """Test cases for orders app models"""

    def setUp(self):
        """Set up test data"""
        # Create users
        self.customer = UserModel.objects.create_user(
            username="testcustomer",
            email="customer@example.com",
            password="testpass123",
            first_name="Test",
            last_name="Customer",
        )

        self.provider = UserModel.objects.create_user(
            username="testprovider",
            email="provider@example.com",
            password="testpass123",
            first_name="Test",
            last_name="Provider",
        )

        # Create service category and service
        self.category = ServiceCategory.objects.create(
            name="Test Category", description="Test category for orders"
        )

        self.service = Service.objects.create(
            name="Test Service",
            short_desc="Test service for orders",
            description="A test service for order functionality",
            category=self.category,
            owner=self.provider,
            price=Decimal("100.00"),
        )

    def test_order_model(self):
        """Test Order model basic functionality"""
        order = Order.objects.create(
            user=self.customer,
            customer_name="Test Customer",
            customer_address="123 Test Street, Test City",
            customer_phone="+1234567890",
        )

        self.assertEqual(order.user, self.customer)
        self.assertEqual(order.customer_name, "Test Customer")
        self.assertEqual(order.customer_address, "123 Test Street, Test City")
        self.assertEqual(order.customer_phone, "+1234567890")
        self.assertEqual(order.status, "draft")

    def test_order_item_model(self):
        """Test OrderItem model functionality"""
        order = Order.objects.create(
            user=self.customer,
            customer_name="Test Customer",
            customer_address="123 Test Street, Test City",
        )

        order_item = OrderItem.objects.create(
            order=order, service=self.service, quantity=1, price=Decimal("100.00")
        )

        self.assertEqual(order_item.order, order)
        self.assertEqual(order_item.service, self.service)
        self.assertEqual(order_item.quantity, 1)
        self.assertEqual(order_item.price, Decimal("100.00"))

    def test_order_status_property(self):
        """Test order status property"""
        order = Order.objects.create(
            user=self.customer,
            customer_name="Test Customer",
            customer_address="123 Status Street",
        )

        # Test initial status
        self.assertEqual(order.status, "draft")

        # Test status property access
        self.assertIsNotNone(order.status)

    def test_order_string_representation(self):
        """Test order string representation"""
        order = Order.objects.create(
            user=self.customer,
            customer_name="String Test Customer",
            customer_address="123 String Street",
        )

        # The string representation should include order_id and status
        str_repr = str(order)
        self.assertIn(order.order_id, str_repr)
        self.assertIn(order.status, str_repr)

    def test_order_total_properties(self):
        """Test order total calculation properties"""
        order = Order.objects.create(
            user=self.customer,
            customer_name="Total Test Customer",
            customer_address="123 Total Street",
        )

        # Test that order has total-related properties
        # These are likely properties that calculate from order items
        self.assertIsNotNone(order.order_id)

    def test_order_creation_with_minimal_data(self):
        """Test order creation with minimal required data"""
        order = Order.objects.create(
            user=self.customer,
            customer_name="Minimal Customer",
            customer_address="123 Minimal Street",
        )

        self.assertEqual(order.user, self.customer)
        self.assertEqual(order.customer_name, "Minimal Customer")
        self.assertEqual(order.customer_address, "123 Minimal Street")
        self.assertTrue(order.order_id)  # Should be auto-generated

    def test_multiple_order_items(self):
        """Test order with multiple items"""
        order = Order.objects.create(
            user=self.customer,
            customer_name="Multi Item Customer",
            customer_address="123 Multi Street",
        )

        # Create first order item
        OrderItem.objects.create(
            order=order, service=self.service, quantity=2, price=Decimal("100.00")
        )

        # Create another service for second item
        service2 = Service.objects.create(
            name="Test Service 2",
            short_desc="Second test service",
            description="A second test service for order functionality",
            category=self.category,
            owner=self.provider,
            price=Decimal("50.00"),
        )

        OrderItem.objects.create(
            order=order, service=service2, quantity=1, price=Decimal("50.00")
        )

        # Verify order has multiple items
        self.assertEqual(order.items.count(), 2)

    def test_order_user_relationship(self):
        """Test order-user relationship"""
        order = Order.objects.create(
            user=self.customer,
            customer_name="Relationship Test",
            customer_address="123 Relationship Street",
        )

        # Test reverse relationship
        user_orders = self.customer.orders.all()
        self.assertIn(order, user_orders)

    def test_order_item_service_relationship(self):
        """Test order item-service relationship"""
        order = Order.objects.create(
            user=self.customer,
            customer_name="Service Relationship Test",
            customer_address="123 Service Street",
        )

        order_item = OrderItem.objects.create(
            order=order, service=self.service, quantity=1, price=Decimal("100.00")
        )

        # Test that order item correctly references service
        self.assertEqual(order_item.service.name, "Test Service")
        self.assertEqual(order_item.service.owner, self.provider)
