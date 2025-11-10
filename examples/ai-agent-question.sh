#!/bin/bash
# AI Agent Asking for Guidance
# Example: Agent encounters uncertainty and asks user for direction

AGENT_NAME="cleanup-agent"
INBOX="$HOME/.telemux/agents/$AGENT_NAME/inbox.txt"

echo "🤖 AI Agent: Database Cleanup Task"
echo ""

# Simulate discovering duplicates
echo "Scanning database..."
sleep 2
echo "Found: 3 duplicate customer entries"
echo ""

# Ask user for guidance
QUESTION="🤖 Database Cleanup Agent

Found 3 duplicate customer entries:
  - Customer #1234 (3 records)
  - Customer #5678 (2 records)
  - Customer #9012 (2 records)

What should I do?
  1️⃣ Auto-merge duplicates
  2️⃣ Flag for manual review
  3️⃣ Skip and continue

Reply with: $(tmux display-message -p '#S'): [1/2/3 or description]"

tg_agent "$AGENT_NAME" "$QUESTION"

echo "⏳ Waiting for user's guidance..."

# Clear old inbox
> "$INBOX"

# Wait for response
while true; do
    if [ -f "$INBOX" ]; then
        REPLY=$(grep -v "^\[" "$INBOX" 2>/dev/null | grep -v "^---" | grep -v "^$" | tail -1)

        if [ -n "$REPLY" ]; then
            echo ""
            echo "📨 Received from user: $REPLY"
            echo ""

            if echo "$REPLY" | grep -qi "1\|auto\|merge"; then
                echo "✓ Auto-merging duplicates..."
                sleep 2
                echo "✅ Merged 3 duplicate groups"
                tg_alert "✅ Cleanup Agent: Successfully merged duplicates"
                break

            elif echo "$REPLY" | grep -qi "2\|manual\|review\|flag"; then
                echo "✓ Flagging for manual review..."
                sleep 1
                echo "✅ 3 duplicate groups flagged for review"
                tg_alert "✅ Cleanup Agent: Flagged duplicates for manual review"
                break

            elif echo "$REPLY" | grep -qi "3\|skip\|continue"; then
                echo "✓ Skipping duplicates..."
                echo "✅ Continuing with other tasks"
                tg_alert "✅ Cleanup Agent: Skipped duplicates, continuing"
                break
            else
                echo "⚠️  Unclear response, waiting for clarification..."
            fi
        fi
    fi
    sleep 3
done

echo ""
echo "✅ Task complete!"
