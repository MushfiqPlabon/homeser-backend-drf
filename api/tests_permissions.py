"""Tests for the UniversalObjectPermission class"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory

from .permissions import UniversalObjectPermission, is_owner

User = get_user_model()


@pytest.fixture
def test_users():
    """Create test users for use in tests"""
    user = User.objects.create_user(
        username="testuser_perm",
        email="test_perm@example.com",
        password="testpass123",
    )
    other_user = User.objects.create_user(
        username="otheruser_perm",
        email="other_perm@example.com",
        password="testpass123",
    )
    admin_user = User.objects.create_user(
        username="adminuser_perm",
        email="admin_perm@example.com",
        password="testpass123",
        is_staff=True,
    )
    return user, other_user, admin_user


@pytest.mark.django_db
def test_is_owner_helper_function(test_users):
    """Test the is_owner helper function"""
    user, other_user, _ = test_users

    # Create a simple object with user attribute
    class TestObject:
        def __init__(self, user):
            self.user = user

    obj_with_owner = TestObject(user)
    obj_without_owner = TestObject(other_user)

    # Test ownership check
    assert is_owner(user, obj_with_owner)
    assert not is_owner(other_user, obj_with_owner)
    assert not is_owner(user, obj_without_owner)


@pytest.mark.django_db
def test_universal_permission_authenticated_user_get():
    """Test that authenticated users can make GET requests"""
    factory = APIRequestFactory()

    user = User.objects.create_user(
        username="testuser_perm_get",
        email="test_perm_get@example.com",
        password="testpass123",
    )

    request = factory.get("/")
    request.user = user

    permission = UniversalObjectPermission()
    assert permission.has_permission(request, None)


@pytest.mark.django_db
def test_universal_permission_unauthenticated_user_get():
    """Test that unauthenticated users cannot make GET requests"""
    factory = APIRequestFactory()

    request = factory.get("/")
    request.user = None

    permission = UniversalObjectPermission()
    assert not permission.has_permission(request, None)


@pytest.mark.django_db
def test_universal_permission_authenticated_user_post():
    """Test that authenticated users can make POST requests"""
    factory = APIRequestFactory()

    user = User.objects.create_user(
        username="testuser_perm_post",
        email="test_perm_post@example.com",
        password="testpass123",
    )

    request = factory.post("/")
    request.user = user

    permission = UniversalObjectPermission()
    # For POST requests without a model_class, should allow authenticated users
    assert permission.has_permission(request, None)
