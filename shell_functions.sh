#!/bin/bash
#
# TeleMux Shell Functions - Single Source of Truth
#
# This file contains all shell functions for TeleMux.
# Source this file to get: tg_alert, tg_agent, tg_done
#
# Deployed to: ~/.telemux/shell_functions.sh
# Sourced by: ~/.zshrc (via INSTALL.sh)
#

# Load TeleMux configuration
if [ -f "$HOME/.telemux/telegram_config" ]; then
    source "$HOME/.telemux/telegram_config"
fi

# Simple alert function - NOW BIDIRECTIONAL (can receive replies)
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

    # Get tmux session name for context AND routing
    local tmux_session="$(tmux display-message -p '#S' 2>/dev/null || echo 'terminal')"

    # NEW: Send with reply instructions (makes tg_alert bidirectional)
    curl -s -X POST "https://api.telegram.org/bot${TELEMUX_TG_BOT_TOKEN}/sendMessage" \
        -d chat_id="${TELEMUX_TG_CHAT_ID}" \
        -d text="[!] <b>[${tmux_session}]</b> ${message}

<i>Reply: ${tmux_session}: your response</i>" \
        -d parse_mode="HTML" > /dev/null && echo "[+] Message sent to Telegram"
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

    # Record mapping for listener daemon (backward compatibility)
    # NOTE: New routing doesn't require this, but kept for transition period
    mkdir -p "$HOME/.telemux/message_queue"
    echo "${msg_id}:${agent_name}:${tmux_session}:$(date -Iseconds)" >> "$HOME/.telemux/message_queue/outgoing.log"

    # Send to Telegram with identifier
    curl -s -X POST "https://api.telegram.org/bot${TELEMUX_TG_BOT_TOKEN}/sendMessage" \
        -d chat_id="${TELEMUX_TG_CHAT_ID}" \
        -d text="[>] <b>[${agent_name}:${msg_id}]</b>

${message}

<i>Reply with: ${msg_id}: your response</i>" \
        -d parse_mode="HTML" > /dev/null && echo "[+] Agent alert sent: ${msg_id}"

    echo "$msg_id"  # Return message ID
}

# Alert when command completes
tg_done() {
    local exit_code=$?
    local cmd="${history[$((HISTCMD-1))]}"

    if [[ $exit_code -eq 0 ]]; then
        tg_alert "[+] Command completed: ${cmd}"
    else
        tg_alert "[-] Command failed (exit $exit_code): ${cmd}"
    fi
}

# Control aliases (defined here for consistency)
alias tg-start="$HOME/.telemux/telegram_control.sh start"
alias tg-stop="$HOME/.telemux/telegram_control.sh stop"
alias tg-restart="$HOME/.telemux/telegram_control.sh restart"
alias tg-status="$HOME/.telemux/telegram_control.sh status"
alias tg-logs="$HOME/.telemux/telegram_control.sh logs"
alias tg-attach="$HOME/.telemux/telegram_control.sh attach"
alias tg-cleanup="$HOME/.telemux/telegram_control.sh cleanup"
alias tg-doctor="$HOME/.telemux/telegram_control.sh doctor"

# Backward compatibility aliases (for users upgrading from old Team Mux)
alias alert_telegram="tg_alert"
alias agent_telegram="tg_agent"
