#!/bin/bash
# TeleMux Installation Script

set -e

echo "================================"
echo "TeleMux Installation"
echo "================================"
echo ""

# Check prerequisites
echo "Checking prerequisites..."
command -v tmux >/dev/null 2>&1 || { echo "❌ tmux is required but not installed. Aborting." >&2; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "❌ python3 is required but not installed. Aborting." >&2; exit 1; }
command -v curl >/dev/null 2>&1 || { echo "❌ curl is required but not installed. Aborting." >&2; exit 1; }
echo "✅ All prerequisites met"
echo ""

# Get Telegram credentials
echo "=== Telegram Configuration ==="
echo ""
read -p "Enter your Telegram Bot Token: " BOT_TOKEN
read -p "Enter your Chat ID (group or personal): " CHAT_ID

# Create TeleMux directory
echo "Creating ~/.telemux directory..."
mkdir -p ~/.telemux/message_queue
echo "✅ Directory structure created"
echo ""

# Create config file
echo "Creating ~/.telemux/telegram_config..."
cat > ~/.telemux/telegram_config << EOF
#!/bin/bash
# TeleMux Telegram Bot Configuration
# Keep this file secure! (chmod 600)

export TELEMUX_TG_BOT_TOKEN="${BOT_TOKEN}"
export TELEMUX_TG_CHAT_ID="${CHAT_ID}"
EOF

chmod 600 ~/.telemux/telegram_config
echo "✅ Config file created and secured"
echo ""

# Install files
echo "Installing files..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cp "$SCRIPT_DIR/telegram_listener.py" ~/.telemux/
chmod +x ~/.telemux/telegram_listener.py

cp "$SCRIPT_DIR/telegram_control.sh" ~/.telemux/
chmod +x ~/.telemux/telegram_control.sh

echo "✅ Files installed"
echo ""

# Detect shell
SHELL_RC=""
if [ -n "$ZSH_VERSION" ]; then
    SHELL_RC="$HOME/.zshrc"
elif [ -n "$BASH_VERSION" ]; then
    SHELL_RC="$HOME/.bashrc"
else
    echo "⚠️  Could not detect shell. Please manually add functions to your rc file."
    echo "    See README.md for shell function code."
    exit 0
fi

# Check if already installed
if grep -q "# TELEGRAM NOTIFICATIONS" "$SHELL_RC" 2>/dev/null; then
    echo "⚠️  Shell functions already exist in $SHELL_RC"
    read -p "Overwrite? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Skipping shell function installation"
        echo "✅ Installation complete (files only)"
        exit 0
    fi
fi

# Add shell functions
echo "Adding shell functions to $SHELL_RC..."
cat >> "$SHELL_RC" << 'SHELL_FUNCTIONS'

# =============================================================================
# TELEGRAM NOTIFICATIONS
# =============================================================================

# Load Telegram config
if [[ -f "$HOME/.telemux/telegram_config" ]]; then
    source "$HOME/.telemux/telegram_config"
fi

# Simple alert function - send any message to Telegram
tg_alert() {
    local message="$*"
    if [[ -z "$message" ]]; then
        echo "Usage: tg_alert <message>"
        return 1
    fi

    if [[ -z "$TELEMUX_TG_BOT_TOKEN" ]] || [[ -z "$TELEMUX_TG_CHAT_ID" ]]; then
        echo "Error: TeleMux not configured. Check ~/.telemux/telegram_config"
        return 1
    fi

    curl -s -X POST "https://api.telegram.org/bot${TELEMUX_TG_BOT_TOKEN}/sendMessage" \
        -d chat_id="${TELEMUX_TG_CHAT_ID}" \
        -d text="🔔 ${message}" \
        -d parse_mode="HTML" > /dev/null && echo "✓ Alert sent to Telegram"
}

# Bidirectional agent alert - sends message and can receive replies
tg_agent() {
    local agent_name="$1"
    local message="$2"

    if [[ -z "$agent_name" ]] || [[ -z "$message" ]]; then
        echo "Usage: tg_agent <agent_name> <message>"
        return 1
    fi

    # Use tmux session name as message ID (much simpler!)
    local tmux_session="$(tmux display-message -p '#S' 2>/dev/null || echo 'unknown')"
    local msg_id="${tmux_session}"

    # Record mapping for listener daemon
    mkdir -p "$HOME/.telemux/message_queue"
    echo "${msg_id}:${agent_name}:${tmux_session}:$(date -Iseconds)" >> "$HOME/.telemux/message_queue/outgoing.log"

    # Send to Telegram with identifier
    curl -s -X POST "https://api.telegram.org/bot${TELEMUX_TG_BOT_TOKEN}/sendMessage" \
        -d chat_id="${TELEMUX_TG_CHAT_ID}" \
        -d text="🤖 <b>[${agent_name}:${msg_id}]</b>

${message}

<i>Reply with: ${msg_id}: your response</i>" \
        -d parse_mode="HTML" > /dev/null && echo "✓ Agent alert sent: ${msg_id}"

    echo "$msg_id"  # Return message ID
}

# Alert when command completes
tg_done() {
    local exit_code=$?
    local cmd="${history[$((HISTCMD-1))]}"

    if [[ $exit_code -eq 0 ]]; then
        tg_alert "✅ Command completed: ${cmd}"
    else
        tg_alert "❌ Command failed (exit $exit_code): ${cmd}"
    fi
}

# Telegram listener control
alias tg-start="$HOME/.telemux/telegram_control.sh start"
alias tg-stop="$HOME/.telemux/telegram_control.sh stop"
alias tg-status="$HOME/.telemux/telegram_control.sh status"
alias tg-logs="$HOME/.telemux/telegram_control.sh logs"
alias tg-restart="$HOME/.telemux/telegram_control.sh restart"

SHELL_FUNCTIONS

echo "✅ Shell functions added"
echo ""

# Test installation
echo "=== Testing Installation ==="
source ~/.telemux/telegram_config

echo "Testing Telegram bot connection..."
RESPONSE=$(curl -s "https://api.telegram.org/bot${TELEMUX_TG_BOT_TOKEN}/getMe")

if echo "$RESPONSE" | grep -q '"ok":true'; then
    BOT_NAME=$(echo "$RESPONSE" | grep -o '"first_name":"[^"]*"' | cut -d'"' -f4)
    echo "✅ Bot connection successful: $BOT_NAME"
else
    echo "❌ Bot connection failed. Please check your bot token."
    echo "Response: $RESPONSE"
    exit 1
fi

echo ""
echo "================================"
echo "✅ Installation Complete!"
echo "================================"
echo ""
echo "Next steps:"
echo "  1. Reload your shell: source ~/$SHELL_RC"
echo "  2. Start the listener: tg-start"
echo "  3. Test it: tg_alert 'Hello from terminal!'"
echo ""
echo "See README.md for full documentation and examples."
echo ""
