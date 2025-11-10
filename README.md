# TeleMux

**Bidirectional Telegram integration for tmux sessions** - Monitor commands, interact with agents, and stay connected to your terminal from anywhere.

## Features

- **One-way notifications**: Send alerts to Telegram when commands complete
- **Bidirectional communication**: Interact with tmux sessions via Telegram
- **Agent support**: Create interactive agents that can receive replies
- **Session routing**: Messages automatically delivered to the correct tmux session
- **Daemon-based**: Runs as a background service in tmux
- **Shell integration**: Simple shell functions for easy use
- **Secure**: Configuration files are automatically protected (chmod 600)

## Installation

### Via pip (Recommended)

```bash
# Install the package
pip install telemux

# Run the interactive installer
telemux install

# Start the listener daemon
telemux start
```

### From source

```bash
# Clone the repository
git clone https://github.com/malmazan/telemux.git
cd telemux

# Install in development mode
pip install -e .

# Run the installer
telemux install
```

## Quick Start

### 1. Create a Telegram Bot

1. Open Telegram and search for [@BotFather](https://t.me/BotFather)
2. Send `/newbot` and follow the prompts
3. Save the bot token provided

### 2. Install TeleMux

```bash
# Install via pip
pip install telemux

# Run the interactive installer
telemux install
```

The installer will:
- Check prerequisites (tmux, python3, curl)
- Validate your bot token
- Auto-detect available chats (with retry logic)
- Create configuration files
- Install shell functions
- Test the connection

### 3. Start the Listener

```bash
# Start the daemon
telemux start

# Check status
telemux status

# View logs
telemux logs
```

### 4. Use Shell Functions

```bash
# Send a simple notification
tg_alert "Build complete!"

# Send a message and receive replies (auto-detects tmux session name)
tg_agent "Ready to deploy to production?"
# Reply via Telegram: "session-name: yes"
# The reply appears directly in your terminal

# Get notified when a command completes
npm run build && tg_done
```

## Commands

### Control Commands

```bash
telemux start       # Start the listener daemon
telemux stop        # Stop the listener daemon
telemux restart     # Restart the listener daemon
telemux status      # Check daemon status
telemux logs        # View listener logs (tail -f)
telemux attach      # Attach to the listener tmux session
telemux cleanup     # Rotate and clean up log files
telemux doctor      # Run health check and diagnose issues
telemux install     # Run interactive installer
```

### Shortcuts

For convenience, all commands have `tg-` shortcuts:

```bash
tg-start    # Same as: telemux start
tg-stop     # Same as: telemux stop
tg-status   # Same as: telemux status
tg-logs     # Same as: telemux logs
```

## Shell Functions

After installation, these functions are available in your shell:

### `tg_alert`

Send one-way notifications to Telegram:

```bash
tg_alert "Message text"
```

**Examples:**

```bash
# Simple notification
tg_alert "Server is ready"

# Notify when command completes
npm install && tg_alert "Dependencies installed"

# Multiline messages
tg_alert "Deploy complete
- 50 files updated
- 0 errors"
```

### `tg_agent`

Send messages and receive replies via Telegram (automatically uses your tmux session name):

```bash
tg_agent "Message text"
```

**Examples:**

```bash
# Ask a question (inside a tmux session named "deploy")
tg_agent "Ready to deploy to production?"

# Wait for user response via Telegram
# User replies: "deploy: yes, proceed"
# Reply appears in your terminal

# Use in scripts (inside a tmux session named "approval")
tg_agent "Approve release v2.0?"
# Returns the session name, user responds via Telegram
# Check incoming message for approval
```

### `tg_done`

Automatically notify when the previous command completes:

```bash
npm run build && tg_done
```

This sends a notification with:
- Command that ran
- Exit code (success/failure)
- Timestamp

## Bidirectional Communication

TeleMux uses **session-based routing** for bidirectional communication:

### Sending Messages from Terminal

```bash
# In tmux session named "deploy"
tg_agent "Should I proceed with deployment?"
```

This sends a message to Telegram with instructions on how to reply. The session name is automatically detected.

### Replying from Telegram

Reply with the format: `session-name: your message`

```
deploy: yes, proceed with deployment
```

The reply is automatically routed to the correct tmux session and appears in your terminal.

### Security

- Messages are routed **only** to existing tmux sessions
- User input is sanitized to prevent command injection
- Session names are validated before routing
- No session names are revealed in error messages

## Configuration

Configuration is stored in `~/.telemux/`:

```
~/.telemux/
├── telegram_config          # Bot token and chat ID (chmod 600)
├── telegram_listener.log    # Listener daemon logs
├── telegram_errors.log      # Error logs
├── message_queue/           # Message routing data
│   ├── outgoing.log        # Sent messages
│   ├── incoming.log        # Received messages
│   └── archive/            # Rotated logs
└── shell_functions.sh       # Shell integration functions
```

### Environment Variables

You can override configuration with environment variables:

```bash
export TELEMUX_TG_BOT_TOKEN="your-bot-token"
export TELEMUX_TG_CHAT_ID="your-chat-id"
export TELEMUX_LOG_LEVEL="DEBUG"  # DEBUG, INFO, WARNING, ERROR
```

## Log Management

Logs are automatically rotated when they exceed 10MB:

```bash
# Manual log rotation
telemux cleanup

# Install automatic monthly cleanup
telemux cleanup --install-cron
```

Archives are stored in `~/.telemux/message_queue/archive/` and compressed with gzip.

## Troubleshooting

### Run Health Check

```bash
telemux doctor
```

This checks:
- Prerequisites (tmux, python3)
- Configuration files
- Telegram bot connection
- Listener daemon status
- Log files

### Common Issues

**Listener won't start:**
```bash
# Check if it's already running
telemux status

# View logs for errors
telemux logs

# Restart the listener
telemux restart
```

**Messages not being received:**
```bash
# Check listener status
telemux status

# Verify configuration
cat ~/.telemux/telegram_config

# Test bot connection
telemux doctor
```

**Shell functions not available:**
```bash
# Reload your shell configuration
source ~/.zshrc  # or ~/.bashrc

# Verify functions are sourced
type tg_alert
```

## Examples

### Long-Running Build Notification

```bash
#!/bin/bash
# Build script with notification

echo "Starting build..."
tg_alert "Build started for project-x"

npm run build
if [ $? -eq 0 ]; then
    tg_alert "Build succeeded!"
else
    tg_alert "Build failed! Check logs."
fi
```

### Interactive Deployment Agent

```bash
#!/bin/bash
# Deployment with approval (run in tmux session named "deploy")

tg_agent "Ready to deploy v2.0 to production?"

# User responds via Telegram: "deploy: yes"
# Response appears in terminal

read -p "Proceed with deployment? " response
if [[ "$response" == *"yes"* ]]; then
    ./deploy.sh
    tg_alert "Deployment complete!"
fi
```

### Multi-Step Workflow

```bash
#!/bin/bash
# Complex workflow with multiple checkpoints (run in tmux session named "migration")

tg_alert "Starting migration workflow..."

# Step 1: Backup
tg_agent "Backup database before migration?"
# Wait for approval...

# Step 2: Migration
./run-migration.sh && tg_done

# Step 3: Verification
tg_agent "Verify migration results?"
# Wait for verification...

tg_alert "Migration workflow complete!"
```

## Development

### Running Tests

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=telemux --cov-report=term-missing
```

### Project Structure

```
telemux/
├── telemux/
│   ├── __init__.py       # Package initialization
│   ├── cli.py            # Main CLI entry point
│   ├── control.py        # Daemon control (start, stop, status)
│   ├── listener.py       # Telegram listener daemon
│   ├── installer.py      # Interactive installer
│   ├── cleanup.py        # Log rotation and cleanup
│   ├── config.py         # Configuration management
│   └── shell_functions.sh # Shell integration
├── examples/             # Example scripts
├── tests/               # Test suite
├── pyproject.toml       # Package metadata and dependencies
├── MANIFEST.in          # Package file manifest
└── README.md            # This file
```

## Requirements

- Python 3.7+
- tmux
- curl
- requests library (automatically installed)

## License

MIT License - see LICENSE file for details

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.

## Support

- GitHub Issues: https://github.com/malmazan/telemux/issues
- Documentation: https://github.com/malmazan/telemux

## Credits

Created by Marco Almazan

## Related Projects

- [tmux](https://github.com/tmux/tmux) - Terminal multiplexer
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - Telegram Bot API wrapper
