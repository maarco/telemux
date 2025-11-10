# TeleMux Technical Documentation

**For AI Assistants & Developers**

This document explains how TeleMux works internally. Read this to understand the architecture, data flow, and how to extend the system.

---

## What is TeleMux?

TeleMux is a **bidirectional messaging bridge** between Telegram and tmux sessions running LLM CLI tools (Claude Code, Codex, Gemini-CLI, etc.). It allows:

1. **Outgoing:** Send alerts/messages from terminal → Telegram
2. **Incoming:** Receive replies from Telegram → Route back to specific tmux session
3. **Agent Communication:** LLM agents can ask questions and receive user responses via Telegram

---

## Documentation & Code Style Guide

**For AI Assistants & Contributors:**

### Emoji Policy

**DO NOT use emojis** in:
- New code development
- Documentation prose
- Comments or docstrings
- User-facing messages (new features)
- Code examples (unless documenting existing behavior)

**Emojis shown in this document** are:
- Examples of existing Telegram message output
- Part of the current system behavior (legacy)
- Documented for accuracy, not as a pattern to follow

**When documenting existing output:**
```bash
# Acceptable: Showing what the system currently outputs
tg_alert "Build complete!"
# Output: 🔔 Build complete!  (current system behavior)

# Future development: Avoid adding new emojis
# Prefer: [ALERT] Build complete!
```

### Writing Style

- Clear, technical prose
- No unnecessary embellishments
- Code examples should be functional and accurate
- Focus on architecture and data flow

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         USER (Telegram)                     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ├── Outgoing: Shell functions via curl
                         │   (tg_alert, tg_agent)
                         │
                         └── Incoming: Long-polling listener daemon
                                    │
                         ┌──────────▼──────────┐
                         │ telegram_listener.py│
                         │  (Python daemon in  │
                         │   tmux session)     │
                         └──────────┬──────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
           Parse msg ID    Lookup agent    Route to tmux
                    │               │               │
                    ▼               ▼               ▼
            session-name    outgoing.log    tmux send-keys
                                                    │
                                        ┌───────────▼──────────┐
                                        │ Target tmux session  │
                                        │ (LLM CLI running)    │
                                        └──────────────────────┘
```

---

## Directory Structure

```
~/.telemux/
├── telegram_config              # Secure credentials (chmod 600)
├── telegram_listener.py         # Python daemon (long-polling)
├── telegram_control.sh          # Control script (start/stop/status)
├── telegram_listener.log        # Daemon logs
├── message_queue/
│   ├── outgoing.log            # Record of sent messages
│   ├── incoming.log            # Record of received replies
│   └── listener_state.json     # Last Telegram update offset
└── agents/
    └── {agent-name}/
        └── inbox.txt           # Agent-specific message inbox
```

**Distribution Package:**
```
~/dev/telemux/
├── telegram_listener.py         # Main daemon (copy to ~/.telemux/)
├── telegram_control.sh          # Control script (copy to ~/.telemux/)
├── INSTALL.sh                   # Automated installer
├── README.md                    # User documentation
├── CLAUDE.md                    # This file (technical docs)
├── QUICKSTART.md               # Fast setup guide
├── COMPATIBLE_LLMS.md          # Supported LLM CLIs
└── examples/
    ├── deployment-approval.sh   # Example: Deployment approval workflow
    ├── ai-agent-question.sh     # Example: Agent asking for guidance
    └── long-build-notify.sh     # Example: Build completion notification
```

---

## Environment Variables

**Current (Telegram only):**
```bash
TELEMUX_TG_BOT_TOKEN="bot123456:ABC..."      # Telegram bot API token
TELEMUX_TG_CHAT_ID="-1234567890"            # Telegram chat ID (group/personal)
TELEMUX_TG_PERSONAL_CHAT_ID="987654321"     # Personal DM chat ID
```

**Future-Ready Naming:**
When adding WhatsApp, Slack, Discord, etc:
```bash
TELEMUX_WA_ACCOUNT_SID="..."                # WhatsApp (Twilio)
TELEMUX_WA_AUTH_TOKEN="..."
TELEMUX_WA_PHONE_NUMBER="..."

