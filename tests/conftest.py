"""Pytest configuration with custom HTML email reporting for JIRA stories.

This module extends pytest functionality to automatically generate and send
HTML email reports when tests are run for specific JIRA stories.
"""

import os
import sys
import inspect
from typing import Dict, List, Optional, Any
from pathlib import Path

import pytest
from _pytest.config import Config
from _pytest.nodes import Item
from _pytest.reports import TestReport


# Test result storage
class TestResultCollector:
    """Collects and stores test results for email generation."""
    
    def __init__(self):
        self.results: List[Dict[str, Any]] = []
        self.stats = {
            'passed': 0,
            'failed': 0,
            'skipped': 0,
            'error': 0
        }
    
    def add_result(self, nodeid: str, outcome: str, docstring: str, 
                   error_msg: Optional[str] = None):
        """Add a test result to the collection.
        
        Args:
            nodeid: Test node identifier
            outcome: Test outcome (passed/failed/skipped/error)
            docstring: First line of test docstring
            error_msg: Error message if test failed
        """
        self.results.append({
            'nodeid': nodeid,
            'outcome': outcome,
            'docstring': docstring,
            'error_msg': error_msg
        })
        
        if outcome in self.stats:
            self.stats[outcome] += 1
    
    def get_summary(self) -> str:
        """Get summary statistics string.
        
        Returns:
            Summary string with pass/fail counts
        """
        total = sum(self.stats.values())
        return (f"Total: {total}, Passed: {self.stats['passed']}, "
                f"Failed: {self.stats['failed']}, Skipped: {self.stats['skipped']}, "
                f"Errors: {self.stats['error']}")


# Global collector instance
collector = TestResultCollector()


def pytest_addoption(parser):
    """Add custom command-line options.
    
    Args:
        parser: pytest command-line parser
    """
    parser.addoption(
        "--email-dry-run",
        action="store_true",
        default=False,
        help="Save email HTML to file instead of sending"
    )


def pytest_configure(config: Config):
    """Configure pytest with custom settings.
    
    Args:
        config: pytest configuration object
    """
    # Reset collector for new test session
    global collector
    collector = TestResultCollector()


def get_test_docstring(item: Item) -> str:
    """Extract first line of test function docstring.
    
    Args:
        item: pytest test item
        
    Returns:
        First line of docstring or empty string if none exists
    """
    try:
        # Get the actual test function
        func = item.obj
        if func.__doc__:
            # Get first non-empty line
            lines = [line.strip() for line in func.__doc__.strip().split('\n')]
            for line in lines:
                if line:
                    return line
        return ""
    except Exception:
        return ""


def truncate_error(error_msg: str, max_lines: int = 5, max_chars: int = 500) -> str:
    """Truncate error message for email display.
    
    Args:
        error_msg: Full error message
        max_lines: Maximum number of lines to include
        max_chars: Maximum total characters
        
    Returns:
        Truncated error message
    """
    if not error_msg:
        return ""
    
    lines = error_msg.split('\n')
    
    # Take first max_lines
    truncated_lines = lines[:max_lines]
    result = '\n'.join(truncated_lines)
    
    # Truncate by characters if needed
    if len(result) > max_chars:
        result = result[:max_chars] + "..."
    elif len(lines) > max_lines:
        result += "\n... (truncated)"
    
    return result


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item: Item, call):
    """Hook to capture test results.
    
    Args:
        item: pytest test item
        call: test call information
    """
    outcome = yield
    report: TestReport = outcome.get_result()
    
    # Only process the call phase (not setup/teardown)
    if report.when == "call":
        docstring = get_test_docstring(item)
        error_msg = None
        
        if report.failed:
            # Extract error information
            if hasattr(report, 'longreprtext'):
                error_msg = truncate_error(report.longreprtext)
            elif hasattr(report.longrepr, 'reprcrash'):
                error_msg = truncate_error(str(report.longrepr.reprcrash))
            else:
                error_msg = truncate_error(str(report.longrepr))
        
        collector.add_result(
            nodeid=item.nodeid,
            outcome=report.outcome,
            docstring=docstring,
            error_msg=error_msg
        )


