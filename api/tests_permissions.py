"""Tests for the UniversalObjectPermission class"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIRequestFactory

from .permissions import (
    UniversalObjectPermission,
    is_owner,
)

User = get_user_model()


class UniversalObjectPermissionTestCase(TestCase):
    """Test cases for UniversalObjectPermission class"""

    def setUp(self):
        """Set up test data"""
        self.factory = APIRequestFactory()

        # Create users
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        self.other_user = User.objects.create_user(
            username="otheruser",
            email="other@example.com",
            password="testpass123",
        )
        self.admin_user = User.objects.create_user(
            username="adminuser",
            email="admin@example.com",
            password="testpass123",
            is_staff=True,
        )

    def test_is_owner_helper_function(self):
        """Test the is_owner helper function"""

        # Create a simple object with user attribute
        class TestObject:
            def __init__(self, user):
                self.user = user

        obj_with_owner = TestObject(self.user)
        obj_without_owner = TestObject(self.other_user)

        # Test ownership check
        self.assertTrue(is_owner(self.user, obj_with_owner))
        self.assertFalse(is_owner(self.other_user, obj_with_owner))
        self.assertFalse(is_owner(self.user, obj_without_owner))

    def test_universal_permission_authenticated_user_get(self):
        """Test that authenticated users can make GET requests"""
        request = self.factory.get("/")
        request.user = self.user

        permission = UniversalObjectPermission()
        self.assertTrue(permission.has_permission(request, None))

    def test_universal_permission_unauthenticated_user_get(self):
        """Test that unauthenticated users cannot make GET requests"""
        request = self.factory.get("/")
        request.user = None

        permission = UniversalObjectPermission()
        self.assertFalse(permission.has_permission(request, None))

    def test_universal_permission_authenticated_user_post(self):
        """Test that authenticated users can make POST requests"""
        request = self.factory.post("/")
        request.user = self.user

        permission = UniversalObjectPermission()
        # For POST requests without a model_class, should allow authenticated users
        self.assertTrue(permission.has_permission(request, None))
