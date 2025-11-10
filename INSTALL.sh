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

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $PYTHON_VERSION"

# Check pip
if ! command -v pip3 >/dev/null 2>&1; then
    echo "⚠️  pip3 not found. Attempting to continue without dependency check..."
fi

echo "✅ All prerequisites met"
echo ""

# Install Python dependencies
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/requirements.txt" ] && command -v pip3 >/dev/null 2>&1; then
    echo "Installing Python dependencies..."
    if pip3 install -r "$SCRIPT_DIR/requirements.txt" --quiet; then
        echo "✅ Python dependencies installed"
    else
        echo "⚠️  Failed to install some dependencies. Installation will continue..."
        echo "   You may need to manually run: pip3 install -r $SCRIPT_DIR/requirements.txt"
    fi
    echo ""
fi

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

if [ -f "$SCRIPT_DIR/cleanup-logs.sh" ]; then
    cp "$SCRIPT_DIR/cleanup-logs.sh" ~/.telemux/
    chmod +x ~/.telemux/cleanup-logs.sh
fi

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

# Copy shell functions to ~/.telemux/
echo "Deploying shell functions..."
cp "$SCRIPT_DIR/shell_functions.sh" "$TELEMUX_DIR/"
chmod +x "$TELEMUX_DIR/shell_functions.sh"
echo "✅ Shell functions deployed to ~/.telemux/"

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

echo "✅ Shell functions added (sourced from ~/.telemux/shell_functions.sh)"
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
echo "  1. Reload your shell: source $SHELL_RC"
echo "  2. Start the listener: tg-start"
echo "  3. Test it: tg_alert 'Hello from terminal!'"
echo ""
echo "See README.md for full documentation and examples."
echo ""

# Optional: Add to Claude Code configuration
if [ -f "$HOME/.claude/CLAUDE.md" ]; then
    echo "================================"
    echo "Claude Code Integration"
    echo "================================"
    echo ""
    echo "📋 Found Claude Code configuration at ~/.claude/CLAUDE.md"
    echo ""
    read -p "Add TeleMux documentation to Claude config? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Check if TeleMux section already exists
        if grep -q "# TeleMux" "$HOME/.claude/CLAUDE.md" 2>/dev/null; then
            echo "⚠️  TeleMux section already exists in Claude config"
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
            echo "✅ TeleMux documentation added to Claude config"
        fi
    else
        echo "Skipped Claude config update"
    fi
    echo ""
fi
