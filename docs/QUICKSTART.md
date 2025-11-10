# TeleMux Quick Start

Get up and running in 5 minutes!

## Prerequisites

- Telegram app installed
- Terminal with tmux
- 5 minutes of your time

## Step 1: Create Telegram Bot (1 minute)

1. **Open Telegram** and search for `@BotFather`
2. **Send:** `/newbot`
3. **Follow prompts:**
   - Name: `TeleMux Bot` (or whatever you want)
   - Username: `your_bot_name_bot` (must end in 'bot')
4. **Copy the token** - looks like: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`

## Step 2: Configure Permissions & Send Test Message (1 minute)

### For Group Chat (Recommended):

**FIRST - Turn off Privacy Mode:**
1. Message `@BotFather` again
2. Send `/mybots` → Select your bot
3. **Bot Settings → Group Privacy → Turn off**
4. This lets the bot read all messages in groups

**THEN - Create group and test:**
1. Create a new Telegram group
2. Add your bot to the group
3. **Send "hello"** - This is required for the installer to find your chat!

### For Private DM:
1. Message your bot directly
2. **Send "hello"** - This is required for the installer to find your chat!

> The installer fetches your chats from Telegram. If you don't send a message first, your chat won't appear!

## Step 3: Install (1 minute)

```bash
cd ~/dev/telemux
./INSTALL.sh
```

The installer will:
- Ask for your bot token
- **Automatically fetch your available chats**
- Display chat IDs, types, and names for easy selection
- Test the connection with a message

No more manual curl commands needed!

## Step 4: Start & Test (1 minute)

```bash
# Reload shell
source ~/.zshrc  # or ~/.bashrc

# Start listener
tg-start

# Test it!
tg_alert "Hello from my terminal!"
```

**Check Telegram** - you should see the message!

## Step 5: Try Bidirectional (1 minute)

```bash
# Create a test tmux session
tmux new-session -s demo

# Inside the session:
tg_agent "demo-agent" "Can you hear me?"

# In Telegram, reply with:
# demo: Yes I can!

# Watch it appear in your tmux session!
```

## Common Issues

### "Bot not receiving my replies in group"
**Solution:** Disable Privacy Mode
```bash
# In Telegram:
# 1. Message @BotFather
# 2. /mybots → Select your bot
# 3. Bot Settings → Group Privacy → Turn off
```

### "tg-start: command not found"
**Solution:** Reload your shell
```bash
source ~/.zshrc  # or source ~/.bashrc
```

### "Message not appearing in tmux"
**Check:**
1. Is the listener running? `tg-status`
2. Are you in the right tmux session? `tmux list-sessions`
3. Did you use the correct session name in your reply?

## Next Steps

- Read the full README.md for advanced usage
- Check out examples/ for real-world scripts
- Integrate with your AI agents!

## Quick Commands

```bash
tg_alert "message"           # Simple alert
tg_agent "name" "msg"        # Bidirectional
tg_done                      # After commands
tg-status                          # Check listener
tg-logs                            # View logs
tg-restart                         # Restart listener
```

---

**That's it!** You now have bidirectional Telegram communication with your terminal.

Need help? Check `README.md` or the logs: `tg-logs`
