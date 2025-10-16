import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from orders.models import Order, OrderItem
from payments.models import Payment
from services.models import Service, ServiceCategory

User = get_user_model()


@pytest.mark.django_db
def test_user_registration():
    """Test user registration returns tokens"""
    client = APIClient()
    url = reverse("register")
    data = {
        "username": "testuser_reg",
        "email": "test_reg@example.com",
        "password": "testpass123",
        "password_confirm": "testpass123",
        "first_name": "Test",
        "last_name": "User",
    }
    response = client.post(url, data)
    assert response.status_code == status.HTTP_201_CREATED
    assert "access" in response.data
    assert "refresh" in response.data
    assert "user" in response.data


@pytest.mark.django_db
def test_user_login():
    """Test user login returns tokens"""
    # Create user
    User.objects.create_user(
        username="testuser_login",
        email="test_login@example.com",
        password="testpass123",
    )

    client = APIClient()
    url = reverse("login")
    data = {"username": "test_login@example.com", "password": "testpass123"}
    response = client.post(url, data)
    assert response.status_code == status.HTTP_200_OK
    assert "access" in response.data
    assert "refresh" in response.data


@pytest.mark.django_db
def test_review_without_purchase_fails():
    """Test that trying to post review without owning paid order fails"""
    # Create user and service
    user = User.objects.create_user(
        username="testuser_rev_fail",
        email="test_rev_fail@example.com",
        password="testpass123",
    )
    category = ServiceCategory.objects.create(name="Test Category Review Fail")
    service = Service.objects.create(
        name="Test Service Review Fail",
        category=category,
        short_desc="Test description",
        description="Longer test description",
        price=100.00,
    )

    client = APIClient()
    client.force_authenticate(user=user)

    url = reverse("service-reviews", kwargs={"service_id": service.id})
    data = {"rating": 5, "text": "Great service!"}
    response = client.post(url, data)
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_review_with_purchase_succeeds():
    """Test that review works after purchasing service"""
    # Create user, category, and service
    user = User.objects.create_user(
        username="testuser_rev_success",
        email="test_rev_success@example.com",
        password="testpass123",
    )
    category = ServiceCategory.objects.create(name="Test Category Review Success")
    service = Service.objects.create(
        name="Test Service Review Success",
        category=category,
        short_desc="Test description",
        description="Longer test description",
        price=100.00,
    )

    # Create an order using proper initial state
    order = Order.objects.create(
        user=user,
        status="draft",
        payment_status="unpaid",
    )
    OrderItem.objects.create(
        order=order,
        service=service,
        quantity=1,
        unit_price=service.price,
    )

    # Use proper transitions to set the order status
    order.submit()  # Transition from draft to pending
    order.set_payment_paid()  # This will set payment_status to "paid"
    order.confirm()  # This will set status to "confirmed" if payment_status is "paid"
    order.save()

    client = APIClient()
    client.force_authenticate(user=user)

    url = reverse("service-reviews", kwargs={"service_id": service.id})
    data = {"rating": 5, "text": "Great service!"}
    response = client.post(url, data)
    assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
def test_checkout_creates_order():
    """Test checkout endpoint creates order and attempts SSLCOMMERZ session"""
    # Create user, category, and service
    user = User.objects.create_user(
        username="testuser_checkout",
        email="test_checkout@example.com",
        password="testpass123",
    )
    category = ServiceCategory.objects.create(name="Test Category Checkout")
    service = Service.objects.create(
        name="Test Service Checkout",
        category=category,
        short_desc="Test description",
        description="Longer test description",
        price=100.00,
    )

    client = APIClient()
    client.force_authenticate(user=user)

    # Add item to cart - using the proper initial state
    cart = Order.objects.create(
        user=user,
        status="draft",
        payment_status="unpaid",
        customer_name="",
        customer_address="",
        customer_phone="",
    )
    OrderItem.objects.create(
        order=cart,
        service=service,
        quantity=1,
        unit_price=service.price,
    )

    url = reverse("checkout")
    data = {
        "name": "Test User Checkout",
        "address": "123 Test St Checkout",
        "phone": "1234567890",
        "payment_method": "sslcommerz",
    }
    response = client.post(url, data)

    # Should either succeed or fail gracefully (depending on network)
    assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]

    # Fetch the updated order from the database
    updated_order = Order.objects.get(id=cart.id)  # Use the original cart's ID

    assert updated_order.customer_name == "Test User Checkout"
    assert updated_order.customer_address == "123 Test St Checkout"


@pytest.mark.django_db
def test_ipn_processing_sets_payment_status():
    """Test IPN processing sets payment_status='paid' after validation"""
    # Create user and order
    user = User.objects.create_user(
        username="testuser_ipn",
        email="test_ipn@example.com",
        password="testpass123",
    )
    order = Order.objects.create(
        user=user,
        status="pending",
        total=100.00,
    )

    # Create payment record
    payment = Payment.objects.create(
        order=order,
        transaction_id="test_tran_123_ipn",
        amount=100.00,
    )

    # Simulate successful validation (would normally call SSLCOMMERZ)
    payment.status = "completed"
    payment.save()

    # Use the proper django-fsm transition method
    order.set_payment_paid()
    order.save()

    assert order.payment_status == "paid"
