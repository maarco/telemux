#!/bin/bash
# Deployment Script with Telegram Approval
# Example: Request approval before deploying to production

set -e

VERSION="${1:-v1.0.0}"
ENVIRONMENT="${2:-production}"

echo "🚀 Deployment Request"
echo "   Version: $VERSION"
echo "   Environment: $ENVIRONMENT"
echo ""

# Send approval request to Telegram
tg_agent "deploy-agent" "🚀 Deploy $VERSION to $ENVIRONMENT?

Options:
  yes - Proceed with deployment
  no  - Cancel deployment

Reply with: $(tmux display-message -p '#S'): yes/no"

# Wait for approval
INBOX="$HOME/.telemux/agents/deploy-agent/inbox.txt"
echo "⏳ Waiting for approval via Telegram..."

# Timeout after 5 minutes
TIMEOUT=300
ELAPSED=0

while [ $ELAPSED -lt $TIMEOUT ]; do
    if [ -f "$INBOX" ]; then
        # Get last non-empty line that's not a timestamp
        REPLY=$(grep -v "^\[" "$INBOX" 2>/dev/null | grep -v "^---" | grep -v "^$" | tail -1)

        if echo "$REPLY" | grep -qi "yes\|approve\|proceed\|go"; then
            echo ""
            echo "✅ Deployment approved by user!"
            echo ""

            # Simulate deployment
            echo "📦 Building application..."
            sleep 2
            echo "🚢 Deploying to $ENVIRONMENT..."
            sleep 3
            echo "✅ Deployment complete!"

            # Notify completion
            tg_alert "✅ Deployment successful: $VERSION → $ENVIRONMENT"
            exit 0

        elif echo "$REPLY" | grep -qi "no\|cancel\|reject\|stop"; then
            echo ""
            echo "❌ Deployment cancelled by user"
            tg_alert "❌ Deployment cancelled: $VERSION"
            exit 1
        fi
    fi

    sleep 5
    ELAPSED=$((ELAPSED + 5))
done

# Timeout reached
echo ""
echo "⏱️  Approval timeout (${TIMEOUT}s)"
tg_alert "⏱️ Deployment timed out: $VERSION (no response)"
exit 1