TELEMUX_SLACK_BOT_TOKEN="xoxb-..."          # Slack
TELEMUX_SLACK_CHANNEL_ID="C12345..."

TELEMUX_DISCORD_BOT_TOKEN="..."             # Discord
TELEMUX_DISCORD_CHANNEL_ID="..."
```

The `TELEMUX_` prefix keeps all config namespaced and extensible.

---

## How Bidirectional Flow Works

### 1. **Outgoing Message (Terminal → Telegram)**

**Shell Function:**
```bash
tg_agent "agent-name" "message"
```

**What Happens:**
1. Get current tmux session name: `$(tmux display-message -p '#S')`
2. Use session name as message ID: `msg_id="${tmux_session}"`
3. Log to outgoing queue: `~/.telemux/message_queue/outgoing.log`
   ```
   session-name:agent-name:session-name:2025-11-09T19:23:10-07:00
   ```
4. Send to Telegram via curl:
   ```
   🤖 [agent-name:session-name]

   message content here

   Reply with: session-name: your response
   ```

### 2. **Incoming Message (Telegram → Terminal)**

**User Replies:**
```
session-name: your response here
```

**What Happens:**
1. **Listener polls Telegram** (long-polling, 30s timeout)
2. **Parse message:** Extract `session-name` and `response` using regex: `^([\w-]+):\s*(.+)$`
3. **Lookup agent:** Read `outgoing.log`, find matching `session-name`
4. **Write to inbox:** `~/.telemux/agents/{agent-name}/inbox.txt`
   ```
   [2025-11-09T19:23:15] MESSAGE FROM USER
   Message ID: session-name
   ---
   your response here
   ---
   ```
5. **Route to tmux:** If session exists, inject message directly:
   ```bash
   tmux send-keys -t session-name "[FROM USER via Telegram] your response here"
   sleep 1
   tmux send-keys -t session-name C-m  # Press Enter
   ```
6. **Confirm to Telegram:** Send confirmation back to user
   ```
   ✅ Response delivered to agent-name (ID: session-name)
   ```

---

## Message ID Design

**Why Session Names?**

**Old approach (timestamp-based):**
```
msg-1762739355-50350: your response
```
- Hard to remember
- Hard to type on mobile
- Requires looking up ID

**New approach (session-name-based):**
```
claude-session: your response
team-mux-setup: confirmed
deploy-agent: yes
```
- Easy to remember (you know your session names)
- Easy to type
- Self-documenting

**How it works:**
```bash
# In shell function:
local tmux_session="$(tmux display-message -p '#S' 2>/dev/null || echo 'unknown')"
local msg_id="${tmux_session}"

# In listener daemon:
pattern = r'^([\w-]+):\s*(.+)$'  # Match: "word-characters: message"
```

---

## Telegram Listener Daemon

**How it Works:**

1. **Long-Polling:**
   ```python
   url = "https://api.telegram.org/bot{TOKEN}/getUpdates"
   params = {"offset": last_update_id, "timeout": 30}
   response = requests.get(url, params=params, timeout=35)
   ```
   - Waits up to 30 seconds for new messages
   - Returns immediately if messages arrive
   - Efficient (no constant polling)

2. **State Persistence:**
   ```json
   // ~/.telemux/message_queue/listener_state.json
   {
     "last_update_id": 453122732
   }
   ```
   - Prevents processing duplicate messages
   - Survives daemon restarts

3. **Message Routing:**
   ```python
   def route_to_agent(agent_info: Dict, response: str):
       # 1. Write to inbox file (persistent)
       inbox_file = TELEMUX_DIR / "agents" / agent_name / "inbox.txt"

       # 2. Try to deliver to tmux session (if active)
       if tmux_session in active_sessions:
           tmux send-keys -t session formatted_message
           sleep 1
           tmux send-keys -t session C-m
   ```

4. **Why sleep(1) before Enter?**
   ```python
   # Send text first
   subprocess.run(['tmux', 'send-keys', '-t', session, message])

   # CRITICAL: Sleep before Enter, or message won't execute
   time.sleep(1)

   # Then press Enter
   subprocess.run(['tmux', 'send-keys', '-t', session, 'C-m'])
   ```
   Without the sleep, tmux doesn't have time to buffer the text before Enter is sent, and the message gets lost.

---

## Shell Functions

### `tg_alert "message"`
**Purpose:** Simple one-way notification

**Example:**
```bash
tg_alert "Build complete!"
tg_alert "Error: Database connection failed"
```

**Use Cases:**
- Command completion notifications
- Build/deployment status
- Error alerts
- Cron job results

---

### `tg_agent "agent-name" "message"`
**Purpose:** Bidirectional agent communication

**Example:**
```bash
tg_agent "deploy-agent" "Deploy v2.0 to production? (yes/no)"

