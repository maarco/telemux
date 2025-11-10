#!/bin/bash
# TeleMux Installation Script

set -e

# Script directory and installation directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TELEMUX_DIR="$HOME/.telemux"

echo "================================"
echo "TeleMux Installation"
echo "================================"
echo ""

# Check prerequisites
echo "Checking prerequisites..."
command -v tmux >/dev/null 2>&1 || { echo "ERROR: tmux is required but not installed. Aborting." >&2; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "ERROR: python3 is required but not installed. Aborting." >&2; exit 1; }
command -v curl >/dev/null 2>&1 || { echo "ERROR: curl is required but not installed. Aborting." >&2; exit 1; }

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $PYTHON_VERSION"

# Check pip
if ! command -v pip3 >/dev/null 2>&1; then
    echo "WARNING: pip3 not found. Attempting to continue without dependency check..."
fi

echo "All prerequisites met"
echo ""

# Install Python dependencies
if [ -f "$SCRIPT_DIR/requirements.txt" ] && command -v pip3 >/dev/null 2>&1; then
    echo "Installing Python dependencies..."
    if pip3 install -r "$SCRIPT_DIR/requirements.txt" --quiet; then
        echo "Python dependencies installed"
    else
        echo "WARNING: Failed to install some dependencies. Installation will continue..."
        echo "   You may need to manually run: pip3 install -r $SCRIPT_DIR/requirements.txt"
    fi
    echo ""
fi

# Get Telegram credentials
echo "=== Telegram Configuration ==="
echo ""
read -p "Enter your Telegram Bot Token: " BOT_TOKEN

# Test bot token and fetch available chats
echo ""
echo "Testing bot token and fetching available chats..."
UPDATES_RESPONSE=$(curl -s "https://api.telegram.org/bot${BOT_TOKEN}/getUpdates")

if echo "$UPDATES_RESPONSE" | grep -q '"ok":true'; then
    BOT_INFO=$(curl -s "https://api.telegram.org/bot${BOT_TOKEN}/getMe")
    BOT_NAME=$(echo "$BOT_INFO" | grep -o '"first_name":"[^"]*"' | cut -d'"' -f4)
    echo "Bot token valid: $BOT_NAME"
    echo ""

    # Parse and display available chats
    echo "Available chats (send a message to your bot first if empty):"
    echo "-----------------------------------------------------------"

    # Extract chat IDs and titles/names
    CHAT_COUNT=$(echo "$UPDATES_RESPONSE" | grep -o '"chat":{[^}]*}' | wc -l | tr -d ' ')

    if [ "$CHAT_COUNT" -gt 0 ]; then
        # Create temp file for deduplication
        TEMP_CHATS=$(mktemp)

        echo "$UPDATES_RESPONSE" | grep -o '"chat":{[^}]*}' | while IFS= read -r chat; do
            CHAT_ID=$(echo "$chat" | grep -o '"id":[^,}]*' | head -1 | cut -d':' -f2 | tr -d ' ')
            CHAT_TYPE=$(echo "$chat" | grep -o '"type":"[^"]*"' | cut -d'"' -f4)

            # Try to get name/title
            if echo "$chat" | grep -q '"title"'; then
                CHAT_NAME=$(echo "$chat" | grep -o '"title":"[^"]*"' | cut -d'"' -f4)
            elif echo "$chat" | grep -q '"first_name"'; then
                FIRST_NAME=$(echo "$chat" | grep -o '"first_name":"[^"]*"' | cut -d'"' -f4)
                LAST_NAME=$(echo "$chat" | grep -o '"last_name":"[^"]*"' | cut -d'"' -f4 || echo "")
                CHAT_NAME="$FIRST_NAME $LAST_NAME"
            else
                CHAT_NAME="Unknown"
            fi

            echo "$CHAT_ID|$CHAT_TYPE|$CHAT_NAME"
        done | sort -u > "$TEMP_CHATS"

        # Display unique chats
        while IFS='|' read -r cid ctype cname; do
            echo "  Chat ID: $cid"
            echo "  Type: $ctype"
            echo "  Name: $cname"
            echo "-----------------------------------------------------------"
        done < "$TEMP_CHATS"

        echo ""
        echo "Note: Group chat IDs are negative, personal chat IDs are positive"
        echo ""

        # Check if exactly one chat found
        UNIQUE_CHAT_COUNT=$(wc -l < "$TEMP_CHATS" | tr -d ' ')

        if [ "$UNIQUE_CHAT_COUNT" -eq 1 ]; then
            # Exactly one chat - offer to use it automatically
            SINGLE_CHAT=$(head -1 "$TEMP_CHATS")
            SINGLE_CHAT_ID=$(echo "$SINGLE_CHAT" | cut -d'|' -f1)
            SINGLE_CHAT_NAME=$(echo "$SINGLE_CHAT" | cut -d'|' -f3)

            echo "Found only one chat: $SINGLE_CHAT_NAME (ID: $SINGLE_CHAT_ID)"
            read -p "Use this chat? (y/n): " -n 1 -r
            echo

            if [[ $REPLY =~ ^[Yy]$ ]]; then
                CHAT_ID="$SINGLE_CHAT_ID"
                echo "Using chat ID: $CHAT_ID"
            else
                read -p "Enter your Chat ID manually: " CHAT_ID
            fi
        else
            # Multiple chats - ask for manual input
            read -p "Enter your Chat ID (from above): " CHAT_ID
        fi

        rm -f "$TEMP_CHATS"
    else
        echo "  No chats found. You need to:"
        echo "  1. Start a conversation with your bot (send any message)"
        echo "  2. Or add the bot to a group and send a message"
        echo "  3. Then run this installer again"
        echo ""
        echo "  Or manually enter your chat ID if you know it:"
        read -p "Enter your Chat ID (or press Ctrl+C to exit): " CHAT_ID
    fi
