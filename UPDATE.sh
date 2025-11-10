#!/bin/bash
# TeleMux Update Script
# Updates an existing installation to the latest version

set -e

echo "================================"
echo "TeleMux Update"
echo "================================"
echo ""

# Check if TeleMux is already installed
if [ ! -d "$HOME/.telemux" ]; then
    echo "❌ TeleMux is not installed"
    echo "   Run ./INSTALL.sh to install for the first time"
    exit 1
fi

echo "Detected existing TeleMux installation"
echo ""

# Detect shell
SHELL_RC=""
if [ -n "$ZSH_VERSION" ]; then
    SHELL_RC="$HOME/.zshrc"
elif [ -n "$BASH_VERSION" ]; then
    SHELL_RC="$HOME/.bashrc"
else
    echo "⚠️  Could not detect shell (zsh/bash)"
    read -p "Enter path to your shell RC file: " SHELL_RC
fi

echo "Shell config: $SHELL_RC"
echo ""

# Stop listener if running
LISTENER_RUNNING=false
if tmux has-session -t telegram-listener 2>/dev/null; then
    LISTENER_RUNNING=true
    echo "🛑 Stopping listener daemon..."
    tmux kill-session -t telegram-listener
    echo "✅ Listener stopped"
    echo ""
fi

# Update scripts
echo "=== Updating Scripts ==="
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Updating telegram_listener.py..."
cp "$SCRIPT_DIR/telegram_listener.py" ~/.telemux/
chmod +x ~/.telemux/telegram_listener.py
echo "✅ Listener daemon updated"

echo "Updating telegram_control.sh..."
cp "$SCRIPT_DIR/telegram_control.sh" ~/.telemux/
chmod +x ~/.telemux/telegram_control.sh
echo "✅ Control script updated"

# Install new cleanup script if it exists
if [ -f "$SCRIPT_DIR/cleanup-logs.sh" ]; then
    echo "Installing cleanup-logs.sh..."
    cp "$SCRIPT_DIR/cleanup-logs.sh" ~/.telemux/
    chmod +x ~/.telemux/cleanup-logs.sh
    echo "✅ Cleanup script installed"
fi

echo ""
echo "=== Updating Shell Configuration ==="
echo ""

# Check which aliases are missing
MISSING_ALIASES=()

if ! grep -q "tg-cleanup" "$SHELL_RC" 2>/dev/null; then
    MISSING_ALIASES+=("tg-cleanup")
fi

if ! grep -q "tg-doctor" "$SHELL_RC" 2>/dev/null; then
    MISSING_ALIASES+=("tg-doctor")
fi

