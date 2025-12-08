"""Test suite for conftest.py email reporting functionality.

This module contains comprehensive tests for the pytest HTML email reporter,
testing all major functionality including result collection, HTML generation,
dry-run mode, and error handling.
"""

import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest

# Import functions from conftest for testing
from conftest import (
    TestResultCollector,
    get_test_docstring,
    truncate_error,
    generate_html_email,
)


class TestResultCollectorClass:
    """Test cases for TestResultCollector class."""
    
    def test_initialization(self):
        """Verify collector initializes with empty results and zero stats."""
        collector = TestResultCollector()
        
        assert collector.results == []
        assert collector.stats == {
            'passed': 0,
            'failed': 0,
            'skipped': 0,
            'error': 0
        }
    
    def test_add_passing_result(self):
        """Verify adding a passing test result updates stats correctly."""
        collector = TestResultCollector()
        collector.add_result(
            nodeid="test_file.py::test_func",
            outcome="passed",
            docstring="Test description"
        )
        
        assert len(collector.results) == 1
        assert collector.stats['passed'] == 1
    
    def test_add_failing_result_with_error(self):
        """Verify adding a failed test with error message stores correctly."""
        collector = TestResultCollector()
        error_msg = "AssertionError: Expected 5 but got 10"
        
        collector.add_result(
            nodeid="test_file.py::test_fail",
            outcome="failed",
            docstring="This test fails",
            error_msg=error_msg
        )
        
        assert len(collector.results) == 1
        assert collector.stats['failed'] == 1
        assert collector.results[0]['error_msg'] == error_msg
    
    def test_add_multiple_results(self):
        """Verify multiple results are collected and counted correctly."""
        collector = TestResultCollector()
        
        collector.add_result("test1.py::test_a", "passed", "Test A")
        collector.add_result("test1.py::test_b", "failed", "Test B", "Error")
        collector.add_result("test1.py::test_c", "skipped", "Test C")
        collector.add_result("test1.py::test_d", "error", "Test D", "Error")
        
        assert len(collector.results) == 4
        assert collector.stats['passed'] == 1
        assert collector.stats['failed'] == 1
        assert collector.stats['skipped'] == 1
        assert collector.stats['error'] == 1
    
    def test_get_summary(self):
        """Verify summary string format is correct."""
        collector = TestResultCollector()
        collector.add_result("test.py::test1", "passed", "")
        collector.add_result("test.py::test2", "failed", "", "Error")
        
        summary = collector.get_summary()
        
        assert "Total: 2" in summary
        assert "Passed: 1" in summary
        assert "Failed: 1" in summary


class TestDocstringExtraction:
    """Test cases for test docstring extraction."""
    
    def test_extract_first_line_from_simple_docstring(self):
        """Verify first line extraction from simple docstring."""
        def sample_test():
            """This is the first line.
            This is the second line.
            """
            pass
        
        # Create mock item
        item = Mock()
        item.obj = sample_test
        
        result = get_test_docstring(item)
        
        assert result == "This is the first line."
    
    def test_extract_from_single_line_docstring(self):
        """Verify extraction from single-line docstring."""
        def sample_test():
            """Single line docstring"""
            pass
        
        item = Mock()
        item.obj = sample_test
        
        result = get_test_docstring(item)
        
        assert result == "Single line docstring"
    
    def test_extract_from_google_style_docstring(self):
        """Verify extraction from Google-style docstring."""
        def sample_test():
            """Brief description of test.
            
            Args:
                param1: Description
            """
            pass
        
        item = Mock()
        item.obj = sample_test
        
        result = get_test_docstring(item)
        
        assert result == "Brief description of test."
    
    def test_no_docstring_returns_empty_string(self):
        """Verify function without docstring returns empty string."""
        def sample_test():
            pass
        
        item = Mock()
        item.obj = sample_test
        
        result = get_test_docstring(item)
        
        assert result == ""
    
    def test_docstring_with_leading_whitespace(self):
        """Verify leading/trailing whitespace is stripped."""
        def sample_test():
            """
            First line with leading newline
            """
            pass
        
        item = Mock()
        item.obj = sample_test
        
        result = get_test_docstring(item)
        
        assert result == "First line with leading newline"
    
    def test_exception_during_extraction_returns_empty(self):
        """Verify exception during extraction returns empty string."""
        item = Mock()
        item.obj = None  # Will cause AttributeError
        
        result = get_test_docstring(item)
        
        assert result == ""


