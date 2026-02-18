#!/bin/bash
#
# TeleMux Shell Functions - Single Source of Truth
#
# This file contains all shell functions for TeleMux.
# Source this file to get: tg_alert, tg_agent, tg_done
#
# Deployed to: ~/.telemux/shell_functions.sh
# Sourced by: ~/.zshrc or ~/.bashrc (via telemux install)
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
        -d parse_mode="HTML" > /dev/null && echo "Message sent to Telegram"
}

# Bidirectional agent alert - sends message and can receive replies
tg_agent() {
    local message="$*"

    if [[ -z "$message" ]]; then
        echo "Usage: tg_agent <message>"
        return 1
    fi

    # Auto-detect tmux session name
    local tmux_session="$(tmux display-message -p '#S' 2>/dev/null || echo 'unknown')"
    local agent_name="${tmux_session}"
    local msg_id="${tmux_session}"

    # Check if we're in a tmux session
    if [[ -z "$TMUX" ]]; then
        echo "Warning: Not in a tmux session. Using 'terminal' as session name."
        agent_name="terminal"
        msg_id="terminal"
    fi

    # Record mapping for listener daemon (backward compatibility)
    # NOTE: New routing doesn't require this, but kept for transition period
    mkdir -p "$HOME/.telemux/message_queue"
    echo "${msg_id}:${agent_name}:${tmux_session}:$(date -Iseconds)" >> "$HOME/.telemux/message_queue/outgoing.log"

    # Send to Telegram with identifier
    curl -s -X POST "https://api.telegram.org/bot${TELEMUX_TG_BOT_TOKEN}/sendMessage" \
        -d chat_id="${TELEMUX_TG_CHAT_ID}" \
        -d text="[>] <b>[${agent_name}]</b>

${message}

<i>Reply with: ${msg_id}: your response</i>" \
        -d parse_mode="HTML" > /dev/null && echo "Agent message sent from: ${msg_id}"

    echo "$msg_id"  # Return message ID
}

# Alert when command completes
tg_done() {
    local exit_code=$?
    local cmd

    # Bash-compatible history access
    if [ -n "$BASH_VERSION" ]; then
        cmd="$(fc -ln -1 2>/dev/null || echo 'unknown command')"
    else
        # zsh
        cmd="${history[$((HISTCMD-1))]}"
    fi

    # Trim leading/trailing whitespace
    cmd="$(echo "$cmd" | xargs)"

    if [[ $exit_code -eq 0 ]]; then
        tg_alert "Command completed: ${cmd}"
    else
        tg_alert "Command failed (exit $exit_code): ${cmd}"
    fi
}

# Control aliases (defined here for consistency)
# Uses Python-based telemux commands
alias tg-start="telemux-start"
alias tg-stop="telemux-stop"
alias tg-restart="telemux-restart"
alias tg-status="telemux-status"
alias tg-logs="telemux-logs"
alias tg-attach="telemux-attach"
alias tg-cleanup="telemux-cleanup"
alias tg-doctor="telemux-doctor"

# I added these
alias tg-alert="tg_alert"
alias tg-msg="tg_agent"
