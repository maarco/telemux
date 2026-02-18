"""
Configuration management for TeleMux
"""

import os
from typing import Optional, Tuple

from . import TELEMUX_DIR, MESSAGE_QUEUE_DIR, CONFIG_FILE


def ensure_directories() -> None:
    """Create TeleMux directories if they don't exist."""
    TELEMUX_DIR.mkdir(parents=True, exist_ok=True)
    MESSAGE_QUEUE_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Load Telegram configuration from config file.

    Returns:
        Tuple of (bot_token, chat_id, user_id) or (None, None, None) if not configured
        user_id is optional - if set, only that user can control the bot
    """
    if not CONFIG_FILE.exists():
        return None, None, None

    # Source the bash config file to extract env vars
    bot_token = None
    chat_id = None
    user_id = None

    try:
        with open(CONFIG_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('export TELEMUX_TG_BOT_TOKEN='):
                    bot_token = line.split('=', 1)[1].strip('"').strip("'")
                elif line.startswith('export TELEMUX_TG_CHAT_ID='):
                    chat_id = line.split('=', 1)[1].strip('"').strip("'")
                elif line.startswith('export TELEMUX_TG_USER_ID='):
                    user_id = line.split('=', 1)[1].strip('"').strip("'")
    except Exception:
        pass

    # Also check environment variables (they take precedence)
    bot_token = os.environ.get('TELEMUX_TG_BOT_TOKEN', bot_token)
    chat_id = os.environ.get('TELEMUX_TG_CHAT_ID', chat_id)
    user_id = os.environ.get('TELEMUX_TG_USER_ID', user_id)

    return bot_token, chat_id, user_id


def save_config(bot_token: str, chat_id: str) -> None:
    """
    Save Telegram configuration to config file.

    Args:
        bot_token: Telegram bot token
        chat_id: Telegram chat ID
    """
    ensure_directories()

    config_content = f"""#!/bin/bash
# TeleMux Telegram Bot Configuration
# Keep this file secure! (chmod 600)

export TELEMUX_TG_BOT_TOKEN="{bot_token}"
export TELEMUX_TG_CHAT_ID="{chat_id}"
"""

    with open(CONFIG_FILE, 'w') as f:
        f.write(config_content)

    # Secure the config file
    os.chmod(CONFIG_FILE, 0o600)


def is_configured() -> bool:
    """Check if TeleMux is configured."""
    bot_token, chat_id, _ = load_config()
    return bot_token is not None and chat_id is not None
