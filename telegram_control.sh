#!/bin/bash
# Telegram Listener Control Script

LISTENER_SCRIPT="$HOME/.telemux/telegram_listener.py"
CLEANUP_SCRIPT="$HOME/.telemux/cleanup-logs.sh"
TMUX_SESSION="telegram-listener"
LOG_FILE="$HOME/.telemux/telegram_listener.log"

case "$1" in
    start)
        if tmux has-session -t "$TMUX_SESSION" 2>/dev/null; then
            echo "❌ Telegram listener is already running"
            echo "   Use: telegram_control.sh status"
            exit 1
        fi

        echo "🚀 Starting Telegram listener..."
        tmux new-session -d -s "$TMUX_SESSION" "python3 $LISTENER_SCRIPT"
        sleep 1

        if tmux has-session -t "$TMUX_SESSION" 2>/dev/null; then
            echo "✅ Telegram listener started successfully"
            echo "   Session: $TMUX_SESSION"
            echo "   Log: $LOG_FILE"
            echo ""
            echo "Commands:"
            echo "   telegram_control.sh status   - Check status"
            echo "   telegram_control.sh logs     - View logs"
            echo "   telegram_control.sh attach   - Attach to session"
            echo "   telegram_control.sh stop     - Stop listener"
        else
            echo "❌ Failed to start listener"
            exit 1
        fi
        ;;

    stop)
        if ! tmux has-session -t "$TMUX_SESSION" 2>/dev/null; then
            echo "ℹ️  Telegram listener is not running"
            exit 0
        fi

        echo "🛑 Stopping Telegram listener..."
        tmux kill-session -t "$TMUX_SESSION"
        echo "✅ Telegram listener stopped"
        ;;

    restart)
        "$0" stop
        sleep 2
        "$0" start
        ;;

    status)
        if tmux has-session -t "$TMUX_SESSION" 2>/dev/null; then
            echo "✅ Telegram listener is RUNNING"
            echo "   Session: $TMUX_SESSION"
            echo "   Log: $LOG_FILE"
            echo ""
            echo "Recent activity:"
            tail -10 "$LOG_FILE" 2>/dev/null || echo "No logs yet"
        else
            echo "❌ Telegram listener is NOT running"
            echo "   Start with: telegram_control.sh start"
        fi
        ;;

    logs)
        if [[ -f "$LOG_FILE" ]]; then
            tail -f "$LOG_FILE"
        else
            echo "No log file found at $LOG_FILE"
        fi
        ;;

    attach)
        if tmux has-session -t "$TMUX_SESSION" 2>/dev/null; then
            tmux attach-session -t "$TMUX_SESSION"
        else
            echo "❌ Telegram listener is not running"
            exit 1
        fi
        ;;

    cleanup)
        if [[ -f "$CLEANUP_SCRIPT" ]]; then
            bash "$CLEANUP_SCRIPT" "$2"
        else
            echo "❌ Cleanup script not found at $CLEANUP_SCRIPT"
            exit 1
        fi
        ;;

    doctor)
        echo "TeleMux Health Check"
        echo "===================="
        echo ""

        # Check tmux
        echo "🔍 Checking tmux..."
        if command -v tmux >/dev/null 2>&1; then
            TMUX_VERSION=$(tmux -V)
            echo "✅ tmux is installed ($TMUX_VERSION)"
        else
            echo "❌ tmux is NOT installed"
        fi
        echo ""

        # Check Python
        echo "🔍 Checking Python..."
        if command -v python3 >/dev/null 2>&1; then
            PYTHON_VERSION=$(python3 --version)
            echo "✅ Python is installed ($PYTHON_VERSION)"
        else
            echo "❌ Python3 is NOT installed"
        fi
        echo ""

        # Check dependencies
        echo "🔍 Checking Python dependencies..."
        if python3 -c "import requests" 2>/dev/null; then
            echo "✅ requests library is installed"
        else
            echo "❌ requests library is NOT installed"
            echo "   Install with: pip3 install requests"
        fi
        echo ""

        # Check config file
        echo "🔍 Checking configuration..."
        CONFIG_FILE="$HOME/.telemux/telegram_config"
        if [[ -f "$CONFIG_FILE" ]]; then
            echo "✅ Config file exists: $CONFIG_FILE"

            # Check permissions
            PERMS=$(stat -f%A "$CONFIG_FILE" 2>/dev/null || stat -c%a "$CONFIG_FILE" 2>/dev/null)
            if [[ "$PERMS" == "600" ]]; then
                echo "✅ Config file permissions are secure (600)"
            else
                echo "⚠️  Config file permissions: $PERMS (should be 600)"
                echo "   Fix with: chmod 600 $CONFIG_FILE"
            fi

            # Check if credentials are set
            source "$CONFIG_FILE" 2>/dev/null
            if [[ -n "$TELEMUX_TG_BOT_TOKEN" ]]; then
                echo "✅ Bot token is set"
            else
                echo "❌ Bot token is NOT set"
            fi

            if [[ -n "$TELEMUX_TG_CHAT_ID" ]]; then
                echo "✅ Chat ID is set"
                # Validate format
                if [[ "$TELEMUX_TG_CHAT_ID" =~ ^-?[0-9]+$ ]]; then
                    if [[ "$TELEMUX_TG_CHAT_ID" =~ ^- ]]; then
                        echo "   (Group chat: $TELEMUX_TG_CHAT_ID)"
                    else
                        echo "   (Personal chat: $TELEMUX_TG_CHAT_ID)"
                    fi
                else
                    echo "⚠️  Chat ID format may be invalid"
                fi
            else
                echo "❌ Chat ID is NOT set"
            fi
        else
            echo "❌ Config file NOT found: $CONFIG_FILE"
            echo "   Run INSTALL.sh to create it"
        fi
        echo ""

        # Test bot connection
        echo "🔍 Testing Telegram bot connection..."
        if [[ -n "$TELEMUX_TG_BOT_TOKEN" ]]; then
            RESPONSE=$(curl -s "https://api.telegram.org/bot${TELEMUX_TG_BOT_TOKEN}/getMe")
            if echo "$RESPONSE" | grep -q '"ok":true'; then
                BOT_NAME=$(echo "$RESPONSE" | grep -o '"first_name":"[^"]*"' | cut -d'"' -f4)
                BOT_USERNAME=$(echo "$RESPONSE" | grep -o '"username":"[^"]*"' | cut -d'"' -f4)
                echo "✅ Bot connection successful!"
                echo "   Bot name: $BOT_NAME"
                echo "   Username: @$BOT_USERNAME"
            else
                echo "❌ Bot connection failed"
                echo "   Response: $RESPONSE"
                echo "   Check your bot token"
            fi
        else
            echo "⚠️  Skipping (no bot token configured)"
        fi
        echo ""

        # Check listener process
        echo "🔍 Checking listener daemon..."
        if tmux has-session -t "$TMUX_SESSION" 2>/dev/null; then
            echo "✅ Listener is RUNNING (session: $TMUX_SESSION)"
        else
            echo "⚠️  Listener is NOT running"
            echo "   Start with: tg-start"
        fi
        echo ""

        # Check log files
        echo "🔍 Checking log files..."
        if [[ -f "$LOG_FILE" ]]; then
            LOG_SIZE=$(du -h "$LOG_FILE" | cut -f1)
            LOG_LINES=$(wc -l < "$LOG_FILE")
            echo "✅ Listener log exists: $LOG_FILE"
            echo "   Size: $LOG_SIZE ($LOG_LINES lines)"
        else
            echo "⚠️  No listener log file yet"
        fi

        OUTGOING_LOG="$HOME/.telemux/message_queue/outgoing.log"
        if [[ -f "$OUTGOING_LOG" ]]; then
            OUTGOING_COUNT=$(wc -l < "$OUTGOING_LOG")
            echo "✅ Outgoing message log exists ($OUTGOING_COUNT messages)"
        else
            echo "ℹ️  No outgoing messages yet"
        fi

        INCOMING_LOG="$HOME/.telemux/message_queue/incoming.log"
        if [[ -f "$INCOMING_LOG" ]]; then
            INCOMING_COUNT=$(wc -l < "$INCOMING_LOG")
            echo "✅ Incoming message log exists ($INCOMING_COUNT messages)"
        else
            echo "ℹ️  No incoming messages yet"
        fi
        echo ""

        # Summary
        echo "===================="
        echo "Health Check Complete"
        echo "===================="
        ;;

    *)
        echo "Telegram Listener Control"
        echo ""
        echo "Usage: $0 {start|stop|restart|status|logs|attach|cleanup|doctor}"
        echo ""
        echo "Commands:"
        echo "  start    - Start the listener daemon"
        echo "  stop     - Stop the listener daemon"
        echo "  restart  - Restart the listener daemon"
        echo "  status   - Check if listener is running"
        echo "  logs     - Tail the log file"
        echo "  attach   - Attach to the tmux session"
        echo "  cleanup  - Rotate and clean up log files"
        echo "  doctor   - Run health check and diagnose issues"
        echo ""
        echo "Options:"
        echo "  cleanup --install-cron  - Install automatic monthly cleanup"
        exit 1
        ;;
esac