# User replies via Telegram: "deploy-agent: yes"
# Message appears in terminal and inbox file
```

**Use Cases:**
- LLM agents asking for approval
- Requesting user guidance during tasks
- Interactive workflows
- Multi-step decision making

**Returns:** Message ID (session name) so scripts can monitor inbox

---

### `tg_done`
**Purpose:** Notify when previous command completes

**Example:**
```bash
npm run build && tg_done
# ✅ Command completed: npm run build

make test || tg_done
# ❌ Command failed (exit 1): make test
```

**Use Cases:**
- Long-running processes
- CI/CD pipelines
- Background tasks

---

## Control Commands

```bash
tg-start     # Start listener daemon
tg-stop      # Stop listener daemon
tg-restart   # Restart listener daemon
tg-status    # Check daemon status + recent logs
tg-logs      # Tail -f the log file
```

**Implementation:**
```bash
alias tg-start="$HOME/.telemux/telegram_control.sh start"
```

The control script uses tmux to run the daemon in a detached session called `telegram-listener`.

---

## Adding New Platforms (Future)

### Architecture for Multi-Platform

**Option 1: Keep TeleMux, Add Plugins**
```
~/.telemux/
├── platforms/
│   ├── telegram/
│   │   ├── listener.py
│   │   └── config
│   └── whatsapp/
│       ├── listener.py
│       └── config
├── core/
│   └── router.py          # Platform-agnostic routing
└── message_queue/
    ├── telegram/
    └── whatsapp/
```

**Option 2: Rename to MessageMux**
```
~/.messagemux/
├── config/
│   ├── telegram.conf
│   ├── whatsapp.conf
│   └── enabled_platforms.conf
├── listeners/
│   ├── telegram_listener.py
│   ├── whatsapp_listener.py
│   └── slack_listener.py
└── core/
    └── router.py
```

**Shell Functions:**
```bash
# Platform-specific
tg_alert "message"         # Telegram only
wa_alert "message"         # WhatsApp only
slack_alert "message"      # Slack only

# Multi-platform
mux_alert "message"        # ALL enabled platforms
mux_agent "name" "msg"     # Bidirectional on all
```

### WhatsApp Implementation Options

1. **Twilio WhatsApp API** (Recommended)
   - Official, reliable
   - Paid ($$$)
   - Same long-polling pattern as Telegram
   ```bash
   TELEMUX_WA_ACCOUNT_SID="AC..."
   TELEMUX_WA_AUTH_TOKEN="..."
   TELEMUX_WA_PHONE_NUMBER="+1234567890"
   ```

2. **WhatsApp Business API**
   - Free but requires Meta approval
   - More complex setup

3. **whatsapp-web.js** (Unofficial)
   - Free, Node.js library
   - Less stable, may break with WhatsApp updates

4. **Baileys** (Unofficial)
   - Modern TypeScript library
   - No browser needed

---

## Security Considerations

### 1. **Credentials Protection**
```bash
chmod 600 ~/.telemux/telegram_config  # Only you can read
```

Never commit `telegram_config` to git.

### 2. **Bot Token Security**
- Use BotFather to regenerate token if compromised
- Bot can only send messages to chats it's been added to
- Use group chat instead of posting to public channels

### 3. **Command Injection Protection**
```bash
# BAD: Don't do this
eval "$(telegram_message)"  # DANGEROUS!

# GOOD: Read from inbox, validate input
if echo "$REPLY" | grep -qi "^yes$\|^no$"; then
    # Safe, validated input
