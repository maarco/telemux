# TeleMux Simplification - Implementation Plan

**Goal:** Remove tg_alert/tg_agent distinction. Make ALL messages bidirectional - you can reply to any tmux session directly.

---

## Problem Statement

**Current Issue:**
- `tg_alert` sends one-way messages (can't reply)
- `tg_agent` sends two-way messages (can reply, but only if "registered" in outgoing.log)
- User tried to reply to a `tg_alert` message → got "Unknown message ID" error
- Confusing: why can't you reply to everything?

**Desired Behavior:**
- Type `session-name: message` in Telegram
- System checks if tmux session `session-name` exists
- If yes → deliver message to that session
- If no → tell user which sessions exist
- No pre-registration needed

---

## Files That Need Changes

### 1. `telegram_listener.py` (CRITICAL)
**Current Location:** `~/dev/telemux/telegram_listener.py` (source) and `~/.telemux/telegram_listener.py` (deployed)

**Changes Needed:**

#### In `process_update()` function (around line 236):

**REPLACE THIS:**
```python
def process_update(update: Dict):
    """Process a single Telegram update"""
    if "message" not in update:
        return

    message = update["message"]
    text = message.get("text", "")
    from_user = message.get("from", {}).get("first_name", "Unknown")

    logger.info(f"Received message from {from_user}: {text[:50]}...")

    # Parse message for agent response
    parsed = parse_message_id(text)
    if not parsed:
        logger.info("Message doesn't match agent response format, ignoring")
        return

    message_id, response = parsed
    logger.info(f"Parsed agent response - ID: {message_id}")

    # Lookup agent
    agent_info = lookup_agent(message_id)
    if not agent_info:
        logger.warning(f"No agent found for message ID: {message_id}")
        send_telegram_message(f"❌ Unknown message ID: {message_id}")
        return

    # Route to agent
    route_to_agent(agent_info, response)
```

**WITH THIS:**
```python
def process_update(update: Dict):
    """Process a single Telegram update"""
    if "message" not in update:
        return

    message = update["message"]
    text = message.get("text", "")
    from_user = message.get("from", {}).get("first_name", "Unknown")

    logger.info(f"Received message from {from_user}: {text[:50]}...")

    # Parse message for session: message format
    parsed = parse_message_id(text)
    if not parsed:
        logger.info("Message doesn't match format (session-name: message), ignoring")
        return

    session_name, response = parsed
    logger.info(f"Parsed message - Target session: {session_name}")

    # Check if tmux session exists
    try:
        result = subprocess.run(
            ['tmux', 'list-sessions', '-F', '#{session_name}'],
            capture_output=True,
            text=True,
            check=False
        )

        if result.returncode != 0:
            # No tmux sessions at all
            logger.warning("No tmux sessions found")
            send_telegram_message(f"[-] No tmux sessions are running")
            return

        active_sessions = [s for s in result.stdout.strip().split('\n') if s]

        if session_name not in active_sessions:
            logger.warning(f"Tmux session not found: {session_name}")
            sessions_list = ', '.join(active_sessions) if active_sessions else 'none'
            send_telegram_message(f"[-] Session <b>{session_name}</b> not found\n\nActive sessions: {sessions_list}")
            return

        # Send message to tmux session
        formatted_message = f"[FROM USER via Telegram] {response}"

        subprocess.run(
            ['tmux', 'send-keys', '-t', session_name, formatted_message],
            check=False
        )

        time.sleep(1)

        subprocess.run(
            ['tmux', 'send-keys', '-t', session_name, 'C-m'],
            check=False
        )

        logger.info(f"✓ Message delivered to tmux session: {session_name}")
        logger.info(f"✓ Content: {response}")

        # Send confirmation
        send_telegram_message(f"[+] Message delivered to <b>{session_name}</b>")

    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        send_telegram_message(f"[-] Error: {str(e)}")
```

**Why This Works:**
- No longer depends on `lookup_agent()` or `outgoing.log`
- Directly checks tmux for active sessions
- If session exists → deliver message
- If not → show what sessions exist

---

### 2. `INSTALL.sh`
**Location:** `~/dev/telemux/INSTALL.sh`

**Changes Needed:**

Make `tg_alert` also add reply instructions (make it bidirectional):

**FIND (around line 140):**
```bash
    curl -s -X POST "https://api.telegram.org/bot${TELEMUX_TG_BOT_TOKEN}/sendMessage" \
        -d chat_id="${TELEMUX_TG_CHAT_ID}" \
        -d text="[!] <b>[${tmux_session}]</b> ${message}" \
        -d parse_mode="HTML" > /dev/null && echo "[+] Alert sent to Telegram"
```

**REPLACE WITH:**
```bash
    curl -s -X POST "https://api.telegram.org/bot${TELEMUX_TG_BOT_TOKEN}/sendMessage" \
        -d chat_id="${TELEMUX_TG_CHAT_ID}" \
        -d text="[!] <b>[${tmux_session}]</b> ${message}

<i>Reply: ${tmux_session}: your response</i>" \
        -d parse_mode="HTML" > /dev/null && echo "[+] Message sent to Telegram"
```

**Why:** Shows users how to reply, even for "alert" messages.

---

### 3. `~/.zshrc` (User's shell config)
**Location:** `/Users/malmazan/.zshrc`

**Changes Needed:**

Same change as INSTALL.sh - make tg_alert show reply format:

**FIND (around line 242):**
```bash
    curl -s -X POST "https://api.telegram.org/bot${TELEMUX_TG_BOT_TOKEN}/sendMessage" \
        -d chat_id="${TELEMUX_TG_CHAT_ID}" \
        -d text="[!] <b>[${tmux_session}]</b> ${message}" \
        -d parse_mode="HTML" > /dev/null && echo "[+] Alert sent to Telegram"
```

**REPLACE WITH:**
```bash
    curl -s -X POST "https://api.telegram.org/bot${TELEMUX_TG_BOT_TOKEN}/sendMessage" \
        -d chat_id="${TELEMUX_TG_CHAT_ID}" \
        -d text="[!] <b>[${tmux_session}]</b> ${message}

<i>Reply: ${tmux_session}: your response</i>" \
        -d parse_mode="HTML" > /dev/null && echo "[+] Message sent to Telegram"
```

---

### 4. `UPDATE.sh` (Optional - for existing users)
**Location:** `~/dev/telemux/UPDATE.sh`

**Changes Needed:**

If UPDATE.sh updates shell functions, it needs the same changes. Check if it contains the `tg_alert` function and update it.

---

## Testing Plan

### 1. Test in Dev First

**Before deploying:**
```bash
# In ~/dev/telemux
python3 telegram_listener.py
# Watch the logs, make sure it starts without errors
```

### 2. Test the Flow

**Create a test tmux session:**
```bash
tmux new-session -d -s test-reply
```

**Send test alert:**
```bash
tmux send-keys -t test-reply 'source ~/.zshrc && tg_alert "Testing bidirectional alerts"' C-m
```

**In Telegram, you should see:**
```
[!] [test-reply] Testing bidirectional alerts

Reply: test-reply: your response
```

**Reply in Telegram:**
```
test-reply: This is my reply
```

**Expected result:**
```
[+] Message delivered to test-reply
```

**Check the tmux session:**
```bash
tmux capture-pane -t test-reply -p
```

**Should see:**
```
[FROM USER via Telegram] This is my reply
```

### 3. Test Non-Existent Session

**In Telegram, try:**
```
nonexistent-session: hello
```

**Expected:**
```
[-] Session nonexistent-session not found

Active sessions: test-reply, telegram-listener, telemux
```

### 4. Edge Cases

**Test with no tmux sessions:**
```bash
# Kill all tmux except listener
tmux list-sessions | grep -v telegram-listener | cut -d: -f1 | xargs -I {} tmux kill-session -t {}
```

**Then try to send message in Telegram:**
```
test: hello
```

**Expected:**
```
[-] No tmux sessions are running
```

---

## Deployment Steps

### 1. Stop Listener
```bash
tg-stop
```

### 2. Update Files in Order

```bash
# Update source
cd ~/dev/telemux
# Make changes to telegram_listener.py
# Make changes to INSTALL.sh

# Copy to deployment
cp telegram_listener.py ~/.telemux/

# Update shell config
# Make changes to ~/.zshrc
source ~/.zshrc
```

### 3. Start Listener
```bash
tg-start
```

### 4. Verify
```bash
tg-status
tail -20 ~/.telemux/telegram_listener.log
```

---

## Rollback Plan

If something breaks:

```bash
# Stop broken listener
tg-stop

# Restore from git
cd ~/dev/telemux
git checkout HEAD~1 telegram_listener.py
cp telegram_listener.py ~/.telemux/

# Restore shell config from backup
# (Make a backup before starting!)
cp ~/.zshrc.backup ~/.zshrc
source ~/.zshrc

# Start listener
tg-start
```

---

## Expected Outcomes

### Before (Current):
- `tg_alert`: Can't reply → ❌ Unknown message ID
- `tg_agent`: Can reply (if pre-registered)
- Confusing distinction

### After (Fixed):
- `tg_alert`: Can reply → works
- `tg_agent`: Can reply → works
- ANY tmux session can be messaged directly
- No pre-registration needed

---

## Additional Notes

### Why `lookup_agent()` Can Be Removed (Eventually)

Once this works, these functions become obsolete:
- `lookup_agent()` - no longer needed
- `route_to_agent()` - simplified (just send to tmux)
- Inbox files - less critical (messages go to tmux directly)

But don't remove them yet - do it in a separate cleanup phase.

### Future Simplification

Once this is stable, consider:
1. Remove `tg_agent` entirely - just use `tg_alert` for everything
2. Rename `tg_alert` to `tg_message` or just `tg`
3. Remove unused `lookup_agent()` and `route_to_agent()` functions
4. Simplify outgoing.log (maybe not needed at all)

---

## Commit Messages

**For telegram_listener.py:**
```
Simplify: Route messages directly to tmux sessions

- No longer requires pre-registration via tg_agent
- Check if tmux session exists directly
- If yes: deliver message
- If no: show active sessions
- Removed dependency on lookup_agent() and outgoing.log
```

**For INSTALL.sh and .zshrc:**
```
Make tg_alert bidirectional by showing reply format

- Add reply instructions to tg_alert messages
- Show: "Reply: session-name: your response"
- Makes all messages replyable, not just tg_agent
```

---

## Summary

**Files to modify:** 3-4 files
**Lines changed:** ~60 lines total
**Risk level:** Medium (changes core routing logic)
**Testing required:** Yes - full end-to-end
**Rollback plan:** Ready

**Key insight:** The outgoing.log registration was solving the wrong problem. Just check tmux directly.
