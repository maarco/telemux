#!/usr/bin/env bash
# TeleMux Performance Benchmarking Script
#
# Tests system stability and performance under load
# Sends configurable number of messages and measures response times

set -euo pipefail

# Configuration
BENCHMARK_SESSION="telemux-benchmark"
MESSAGE_COUNT="${1:-1000}"
DELAY_MS="${2:-100}"
LOG_FILE="$HOME/.telemux/benchmark_$(date +%Y%m%d_%H%M%S).log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}==================================================${NC}"
echo -e "${BLUE}    TeleMux Performance Benchmark${NC}"
echo -e "${BLUE}==================================================${NC}"
echo ""
echo "Configuration:"
echo "  Message count: $MESSAGE_COUNT"
echo "  Delay between messages: ${DELAY_MS}ms"
echo "  Log file: $LOG_FILE"
echo ""

# Check if tg_alert function exists
if ! type tg_alert &>/dev/null; then
    echo -e "${RED}ERROR: tg_alert function not found${NC}"
    echo "Please ensure TeleMux is installed and shell functions are loaded"
    echo "Run: source ~/.zshrc  (or source ~/.bashrc)"
    exit 1
fi

# Check if listener is running
if ! tmux has-session -t telegram-listener 2>/dev/null; then
    echo -e "${YELLOW}WARNING: Telegram listener not running${NC}"
    echo "Starting listener with: tg-start"
    if ! tg-start; then
        echo -e "${RED}ERROR: Failed to start listener${NC}"
        exit 1
    fi
    sleep 3
fi

# Create benchmark session if it doesn't exist
if ! tmux has-session -t "$BENCHMARK_SESSION" 2>/dev/null; then
    echo "Creating benchmark tmux session: $BENCHMARK_SESSION"
    tmux new-session -d -s "$BENCHMARK_SESSION"
fi

echo ""
echo -e "${GREEN}Starting benchmark...${NC}"
echo ""

# Initialize counters
sent_count=0
success_count=0
fail_count=0
start_time=$(date +%s)

# Create log file header
{
    echo "TeleMux Performance Benchmark"
    echo "Started: $(date -Iseconds)"
    echo "Message count: $MESSAGE_COUNT"
    echo "Delay: ${DELAY_MS}ms"
    echo "----------------------------------------"
} > "$LOG_FILE"

# Send messages
for i in $(seq 1 "$MESSAGE_COUNT"); do
    timestamp=$(date +%s.%N)
    message="Benchmark message $i/$MESSAGE_COUNT (timestamp: $timestamp)"

    # Send message and capture result
    if tg_alert "$message" >> "$LOG_FILE" 2>&1; then
        ((success_count++))

        # Progress indicator every 100 messages
        if ((i % 100 == 0)); then
            elapsed=$(($(date +%s) - start_time))
            rate=$((i / (elapsed > 0 ? elapsed : 1)))
            echo -e "${GREEN}[+]${NC} Sent $i/$MESSAGE_COUNT messages ($success_count successful, $fail_count failed) - ${rate} msg/s"
        fi
    else
        ((fail_count++))
        echo -e "${RED}[-]${NC} Failed to send message $i" | tee -a "$LOG_FILE"
    fi

    ((sent_count++))

    # Delay between messages (convert ms to seconds for sleep)
    if ((DELAY_MS > 0)); then
        sleep "$(awk "BEGIN {print $DELAY_MS/1000}")"
    fi
done

# Calculate final stats
end_time=$(date +%s)
total_duration=$((end_time - start_time))
avg_rate=$((sent_count / (total_duration > 0 ? total_duration : 1)))
success_rate=$((success_count * 100 / sent_count))

echo ""
echo -e "${BLUE}==================================================${NC}"
echo -e "${BLUE}    Benchmark Complete${NC}"
echo -e "${BLUE}==================================================${NC}"
echo ""
echo "Results:"
echo "  Total messages: $sent_count"
echo -e "  Successful: ${GREEN}$success_count${NC}"
echo -e "  Failed: ${RED}$fail_count${NC}"
echo "  Success rate: ${success_rate}%"
echo "  Duration: ${total_duration}s"
echo "  Average rate: ${avg_rate} msg/s"
echo ""
echo "Log file: $LOG_FILE"
echo ""

# Write summary to log
{
    echo "----------------------------------------"
    echo "Benchmark Complete"
    echo "Finished: $(date -Iseconds)"
    echo "Total messages: $sent_count"
    echo "Successful: $success_count"
    echo "Failed: $fail_count"
    echo "Success rate: ${success_rate}%"
    echo "Duration: ${total_duration}s"
    echo "Average rate: ${avg_rate} msg/s"
} >> "$LOG_FILE"

# Check listener health after benchmark
echo "Checking listener health..."
if tg-status | grep -q "running"; then
    echo -e "${GREEN}[+] Listener still running and healthy${NC}"
else
    echo -e "${RED}[-] WARNING: Listener may have crashed during benchmark${NC}"
    echo "Check logs with: tg-logs"
fi

echo ""
echo "To analyze results:"
echo "  cat $LOG_FILE"
echo "  tg-logs  # Check listener logs"
echo ""

# Check for errors in listener log
listener_log="$HOME/.telemux/telegram_listener.log"
if [ -f "$listener_log" ]; then
    error_count=$(grep -c "ERROR" "$listener_log" 2>/dev/null || echo "0")
    if ((error_count > 0)); then
        echo -e "${YELLOW}WARNING: Found $error_count errors in listener log${NC}"
        echo "Recent errors:"
        tail -20 "$listener_log" | grep "ERROR" || true
    fi
fi

if ((success_rate >= 95)); then
    echo -e "${GREEN}✓ PASS: Success rate ${success_rate}% meets threshold (>=95%)${NC}"
    exit 0
elif ((success_rate >= 80)); then
    echo -e "${YELLOW}⚠ MARGINAL: Success rate ${success_rate}% below ideal (>=95%)${NC}"
    exit 1
else
    echo -e "${RED}✗ FAIL: Success rate ${success_rate}% below acceptable threshold (>=80%)${NC}"
    exit 2
fi