def generate_html_email(jira_story: str, results: List[Dict[str, Any]], 
                       stats: Dict[str, int]) -> str:
    """Generate HTML email content with test results.
    
    Args:
        jira_story: JIRA story key
        results: List of test result dictionaries
        stats: Statistics dictionary with pass/fail counts
        
    Returns:
        Complete HTML email as string
    """
    # Determine overall status
    all_passed = stats['failed'] == 0 and stats['error'] == 0
    status_text = "All Tests Passed ✓" if all_passed else "Some Tests Failed ✗"
    status_color = "#FFD700" if all_passed else "#FF6B6B"
    
    # Build table rows
    table_rows = []
    for result in results:
        outcome = result['outcome']
        
        # Status styling
        if outcome == 'passed':
            status_badge = '<span style="color: #4CAF50; font-weight: bold;">✓ PASSED</span>'
        elif outcome == 'failed':
            status_badge = '<span style="color: #FF6B6B; font-weight: bold;">✗ FAILED</span>'
        elif outcome == 'skipped':
            status_badge = '<span style="color: #FFA726; font-weight: bold;">⊘ SKIPPED</span>'
        else:  # error
            status_badge = '<span style="color: #FF6B6B; font-weight: bold;">⚠ ERROR</span>'
        
        # Extract clean test name from nodeid
        test_name = result['nodeid'].split("::")[-1]
        
        # Error cell
        error_cell = ""
        if result['error_msg']:
            escaped_error = (result['error_msg']
                           .replace('&', '&amp;')
                           .replace('<', '&lt;')
                           .replace('>', '&gt;')
                           .replace('\n', '<br>'))
            error_cell = f'<td style="padding: 12px; border: 1px solid #004d73; color: #FFB6B6; font-family: monospace; font-size: 11px; max-width: 400px; word-wrap: break-word;">{escaped_error}</td>'
        else:
            error_cell = '<td style="padding: 12px; border: 1px solid #004d73; color: #CCCCCC;">-</td>'
        
        row = f"""
        <tr style="background-color: #002b4d;">
            <td style="padding: 12px; border: 1px solid #004d73; color: #FFFFFF; font-family: monospace;">{test_name}</td>
            <td style="padding: 12px; border: 1px solid #004d73; text-align: center;">{status_badge}</td>
            <td style="padding: 12px; border: 1px solid #004d73; color: #E0E0E0; font-style: italic;">{result['docstring']}</td>
            {error_cell}
        </tr>
        """
        table_rows.append(row)
    
    table_rows_html = '\n'.join(table_rows)
    
    # Statistics summary
    total_tests = sum(stats.values())
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Test Results for {jira_story}</title>
    </head>
    <body style="margin: 0; padding: 0; background-color: #001a33; font-family: Arial, sans-serif;">
        <div style="max-width: 1200px; margin: 0 auto; padding: 20px;">
            <!-- Header -->
            <div style="background: linear-gradient(135deg, #003d5c 0%, #002b4d 100%); padding: 30px; border-radius: 8px 8px 0 0; border-bottom: 3px solid #FFD700;">
                <h1 style="margin: 0 0 10px 0; color: #FFFFFF; font-size: 28px;">
                    Test Results Report
                </h1>
                <p style="margin: 0; color: #B0BEC5; font-size: 14px;">
                    Automated Test Execution Summary
                </p>
            </div>
            
            <!-- Summary Section -->
            <div style="background-color: #002b4d; padding: 25px; border-left: 4px solid {status_color};">
                <h2 style="margin: 0 0 15px 0; color: {status_color}; font-size: 22px;">
                    {status_text}
                </h2>
                <p style="margin: 0 0 10px 0; color: #FFFFFF; font-size: 16px;">
                    <strong>JIRA Story:</strong> <span style="color: #FFD700;">{jira_story}</span>
                </p>
                <p style="margin: 0; color: #E0E0E0; font-size: 14px;">
                    <strong>Summary:</strong> 
                    {total_tests} test{"s" if total_tests != 1 else ""} executed • 
                    <span style="color: #4CAF50;">{stats['passed']} passed</span> • 
                    <span style="color: #FF6B6B;">{stats['failed']} failed</span> • 
                    <span style="color: #FFA726;">{stats['skipped']} skipped</span>
                    {f" • <span style='color: #FF6B6B;'>{stats['error']} errors</span>" if stats['error'] > 0 else ""}
                </p>
            </div>
            
            <!-- Test Results Table -->
            <div style="background-color: #003d5c; padding: 20px; border-radius: 0 0 8px 8px;">
                <table style="width: 100%; border-collapse: collapse; background-color: #002b4d;">
                    <thead>
                        <tr style="background-color: #004d73;">
                            <th style="padding: 15px; border: 1px solid #005580; color: #FFD700; text-align: left; font-size: 14px; width: 30%;">Test Name</th>
                            <th style="padding: 15px; border: 1px solid #005580; color: #FFD700; text-align: center; font-size: 14px; width: 12%;">Status</th>
                            <th style="padding: 15px; border: 1px solid #005580; color: #FFD700; text-align: left; font-size: 14px; width: 30%;">Description</th>
                            <th style="padding: 15px; border: 1px solid #005580; color: #FFD700; text-align: left; font-size: 14px; width: 28%;">Error Details</th>
                        </tr>
                    </thead>
                    <tbody>
                        {table_rows_html}
                    </tbody>
                </table>
            </div>
            
            <!-- Footer -->
            <div style="margin-top: 20px; padding: 15px; background-color: #001a33; border-top: 2px solid #004d73; text-align: center;">
                <p style="margin: 0; color: #78909C; font-size: 12px;">
                    This is an automated test report generated by the QA team's test suite.
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html


