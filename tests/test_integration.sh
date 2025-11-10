#!/bin/bash
#
# Integration tests for TeleMux - NEW SESSION-BASED ROUTING
#
# These tests verify the complete flow:
# 1. Shell functions send messages correctly
# 2. Listener routes to tmux sessions
# 3. Error handling for non-existent sessions
# 4. Backward compatibility
#
# These tests should FAIL initially (TDD red phase).
# After implementing new routing, they should PASS (green phase).

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

TESTS_PASSED=0
TESTS_FAILED=0
TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$TEST_DIR")"

# Test counter
TEST_NUM=0

# Test result tracking
declare -a FAILED_TESTS

# Source the telegram config for testing
if [ -f "$HOME/.telemux/telegram_config" ]; then
    source "$HOME/.telemux/telegram_config"
else
    echo -e "${RED}ERROR: No telegram_config found. Run INSTALL.sh first.${NC}"
    exit 1
fi

# Source shell functions for testing
if [ -f "$PROJECT_ROOT/shell_functions.sh" ]; then
    source "$PROJECT_ROOT/shell_functions.sh"
elif [ -f "$HOME/.telemux/shell_functions.sh" ]; then
    source "$HOME/.telemux/shell_functions.sh"
else
    echo -e "${YELLOW}WARNING: shell_functions.sh not found. Some tests may fail.${NC}"
fi

# Helper functions
print_test_header() {
    TEST_NUM=$((TEST_NUM + 1))
    echo ""
    echo -e "${YELLOW}TEST $TEST_NUM: $1${NC}"
}

assert_success() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}  ✓ PASS${NC}"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        echo -e "${RED}  ✗ FAIL: $1${NC}"
        FAILED_TESTS+=("TEST $TEST_NUM: $1")
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