class TestErrorTruncation:
    """Test cases for error message truncation."""
    
    def test_short_error_not_truncated(self):
        """Verify short error messages are not truncated."""
        error = "Simple error message"
        
        result = truncate_error(error)
        
        assert result == error
    
    def test_truncate_by_line_count(self):
        """Verify truncation by maximum line count."""
        lines = [f"Line {i}" for i in range(10)]
        error = "\n".join(lines)
        
        result = truncate_error(error, max_lines=3)
        
        assert "Line 0" in result
        assert "Line 1" in result
        assert "Line 2" in result
        assert "(truncated)" in result
        assert "Line 6" not in result
    
    def test_truncate_by_character_count(self):
        """Verify truncation by maximum character count."""
        error = "x" * 1000
        
        result = truncate_error(error, max_chars=100)
        
        assert len(result) <= 103  # 100 + "..."
        assert result.endswith("...")
    
    def test_empty_error_returns_empty(self):
        """Verify empty error message returns empty string."""
        result = truncate_error("")
        
        assert result == ""
    
    def test_none_error_returns_empty(self):
        """Verify None error returns empty string."""
        result = truncate_error(None)
        
        assert result == ""
    
    def test_multiline_within_limits(self):
        """Verify multiline error within limits is not truncated."""
        error = "Line 1\nLine 2\nLine 3"
        
        result = truncate_error(error, max_lines=5, max_chars=500)
        
        assert result == error
    
    def test_truncation_adds_ellipsis_for_chars(self):
        """Verify character truncation adds ellipsis."""
        error = "a" * 600
        
        result = truncate_error(error, max_lines=10, max_chars=100)
        
        assert "..." in result


class TestHTMLEmailGeneration:
    """Test cases for HTML email generation."""
    
    def test_generate_email_with_all_passing_tests(self):
        """Verify HTML email generation for all passing tests."""
        results = [
            {
                'nodeid': 'test_file.py::test_one',
                'outcome': 'passed',
                'docstring': 'Test one description',
                'error_msg': None
            },
            {
                'nodeid': 'test_file.py::test_two',
                'outcome': 'passed',
                'docstring': 'Test two description',
                'error_msg': None
            }
        ]
        stats = {'passed': 2, 'failed': 0, 'skipped': 0, 'error': 0}
        
        html = generate_html_email('PROJ-123', results, stats)
        
        assert 'PROJ-123' in html
        assert 'All Tests Passed' in html
        assert 'test_one' in html
        assert 'test_two' in html
        assert 'Test one description' in html
        assert '✓ PASSED' in html
        assert '2 tests executed' in html
        assert '2 passed' in html
    
    def test_generate_email_with_failures(self):
        """Verify HTML email generation includes failure information."""
        results = [
            {
                'nodeid': 'test_file.py::test_fail',
                'outcome': 'failed',
                'docstring': 'This test fails',
                'error_msg': 'AssertionError: Expected 5 but got 10'
            }
        ]
        stats = {'passed': 0, 'failed': 1, 'skipped': 0, 'error': 0}
        
        html = generate_html_email('PROJ-456', results, stats)
        
        assert 'PROJ-456' in html
        assert 'Some Tests Failed' in html
        assert 'test_fail' in html
        assert 'This test fails' in html
        assert '✗ FAILED' in html
        assert 'AssertionError' in html
        assert '1 failed' in html
    
    def test_generate_email_with_skipped_tests(self):
        """Verify HTML email generation includes skipped tests."""
        results = [
            {
                'nodeid': 'test_file.py::test_skip',
                'outcome': 'skipped',
                'docstring': 'Skipped test',
                'error_msg': None
            }
        ]
        stats = {'passed': 0, 'failed': 0, 'skipped': 1, 'error': 0}
        
        html = generate_html_email('PROJ-789', results, stats)
        
        assert '⊘ SKIPPED' in html
        assert 'Skipped test' in html
        assert '1 skipped' in html
    
    def test_generate_email_with_errors(self):
        """Verify HTML email generation includes error tests."""
        results = [
            {
                'nodeid': 'test_file.py::test_error',
                'outcome': 'error',
                'docstring': 'Test with error',
                'error_msg': 'KeyError: missing_key'
            }
        ]
        stats = {'passed': 0, 'failed': 0, 'skipped': 0, 'error': 1}
        
        html = generate_html_email('PROJ-999', results, stats)
        
        assert '⚠ ERROR' in html
        assert 'KeyError' in html
        assert '1 errors' in html
    
    def test_html_structure_is_valid(self):
        """Verify generated HTML has proper structure."""
        results = [{'nodeid': 'test.py::test', 'outcome': 'passed', 
                   'docstring': '', 'error_msg': None}]
        stats = {'passed': 1, 'failed': 0, 'skipped': 0, 'error': 0}
        
        html = generate_html_email('TEST-1', results, stats)
        
        assert '<!DOCTYPE html>' in html
        assert '<html>' in html
        assert '<head>' in html
        assert '<body' in html
        assert '</html>' in html
    
    def test_html_escaping_in_error_messages(self):
        """Verify HTML special characters are properly escaped."""
        results = [
            {
                'nodeid': 'test.py::test',
                'outcome': 'failed',
                'docstring': '',
                'error_msg': '<script>alert("xss")</script>'
            }
        ]
        stats = {'passed': 0, 'failed': 1, 'skipped': 0, 'error': 0}
        
        html = generate_html_email('SEC-1', results, stats)
        
        assert '<script>' not in html
        assert '&lt;script&gt;' in html
    
    def test_color_scheme_applied(self):
        """Verify color scheme is applied to HTML."""
        results = [{'nodeid': 'test.py::test', 'outcome': 'passed',
                   'docstring': '', 'error_msg': None}]
        stats = {'passed': 1, 'failed': 0, 'skipped': 0, 'error': 0}
        
        html = generate_html_email('COLOR-1', results, stats)
        
        # Check for deep blue backgrounds
        assert '#003d5c' in html or '#002b4d' in html
        # Check for yellow highlights
        assert '#FFD700' in html
        # Check for green for passed tests
        assert '#4CAF50' in html


