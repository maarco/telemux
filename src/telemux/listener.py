#!/usr/bin/env python3
"""
Telegram Listener Daemon for TeleMux
Monitors Telegram bot for incoming messages and routes them to LLM agents
"""

import os
import re
import sys
import json
import time
import logging
import requests
import subprocess
import shlex
from typing import Dict, List, Optional, Tuple, Any

from . import TELEMUX_DIR, MESSAGE_QUEUE_DIR, LOG_FILE, TMUX_SOCKET
from .config import load_config


def tmux_cmd(*args):
    """Build tmux command with custom socket (for listener daemon)."""
    return ['tmux', '-L', TMUX_SOCKET] + list(args)


def tmux_user_cmd(*args):
    """Build tmux command for user's default socket (for message routing)."""
    # Clear TMUX env var to avoid inheriting listener's socket context
    env = os.environ.copy()
    env.pop('TMUX', None)
    return ['tmux'] + list(args), env

# Message queue files
OUTGOING_LOG = MESSAGE_QUEUE_DIR / "outgoing.log"
INCOMING_LOG = MESSAGE_QUEUE_DIR / "incoming.log"
LISTENER_STATE = MESSAGE_QUEUE_DIR / "listener_state.json"

# Logging setup
ERROR_LOG_FILE = TELEMUX_DIR / "telegram_errors.log"

# Get log level from environment variable (default: INFO)
LOG_LEVEL = os.environ.get('TELEMUX_LOG_LEVEL', 'INFO').upper()
LOG_LEVEL_MAP = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL
}

# Configure logging with multiple handlers
logger = logging.getLogger('TelegramListener')
logger.setLevel(LOG_LEVEL_MAP.get(LOG_LEVEL, logging.INFO))

# Main log file handler (all levels)
main_handler = logging.FileHandler(LOG_FILE)
main_handler.setLevel(logging.DEBUG)
main_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
main_handler.setFormatter(main_formatter)

# Error log file handler (errors only)
error_handler = logging.FileHandler(ERROR_LOG_FILE)
error_handler.setLevel(logging.ERROR)
error_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
error_handler.setFormatter(error_formatter)

# Console handler (configurable level)
console_handler = logging.StreamHandler()
console_handler.setLevel(LOG_LEVEL_MAP.get(LOG_LEVEL, logging.INFO))
console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_formatter)

# Only add handlers if not already present (prevents duplicates on re-import)
if not logger.handlers:
    logger.addHandler(main_handler)
    logger.addHandler(error_handler)
    logger.addHandler(console_handler)


def _send_capture(session_name: str, bot_token: str, chat_id: str) -> None:
    """Capture and send tmux session output"""
    cmd, env = tmux_user_cmd('capture-pane', '-t', session_name, '-p', '-S', '-100')
    capture_result = subprocess.run(cmd, capture_output=True, text=True, check=False, env=env)

    if capture_result.returncode == 0:
        output = capture_result.stdout.strip()
        if len(output) > 3800:
            output = output[-3800:] + "\n\n[...truncated]"
        send_telegram_message(bot_token, chat_id, f"<b>{session_name}:</b>\n<pre>{output}</pre>")
    else:
        send_telegram_message(bot_token, chat_id, "Capture failed")


def load_state() -> Dict:
    """Load listener state"""
    if LISTENER_STATE.exists():
        with open(LISTENER_STATE) as f:
            state = json.load(f)
            # Backward compatibility
            if "last_active_session" not in state:
                state["last_active_session"] = None
            if "auto_capture" not in state:
                state["auto_capture"] = False
            return state
    return {"last_update_id": 0, "last_active_session": None, "auto_capture": False}


def save_state(state: Dict):
    """Save listener state"""
    MESSAGE_QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    with open(LISTENER_STATE, 'w') as f:
        json.dump(state, f, indent=2)