else
    echo "ERROR: Invalid bot token. Please check and try again."
    echo "Response: $UPDATES_RESPONSE"
    exit 1
fi

# Create TeleMux directory
echo "Creating ~/.telemux directory..."
mkdir -p ~/.telemux/message_queue
echo "Directory structure created"
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
echo "Config file created and secured"
echo ""

# Install files
echo "Installing files..."

cp "$SCRIPT_DIR/telegram_listener.py" ~/.telemux/
chmod +x ~/.telemux/telegram_listener.py

cp "$SCRIPT_DIR/telegram_control.sh" ~/.telemux/
chmod +x ~/.telemux/telegram_control.sh

if [ -f "$SCRIPT_DIR/cleanup-logs.sh" ]; then
    cp "$SCRIPT_DIR/cleanup-logs.sh" ~/.telemux/
    chmod +x ~/.telemux/cleanup-logs.sh
fi

echo "Files installed"
echo ""

# Detect shell
SHELL_RC=""
if [ -n "$ZSH_VERSION" ]; then
    SHELL_RC="$HOME/.zshrc"
elif [ -n "$BASH_VERSION" ]; then
    SHELL_RC="$HOME/.bashrc"
else
    echo "ERROR: Could not detect shell (bash/zsh). Unsupported shell."
    echo "   Please manually add functions to your rc file."
    echo "   See README.md for shell function code."
    exit 1
fi

# Check if already installed
if grep -q "# TELEGRAM NOTIFICATIONS" "$SHELL_RC" 2>/dev/null; then
    echo "WARNING: Shell functions already exist in $SHELL_RC"
    read -p "Overwrite? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Skipping shell function installation"
        echo "Installation complete (files only)"
        exit 0
    fi
fi

# Copy shell functions to ~/.telemux/
echo "Deploying shell functions..."
cp "$SCRIPT_DIR/shell_functions.sh" "$TELEMUX_DIR/"
chmod +x "$TELEMUX_DIR/shell_functions.sh"
echo "Shell functions deployed to ~/.telemux/"

# Add shell functions to shell RC by sourcing the single source file
echo "Adding shell functions to $SHELL_RC..."
cat >> "$SHELL_RC" << 'SHELL_FUNCTIONS'

# =============================================================================
# TELEGRAM NOTIFICATIONS (TeleMux)
# =============================================================================
# Source TeleMux shell functions (single source of truth)
if [[ -f "$HOME/.telemux/shell_functions.sh" ]]; then
    source "$HOME/.telemux/shell_functions.sh"
fi

SHELL_FUNCTIONS

echo "Shell functions added (sourced from ~/.telemux/shell_functions.sh)"
echo ""

# Test installation
echo "=== Testing Installation ==="
source ~/.telemux/telegram_config

echo "Verifying chat ID..."
TEST_MESSAGE="TeleMux installation test - $(date)"
SEND_RESPONSE=$(curl -s -X POST "https://api.telegram.org/bot${TELEMUX_TG_BOT_TOKEN}/sendMessage" \
    -d chat_id="${TELEMUX_TG_CHAT_ID}" \
    -d text="$TEST_MESSAGE" \
    -d parse_mode="HTML")

if echo "$SEND_RESPONSE" | grep -q '"ok":true'; then
    echo "Test message sent successfully to chat $TELEMUX_TG_CHAT_ID"
else
    echo "ERROR: Failed to send test message. Please verify your chat ID."
    echo "Response: $SEND_RESPONSE"
    exit 1
fi

echo ""
echo "================================"
echo "Installation Complete!"
echo "================================"
echo ""
echo "Next steps:"
echo "  1. Reload your shell: source $SHELL_RC"
echo "  2. Start the listener: tg-start"
echo ""
echo "See README.md for full documentation and examples."
echo ""

# Optional: Add to Claude Code configuration
if [ -f "$HOME/.claude/CLAUDE.md" ]; then
    echo "================================"
    echo "Claude Code Integration"
    echo "================================"
    echo ""
    echo "Found Claude Code configuration at ~/.claude/CLAUDE.md"
    echo ""
    read -p "Add TeleMux documentation to Claude config? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Check if TeleMux section already exists
        if grep -q "# TeleMux" "$HOME/.claude/CLAUDE.md" 2>/dev/null; then
            echo "WARNING: TeleMux section already exists in Claude config"
        else
            cat >> "$HOME/.claude/CLAUDE.md" << 'CLAUDE_DOC'

---

# TeleMux - Telegram Integration

TeleMux is installed and available for bidirectional communication with Telegram.

## Available Functions

- `tg_alert "message"` - Send one-way notifications to Telegram
- `tg_agent "agent-name" "message"` - Send message and receive replies
- `tg_done` - Alert when previous command completes

## Control Commands

- `tg-start` - Start the listener daemon
- `tg-stop` - Stop the listener daemon
- `tg-status` - Check daemon status
- `tg-logs` - View listener logs

## Usage in Agents

When running in tmux, agents can use `tg_agent` to ask questions and receive user replies via Telegram. Replies are delivered directly back to the tmux session.

**Example:**
```bash
tg_agent "deploy-agent" "Ready to deploy to production?"
# User replies via Telegram: "session-name: yes"
# Reply appears in terminal
```

See: `~/.telemux/` for configuration and logs.

CLAUDE_DOC
            echo "TeleMux documentation added to Claude config"
        fi
    else
        echo "Skipped Claude config update"
    fi
    echo ""
fi