assert_failure() {
    if [ $? -ne 0 ]; then
        echo -e "${GREEN}  ✓ PASS (expected failure)${NC}"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        echo -e "${RED}  ✗ FAIL: $1 (should have failed)${NC}"
        FAILED_TESTS+=("TEST $TEST_NUM: $1")
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

assert_contains() {
    if echo "$1" | grep -q "$2"; then
        echo -e "${GREEN}  ✓ PASS: Found '$2'${NC}"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        echo -e "${RED}  ✗ FAIL: Expected to find '$2' in output${NC}"
        echo "  Output was: $1"
        FAILED_TESTS+=("TEST $TEST_NUM: Expected '$2'")
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

assert_not_contains() {
    if echo "$1" | grep -q "$2"; then
        echo -e "${RED}  ✗ FAIL: Found '$2' (should not be present)${NC}"
        FAILED_TESTS+=("TEST $TEST_NUM: Should not find '$2'")
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    else
        echo -e "${GREEN}  ✓ PASS: '$2' not found (as expected)${NC}"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    fi
}

# Cleanup function
cleanup() {
    echo ""
    echo "Cleaning up test tmux sessions..."
    tmux kill-session -t test-reply 2>/dev/null || true
    tmux kill-session -t test-agent-session 2>/dev/null || true
    tmux kill-session -t integration-test 2>/dev/null || true
}

trap cleanup EXIT

# Start tests
echo "======================================================================"
echo "TeleMux Integration Tests - NEW SESSION-BASED ROUTING"
echo "======================================================================"

# TEST 1: Verify tg_alert shows reply instructions
print_test_header "tg_alert message includes reply instructions"

# Check the function definition in ~/.zshrc
ALERT_FUNCTION=$(sed -n '/^tg_alert()/,/^}/p' ~/.zshrc)

# Should contain reply instructions in the message
echo "$ALERT_FUNCTION" | grep -q "Reply:" && assert_success "tg_alert shows reply format" || assert_failure "tg_alert missing reply instructions"

# TEST 2: Verify message format includes session name
print_test_header "tg_alert message format includes session name for replies"

echo "$ALERT_FUNCTION" | grep -q "\${tmux_session}:" && assert_success "Reply format uses session name" || assert_failure "Reply format doesn't use session name"

# TEST 3: Create test tmux session
print_test_header "Create test tmux session"

tmux new-session -d -s test-reply
assert_success "Created test-reply session"

# Verify it's running
tmux has-session -t test-reply 2>/dev/null
assert_success "test-reply session is running"

# TEST 4: Test parse_message_id in Python
print_test_header "Python parse_message_id handles session-name format"

PARSE_TEST=$(python3 -c "
import sys
sys.path.insert(0, '$PROJECT_ROOT')
import telegram_listener
result = telegram_listener.parse_message_id('test-reply: hello')
print('PASS' if result == ('test-reply', 'hello') else 'FAIL')
")

[ "$PARSE_TEST" = "PASS" ] && assert_success "parse_message_id works correctly" || assert_failure "parse_message_id failed"

# TEST 5: Test routing to existing session (simulated)
print_test_header "Route message to existing tmux session"

# This tests the NEW routing logic in process_update()
# We'll simulate what happens when a message arrives

# Check if process_update checks tmux sessions directly
LISTENER_CODE=$(cat "$PROJECT_ROOT/telegram_listener.py")

# Should contain subprocess.run with tmux list-sessions
echo "$LISTENER_CODE" | grep -q "tmux.*list-sessions" && assert_success "Listener checks tmux sessions directly" || assert_failure "Listener doesn't check tmux directly"

# TEST 6: Test routing handles non-existent session
print_test_header "Show active sessions when target doesn't exist"

# Should send active session list in error message
echo "$LISTENER_CODE" | grep -q "Active sessions:" && assert_success "Error shows active sessions" || assert_failure "Error doesn't show active sessions"

# TEST 7: Test no pre-registration requirement
print_test_header "NEW routing doesn't require outgoing.log lookup"

# The NEW implementation should NOT call lookup_agent() for routing
# It should check tmux directly instead

# Check process_update implementation
PROCESS_UPDATE=$(sed -n '/def process_update/,/^def /p' "$PROJECT_ROOT/telegram_listener.py" | sed '$d')

# Should NOT contain lookup_agent() call in the main routing path
# (it's OK if lookup_agent exists for backward compat, but routing shouldn't depend on it)
echo "$PROCESS_UPDATE" | grep -q "lookup_agent" && echo "  Note: lookup_agent still called (may need removal)" || echo "  ✓ No lookup_agent dependency"

# TEST 8: Verify 1-second sleep before Enter
print_test_header "Message delivery includes 1-second sleep before Enter"

# Check for sleep(1) in route logic
echo "$LISTENER_CODE" | grep -q "time.sleep(1)" && assert_success "Contains required sleep" || assert_failure "Missing sleep before Enter"

# TEST 9: Test backward compatibility with tg_agent
print_test_header "tg_agent function still works"

# tg_agent should still be defined
type tg_agent &>/dev/null
assert_success "tg_agent function exists"

# TEST 10: Test message format sent to tmux
print_test_header "Message format in tmux includes '[FROM USER via Telegram]'"

echo "$LISTENER_CODE" | grep -q "\[FROM USER via Telegram\]" && assert_success "Correct message prefix" || assert_failure "Wrong message prefix"

# TEST 11: Test listener is actually running
print_test_header "Telegram listener daemon is running"

tmux has-session -t telegram-listener 2>/dev/null
assert_success "telegram-listener session exists"

# TEST 12: Test control commands exist
print_test_header "Control commands are defined"

type tg-start &>/dev/null && assert_success "tg-start exists" || assert_failure "tg-start missing"
type tg-stop &>/dev/null && assert_success "tg-stop exists" || assert_failure "tg-stop missing"
type tg-status &>/dev/null && assert_success "tg-status exists" || assert_failure "tg-status missing"

# TEST 13: Verify no duplicate function definitions
print_test_header "Check for DRY violations in shell functions"

# Count how many times tg_alert is defined
ALERT_COUNT=$(grep -c "^tg_alert()" ~/.zshrc "$PROJECT_ROOT/INSTALL.sh" "$PROJECT_ROOT/README.md" 2>/dev/null || echo "0")

if [ "$ALERT_COUNT" -le 2 ]; then
    echo -e "${GREEN}  ✓ Acceptable: tg_alert defined $ALERT_COUNT times${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${YELLOW}  ⚠ WARNING: tg_alert defined $ALERT_COUNT times (DRY violation)${NC}"
fi

# TEST 14: Test edge cases - empty session list
print_test_header "Handle case when no tmux sessions exist"

# Check for "No tmux sessions" error message
echo "$LISTENER_CODE" | grep -q "No tmux sessions" && assert_success "Handles empty session list" || assert_failure "Missing empty session handling"

# Final summary
echo ""
echo "======================================================================"
echo "TEST SUMMARY"
echo "======================================================================"
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Failed: $TESTS_FAILED${NC}"

if [ $TESTS_FAILED -gt 0 ]; then
    echo ""
    echo "Failed tests:"
    for test in "${FAILED_TESTS[@]}"; do
        echo -e "  ${RED}✗ $test${NC}"
    done
    echo ""
    echo -e "${YELLOW}This is expected (TDD red phase).${NC}"
    echo -e "${YELLOW}After implementing new routing, these should pass.${NC}"
    exit 1
else
    echo ""
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
fi
