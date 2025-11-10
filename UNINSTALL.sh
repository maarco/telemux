#!/bin/bash
# TeleMux Uninstallation Script

set -e

echo "================================"
echo "TeleMux Uninstallation"
echo "================================"
echo ""
echo "This will remove:"
echo "  - ~/.telemux/ directory and all data"
echo "  - Shell functions from your rc file"
echo "  - Listener daemon (if running)"
echo ""
read -p "Are you sure you want to uninstall TeleMux? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Uninstallation cancelled"
    exit 0
fi
echo ""

# Stop listener if running
TMUX_SESSION="telegram-listener"
if tmux has-session -t "$TMUX_SESSION" 2>/dev/null; then
    echo "🛑 Stopping listener daemon..."
    tmux kill-session -t "$TMUX_SESSION"
    echo "✅ Listener stopped"
else
    echo "ℹ️  Listener is not running"
fi
echo ""

# Backup data option
TELEMUX_DIR="$HOME/.telemux"
if [ -d "$TELEMUX_DIR" ]; then
    echo "Found TeleMux data directory"
    read -p "Create backup before removal? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        BACKUP_FILE="$HOME/telemux-backup-$(date +%Y%m%d-%H%M%S).tar.gz"
        echo "📦 Creating backup: $BACKUP_FILE"
        tar -czf "$BACKUP_FILE" -C "$HOME" .telemux
        echo "✅ Backup created: $BACKUP_FILE"
        echo ""
    fi

    # Remove directory
    echo "🗑️  Removing ~/.telemux directory..."
    rm -rf "$TELEMUX_DIR"
    echo "✅ Directory removed"
else
    echo "ℹ️  No TeleMux directory found"
fi
echo ""

# Remove shell functions
SHELL_RC=""
if [ -n "$ZSH_VERSION" ]; then
    SHELL_RC="$HOME/.zshrc"
elif [ -n "$BASH_VERSION" ]; then
    SHELL_RC="$HOME/.bashrc"
else
    echo "⚠️  Could not detect shell. Please manually remove functions from your rc file."
    echo "    Look for '# TELEGRAM NOTIFICATIONS' section"
fi

if [ -n "$SHELL_RC" ] && [ -f "$SHELL_RC" ]; then
    if grep -q "# TELEGRAM NOTIFICATIONS" "$SHELL_RC" 2>/dev/null; then
        echo "Removing shell functions from $SHELL_RC..."

        # Create backup of shell rc
        cp "$SHELL_RC" "${SHELL_RC}.backup-$(date +%Y%m%d-%H%M%S)"
        echo "✅ Backed up shell config to ${SHELL_RC}.backup-*"

        # Remove TeleMux section
        # This removes from "# TELEGRAM NOTIFICATIONS" to the end of the tg-* aliases
        sed -i.bak '/# TELEGRAM NOTIFICATIONS/,/alias tg-doctor=/d' "$SHELL_RC" 2>/dev/null || \
        sed -i '.bak' '/# TELEGRAM NOTIFICATIONS/,/alias tg-doctor=/d' "$SHELL_RC" 2>/dev/null || \
        echo "⚠️  Could not automatically remove shell functions. Please edit $SHELL_RC manually."

        # Clean up blank lines left by sed
        if command -v awk >/dev/null 2>&1; then
            awk 'NF > 0 || prev_nf > 0 {print; prev_nf = NF}' "$SHELL_RC" > "${SHELL_RC}.tmp" && mv "${SHELL_RC}.tmp" "$SHELL_RC"
        fi

        echo "✅ Shell functions removed"
        echo "   (Original backed up with .backup-* suffix)"
    else
        echo "ℹ️  No TeleMux shell functions found in $SHELL_RC"
    fi
fi
echo ""

# Remove config file (if exists outside telemux dir)
OLD_CONFIG="$HOME/.telegram_config"
if [ -f "$OLD_CONFIG" ]; then
    echo "Found old config file: $OLD_CONFIG"
    read -p "Remove it? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm "$OLD_CONFIG"
        echo "✅ Removed $OLD_CONFIG"
    fi
    echo ""
fi

# Remove from Claude config if present
CLAUDE_CONFIG="$HOME/.claude/CLAUDE.md"
if [ -f "$CLAUDE_CONFIG" ] && grep -q "# TeleMux" "$CLAUDE_CONFIG" 2>/dev/null; then
    echo "Found TeleMux section in Claude Code config"
    read -p "Remove it? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Backup Claude config
        cp "$CLAUDE_CONFIG" "${CLAUDE_CONFIG}.backup-$(date +%Y%m%d-%H%M%S)"

        # Remove TeleMux section (from "# TeleMux" to end or next "---")
        sed -i.bak '/# TeleMux/,/^---$/d' "$CLAUDE_CONFIG" 2>/dev/null || \
        sed -i '.bak' '/# TeleMux/,/^---$/d' "$CLAUDE_CONFIG" 2>/dev/null

        echo "✅ Removed TeleMux section from Claude config"
    fi
    echo ""
fi

echo "================================"
echo "✅ Uninstallation Complete!"
echo "================================"
echo ""
echo "TeleMux has been removed from your system."
echo ""
echo "Note:"
echo "  - Reload your shell: source $SHELL_RC"
echo "  - Shell config backups saved with .backup-* suffix"
echo "  - Python dependencies (requests) were not removed"
echo ""

# Optional: Ask if they want to remove Python dependencies
read -p "Remove Python dependencies (requests library)? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if command -v pip3 >/dev/null 2>&1; then
        echo "Removing requests library..."
        pip3 uninstall -y requests 2>/dev/null || echo "⚠️  Could not remove requests"
    else
        echo "⚠️  pip3 not found, cannot remove dependencies"
    fi
fi

echo ""
echo "Thank you for using TeleMux!"
echo ""