def get_telegram_updates(bot_token: str, offset: int = 0, max_retries: int = 3) -> List[Dict]:
    """Poll Telegram for new messages with retry logic"""
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    params = {
        "offset": offset,
        "timeout": 30  # Long polling
    }

    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=35)
            response.raise_for_status()
            data = response.json()

            if data.get("ok"):
                return data.get("result", [])
            else:
                logger.warning(f"Telegram API returned not ok: {data}")
                return []

        except requests.exceptions.Timeout:
            # Timeout is expected with long polling, only log if it's a problem
            if attempt < max_retries - 1:
                logger.debug(f"Telegram long-poll timeout (attempt {attempt + 1}/{max_retries})")
                time.sleep(2 ** attempt)
            else:
                logger.warning(f"Failed to get updates after {max_retries} timeout attempts")
                return []

        except requests.exceptions.ConnectionError as e:
            logger.warning(f"Connection error (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                logger.error(f"Failed to connect after {max_retries} attempts. Is the network down?")
                return []

        except requests.exceptions.RequestException as e:
            logger.warning(f"Request error (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                logger.error(f"Failed to get updates after {max_retries} attempts: {e}")
                return []

        except Exception as e:
            logger.error(f"Unexpected error getting Telegram updates: {e}")
            return []

    return []


def send_telegram_message(bot_token: str, chat_id: str, text: str, max_retries: int = 3):
    """Send a message to Telegram with retry logic"""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }

    for attempt in range(max_retries):
        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            logger.info(f"Sent message to Telegram: {text[:50]}...")
            return True

        except requests.exceptions.Timeout:
            logger.warning(f"Telegram API timeout (attempt {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff: 1s, 2s, 4s
            else:
                logger.error(f"Failed to send message after {max_retries} attempts (timeout)")
                return False

        except requests.exceptions.RequestException as e:
            logger.warning(f"Telegram API error (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                logger.error(f"Failed to send message after {max_retries} attempts: {e}")
                return False

        except Exception as e:
            logger.error(f"Unexpected error sending Telegram message: {e}")
            return False

    return False


def parse_message_id(text: str) -> Tuple[Optional[str], str, bool]:
    """
    Parse message ID and response from text
    Expected formats:
      - session-name: Your response here (explicit session, sanitized)
      - session-name: !command (explicit session, bypass sanitization)
      - Your response here (implicit session, sanitized)
      - !command (implicit session, bypass sanitization)
    Returns: (session_name, message_content, bypass_sanitization)
    session_name is None for implicit routing (uses last active session)
    """
    # Try to match explicit session format: "session-name: message"
    pattern = r'^([\w-]+):\s*(.+)$'
    match = re.match(pattern, text, re.DOTALL)

    if match:
        # Explicit session specified
        session_name = match.group(1)
        message_content = match.group(2)

        # Check for bypass prefix
        bypass_sanitization = False
        if message_content.startswith('!'):
            bypass_sanitization = True
            message_content = message_content[1:]  # Remove ! prefix

        return session_name, message_content, bypass_sanitization
    else:
        # No explicit session - treat entire text as message content
        # This will route to last active session
        message_content = text
        bypass_sanitization = False

        # Check for bypass prefix
        if message_content.startswith('!'):
            bypass_sanitization = True
            message_content = message_content[1:]  # Remove ! prefix

        return None, message_content, bypass_sanitization


def process_update(update: Dict[str, Any], bot_token: str, chat_id: str, user_id: Optional[str], state: Dict) -> None:
    """Process a single Telegram update - SESSION-BASED ROUTING

    Args:
        update: Telegram update dict containing message data
        bot_token: Telegram bot token
        chat_id: Telegram chat ID
        user_id: Optional Telegram user ID for additional validation
        state: Listener state dict (contains last_update_id and last_active_session)

    Returns:
        None
    """
    if "message" not in update:
        return

    message = update["message"]
    text = message.get("text", "")
    from_user_data = message.get("from", {})
    from_user_name = from_user_data.get("first_name", "Unknown")
    from_user_id = str(from_user_data.get("id", ""))
    incoming_chat_id = str(message.get("chat", {}).get("id", ""))

    logger.info(
        f"Received message from {from_user_name} "
        f"(user_id: {from_user_id}, chat_id: {incoming_chat_id}): {text[:50]}..."
    )

    # SECURITY: Validate that message is from authorized chat ID
    if incoming_chat_id != chat_id:
        logger.warning(f"UNAUTHORIZED ACCESS ATTEMPT from chat_id {incoming_chat_id} (expected {chat_id})")
        logger.warning(f"Unauthorized user: {from_user_name} (user_id: {from_user_id}), message: {text}")
        return

    # SECURITY: Validate user ID if configured (extra layer of security)
    if user_id and from_user_id != user_id:
        logger.warning(f"UNAUTHORIZED USER ATTEMPT from user_id {from_user_id} (expected {user_id})")
        logger.warning(f"Unauthorized user: {from_user_name}, message: {text}")
        return

    # Handle special "capture" commands
    text = text.strip().lower()

    if text == "capture":
        logger.info("Manual capture command")
        session_name = state.get("last_active_session")
        if not session_name:
            send_telegram_message(bot_token, chat_id, "No active session. Send a message first.")
            return
        _send_capture(session_name, bot_token, chat_id)
        return

    if text == "capture on":
        logger.info("Auto-capture enabled")
        state["auto_capture"] = True
        save_state(state)
        send_telegram_message(bot_token, chat_id, "Auto-capture ON. Will capture after each message.")
        return

    if text == "capture off":
        logger.info("Auto-capture disabled")
        state["auto_capture"] = False
        save_state(state)
        send_telegram_message(bot_token, chat_id, "Auto-capture OFF.")
        return

    if text == "capture status":
        status = "ON" if state.get("auto_capture") else "OFF"
        send_telegram_message(bot_token, chat_id, f"Auto-capture: {status}")
        return

    # Parse message (supports both explicit "session: message" and implicit "message" formats)
    session_name, response, bypass_sanitization = parse_message_id(text)

    # Session resolution: if no explicit session, use last active session
    if session_name is None:
        session_name = state.get("last_active_session")
        if not session_name:
            logger.warning("No active session stored and no explicit session specified")
            send_telegram_message(bot_token, chat_id, "No active session. Reply with: session-name: message")
            return
        logger.info(f"Using last active session: {session_name}")
    else:
        logger.info(f"Explicit session specified: {session_name}")

    if bypass_sanitization:
        logger.warning(f"BYPASS MODE: Sanitization disabled for session {session_name}")

    # Check if tmux session exists (use user's default socket)
    try:
        cmd, env = tmux_user_cmd('list-sessions', '-F', '#{session_name}')
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            env=env
        )

        if result.returncode != 0:
            # No tmux sessions at all
            logger.warning("No tmux sessions found")
            send_telegram_message(bot_token, chat_id, "No tmux sessions are running")
            return

        active_sessions = [s for s in result.stdout.strip().split('\n') if s]
        logger.info(f"Found {len(active_sessions)} sessions: {active_sessions}")

        if session_name not in active_sessions:
            logger.warning(f"Tmux session not found: {session_name}")
            # Show available sessions so user knows what to use
            sessions_list = ", ".join(active_sessions)
            msg = (f"Session <b>{session_name}</b> not found.\n"
                   f"Active: {sessions_list}")
            send_telegram_message(bot_token, chat_id, msg)
            return

        # SECURITY: Sanitize user input to prevent command injection
        # tmux send-keys interprets special characters like $(), ``, &&, ;
        # Without sanitization, malicious input could execute arbitrary commands
        # Use !raw: prefix to bypass sanitization when needed
        if bypass_sanitization:
            # DANGER: No sanitization - user explicitly bypassed security
            safe_response = response
        else:
            safe_response = shlex.quote(response)

        formatted_message = f"{safe_response}\n # Respond using: tg_agent \"your response\""

        # Send message to tmux session (use user's default socket)
        cmd, env = tmux_user_cmd('send-keys', '-t', session_name, formatted_message)
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            env=env
        )

        if result.returncode != 0:
            logger.error(f"Failed to send message to tmux: {result.stderr}")
            send_telegram_message(bot_token, chat_id, "Failed to deliver message to session")
            return

        # CRITICAL: Sleep required for tmux to buffer text before Enter is sent
        # Without this delay, tmux doesn't have time to process send-keys and
        # the message gets lost. See: https://github.com/tmux/tmux/issues/1254
        time.sleep(1)

        # Send Enter to execute the command (use user's default socket)
        cmd, env = tmux_user_cmd('send-keys', '-t', session_name, 'C-m')
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            env=env
        )

        if result.returncode != 0:
            logger.error(f"Failed to send Enter to tmux: {result.stderr}")
            send_telegram_message(bot_token, chat_id, "Message sent but not executed")
            return

        logger.info(f"Message delivered to tmux session: {session_name}")
        logger.info(f"Content: {response}")

        # Update last active session (message was successfully delivered)
        state["last_active_session"] = session_name
        logger.info(f"Updating last active session: {session_name}")

        # If bypass mode, wait and capture screen output
        if bypass_sanitization:
            logger.info("Bypass mode: waiting for command execution and capturing output")
            time.sleep(2)  # Wait for command to execute

            # Capture last 100 lines from tmux session (use user's default socket)
            cmd, env = tmux_user_cmd('capture-pane', '-t', session_name, '-p', '-S', '-100')
            capture_result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                env=env
            )

            if capture_result.returncode == 0:
                output = capture_result.stdout.strip()
                if output:
                    # Truncate if too long for Telegram (4096 char limit)
                    if len(output) > 3800:
                        output = output[-3800:] + "\n\n[...truncated to last 3800 characters]"

                    send_telegram_message(
                        bot_token,
                        chat_id,
                        f"<b>Output from {session_name}:</b>\n<pre>{output}</pre>"
                    )
                else:
                    send_telegram_message(bot_token, chat_id, f"Command executed in <b>{session_name}</b> (no output)")
            else:
                send_telegram_message(bot_token, chat_id, f"Command executed in <b>{session_name}</b> (capture failed)")
        else:
            # Normal mode - check if auto-capture is enabled
            if state.get("auto_capture"):
                logger.info("Auto-capture enabled, waiting 5 seconds...")
                time.sleep(5)
                _send_capture(session_name, bot_token, chat_id)
            else:
                send_telegram_message(bot_token, chat_id, f"Message delivered to <b>{session_name}</b>")

    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        send_telegram_message(bot_token, chat_id, f"Error: {str(e)}")


