# TeleMux: Bidirectional Telegram Bridge for Any LLM CLI

> Universal Telegram integration for LLM CLIs (Claude Code, Codex, Gemini-CLI, etc.) and AI agents running in tmux - send messages to your phone and receive replies back in real-time
# TeleMux: Bidirectional Telegram Bridge for Any LLM CLI

> Universal Telegram integration for LLM CLIs (Claude Code, Codex, Gemini-CLI, etc.) and AI agents running in tmux - send messages to your phone and receive replies back in real-time
# TeleMux: Bidirectional Telegram Bridge for Any LLM CLI

> Universal Telegram integration for LLM CLIs (Claude Code, Codex, Gemini-CLI, etc.) and AI agents running in tmux - send messages to your phone and receive replies back in real-time
# TeleMux: Bidirectional Telegram Bridge for Any LLM CLI

> Universal Telegram integration for LLM CLIs (Claude Code, Codex, Gemini-CLI, etc.) and AI agents running in tmux - send messages to your phone and receive replies back in real-time
# TeleMux: Bidirectional Telegram Bridge for Any LLM CLI

> Universal Telegram integration for LLM CLIs (Claude Code, Codex, Gemini-CLI, etc.) and AI agents running in tmux - send messages to your phone and receive replies back in real-time

TeleMux enables **true bidirectional communication** between your AI agents running in tmux and you via Telegram. Agents can ask questions, request approvals, or send alerts to your phone, and you can reply directly - your responses are delivered back to the agent's tmux session in real-time.

## Features

✅ **Simple Alerts** - Send one-way notifications from terminal
✅ **Bidirectional Messaging** - Agents can send messages and receive replies
✅ **Direct Delivery** - Replies appear in agent's tmux session via `send-keys`
✅ **Clean Format** - Use tmux session name as message ID
✅ **Persistent Listener** - Runs 24/7 in background tmux session
✅ **Message Queue** - All messages logged for audit trail

## Architecture

```
┌─────────────────┐         ┌──────────────┐         ┌──────────────┐
│  Agent (tmux)   │────────▶│   Telegram   │────────▶│  Your Phone  │
│                 │         │     Bot      │         │              │
└─────────────────┘         └──────────────┘         └──────────────┘
        ▲                          │                         │
        │                          │                         │
        │                   ┌──────▼──────┐                  │
        └───────────────────│  Listener   │◀─────────────────┘
                            │  Daemon     │
                            └─────────────┘
```

**Flow:**
1. LLM CLI or agent sends message to Telegram with session name as ID
2. You receive notification on your phone/desktop
3. You reply: `session-name: your message`
4. Listener catches reply, parses session ID
5. Delivers message to tmux session via `send-keys`
6. Message appears in your Claude Code/agent session

## Quick Start

### Prerequisites

- Telegram account
- tmux installed
- Python 3.6+
- curl

### 1. Create Telegram Bot

