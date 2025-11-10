#!/bin/bash
# Telegram Listener Control Script

LISTENER_SCRIPT="$HOME/.telemux/telegram_listener.py"
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

    *)
        echo "Telegram Listener Control"
        echo ""
        echo "Usage: $0 {start|stop|restart|status|logs|attach}"
        echo ""
        echo "Commands:"
        echo "  start    - Start the listener daemon"
        echo "  stop     - Stop the listener daemon"
        echo "  restart  - Restart the listener daemon"
        echo "  status   - Check if listener is running"
        echo "  logs     - Tail the log file"
        echo "  attach   - Attach to the tmux session"
        exit 1
        ;;
esac
