#!/bin/bash
# demo_email_reporter.sh
#
# Demonstration script showing different usage modes of the pytest email reporter

set -e

echo "=========================================================================="
echo "Pytest HTML Email Reporter - Demo Script"
echo "=========================================================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Demo 1: Normal pytest run (no email)
echo -e "${BLUE}Demo 1: Normal pytest run (no TEST_JIRA_STORY set)${NC}"
echo "Command: pytest test_example.py -v"
echo "Expected: Tests run normally, no email functionality triggered"
echo ""
read -p "Press Enter to continue..."
pytest test_example.py -v
echo ""
echo "=========================================================================="
echo ""

# Demo 2: Dry-run with passing tests
echo -e "${BLUE}Demo 2: Dry-run mode with passing tests${NC}"
echo "Command: TEST_JIRA_STORY='DEMO-100' pytest --email-dry-run test_example.py"
echo "Expected: Tests pass, HTML email saved to file"
echo ""
read -p "Press Enter to continue..."
TEST_JIRA_STORY="DEMO-100" pytest --email-dry-run test_example.py -v
echo ""
if [ -f "test_results_DEMO_100.html" ]; then
    echo -e "${GREEN}✓ Email HTML file created: test_results_DEMO_100.html${NC}"
    echo "File size: $(wc -c < test_results_DEMO_100.html) bytes"
fi
echo ""
echo "=========================================================================="
echo ""

# Demo 3: Dry-run with some failures
echo -e "${BLUE}Demo 3: Dry-run mode with test failures${NC}"
echo "Command: TEST_JIRA_STORY='DEMO-200' EMAIL_DRY_RUN=1 pytest test_failures.py"
echo "Expected: Some tests fail, HTML email saved showing failures"
echo ""
read -p "Press Enter to continue..."
TEST_JIRA_STORY="DEMO-200" EMAIL_DRY_RUN=1 pytest test_failures.py -v || true
echo ""
if [ -f "test_results_DEMO_200.html" ]; then
    echo -e "${GREEN}✓ Email HTML file created: test_results_DEMO_200.html${NC}"
    echo "File size: $(wc -c < test_results_DEMO_200.html) bytes"
fi
echo ""
echo "=========================================================================="
echo ""

# Demo 4: Actual email send (using mock)
echo -e "${BLUE}Demo 4: Actual email send mode (using mock sender)${NC}"
echo "Command: TEST_JIRA_STORY='DEMO-300' pytest test_example.py"
echo "Expected: Tests run, mock email sender called"
echo ""
read -p "Press Enter to continue..."
TEST_JIRA_STORY="DEMO-300" pytest test_example.py -v
echo ""
echo "=========================================================================="
echo ""

# Demo 5: Combined test suite
echo -e "${BLUE}Demo 5: Running combined test suite${NC}"
echo "Command: TEST_JIRA_STORY='DEMO-400' pytest --email-dry-run"
echo "Expected: All tests run, comprehensive HTML report generated"
echo ""
read -p "Press Enter to continue..."
TEST_JIRA_STORY="DEMO-400" pytest --email-dry-run -v || true
echo ""
if [ -f "test_results_DEMO_400.html" ]; then
    echo -e "${GREEN}✓ Email HTML file created: test_results_DEMO_400.html${NC}"
    echo "File size: $(wc -c < test_results_DEMO_400.html) bytes"
fi
echo ""
echo "=========================================================================="
echo ""

# Summary
echo -e "${YELLOW}Demo Complete!${NC}"
echo ""
echo "Generated files:"
ls -lh test_results_*.html 2>/dev/null || echo "No HTML files found"
echo ""
echo "To view the HTML emails, open them in a browser:"
echo "  firefox test_results_DEMO_100.html"
echo "  chrome test_results_DEMO_200.html"
echo ""
echo "To clean up generated files:"
echo "  rm test_results_*.html"
echo ""
echo "=========================================================================="
