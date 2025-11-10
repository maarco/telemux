# Changelog

## v1.0.0 - 2025-11-09

Initial release of TeleMux bidirectional Telegram bridge.

### Features

✅ **Simple Alerts**
- `tg_alert()` - Send one-way notifications to Telegram
- `tg_done()` - Alert when commands complete (with exit status)

✅ **Bidirectional Messaging**
- `tg_agent()` - Send messages from agents and receive replies
- Message routing via tmux session names
- Direct delivery to tmux sessions via `send-keys`

✅ **Listener Daemon**
- Python daemon with long-polling
- Runs 24/7 in dedicated tmux session
- Auto-recovery on restart
- State management for message tracking

✅ **Message Queue System**
- Persistent logging of all messages
- Inbox files for each agent
- Audit trail for sent/received messages

✅ **Clean API**
- Session name as message ID (simple format)
- Formatted delivery: `[FROM USER via Telegram] message`
- Sleep + Enter for proper tmux injection

### Components

- **telegram_listener.py** - Main listener daemon (Python 3.6+)
- **telegram_control.sh** - Control script (start/stop/status/logs)
- **Shell functions** - Integration for zsh/bash
- **INSTALL.sh** - Automated installation script

### Documentation

- **README.md** - Complete documentation (16KB)
- **QUICKSTART.md** - 5-minute setup guide
- **examples/** - Real-world usage examples

### Examples Included

1. **deployment-approval.sh** - Request approval before deploys
2. **long-build-notify.sh** - Notify on build start/completion
3. **ai-agent-question.sh** - Agent asks for guidance

### Requirements

- tmux
- Python 3.6+
- curl
- Telegram bot (via @BotFather)

### Installation

```bash
cd ~/dev/telemux
./INSTALL.sh
```

See QUICKSTART.md for full setup guide.

---

## Future Enhancements (Planned)

🔮 **v1.1.0**
- Multiple chat support (group + personal DM)
- Rich message formatting (markdown, buttons)
- Message threading/conversations
- Command shortcuts (/deploy, /status, etc.)

🔮 **v1.2.0**
- Web dashboard for message history
- Agent status monitoring
- Message analytics and insights

🔮 **v2.0.0**
- Multi-user support
- Permission system
- Approval workflows
- Integration with other platforms (Slack, Discord)

---

**Built for:** AI Agent Automation & LLM CLI Integration
**Project:** TeleMux - Bidirectional Telegram Bridge
**License:** MIT
