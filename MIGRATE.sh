#!/bin/bash
# TeleMux Migration Script
# Migrate from .team_mux to .telemux directory structure

set -e

echo "================================"
echo "TeleMux Migration Tool"
echo "================================"
echo ""
echo "This script will migrate your data from:"
echo "  ~/.team_mux/ → ~/.telemux/"
echo ""

OLD_DIR="$HOME/.team_mux"
NEW_DIR="$HOME/.telemux"

# Check if old directory exists
if [ ! -d "$OLD_DIR" ]; then
    echo "✅ No migration needed - ~/.team_mux not found"
    echo ""
    echo "You can proceed with a fresh installation:"
    echo "  ./INSTALL.sh"
    exit 0
fi

# Check if new directory already exists
if [ -d "$NEW_DIR" ]; then
    echo "⚠️  Warning: ~/.telemux already exists!"
    echo ""
    read -p "Merge old data into existing directory? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Migration cancelled"
        exit 0
    fi
    MERGE_MODE=true
else
    MERGE_MODE=false
fi

echo ""
echo "=== Migration Plan ==="
echo ""

# List what will be migrated
echo "Files to migrate:"

if [ -d "$OLD_DIR/message_queue" ]; then
    MSG_COUNT=$(find "$OLD_DIR/message_queue" -type f | wc -l)
    echo "  ✓ Message queue ($MSG_COUNT files)"
fi

if [ -d "$OLD_DIR/agents" ]; then
    AGENT_COUNT=$(find "$OLD_DIR/agents" -type d -mindepth 1 -maxdepth 1 | wc -l)
    echo "  ✓ Agent inboxes ($AGENT_COUNT agents)"
fi

if [ -f "$OLD_DIR/telegram_listener.log" ]; then
    LOG_SIZE=$(du -h "$OLD_DIR/telegram_listener.log" | cut -f1)
    echo "  ✓ Listener log ($LOG_SIZE)"
fi

echo ""
read -p "Proceed with migration? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Migration cancelled"
    exit 0
fi

echo ""
echo "=== Starting Migration ==="
echo ""

# Create new directory if it doesn't exist
mkdir -p "$NEW_DIR/message_queue"

# Migrate message queue
if [ -d "$OLD_DIR/message_queue" ]; then
    echo "📦 Migrating message queue..."

    if [ -f "$OLD_DIR/message_queue/outgoing.log" ]; then
        if [ -f "$NEW_DIR/message_queue/outgoing.log" ] && [ "$MERGE_MODE" = true ]; then
            # Append to existing file
            cat "$OLD_DIR/message_queue/outgoing.log" >> "$NEW_DIR/message_queue/outgoing.log"
            echo "  ✓ Merged outgoing.log"
        else
            cp "$OLD_DIR/message_queue/outgoing.log" "$NEW_DIR/message_queue/"
            echo "  ✓ Copied outgoing.log"
        fi
    fi

    if [ -f "$OLD_DIR/message_queue/incoming.log" ]; then
        if [ -f "$NEW_DIR/message_queue/incoming.log" ] && [ "$MERGE_MODE" = true ]; then
            # Append to existing file
            cat "$OLD_DIR/message_queue/incoming.log" >> "$NEW_DIR/message_queue/incoming.log"
            echo "  ✓ Merged incoming.log"
        else
            cp "$OLD_DIR/message_queue/incoming.log" "$NEW_DIR/message_queue/"
            echo "  ✓ Copied incoming.log"
        fi
    fi

    if [ -f "$OLD_DIR/message_queue/listener_state.json" ]; then
        cp "$OLD_DIR/message_queue/listener_state.json" "$NEW_DIR/message_queue/"
        echo "  ✓ Copied listener state"
    fi
fi

# Migrate agent inboxes
if [ -d "$OLD_DIR/agents" ]; then
    echo "📥 Migrating agent inboxes..."

    # Copy entire agents directory
    if [ "$MERGE_MODE" = true ]; then
        # Merge agent directories
        cp -r "$OLD_DIR/agents/"* "$NEW_DIR/agents/" 2>/dev/null || mkdir -p "$NEW_DIR/agents"
        echo "  ✓ Merged agent inboxes"
    else
        cp -r "$OLD_DIR/agents" "$NEW_DIR/"
        echo "  ✓ Copied agent inboxes"
    fi
fi

# Migrate logs
if [ -f "$OLD_DIR/telegram_listener.log" ]; then
    echo "📄 Migrating logs..."

    if [ -f "$NEW_DIR/telegram_listener.log" ] && [ "$MERGE_MODE" = true ]; then
        # Append a separator and merge
        echo "" >> "$NEW_DIR/telegram_listener.log"
        echo "=== Migrated from ~/.team_mux on $(date) ===" >> "$NEW_DIR/telegram_listener.log"
        cat "$OLD_DIR/telegram_listener.log" >> "$NEW_DIR/telegram_listener.log"
        echo "  ✓ Merged listener log"
    else
        cp "$OLD_DIR/telegram_listener.log" "$NEW_DIR/"
        echo "  ✓ Copied listener log"
    fi
fi

# Migrate control scripts (if they exist and are not already installed)
if [ -f "$OLD_DIR/telegram_listener.py" ] && [ ! -f "$NEW_DIR/telegram_listener.py" ]; then
    echo "📜 Migrating scripts..."
    cp "$OLD_DIR/telegram_listener.py" "$NEW_DIR/"
    chmod +x "$NEW_DIR/telegram_listener.py"
    echo "  ✓ Copied telegram_listener.py"
fi

if [ -f "$OLD_DIR/telegram_control.sh" ] && [ ! -f "$NEW_DIR/telegram_control.sh" ]; then
    cp "$OLD_DIR/telegram_control.sh" "$NEW_DIR/"
    chmod +x "$NEW_DIR/telegram_control.sh"
    echo "  ✓ Copied telegram_control.sh"
fi

# Migrate config if it exists
if [ -f "$OLD_DIR/telegram_config" ] && [ ! -f "$NEW_DIR/telegram_config" ]; then
    echo "🔐 Migrating configuration..."
    cp "$OLD_DIR/telegram_config" "$NEW_DIR/"
    chmod 600 "$NEW_DIR/telegram_config"
    echo "  ✓ Copied telegram_config"
fi

echo ""
echo "=== Migration Complete! ==="
echo ""

# Ask about removing old directory
echo "Old directory: $OLD_DIR"
read -p "Remove old ~/.team_mux directory? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Create backup first
    BACKUP_FILE="$HOME/team_mux-backup-$(date +%Y%m%d-%H%M%S).tar.gz"
    echo "📦 Creating backup: $BACKUP_FILE"
    tar -czf "$BACKUP_FILE" -C "$HOME" .team_mux
    echo "✅ Backup created"

    # Remove old directory
    rm -rf "$OLD_DIR"
    echo "✅ Old directory removed"
    echo ""
    echo "Backup saved at: $BACKUP_FILE"
else
    echo "ℹ️  Old directory preserved at: $OLD_DIR"
    echo "   You can manually remove it later"
fi

echo ""
echo "================================"
echo "✅ Migration Successful!"
echo "================================"
echo ""
echo "Next steps:"
echo "  1. If listener is running, restart it:"
echo "     tg-stop && tg-start"
echo ""
echo "  2. Verify migration:"
echo "     tg-doctor"
echo ""
echo "  3. Test functionality:"
echo "     tg_alert 'Migration successful!'"
echo ""
