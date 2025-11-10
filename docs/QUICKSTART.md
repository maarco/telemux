# TeleMux Quick Start

Get up and running in 5 minutes!

## Prerequisites

- Telegram app installed
- Terminal with tmux
- 5 minutes of your time

## Step 1: Create Telegram Bot (2 minutes)

1. **Open Telegram** and search for `@BotFather`
2. **Send:** `/newbot`
3. **Follow prompts:**
   - Name: `Kollabor AI` (or whatever you want)
   - Username: `your_bot_name_bot` (must end in 'bot')
4. **Copy the token** - looks like: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`

## Step 2: Get Your Chat ID (1 minute)

### Option A: Group Chat (Recommended)
```bash
# 1. Create a group in Telegram and add your bot
# 2. Send any message to the group
# 3. Run this:
curl "https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates" | jq '.'

# 4. Look for: "chat":{"id": -1234567890}
# (negative number = group chat)
```

### Option B: Private DM
```bash
# 1. Message your bot directly (any message)
# 2. Run the same curl command
# 3. Look for: "chat":{"id": 1234567890}
# (positive number = personal chat)
```

## Step 3: Install (1 minute)

```bash
cd ~/dev/telemux
./INSTALL.sh

# Enter your bot token and chat ID when prompted
```

## Step 4: Start & Test (1 minute)

```bash
# Reload shell
source ~/.zshrc  # or ~/.bashrc

# Start listener
tg-start

# Test it!
tg_alert "Hello from my terminal! 🚀"
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

### ❌ "Bot not receiving my replies in group"
**Solution:** Disable Privacy Mode
```bash
# In Telegram:
# 1. Message @BotFather
# 2. /mybots → Select your bot
# 3. Bot Settings → Group Privacy → Turn off
```

### ❌ "tg-start: command not found"
**Solution:** Reload your shell
```bash
source ~/.zshrc  # or source ~/.bashrc
```

### ❌ "Message not appearing in tmux"
**Check:**
1. Is the listener running? `tg-status`
2. Are you in the right tmux session? `tmux list-sessions`
3. Did you use the correct session name in your reply?

## Next Steps

✅ **Read the full README.md** for advanced usage
✅ **Check out examples/** for real-world scripts
✅ **Integrate with your AI agents!**

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

**That's it!** You now have bidirectional Telegram communication with your terminal. 🎉

Need help? Check `README.md` or the logs: `tg-logs`
