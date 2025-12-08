"""Test module with some intentional failures for demonstration.

This module shows how failed tests appear in the email report.
"""

import pytest


class TestWithFailures:
    """Test cases that include some failures."""
    
    def test_passing_assertion(self):
        """This test should pass successfully."""
        assert 1 + 1 == 2
    
    def test_failing_assertion(self):
        """This test will fail to demonstrate error reporting."""
        expected = 10
        actual = 5
        assert actual == expected, f"Expected {expected} but got {actual}"
    
    def test_exception_raised(self):
        """This test will raise an exception."""
        data = {"key": "value"}
        # This will raise KeyError
        _ = data["nonexistent_key"]
    
    def test_another_passing(self):
        """Another test that passes."""
        result = "hello".upper()
        assert result == "HELLO"
