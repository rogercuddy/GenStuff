"""Example test module to demonstrate email reporting functionality.

This module contains sample tests for JIRA story demonstration.
"""

import pytest


class TestUserAuthentication:
    """Test cases for user authentication features."""
    
    def test_valid_login(self):
        """Verify that valid credentials allow successful login."""
        username = "testuser"
        password = "correctpassword"
        
        # Mock authentication logic
        assert username == "testuser"
        assert password == "correctpassword"
    
    def test_invalid_password(self):
        """Verify that invalid password is rejected."""
        username = "testuser"
        password = "wrongpassword"
        
        # Mock authentication logic
        is_valid = username == "testuser" and password == "correctpassword"
        assert is_valid is False
    
    def test_empty_credentials(self):
        """Verify that empty credentials are rejected."""
        username = ""
        password = ""
        
        assert username == "" and password == ""


class TestDataValidation:
    """Test cases for data validation functionality."""
    
    def test_email_format_valid(self):
        """Verify valid email format is accepted."""
        email = "user@example.com"
        assert "@" in email and "." in email
    
    def test_email_format_invalid(self):
        """Verify invalid email format is rejected."""
        email = "invalid-email"
        has_at = "@" in email
        has_dot = "." in email
        assert not (has_at and has_dot)
    
    @pytest.mark.parametrize("value,expected", [
        ("12345", True),
        ("abc", False),
        ("", False),
    ])
    def test_numeric_validation(self, value, expected):
        """Verify numeric validation works correctly."""
        is_numeric = value.isdigit() if value else False
        assert is_numeric == expected


class TestCalculations:
    """Test cases for calculation functionality."""
    
    def test_addition(self):
        """Verify basic addition operation."""
        result = 2 + 2
        assert result == 4
    
    def test_division_by_zero(self):
        """Verify division by zero raises appropriate error."""
        with pytest.raises(ZeroDivisionError):
            _ = 10 / 0
    
    def test_complex_calculation(self):
        """Verify complex calculation produces correct result."""
        result = (10 + 5) * 2 - 3
        assert result == 27


@pytest.mark.skip(reason="Feature not yet implemented")
class TestFutureFeature:
    """Test cases for future feature (currently skipped)."""
    
    def test_new_feature(self):
        """Verify new feature works as expected."""
        assert True
