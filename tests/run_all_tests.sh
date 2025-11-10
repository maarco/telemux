#!/bin/bash
#
# Master test runner for TeleMux
#
# Runs all tests in sequence:
# 1. Python unit tests
# 2. Shell integration tests
#
# Usage: ./run_all_tests.sh

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[1;34m'
NC='\033[0m'

TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$TEST_DIR")"

echo ""
echo "======================================================================"
echo -e "${BLUE}TeleMux Test Suite - Session-Based Routing (TDD)${NC}"
echo "======================================================================"
echo ""
echo "This test suite validates the NEW routing implementation:"
echo "  - Route messages directly to tmux sessions (no pre-registration)"
echo "  - Check if tmux session exists"
echo "  - Show active sessions if target doesn't exist"
echo "  - Make tg_alert bidirectional"
echo ""
echo -e "${YELLOW}Expected: Tests will FAIL initially (TDD red phase)${NC}"
echo -e "${YELLOW}After implementation: Tests should PASS (TDD green phase)${NC}"
echo ""

# Track overall results
TOTAL_PASSED=0
TOTAL_FAILED=0
SUITE_FAILED=0

# Run Python unit tests
echo "======================================================================"
echo -e "${BLUE}Running Python Unit Tests${NC}"
echo "======================================================================"
echo ""

cd "$TEST_DIR"

if python3 test_telegram_listener.py; then
    echo -e "${GREEN}Python unit tests PASSED${NC}"
    PYTHON_RESULT="PASS"
else
    echo -e "${RED}Python unit tests FAILED${NC}"
    PYTHON_RESULT="FAIL"
    SUITE_FAILED=1
fi

echo ""
echo ""

# Run Shell integration tests
echo "======================================================================"
echo -e "${BLUE}Running Shell Integration Tests${NC}"
echo "======================================================================"
echo ""

if bash test_integration.sh; then
    echo -e "${GREEN}Shell integration tests PASSED${NC}"
    SHELL_RESULT="PASS"
else
    echo -e "${RED}Shell integration tests FAILED${NC}"
    SHELL_RESULT="FAIL"
    SUITE_FAILED=1
fi

echo ""
echo ""

# Final summary
echo "======================================================================"
echo -e "${BLUE}FINAL TEST SUMMARY${NC}"
echo "======================================================================"
echo ""
echo "Python Unit Tests:        $PYTHON_RESULT"
echo "Shell Integration Tests:  $SHELL_RESULT"
echo ""

if [ $SUITE_FAILED -eq 0 ]; then
    echo -e "${GREEN}╔══════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  ALL TESTS PASSED - READY TO DEPLOY ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════╝${NC}"
    echo ""
    echo "New routing logic is working correctly"
    echo "Backward compatibility maintained"
    echo "Edge cases handled properly"
    echo ""
    exit 0
else
    echo -e "${RED}╔═══════════════════════════════════╗${NC}"
    echo -e "${RED}║  TESTS FAILED - NEEDS FIXING      ║${NC}"
    echo -e "${RED}╚═══════════════════════════════════╝${NC}"
    echo ""
    echo -e "${YELLOW}TDD Process:${NC}"
    echo "  1. Tests written (RED phase)"
    echo "  2. → Implement new routing logic"
    echo "  3. → Run tests again (GREEN phase)"
    echo "  4. → Refactor if needed"
    echo ""
    echo "Next steps:"
    echo "  - Review failed tests above"
    echo "  - Implement new routing in telegram_listener.py"
    echo "  - Update shell functions in INSTALL.sh"
    echo "  - Re-run: ./run_all_tests.sh"
    echo ""
    exit 1
fi