def main():
    """Main listener loop"""
    logger.info("=" * 60)
    logger.info("Telegram Listener Daemon Starting")
    logger.info("=" * 60)

    # Load config
    bot_token, chat_id, user_id = load_config()
    if not bot_token or not chat_id:
        logger.error("Failed to load Telegram config. Please run: telemux-install")
        sys.exit(1)

    logger.info(f"Loaded Telegram config - Chat ID: {chat_id}")
    if user_id:
        logger.info(f"User ID validation enabled - Only user {user_id} can control bot")
    else:
        logger.warning("User ID validation disabled - anyone in the chat can control bot")

    # Create directories
    MESSAGE_QUEUE_DIR.mkdir(parents=True, exist_ok=True)

    # Load state
    state = load_state()
    offset = state["last_update_id"]

    logger.info(f"Starting from update offset: {offset}")
    logger.info("Listening for messages...")

    try:
        while True:
            updates = get_telegram_updates(bot_token, offset)

            for update in updates:
                update_id = update["update_id"]

                # Process update
                try:
                    process_update(update, bot_token, chat_id, user_id, state)
                except Exception as e:
                    logger.error(f"Error processing update {update_id}: {e}")

                # Update offset
                offset = update_id + 1
                state["last_update_id"] = offset
                save_state(state)

            # Small sleep if no updates
            if not updates:
                time.sleep(1)

    except KeyboardInterrupt:
        logger.info("\nListener stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
