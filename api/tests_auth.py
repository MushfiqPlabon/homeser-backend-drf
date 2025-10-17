"""
Test module for authentication flow functionality.
Tests user registration, login, logout, and token refresh operations.
"""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()


@pytest.mark.django_db
def test_user_registration_success():
    """Test successful user registration."""
    client = APIClient()
    url = reverse("register")

    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "TestPassword123!",
        "password_confirm": "TestPassword123!",
        "first_name": "Test",
        "last_name": "User",
    }

    response = client.post(url, user_data, format="json")

    assert response.status_code == status.HTTP_201_CREATED
    assert User.objects.count() == 1
    assert response.data["user"]["username"] == "testuser"
    assert "message" in response.data

    # Verify user object was created properly
    user = User.objects.get(username="testuser")
    assert user.email == "test@example.com"
    assert user.check_password("TestPassword123!")


@pytest.mark.django_db
def test_user_registration_password_mismatch():
    """Test registration failure with password mismatch."""
    client = APIClient()
    url = reverse("register")

    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "TestPassword123!",
        "password_confirm": "differentpassword123!",
        "first_name": "Test",
        "last_name": "User",
    }

    response = client.post(url, user_data, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert User.objects.count() == 0


@pytest.mark.django_db
def test_user_registration_weak_password():
    """Test registration failure with weak password."""
    client = APIClient()
    url = reverse("register")

    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "weak",
        "password_confirm": "weak",
        "first_name": "Test",
        "last_name": "User",
    }

    response = client.post(url, user_data, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert User.objects.count() == 0


@pytest.mark.django_db
def test_user_login_success():
    """Test successful user login."""
    client = APIClient()
    register_url = reverse("register")
    login_url = reverse("login")

    # First register a user
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "TestPassword123!",
        "password_confirm": "TestPassword123!",
        "first_name": "Test",
        "last_name": "User",
    }
    register_response = client.post(register_url, user_data, format="json")
    assert register_response.status_code == status.HTTP_201_CREATED

    # Then login with the registered user credentials
    login_data = {"username": "testuser", "password": "TestPassword123!"}
    response = client.post(login_url, login_data, format="json")

    assert response.status_code == status.HTTP_200_OK
    assert "message" in response.data
    assert response.data["message"] == "Login successful"


@pytest.mark.django_db
def test_user_login_invalid_credentials():
    """Test login failure with invalid credentials."""
    client = APIClient()
    login_url = reverse("login")

    login_data = {"username": "nonexistentuser", "password": "wrongpassword"}
    response = client.post(login_url, login_data, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_user_login_with_email():
    """Test successful login using email instead of username."""
    client = APIClient()
    register_url = reverse("register")
    login_url = reverse("login")

    # First register a user
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "TestPassword123!",
        "password_confirm": "TestPassword123!",
        "first_name": "Test",
        "last_name": "User",
    }
    register_response = client.post(register_url, user_data, format="json")
    assert register_response.status_code == status.HTTP_201_CREATED

    # Then login using email
    login_data = {"username": "test@example.com", "password": "TestPassword123!"}
    response = client.post(login_url, login_data, format="json")

    assert response.status_code == status.HTTP_200_OK
    assert "message" in response.data
    assert response.data["message"] == "Login successful"


@pytest.mark.django_db
def test_logout_success():
    """Test successful user logout."""
    client = APIClient()
    register_url = reverse("register")
    login_url = reverse("login")
    logout_url = reverse("logout")

    # First register and login a user
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "TestPassword123!",
        "password_confirm": "TestPassword123!",
        "first_name": "Test",
        "last_name": "User",
    }
    register_response = client.post(register_url, user_data, format="json")
    assert register_response.status_code == status.HTTP_201_CREATED

    login_data = {"username": "testuser", "password": "TestPassword123!"}
    login_response = client.post(login_url, login_data, format="json")
    assert login_response.status_code == status.HTTP_200_OK

    # Now logout
    if "access_token" in login_response.cookies:
        client.credentials(
            HTTP_AUTHORIZATION="Bearer " + login_response.cookies["access_token"].value
        )
    response = client.post(logout_url)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["message"] == "Logged out successfully"


@pytest.mark.django_db
def test_token_refresh_success():
    """Test successful token refresh."""
    client = APIClient()
    register_url = reverse("register")
    login_url = reverse("login")
    refresh_url = reverse("token_refresh")

    # First register and login a user
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "TestPassword123!",
        "password_confirm": "TestPassword123!",
        "first_name": "Test",
        "last_name": "User",
    }
    register_response = client.post(register_url, user_data, format="json")
    assert register_response.status_code == status.HTTP_201_CREATED

    login_data = {"username": "testuser", "password": "TestPassword123!"}
    login_response = client.post(login_url, login_data, format="json")
    assert login_response.status_code == status.HTTP_200_OK

    # Test token refresh using cookies
    refresh_response = client.post(refresh_url)
    assert refresh_response.status_code == status.HTTP_200_OK
    assert "message" in refresh_response.data
    assert refresh_response.data["message"] == "Token refreshed successfully"


@pytest.mark.django_db
def test_token_refresh_invalid_token():
    """Test token refresh with invalid token."""
    client = APIClient()
    refresh_url = reverse("token_refresh")

    # Test refresh with an invalid token
    invalid_refresh_data = {"refresh": "invalid_token_string"}
    response = client.post(refresh_url, invalid_refresh_data, format="json")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