1. Open Telegram and message [@BotFather](https://t.me/BotFather)
2. Send `/newbot`
3. Follow prompts to create bot
4. Save your **bot token** (looks like: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`)

### 2. Get Your Chat ID

**Option A: Group Chat (Recommended)**
1. Create a new Telegram group
2. Add your bot to the group
3. Send a message to the group
4. Run:
   ```bash
   curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates" | jq '.'
   ```
5. Look for `"chat":{"id": -1234567890}` (negative number for groups)

**Option B: Private DM**
1. Message your bot directly (any message)
2. Run the same curl command above
3. Look for `"chat":{"id": 1234567890}` (positive number for DM)

### 3. Disable Privacy Mode (for groups only)

If using a group chat:
1. Message [@BotFather](https://t.me/BotFather)
2. Send `/mybots`
3. Select your bot
4. Click "Bot Settings" → "Group Privacy" → "Turn off"

This allows the bot to see all group messages.

### 4. Install Files

```bash
# Create config file
cat > ~/.telegram_config << 'EOF'
#!/bin/bash
# Telegram Bot Configuration

export TELEMUX_TG_BOT_TOKEN="your-bot-token-here"
export TELEMUX_TG_CHAT_ID="your-chat-id-here"  # Use negative number for groups
export TELEGRAM_PERSONAL_CHAT_ID="your-personal-chat-id"  # Optional: for DMs
EOF

chmod 600 ~/.telegram_config

# Install listener daemon
cp telegram_listener.py ~/.telemux/
chmod +x ~/.telemux/telegram_listener.py

# Install control script
cp telegram_control.sh ~/.telemux/
chmod +x ~/.telemux/telegram_control.sh

# Add functions to ~/.zshrc (or ~/.bashrc)
cat >> ~/.zshrc << 'ZSHRC_EOF'

# =============================================================================
# TELEGRAM NOTIFICATIONS
# =============================================================================

# Load Telegram config
if [[ -f "$HOME/.telegram_config" ]]; then
    source "$HOME/.telegram_config"
fi

# Simple alert function - send any message to Telegram
tg_alert() {
    local message="$*"
    if [[ -z "$message" ]]; then
        echo "Usage: tg_alert <message>"
        return 1
    fi

    if [[ -z "$TELEMUX_TG_BOT_TOKEN" ]] || [[ -z "$TELEMUX_TG_CHAT_ID" ]]; then
        echo "Error: Telegram not configured. Check ~/.telegram_config"
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

ZSHRC_EOF

# Reload shell config
source ~/.zshrc
```

### 5. Start Listener

```bash
tg-start
```

### 6. Test It

```bash
# Test simple alert
tg_alert "Hello from terminal!"

# Test bidirectional from a tmux session
tmux new-session -d -s test-session
tmux send-keys -t test-session "tg_agent 'test-agent' 'Can you hear me?'" C-m

# In Telegram, reply with:
# test-session: Yes I can hear you!

# Check if message was delivered
tmux capture-pane -t test-session -p | tail -10
```

## Usage

### Simple One-Way Alerts

```bash
# Send notification
tg_alert "Build completed successfully!"

# After long-running command
npm run build && tg_done

# With custom message
tg_alert "Database backup finished: 5.2GB"
```

### Bidirectional Agent Messages

```bash
# LLM CLI or agent asks question
tg_agent "deployment-agent" "Ready to deploy to production?"

# You reply in Telegram:
# deployment-session: yes, deploy now

# Message appears in your tmux session:
# [FROM USER via Telegram] yes, deploy now
```

### Message Format

**Outgoing (Agent → Telegram):**
```
🤖 [agent-name:session-name]

Your message here

Reply with: session-name: your response
```

**Incoming (Telegram → Agent):**
```
session-name: your message content
```

**Delivered (in tmux):**
```
[FROM USER via Telegram] your message content
```

## Control Commands

```bash
tg-start      # Start the listener daemon
tg-stop       # Stop the listener daemon
tg-status     # Check if listener is running
tg-logs       # Tail the listener logs
tg-restart    # Restart the listener daemon
```

## File Locations

```
~/.telegram_config                              # Bot credentials (chmod 600)
~/.telemux/telegram_listener.py                # Listener daemon
~/.telemux/telegram_control.sh                 # Control script
~/.telemux/telegram_listener.log               # Listener logs
~/.telemux/message_queue/outgoing.log          # Sent messages
~/.telemux/message_queue/incoming.log          # Received replies
~/.telemux/message_queue/listener_state.json   # Listener state
~/.telemux/agents/{agent-name}/inbox.txt       # Agent inbox files
```

## Advanced Usage

### Custom Agent Scripts

```bash
#!/bin/bash
# deployment-agent.sh

# Send request to User
MSG_ID=$(tg_agent "deployment-agent" "Deploy version $VERSION to production?")

# Wait for reply (check inbox)
INBOX="$HOME/.telemux/agents/deployment-agent/inbox.txt"
while true; do
    if grep -q "yes\|approved" "$INBOX" 2>/dev/null; then
        echo "✅ Deployment approved!"
        ./deploy.sh
        break
    elif grep -q "no\|reject" "$INBOX" 2>/dev/null; then
        echo "❌ Deployment cancelled"
        exit 1
    fi
    sleep 5
done
```

### Integration with AI Agents

```python
# agent.py
import subprocess
import os

def ask_marco(question):
    """Ask User a question via Telegram"""
    result = subprocess.run(
        ['bash', '-c', f'source ~/.zshrc && tg_agent "ai-agent" "{question}"'],
        capture_output=True,
        text=True
    )
    return result.stdout.strip()

def get_marco_reply():
    """Check inbox for User's reply"""
    inbox = os.path.expanduser("~/.telemux/agents/ai-agent/inbox.txt")
    if os.path.exists(inbox):
        with open(inbox) as f:
            lines = f.readlines()
            if lines:
                # Get last message
                for line in reversed(lines):
                    if line.strip() and not line.startswith('['):
                        return line.strip()
    return None

# Usage
ask_marco("Should I proceed with data migration?")
# ... wait for reply or poll inbox ...
reply = get_marco_reply()
if "yes" in reply.lower():
    migrate_data()
```

## Troubleshooting

### Bot not receiving messages in group

**Solution:** Disable Privacy Mode
1. Message @BotFather
2. `/mybots` → Select bot → Bot Settings → Group Privacy → Turn off

### Listener not starting

```bash
# Check logs
cat ~/.telemux/telegram_listener.log

# Test bot connection
curl "https://api.telegram.org/bot<YOUR_TOKEN>/getMe"

# Verify config
source ~/.telegram_config
echo $TELEMUX_TG_BOT_TOKEN
echo $TELEMUX_TG_CHAT_ID
```

### Messages not appearing in tmux

**Check:**
1. Is tmux session running? `tmux list-sessions`
2. Does session name match message ID?
3. Check listener logs: `tg-logs`

### Permission denied errors

```bash
chmod 600 ~/.telegram_config
chmod +x ~/.telemux/telegram_listener.py
chmod +x ~/.telemux/telegram_control.sh
```

## Security Notes

- **Config file:** `~/.telegram_config` is chmod 600 (owner read/write only)
- **Bot token:** Never commit to git - add `*telegram_config*` to .gitignore
- **Messages:** Logged locally in `~/.telemux/message_queue/`
- **Telegram:** Messages sent via HTTPS to Telegram API

## How It Works

### Listener Daemon

The Python daemon (`telegram_listener.py`) runs continuously:

1. **Long polls** Telegram API every 30 seconds for updates
2. **Parses** incoming messages for format: `session-name: message`
3. **Looks up** agent details from `outgoing.log`
4. **Writes** message to agent's inbox file
5. **Delivers** to tmux session via `send-keys` if session is active
6. **Confirms** delivery back to Telegram

### Message Queue

All messages are logged for audit trail:

**outgoing.log:**
```
msg-id:agent-name:tmux-session:timestamp
session-1:deploy-agent:deployment-session:2025-11-09T18:30:00
```

**incoming.log:**
```
msg-id:agent-name:timestamp:message-preview
session-1:deploy-agent:2025-11-09T18:31:00:yes, approved
```

### State Management

Listener maintains offset for processed updates in `listener_state.json`:
```json
{
  "last_update_id": 453122730
}
```

This ensures no messages are lost if listener restarts.

## Examples

### Deploy Script with Approval

```bash
#!/bin/bash
# deploy.sh - Requires User's approval via Telegram

VERSION="v2.1.0"

echo "🚀 Preparing deployment: $VERSION"

# Ask for approval
tg_agent "deploy-agent" "Deploy $VERSION to production? (yes/no)"

# Wait for reply
INBOX="$HOME/.telemux/agents/deploy-agent/inbox.txt"
echo "⏳ Waiting for approval..."

timeout 300 bash -c "
while true; do
    if [ -f '$INBOX' ]; then
        REPLY=\$(tail -1 '$INBOX')
        if echo \"\$REPLY\" | grep -qi 'yes'; then
            exit 0
        elif echo \"\$REPLY\" | grep -qi 'no'; then
            exit 1
        fi
    fi
    sleep 5
done
"

if [ $? -eq 0 ]; then
    echo "✅ Deployment approved!"
    ./deploy-to-production.sh
    tg_alert "✅ Deployment complete: $VERSION"
else
    echo "❌ Deployment cancelled or timed out"
    tg_alert "❌ Deployment cancelled: $VERSION"
    exit 1
fi
```

### Long-Running Build with Notification

```bash
#!/bin/bash
# build-and-notify.sh

START_TIME=$(date +%s)

tg_alert "🔨 Starting build..."

# Run build
if npm run build; then
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    tg_alert "✅ Build completed in ${DURATION}s"
else
    tg_alert "❌ Build failed! Check logs."
    exit 1
fi
```

### AI Agent Asking for Guidance

```bash
#!/bin/bash
# ai-agent.sh

# Agent encounters uncertainty
QUESTION="I found 3 duplicate entries in the database. Should I:
1. Auto-merge them
2. Flag for manual review
3. Skip and continue"

tg_agent "cleanup-agent" "$QUESTION"

# Wait for response
INBOX="$HOME/.telemux/agents/cleanup-agent/inbox.txt"
while true; do
    if [ -f "$INBOX" ]; then
        REPLY=$(tail -5 "$INBOX" | grep -v "^\[" | tail -1)

        if echo "$REPLY" | grep -qi "auto-merge\|option 1\|merge"; then
            echo "✓ Auto-merging duplicates"
            ./merge-duplicates.sh
            break
        elif echo "$REPLY" | grep -qi "manual\|option 2\|review"; then
            echo "✓ Flagging for manual review"
            ./flag-for-review.sh
            break
        elif echo "$REPLY" | grep -qi "skip\|option 3\|continue"; then
            echo "✓ Skipping duplicates"
            break
        fi
    fi
    sleep 5
done
```

## FAQ

**Q: Can multiple agents use this simultaneously?**
A: Yes! Each tmux session has a unique name, so multiple agents can send/receive independently.

**Q: What happens if I don't reply?**
A: Messages are saved in the agent's inbox file. The agent can check it later or timeout.

**Q: Can I use this outside tmux?**
A: `tg_alert()` works anywhere. `tg_agent()` requires tmux for bidirectional replies.

**Q: Does the listener survive reboots?**
A: No, you need to run `tg-start` after reboot. Consider adding to startup scripts.

**Q: Can I customize the message format?**
A: Yes! Edit `telegram_listener.py` line 206 to change the `[FROM MARCO via Telegram]` prefix.

## Credits

Built for User's AI agent automation system.
Part of the Team Mux multi-agent coordination framework.

## License

MIT License - Use freely for personal or commercial projects.

---

**Need help?** Check logs: `tg-logs` or `cat ~/.telemux/telegram_listener.log`