fi
```

### 4. **Rate Limiting**
Telegram API limits:
- 30 messages/second per bot
- 20 messages/minute to same group

TeleMux handles this naturally since messages are user-driven.

---

## Debugging

### Check Listener Status
```bash
tg-status
```

### View Live Logs
```bash
tg-logs  # tail -f
```

### Check Message Queue
```bash
# See sent messages
cat ~/.telemux/message_queue/outgoing.log

# See received replies
cat ~/.telemux/message_queue/incoming.log

# Check listener state
cat ~/.telemux/message_queue/listener_state.json
```

### Check Agent Inbox
```bash
cat ~/.telemux/agents/my-agent/inbox.txt
```

### Manual Telegram API Test
```bash
source ~/.telemux/telegram_config

# Test bot connection
curl "https://api.telegram.org/bot${TELEMUX_TG_BOT_TOKEN}/getMe"

# Send test message
curl -X POST "https://api.telegram.org/bot${TELEMUX_TG_BOT_TOKEN}/sendMessage" \
  -d chat_id="${TELEMUX_TG_CHAT_ID}" \
  -d text="Test message"
```

### Common Issues

**1. "Message doesn't match agent response format"**
```
# User sent: "hello"
# Expected: "session-name: hello"
```
Reply must start with `session-name:` (the message ID shown in Telegram)

**2. "Unknown message ID"**
The session name doesn't exist in `outgoing.log`. Either:
- No message was sent from that session
- `outgoing.log` was cleared
- Typo in session name

**3. "Tmux session not found. Message saved to inbox."**
The tmux session was closed. Message still saved to inbox file for later retrieval.

**4. Listener not receiving messages**
- Check bot Privacy Mode (should be OFF for group chats)
- Via @BotFather → Bot Settings → Group Privacy → Turn off
- Verify bot was added to group chat

---

## Performance

**Telegram API Long-Polling:**
- Timeout: 30 seconds
- Total request timeout: 35 seconds (allows network overhead)
- Latency: ~1-3 seconds from send to receive

**Message Delivery:**
- Inbox write: < 1ms (file I/O)
- tmux send-keys: ~1 second (requires sleep for buffering)
- Total: ~1-2 seconds from Telegram → tmux

**Resource Usage:**
- Python daemon: ~15-30 MB RAM
- Idle CPU: ~0.1%
- Network: Minimal (long-polling connection)

---

## Testing Workflows

### 1. **Simple Alert Test**
```bash
tg_alert "Test message"
# Check Telegram for 🔔 notification
```

### 2. **Bidirectional Test**
```bash
# In tmux session "test-session"
tg_agent "test-agent" "Reply with 'confirmed'"

# In Telegram, reply:
# test-session: confirmed

# Watch for message to appear in terminal
```

### 3. **Approval Workflow Test**
```bash
cd ~/dev/telemux/examples
./deployment-approval.sh v1.0.0 production

