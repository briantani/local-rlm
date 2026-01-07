#!/usr/bin/env bash
#
# Run E2E tests for RLM Agent Web UI
#
# Usage:
#   ./run_e2e_tests.sh              # Run all E2E tests (headless)
#   ./run_e2e_tests.sh --headed     # Run with browser visible
#   ./run_e2e_tests.sh --debug      # Run with slow motion for debugging
#   ./run_e2e_tests.sh happy        # Run only happy path tests
#
# Prerequisites:
#   1. Dev server must be running: uv run uvicorn src.web.app:app --reload
#   2. For local-only tests: Ollama must be running
#   3. Playwright must be installed: uv run playwright install chromium

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if server is running
echo -e "${YELLOW}Checking if dev server is running...${NC}"
if curl -s http://localhost:8000 > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Dev server is running${NC}"
else
    echo -e "${RED}❌ Dev server is not running${NC}"
    echo ""
    echo "Start the server first:"
    echo "  uv run uvicorn src.web.app:app --reload"
    echo ""
    echo "In another terminal, then run this script again."
    exit 1
fi

# Parse arguments
TEST_PATTERN="tests/e2e/"
PYTEST_ARGS=""

if [ "$1" == "--headed" ]; then
    PYTEST_ARGS="--headed"
elif [ "$1" == "--debug" ]; then
    PYTEST_ARGS="--headed --slowmo 500"
elif [ "$1" == "happy" ]; then
    TEST_PATTERN="tests/e2e/test_happy_path.py"
elif [ "$1" == "errors" ]; then
    TEST_PATTERN="tests/e2e/test_error_handling.py"
elif [ "$1" == "keys" ]; then
    TEST_PATTERN="tests/e2e/test_api_keys.py"
fi

echo ""
echo -e "${YELLOW}Running E2E tests...${NC}"
echo "Pattern: $TEST_PATTERN"
echo "Args: $PYTEST_ARGS"
echo ""

# Run tests
uv run pytest $TEST_PATTERN -v $PYTEST_ARGS

# Capture exit code
EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ All E2E tests passed!${NC}"
else
    echo -e "${RED}❌ Some E2E tests failed${NC}"
    echo ""
    echo "Debugging tips:"
    echo "  1. Run with --headed to watch browser: ./run_e2e_tests.sh --headed"
    echo "  2. Run with --debug for slow motion: ./run_e2e_tests.sh --debug"
    echo "  3. Check if Ollama is running: ollama list"
    echo "  4. Check server logs for errors"
fi

exit $EXIT_CODE