if [ ${#MISSING_ALIASES[@]} -eq 0 ]; then
    echo "✅ All aliases are up to date"
else
    echo "Found missing aliases: ${MISSING_ALIASES[*]}"
    echo ""
    read -p "Add missing aliases to $SHELL_RC? (y/n): " -n 1 -r
    echo

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Find the line with tg-restart alias
        if grep -q "tg-restart" "$SHELL_RC" 2>/dev/null; then
            # Add new aliases after tg-restart
            if [[ " ${MISSING_ALIASES[*]} " =~ " tg-cleanup " ]]; then
                # Check if it's already there (in case of partial update)
                if ! grep -q "tg-cleanup" "$SHELL_RC" 2>/dev/null; then
                    # Add after tg-restart line
                    sed -i.bak '/alias tg-restart=/a\
alias tg-cleanup="$HOME/.telemux/telegram_control.sh cleanup"
' "$SHELL_RC"
                    echo "✅ Added tg-cleanup alias"
                fi
            fi

            if [[ " ${MISSING_ALIASES[*]} " =~ " tg-doctor " ]]; then
                if ! grep -q "tg-doctor" "$SHELL_RC" 2>/dev/null; then
                    sed -i.bak '/alias tg-restart=/a\
alias tg-doctor="$HOME/.telemux/telegram_control.sh doctor"
' "$SHELL_RC"
                    echo "✅ Added tg-doctor alias"
                fi
            fi

            # Clean up backup file
            rm -f "${SHELL_RC}.bak"
        else
            echo "⚠️  Could not find existing TeleMux aliases in $SHELL_RC"
            echo "   Please add these manually:"
            echo ""
            echo "   alias tg-cleanup=\"\$HOME/.telemux/telegram_control.sh cleanup\""
            echo "   alias tg-doctor=\"\$HOME/.telemux/telegram_control.sh doctor\""
        fi
    else
        echo "Skipped alias update"
        echo ""
        echo "To add manually, add these lines to $SHELL_RC:"
        echo "  alias tg-cleanup=\"\$HOME/.telemux/telegram_control.sh cleanup\""
        echo "  alias tg-doctor=\"\$HOME/.telemux/telegram_control.sh doctor\""
    fi
fi

echo ""
echo "=== Updating Shell Functions ==="
echo ""

# Always copy latest shell_functions.sh to ~/.telemux/
if [ -f "$SCRIPT_DIR/shell_functions.sh" ]; then
    echo "Updating shell functions..."
    cp "$SCRIPT_DIR/shell_functions.sh" "$TELEMUX_DIR/"
    chmod +x "$TELEMUX_DIR/shell_functions.sh"
    echo "✅ Shell functions updated in ~/.telemux/"

    # Check if user is using old embedded functions or new sourced version
    if grep -q "^tg_alert()" "$SHELL_RC" 2>/dev/null; then
        echo ""
        echo "⚠️  Detected old embedded functions in $SHELL_RC"
        echo "   New version uses sourced functions from ~/.telemux/shell_functions.sh"
        echo ""
        echo "   Benefits of migrating:"
        echo "   - Single source of truth (DRY principle)"
        echo "   - Easier updates (just copy new file)"
        echo "   - Cleaner shell configuration"
        echo ""
        read -p "Migrate to sourced functions? (y/n): " -n 1 -r
        echo

        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "Backing up $SHELL_RC to ${SHELL_RC}.backup-$(date +%Y%m%d-%H%M%S)"
            cp "$SHELL_RC" "${SHELL_RC}.backup-$(date +%Y%m%d-%H%M%S)"

            # Remove old embedded functions (from # TELEGRAM NOTIFICATIONS to the end of that block)
            # This is safer than trying to remove exact line ranges
            echo "Removing old embedded functions..."
            sed -i.tmp '/# TELEGRAM NOTIFICATIONS/,/^$/d' "$SHELL_RC"

            # Add new sourced version
            cat >> "$SHELL_RC" << 'SHELL_FUNCTIONS'

# =============================================================================
# TELEGRAM NOTIFICATIONS (TeleMux)
# =============================================================================
# Source TeleMux shell functions (single source of truth)
if [[ -f "$HOME/.telemux/shell_functions.sh" ]]; then
    source "$HOME/.telemux/shell_functions.sh"
fi

SHELL_FUNCTIONS

            rm -f "${SHELL_RC}.tmp"
            echo "✅ Migrated to sourced shell functions"
            echo "   Reload: source $SHELL_RC"
        else
            echo "Skipped migration. Functions in ~/.telemux/shell_functions.sh are still updated."
            echo "   You can manually source them: source ~/.telemux/shell_functions.sh"
        fi
    else
        echo "✅ Already using sourced functions (no migration needed)"
    fi
else
    echo "⚠️  shell_functions.sh not found in $SCRIPT_DIR"
    echo "   This might be an old version of the repo. Functions not updated."
fi

echo ""
echo "=== Python Dependencies ==="
echo ""

# Check if requirements.txt exists and install dependencies
if [ -f "$SCRIPT_DIR/requirements.txt" ]; then
    if command -v pip3 >/dev/null 2>&1; then
        echo "Checking Python dependencies..."
        pip3 install -q -r "$SCRIPT_DIR/requirements.txt"
        echo "✅ Dependencies up to date"
    else
        echo "⚠️  pip3 not found, skipping dependency check"
    fi
fi

echo ""
echo "================================"
echo "✅ Update Complete!"
echo "================================"
echo ""

# Show what's new
echo "=== New in this version ==="
echo ""
echo "📦 New Commands:"
echo "  • tg-cleanup  - Rotate and clean up log files"
echo "  • tg-doctor   - Health check and diagnostics"
echo ""
echo "🔧 Improvements:"
echo "  • Retry logic with exponential backoff"
echo "  • Enhanced error handling and logging"
echo "  • Separate error log file"
echo "  • Log rotation (10MB limit)"
echo "  • Configuration validation"
echo ""
echo "📝 New Scripts:"
echo "  • cleanup-logs.sh - Automatic log rotation"
echo "  • MIGRATE.sh      - Migrate from .team_mux"
echo "  • UNINSTALL.sh    - Clean uninstaller"
echo ""

echo "Next steps:"
echo "  1. Reload your shell: source $SHELL_RC"
echo "  2. Start listener: tg-start"
echo "  3. Run health check: tg-doctor"
echo "  4. Optional: tg-cleanup --install-cron"
echo ""

# Restart listener if it was running
if [ "$LISTENER_RUNNING" = true ]; then
    read -p "Restart listener now? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo ""
        echo "🚀 Starting listener..."
        tmux new-session -d -s telegram-listener "python3 $HOME/.telemux/telegram_listener.py"
        sleep 1
        if tmux has-session -t telegram-listener 2>/dev/null; then
            echo "✅ Listener restarted successfully"
        else
            echo "❌ Failed to restart listener"
            echo "   Start manually with: tg-start"
        fi
    fi
fi

echo ""
echo "See CHANGELOG.md for full details"
echo ""