# Reply via Telegram when prompted
```

---

## Extension Ideas

### 1. **Rich Media Support**
```python
# Send images, files, buttons
def send_telegram_image(image_path: str, caption: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    files = {'photo': open(image_path, 'rb')}
    data = {'chat_id': CHAT_ID, 'caption': caption}
    requests.post(url, files=files, data=data)
```

### 2. **Inline Keyboards**
```python
# Instead of typing reply, tap buttons
keyboard = {
    "inline_keyboard": [[
        {"text": "✅ Approve", "callback_data": "approve"},
        {"text": "❌ Reject", "callback_data": "reject"}
    ]]
}
```

### 3. **Multi-User Support**
```python
# Track user_id → session mapping
# Allow multiple users to control different sessions
USER_SESSIONS = {
    "123456789": "user-session",    # User's personal chat
    "987654321": "team-session"     # Team member
}
```

### 4. **Voice Message Support**
```python
# Convert voice messages to text via Telegram API
# Send to LLM for processing
```

### 5. **Platform Router**
```python
# Unified message queue for all platforms
class MessageRouter:
    def route_message(self, platform: str, message: dict):
        # Parse message
        # Find target session
        # Deliver via platform-specific method
```

---

## Conventions

**Message ID Format:**
- Lowercase letters, numbers, dashes, underscores
- No spaces (tmux session name restrictions)
- Examples: `claude-agent`, `build_server`, `deploy-prod-1`

**Agent Naming:**
- Descriptive of task: `deploy-agent`, `cleanup-agent`, `review-agent`
- Unique per workflow
- Persistent across runs (same agent name = same inbox)

**Timestamp Format:**
- ISO 8601: `2025-11-09T19:23:10-07:00`
- Sortable, timezone-aware
- Compatible with `date -Iseconds`

---

## File Permissions

```bash
~/.telemux/telegram_config           # 600 (owner read/write only)
~/.telemux/telegram_listener.py      # 755 (executable)
~/.telemux/telegram_control.sh       # 755 (executable)
~/.telemux/message_queue/            # 755 (directory)
~/.telemux/agents/                   # 755 (directory)
```

---

## Dependencies

**Required:**
- `tmux` - Terminal multiplexer
- `python3` - Python 3.7+
- `curl` - HTTP client (for shell functions)
- `bash` or `zsh` - Shell

**Python Libraries:**
- `requests` - HTTP library (usually pre-installed)
- `pathlib` - Path handling (built-in)
- `json` - JSON parsing (built-in)
- `re` - Regular expressions (built-in)
- `subprocess` - Process management (built-in)

**Optional:**
- `jq` - JSON parsing in shell scripts

---

## Version History

**v1.0.0 (2025-11-09)** - Initial TeleMux release
- Renamed from "Team Mux" to standalone "TeleMux"
- Moved from `~/.team_mux/` to `~/.telemux/`
- Environment variables: `TELEGRAM_*` → `TELEMUX_TG_*`
- Session-name-based message IDs
- Generic naming for future platform support
- Complete bidirectional Telegram bridge
- Shell functions: `tg_alert`, `tg_agent`, `tg_done`
- Control commands: `tg-start`, `tg-stop`, `tg-status`, etc.

---

## FAQ

**Q: Can I use this without tmux?**
A: No, tmux is fundamental to the architecture. It provides session management and the `send-keys` capability for message injection.

**Q: Can I run multiple bots?**
A: Yes, but you'd need separate `~/.telemux-bot1/`, `~/.telemux-bot2/` directories with different configs and listener sessions.

**Q: What if I delete `outgoing.log`?**
A: Incoming messages won't be routable (unknown message ID). The log is append-only and grows slowly. Consider rotating it monthly.

**Q: Can I use this for non-LLM workflows?**
A: Absolutely! Any tmux session can use `tg_alert` and `tg_agent`. Great for long builds, deployments, cron jobs, monitoring, etc.

**Q: How do I backup my setup?**
A: Backup `~/.telemux/telegram_config` (credentials) and `~/.telemux/message_queue/` (message history). The rest can be reinstalled.

**Q: Rate limits on Telegram?**
A: 30 msg/sec per bot, 20 msg/min to same group. More than enough for typical usage.

---

## Contributing

When extending TeleMux:

1. **Keep naming generic** - Use `TELEMUX_*` prefix for all env vars
2. **Use platform prefixes** - `TELEMUX_TG_*`, `TELEMUX_WA_*`, etc.
3. **Maintain backward compatibility** - Add features, don't break existing
4. **Update this doc** - Keep CLAUDE.md in sync with code changes
5. **Test bidirectional flow** - Both outgoing and incoming paths

---

## Summary

**TeleMux = Telegram ↔ Tmux Bridge**

**Core Components:**
1. Shell functions (tg_alert, tg_agent) - Send messages
2. Python listener daemon - Receive & route messages
3. Message queue - Log & track conversations
4. Agent inboxes - Persistent message storage

**Key Innovation:**
Session-name-based message IDs make mobile replies easy and natural.

**Future-Ready:**
Generic `TELEMUX_*` naming allows adding WhatsApp, Slack, Discord without breaking changes.

**Use Cases:**
- LLM agent ↔ human communication
- CI/CD approval workflows
- Long-running task notifications
- Remote system monitoring
- Interactive terminal automation

---

**For questions or issues, check:**
- `tg-status` - Daemon status
- `tg-logs` - Live logs
- `~/.telemux/telegram_listener.log` - Full log history
- This document - Architecture reference
