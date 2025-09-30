"""Standardized permission definitions for the HomeSer platform.
Defines permissions using django-guardian for object-level permissions.
"""

from django.contrib.contenttypes.models import ContentType
from guardian.shortcuts import assign_perm

from orders.models import Order
from payments.models import Payment
from services.models import Review, Service

from .models import User


def setup_permissions():
    """Setup initial permissions for the platform.
    This should be called during initial setup or migrations.
    """
    # Define permissions for User model
    ContentType.objects.get_for_model(User)

    # Define permissions for Service model
    ContentType.objects.get_for_model(Service)

    # Define permissions for Order model
    ContentType.objects.get_for_model(Order)

    # Define permissions for Review model
    ContentType.objects.get_for_model(Review)

    # Define permissions for Payment model
    ContentType.objects.get_for_model(Payment)


def assign_user_permissions(user):
    """Assign basic permissions to a user.
    """
    # Users can view and change their own profile
    assign_perm("accounts.view_user", user, user)
    assign_perm("accounts.change_user", user, user)


def assign_service_provider_permissions(user, service=None):
    """Assign service provider permissions to a user.
    If service is provided, assign specific service permissions.
    """
    # Service providers can add services
    assign_perm("services.add_service", user)

    # If a specific service is provided, assign permissions for that service
    if service:
        assign_perm("services.change_service", user, service)
        assign_perm("services.delete_service", user, service)


def assign_customer_permissions(user):
    """Assign customer permissions to a user.
    """
    # Customers can add orders and reviews
    assign_perm("orders.add_order", user)
    assign_perm("services.add_review", user)


def assign_order_permissions(user, order):
    """Assign permissions for a specific order to a user.
    """
    assign_perm("orders.view_order", user, order)
    assign_perm("orders.change_order", user, order)
    assign_perm("orders.delete_order", user, order)

    # Also assign payment permissions if order has payments
    for payment in order.payment_set.all():
        assign_perm("payments.view_payment", user, payment)
        assign_perm("payments.change_payment", user, payment)


def assign_review_permissions(user, review):
    """Assign permissions for a specific review to a user.
    """
    assign_perm("services.view_review", user, review)
    assign_perm("services.change_review", user, review)
    assign_perm("services.delete_review", user, review)


def is_service_owner(user, service):
    """Check if user is the owner of a service.
    """
    return user.has_perm("services.change_service", service)


def is_order_owner(user, order):
    """Check if user is the owner of an order.
    """
    return user.has_perm("orders.view_order", order)


def is_review_owner(user, review):
    """Check if user is the owner of a review.
    """
    return user.has_perm("services.view_review", review)
