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
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

from . import TELEMUX_DIR, MESSAGE_QUEUE_DIR, LOG_FILE, TMUX_SESSION
from .config import load_config

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

logger.addHandler(main_handler)
logger.addHandler(error_handler)
logger.addHandler(console_handler)


def load_state() -> Dict:
    """Load listener state (last update ID)"""
    if LISTENER_STATE.exists():
        with open(LISTENER_STATE) as f:
            return json.load(f)
    return {"last_update_id": 0}


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


def parse_message_id(text: str) -> Optional[Tuple[str, str]]:
    """
    Parse message ID and response from text
    Expected formats:
      - session-name: Your response here (new format)
      - msg-1234567890-12345: Your response here (old format)
    Returns: (message_id, response) or None
    """
    # Match either session name (letters, numbers, dashes, underscores) or old msg format
    pattern = r'^([\w-]+):\s*(.+)$'
    match = re.match(pattern, text, re.DOTALL)
    if match:
        return match.group(1), match.group(2)
    return None


def process_update(update: Dict[str, Any], bot_token: str, chat_id: str) -> None:
    """Process a single Telegram update - SESSION-BASED ROUTING

    Args:
        update: Telegram update dict containing message data
        bot_token: Telegram bot token
        chat_id: Telegram chat ID

    Returns:
        None
    """
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
            send_telegram_message(bot_token, chat_id, f"No tmux sessions are running")
            return

        active_sessions = [s for s in result.stdout.strip().split('\n') if s]

        if session_name not in active_sessions:
            logger.warning(f"Tmux session not found: {session_name}")
            # Security: Show count only, not all session names
            send_telegram_message(bot_token, chat_id, f"Session <b>{session_name}</b> not found. {len(active_sessions)} active session(s).")
            return

        # SECURITY: Sanitize user input to prevent command injection
        # tmux send-keys interprets special characters like $(), ``, &&, ;
        # Without sanitization, malicious input could execute arbitrary commands
        safe_response = shlex.quote(response)
        formatted_message = f"{safe_response}\n # Respond using this terminal command: tg_agent \"{session_name}\" \"your response\""

        # Send message to tmux session
        result = subprocess.run(
            ['tmux', 'send-keys', '-t', session_name, formatted_message],
            capture_output=True,
            text=True,
            check=False
        )

        if result.returncode != 0:
            logger.error(f"Failed to send message to tmux: {result.stderr}")
            send_telegram_message(bot_token, chat_id, f"Failed to deliver message to session")
            return

        # CRITICAL: Sleep required for tmux to buffer text before Enter is sent
        # Without this delay, tmux doesn't have time to process send-keys and
        # the message gets lost. See: https://github.com/tmux/tmux/issues/1254
        time.sleep(1)

        # Send Enter to execute the command
        result = subprocess.run(
            ['tmux', 'send-keys', '-t', session_name, 'C-m'],
            capture_output=True,
            text=True,
            check=False
        )

        if result.returncode != 0:
            logger.error(f"Failed to send Enter to tmux: {result.stderr}")
            send_telegram_message(bot_token, chat_id, f"Message sent but not executed")
            return

        logger.info(f"Message delivered to tmux session: {session_name}")
        logger.info(f"Content: {response}")

        # Send confirmation
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
    bot_token, chat_id = load_config()
    if not bot_token or not chat_id:
        logger.error("Failed to load Telegram config. Please run: telemux-install")
        sys.exit(1)

    logger.info(f"Loaded Telegram config - Chat ID: {chat_id}")

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
                    process_update(update, bot_token, chat_id)
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
