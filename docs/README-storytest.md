# Pytest HTML Email Reporter for JIRA Stories

Automated HTML email generation and delivery for pytest test results associated with JIRA stories.

## Overview

This pytest plugin automatically generates professional, styled HTML email reports when running tests for specific JIRA stories. The email includes:

- Summary of overall test results (pass/fail status)
- JIRA story key
- Detailed test results table with:
  - Test name
  - Status (passed/failed/skipped/error)
  - Test description (from docstring)
  - Error details (truncated for readability)
- Professional deep blue/white/yellow color scheme

## Features

- ✅ Automatic email generation when `TEST_JIRA_STORY` environment variable is set
- ✅ Professional HTML styling optimized for email clients
- ✅ Dry-run mode to preview emails without sending
- ✅ Truncated error messages for failed tests
- ✅ Graceful handling of email failures (doesn't affect test results)
- ✅ Compatible with normal pytest usage when no story is specified

## Installation

No additional dependencies beyond pytest are required for the core functionality.

```bash
pip install pytest pytest-html
```

## Usage

### Basic Usage with JIRA Story

Run tests for a specific JIRA story and automatically send email:

```bash
export TEST_JIRA_STORY="PROJ-1234"
pytest test_example.py
```

Or inline:

```bash
TEST_JIRA_STORY="PROJ-1234" pytest test_example.py
```

### Dry-Run Mode

Preview the email HTML without sending (saves to file):

**Using command-line option:**
```bash
TEST_JIRA_STORY="PROJ-1234" pytest --email-dry-run test_example.py
```

**Using environment variable:**
```bash
TEST_JIRA_STORY="PROJ-1234" EMAIL_DRY_RUN=1 pytest test_example.py
```

**Using both (for clarity):**
```bash
TEST_JIRA_STORY="PROJ-1234" EMAIL_DRY_RUN=true pytest --email-dry-run test_example.py
```

The HTML email will be saved to `test_results_PROJ_1234.html` in the current directory.

### Normal Pytest Usage

When `TEST_JIRA_STORY` is not set, pytest runs normally without email functionality:

```bash
pytest test_example.py
```

### Integration with Test Script

Your bash script can pass the JIRA story key like this:

```bash
#!/bin/bash
# run_tests.sh

JIRA_STORY="$1"

if [ -n "$JIRA_STORY" ]; then
    export TEST_JIRA_STORY="$JIRA_STORY"
    echo "Running tests for story: $JIRA_STORY"
fi

pytest test_example.py
```

Usage:
```bash
./run_tests.sh PROJ-1234
```

## Configuration

### Email Sending Function

The system calls `send_html_email(subject, body)` to send emails. By default, it uses the mock implementation in `send_html_email.py`.

**Replace with your actual email implementation:**

```python
# send_html_email.py

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_html_email(subject: str, body: str, recipient: str = None) -> bool:
    """Send HTML email via SMTP.
    
    Args:
        subject: Email subject line
        body: HTML email body
        recipient: Email recipient (defaults to team email if None)
        
    Returns:
        True if email sent successfully, False otherwise
    """
    try:
        recipient = recipient or "team@example.com"
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = "qa-automation@example.com"
        msg['To'] = recipient
        
        html_part = MIMEText(body, 'html')
        msg.attach(html_part)
        
        with smtplib.SMTP('smtp.example.com', 587) as server:
            server.starttls()
            server.login('username', 'password')
            server.send_message(msg)
        
        return True
    except Exception as e:
        print(f"Email send failed: {e}")
        return False
```

### Customizing Email Styling

Edit the `generate_html_email()` function in `conftest.py` to customize:

- Colors (currently deep blue #003d5c, white, yellow #FFD700)
- Layout and spacing
- Additional information to display
- Font styles and sizes

### Error Message Truncation

By default, errors are truncated to:
- Maximum 5 lines
- Maximum 500 characters

Adjust in `truncate_error()` function:

```python
def truncate_error(error_msg: str, max_lines: int = 5, max_chars: int = 500) -> str:
    # Modify max_lines and max_chars as needed
    ...
```

## Test Writing Best Practices

To get meaningful descriptions in the email report, add docstrings to your tests:

```python
class TestFeature:
    """Test cases for feature X."""
    
    def test_basic_functionality(self):
        """Verify that basic feature works correctly."""
        assert True
    
    def test_edge_case(self):
        """Verify handling of edge case with empty input."""
        assert handle_empty_input() is not None
```

**The first line of the docstring appears in the email's Description column.**

## Output Examples

### Successful Test Run

```
================================================================================
✓ Test results email sent successfully for PROJ-1234
Stats: Total: 10, Passed: 10, Failed: 0, Skipped: 0, Errors: 0
================================================================================
```

### Failed Test Run

```
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
✗ WARNING: Failed to send test results email for PROJ-1234
Stats: Total: 10, Passed: 7, Failed: 3, Skipped: 0, Errors: 0
Test run status unchanged - email failure does not affect test results
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
```

### Dry-Run Output

```
================================================================================
DRY-RUN: Email saved to /path/to/test_results_PROJ_1234.html
Subject: Test Results for Story PROJ-1234 - Success
Stats: Total: 10, Passed: 10, Failed: 0, Skipped: 0, Errors: 0
================================================================================
```

## Email Subject Format

- **All tests pass:** `Test Results for Story PROJ-1234 - Success`
- **Some tests fail:** `Test Results for Story PROJ-1234 - Failure`

## Troubleshooting

### Email not being sent

**Check:**
1. Is `TEST_JIRA_STORY` environment variable set?
2. Is the `send_html_email` module importable?
3. Check pytest output for warning messages

### Email send fails but tests still run

**This is intentional behavior.** Email failures do not affect test results. Check the warning output for details.

### Dry-run file not created

**Check:**
1. Write permissions in current directory
2. Valid JIRA story key format (no special characters that can't be in filenames)

### Tests not showing in email

**Only tests that actually ran are included.** Skipped tests appear with SKIPPED status.

## Architecture

### Flow

1. pytest starts → `pytest_configure()` initializes collector
2. Each test runs → `pytest_runtest_makereport()` captures results and docstrings
3. Tests complete → `pytest_sessionfinish()` checks for `TEST_JIRA_STORY`
4. If set → Generate HTML email
5. If dry-run → Save to file, else send email
6. Log result (success or warning)

### Key Components

- **TestResultCollector:** Stores test results during execution
- **get_test_docstring():** Extracts first line of test docstring
- **truncate_error():** Truncates error messages for display
- **generate_html_email():** Creates styled HTML email
- **pytest hooks:** Integrate with pytest lifecycle

## File Structure

```
project/
├── conftest.py              # Main pytest configuration with hooks
├── send_html_email.py       # Email sending function (customize this)
├── test_example.py          # Example test file
├── test_failures.py         # Example with failures
└── README.md               # This file
```

## Notes

- Email is only triggered when `TEST_JIRA_STORY` is set
- Dry-run mode can be triggered via CLI option `--email-dry-run` OR environment variable `EMAIL_DRY_RUN`
- Test results are unaffected by email failures
- HTML email uses inline CSS for maximum email client compatibility
- Only the first line of test docstrings appears in the report

## Future Enhancements

Potential improvements:
- Attachment support for full pytest-html report
- Configurable color schemes
- Multiple recipient support
- Test duration information
- Historical comparison
- Slack/Teams integration
