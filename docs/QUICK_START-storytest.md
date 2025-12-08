# Quick Start Guide

## 5-Minute Setup

### 1. Copy Files to Your Project

```bash
# Copy conftest.py to your project root or tests directory
cp conftest.py /path/to/your/project/

# Copy the mock email sender (customize this later)
cp send_html_email.py /path/to/your/project/
```

### 2. Test It Out (Dry-Run)

```bash
cd /path/to/your/project/

# Run with dry-run to see the generated email
TEST_JIRA_STORY="PROJ-1234" pytest --email-dry-run

# Open the generated HTML file
firefox test_results_PROJ_1234.html
# or
chrome test_results_PROJ_1234.html
```

### 3. Integrate with Your Existing Script

Add to your test-running bash script:

```bash
#!/bin/bash
# your_existing_script.sh

JIRA_STORY="$1"  # Get JIRA story from argument

# Your existing test discovery logic...
# ...

# Set the environment variable for email reporting
if [ -n "$JIRA_STORY" ]; then
    export TEST_JIRA_STORY="$JIRA_STORY"
fi

# Run pytest (email sent automatically if TEST_JIRA_STORY is set)
pytest $PYTEST_ARGS ${TEST_FILES}
```

### 4. Customize Email Sending

Edit `send_html_email.py` to use your actual email system:

```python
# Example with SMTP
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_html_email(subject: str, body: str, recipient: str = None) -> bool:
    try:
        recipient = recipient or "qa-team@yourcompany.com"
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = "qa-automation@yourcompany.com"
        msg['To'] = recipient
        
        html_part = MIMEText(body, 'html')
        msg.attach(html_part)
        
        with smtplib.SMTP('smtp.yourcompany.com', 587) as server:
            server.starttls()
            server.login('your-username', 'your-password')
            server.send_message(msg)
        
        return True
    except Exception as e:
        print(f"Email failed: {e}")
        return False
```

## Usage Patterns

### Pattern 1: Development - Dry Run
```bash
TEST_JIRA_STORY="DEV-123" pytest --email-dry-run tests/
```

### Pattern 2: CI/CD - Automatic Email
```bash
# In your CI/CD pipeline
export TEST_JIRA_STORY="${JIRA_TICKET}"
pytest tests/
# Email automatically sent
```

### Pattern 3: Manual Testing - No Email
```bash
# Just run tests normally
pytest tests/
```

### Pattern 4: Review Generated Email
```bash
# Use dry-run, then view in browser
TEST_JIRA_STORY="REVIEW-1" EMAIL_DRY_RUN=1 pytest
open test_results_REVIEW_1.html
```

## Common Customizations

### Change Colors
Edit `conftest.py`, find `generate_html_email()`:
```python
# Change these color values:
"#003d5c"  # Deep blue background
"#FFD700"  # Yellow highlights
"#4CAF50"  # Green for passed tests
"#FF6B6B"  # Red for failed tests
```

### Add Company Logo
In `generate_html_email()`, add to header section:
```python
<div style="...">
    <img src="https://yourcompany.com/logo.png" alt="Logo" style="height: 40px;">
    <h1 style="...">Test Results Report</h1>
    ...
</div>
```

### Change Error Truncation
In `conftest.py`, find `truncate_error()`:
```python
def truncate_error(error_msg: str, max_lines: int = 10, max_chars: int = 1000):
    # Adjust max_lines and max_chars as needed
```

### Add More Information to Email
In `generate_html_email()`, add to summary section:
```python
<p>
    <strong>Build:</strong> {os.environ.get('BUILD_NUMBER', 'N/A')}
</p>
<p>
    <strong>Branch:</strong> {os.environ.get('GIT_BRANCH', 'N/A')}
</p>
```

## Troubleshooting

### Problem: Email not being sent
**Solution:** Check these in order:
1. Is `TEST_JIRA_STORY` set? `echo $TEST_JIRA_STORY`
2. Can Python import the module? `python -c "from send_html_email import send_html_email"`
3. Check pytest output for warning messages

### Problem: HTML file not created (dry-run)
**Solution:**
1. Check write permissions: `ls -la`
2. Verify JIRA key format (alphanumeric and hyphens only)
3. Check for filesystem errors in pytest output

### Problem: Tests not showing descriptions
**Solution:** Add docstrings to your tests:
```python
def test_my_feature(self):
    """Verify that my feature works correctly."""
    assert True
```

### Problem: Styling looks wrong in email client
**Solution:** We use inline CSS for compatibility, but some clients are finicky:
- Gmail, Outlook, Apple Mail: Should work perfectly
- Older clients: May have minor rendering differences
- The content will always be readable regardless

## Testing Your Setup

Run the included demo:
```bash
chmod +x demo_email_reporter.sh
./demo_email_reporter.sh
```

This will show you all the different modes of operation.

## Next Steps

1. ✅ Copy files to your project
2. ✅ Test with dry-run
3. ✅ Verify HTML email looks good
4. ✅ Integrate with your bash script
5. ✅ Customize email sender for your environment
6. ✅ Test actual email delivery
7. ✅ Customize colors/styling if desired
8. ✅ Add to your CI/CD pipeline

## Getting Help

All code is well-documented with:
- Comprehensive docstrings
- Inline comments
- README.md with detailed examples
- IMPLEMENTATION_SUMMARY.md with architecture

For questions about specific functions, check:
- `conftest.py` - Main implementation
- `test_conftest.py` - Usage examples in tests
- `README.md` - User-facing documentation

## Tips for Success

1. **Start with dry-run** - Always test with dry-run first
2. **Check docstrings** - Add meaningful docstrings to all tests
3. **Test email delivery** - Verify your email config works before going live
4. **Monitor logs** - Watch for warning messages during test runs
5. **Keep it simple** - Don't over-customize initially

You're ready to go! 🚀
