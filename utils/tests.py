"""
Test suite for utils module
"""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from utils.validation_utils import (validate_email_format, validate_name,
                                    validate_phone, validate_positive_price,
                                    validate_rating, validate_text_length)


class UtilsTestCase(TestCase):
    """Test cases for utils module"""

    def test_validate_email_format(self):
        """Test email format validation utility"""
        # Test valid email formats
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "user+tag@example.org",
            "firstname.lastname@subdomain.example.com",
        ]

        for email in valid_emails:
            self.assertEqual(validate_email_format(email), email)

        # Test invalid email formats
        invalid_emails = [
            "invalid-email",
            "@example.com",
            "test@",
            "test@.com",
            "test@example.",
        ]

        for email in invalid_emails:
            with self.assertRaises(ValidationError):
                validate_email_format(email)

    def test_name_validation(self):
        """Test name validation utility"""
        # Test valid names (only basic ASCII letters, spaces, hyphens, apostrophes)
        valid_names = [
            "John",
            "Mary Jane",
            "Jean-Pierre",
            "O'Connor",
        ]

        for name in valid_names:
            self.assertEqual(validate_name(name), name)

        # Test invalid names
        invalid_names = [
            "",
            "   ",
            "123",
            "John123",
            "José María",  # Contains non-ASCII characters
            "A" * 101,  # Too long
        ]

        for name in invalid_names:
            with self.assertRaises(ValidationError):
                validate_name(name)

    def test_phone_validation(self):
        """Test phone number validation utility"""
        # Test valid phone numbers
        valid_phones = [
            "+1234567890",
            "+44 20 7946 0958",
            "123-456-7890",
            "(123) 456-7890",
        ]

        for phone in valid_phones:
            self.assertEqual(validate_phone(phone), phone)

        # Test invalid phone numbers
        invalid_phones = [
            "123",  # Too short
            "abcdefghij",  # Contains letters
            "+1 abc def ghij",  # Contains letters
            "",  # Empty
            "12345678901234567890",  # Too long
        ]

        for phone in invalid_phones:
            with self.assertRaises(ValidationError):
                validate_phone(phone)

    def test_positive_price_validation(self):
        """Test positive price validation utility"""
        # Test valid prices
        valid_prices = [
            Decimal("10.00"),
            Decimal("0.01"),
            Decimal("999.99"),
        ]

        for price in valid_prices:
            self.assertEqual(validate_positive_price(price), price)

        # Test invalid prices
        invalid_prices = [
            Decimal("0.00"),
            Decimal("-10.00"),
            Decimal("-0.01"),
        ]

        for price in invalid_prices:
            with self.assertRaises(ValidationError):
                validate_positive_price(price)

    def test_rating_validation(self):
        """Test rating validation utility"""
        # Test valid ratings
        for rating in [1, 2, 3, 4, 5]:
            self.assertEqual(validate_rating(rating), rating)

        # Test string ratings that can be converted
        for rating in ["1", "2", "3", "4", "5"]:
            self.assertEqual(validate_rating(rating), int(rating))

        # Test invalid ratings
        invalid_ratings = [0, 6, -1, 10, "abc", None]

        for rating in invalid_ratings:
            with self.assertRaises(ValidationError):
                validate_rating(rating)

    def test_text_length_validation(self):
        """Test text length validation utility"""
        # Test valid text lengths
        valid_texts = [
            ("Hello", 1, 10),
            ("Test message", 5, 20),
            ("A" * 50, 1, 100),
        ]

        for text, min_len, max_len in valid_texts:
            self.assertEqual(validate_text_length(text, min_len, max_len), text)

        # Test invalid text lengths
        with self.assertRaises(ValidationError):
            validate_text_length("Hi", 5, 10)  # Too short

        with self.assertRaises(ValidationError):
            validate_text_length("A" * 20, 1, 10)  # Too long

    def test_name_validation_with_custom_parameters(self):
        """Test name validation with custom min/max length and field name"""
        # Test custom field name in error message
        with self.assertRaises(ValidationError) as cm:
            validate_name("", field_name="First Name")
        self.assertIn("First Name", str(cm.exception))

        # Test custom length limits
        with self.assertRaises(ValidationError):
            validate_name("A" * 50, max_length=10)

        # Test valid name with custom parameters
        result = validate_name(
            "John", min_length=2, max_length=20, field_name="Username"
        )
        self.assertEqual(result, "John")

    def test_text_length_validation_with_custom_parameters(self):
        """Test text length validation with custom field name"""
        with self.assertRaises(ValidationError) as cm:
            validate_text_length("", min_length=5, field_name="Description")
        self.assertIn("Description", str(cm.exception))

    def test_phone_validation_edge_cases(self):
        """Test phone validation edge cases"""
        # Test minimum valid length
        self.assertEqual(validate_phone("1234567890"), "1234567890")

        # Test with various formatting
        formatted_phones = [
            "+1-234-567-8900",
            "+1 (234) 567-8900",
            "234.567.8900",
        ]

        for phone in formatted_phones:
            # Should not raise exception
            validate_phone(phone)

    def test_email_validation_edge_cases(self):
        """Test email validation edge cases"""
        # Test edge cases that should be valid
        edge_case_emails = [
            "a@b.co",
            "test123@example123.com",
            "user_name@domain-name.com",
        ]

        for email in edge_case_emails:
            self.assertEqual(validate_email_format(email), email)

        # Test edge cases that should be invalid
        invalid_edge_cases = [
            "test@exam ple.com",  # Space in domain
            "test@@example.com",  # Double @
            "test@",  # Missing domain
        ]

        for email in invalid_edge_cases:
            with self.assertRaises(ValidationError):
                validate_email_format(email)