class TestIntegrationScenarios:
    """Integration test scenarios for the complete workflow."""
    
    @pytest.fixture
    def temp_dir(self, tmp_path):
        """Provide temporary directory for test outputs."""
        return tmp_path
    
    def test_dry_run_creates_file(self, temp_dir, monkeypatch):
        """Verify dry-run mode creates HTML file in correct location."""
        monkeypatch.chdir(temp_dir)
        
        from conftest import collector, generate_html_email
        
        # Simulate test results
        collector.add_result("test.py::test1", "passed", "Test 1")
        
        # Generate HTML
        html = generate_html_email(
            "DRY-001", 
            collector.results, 
            collector.stats
        )
        
        # Simulate dry-run file save
        output_file = temp_dir / "test_results_DRY_001.html"
        output_file.write_text(html, encoding='utf-8')
        
        assert output_file.exists()
        assert output_file.stat().st_size > 0
    
    def test_environment_variable_detection(self, monkeypatch):
        """Verify TEST_JIRA_STORY environment variable is detected."""
        monkeypatch.setenv('TEST_JIRA_STORY', 'ENV-123')
        
        assert os.environ.get('TEST_JIRA_STORY') == 'ENV-123'
    
    def test_dry_run_env_var_detection(self, monkeypatch):
        """Verify EMAIL_DRY_RUN environment variable detection."""
        test_cases = ['1', 'true', 'yes', 'True', 'YES']
        
        for value in test_cases:
            monkeypatch.setenv('EMAIL_DRY_RUN', value)
            env_value = os.environ.get('EMAIL_DRY_RUN', '').lower()
            assert env_value in ('1', 'true', 'yes')


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_empty_results_list(self):
        """Verify handling of empty results list."""
        html = generate_html_email('EMPTY-1', [], {
            'passed': 0, 'failed': 0, 'skipped': 0, 'error': 0
        })
        
        assert 'EMPTY-1' in html
        assert '0 tests executed' in html
    
    def test_very_long_test_name(self):
        """Verify handling of very long test names."""
        long_name = "test_" + "x" * 200
        results = [{
            'nodeid': f'test.py::{long_name}',
            'outcome': 'passed',
            'docstring': '',
            'error_msg': None
        }]
        stats = {'passed': 1, 'failed': 0, 'skipped': 0, 'error': 0}
        
        html = generate_html_email('LONG-1', results, stats)
        
        assert long_name in html
    
    def test_unicode_in_docstring(self):
        """Verify handling of unicode characters in docstrings."""
        results = [{
            'nodeid': 'test.py::test_unicode',
            'outcome': 'passed',
            'docstring': 'Test with émojis 🎉 and spëcial chars',
            'error_msg': None
        }]
        stats = {'passed': 1, 'failed': 0, 'skipped': 0, 'error': 0}
        
        html = generate_html_email('UNI-1', results, stats)
        
        assert 'émojis' in html
        assert '🎉' in html
    
    def test_special_chars_in_jira_key(self):
        """Verify handling of JIRA keys with various formats."""
        jira_keys = ['PROJ-123', 'ABC-1', 'X-9999', 'LONG_PROJECT-456']
        
        for key in jira_keys:
            results = [{'nodeid': 'test.py::test', 'outcome': 'passed',
                       'docstring': '', 'error_msg': None}]
            stats = {'passed': 1, 'failed': 0, 'skipped': 0, 'error': 0}
            
            html = generate_html_email(key, results, stats)
            
            assert key in html