def pytest_sessionfinish(session, exitstatus):
    """Hook called after all tests complete.
    
    Generates and sends HTML email if TEST_JIRA_STORY is set.
    
    Args:
        session: pytest session object
        exitstatus: exit status of the test run
    """
    jira_story = os.environ.get('TEST_JIRA_STORY')
    
    # Only proceed if JIRA story is set and we have results
    if not jira_story or not collector.results:
        return
    
    # Check for dry-run mode
    dry_run = (
        session.config.getoption("--email-dry-run", default=False) or
        os.environ.get('EMAIL_DRY_RUN', '').lower() in ('1', 'true', 'yes')
    )
    
    # Generate HTML email
    html_content = generate_html_email(
        jira_story=jira_story,
        results=collector.results,
        stats=collector.stats
    )
    
    # Determine subject
    all_passed = collector.stats['failed'] == 0 and collector.stats['error'] == 0
    status = "Success" if all_passed else "Failure"
    subject = f"Test Results for Story {jira_story} - {status}"
    
    if dry_run:
        # Save to file
        output_file = Path(f"test_results_{jira_story.replace('-', '_')}.html")
        try:
            output_file.write_text(html_content, encoding='utf-8')
            print("\n" + "=" * 80)
            print(f"DRY-RUN: Email saved to {output_file.absolute()}")
            print(f"Subject: {subject}")
            print(f"Stats: {collector.get_summary()}")
            print("=" * 80 + "\n")
        except Exception as e:
            print("\n" + "!" * 80, file=sys.stderr)
            print(f"ERROR: Failed to save dry-run email to file: {e}", file=sys.stderr)
            print("!" * 80 + "\n", file=sys.stderr)
    else:
        # Send email
        try:
            # Import the send function (assumes it's available in the environment)
            from send_html_email import send_html_email
            
            success = send_html_email(subject, html_content)
            
            if success:
                print("\n" + "=" * 80)
                print(f"✓ Test results email sent successfully for {jira_story}")
                print(f"Stats: {collector.get_summary()}")
                print("=" * 80 + "\n")
            else:
                print("\n" + "!" * 80, file=sys.stderr)
                print(f"✗ WARNING: Failed to send test results email for {jira_story}", 
                      file=sys.stderr)
                print(f"Stats: {collector.get_summary()}", file=sys.stderr)
                print("Test run status unchanged - email failure does not affect test results", 
                      file=sys.stderr)
                print("!" * 80 + "\n", file=sys.stderr)
                
        except ImportError:
            print("\n" + "!" * 80, file=sys.stderr)
            print("✗ WARNING: Could not import send_html_email function", file=sys.stderr)
            print(f"Email for {jira_story} not sent", file=sys.stderr)
            print("!" * 80 + "\n", file=sys.stderr)
        except Exception as e:
            print("\n" + "!" * 80, file=sys.stderr)
            print(f"✗ WARNING: Unexpected error sending email: {e}", file=sys.stderr)
            print(f"Stats: {collector.get_summary()}", file=sys.stderr)
            print("!" * 80 + "\n", file=sys.stderr)
