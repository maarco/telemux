"""
TeleMux - Bidirectional Telegram integration for tmux sessions
"""

__version__ = "1.2.0"
__author__ = "Marco Almazan"

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# Package-level constants
TELEMUX_DIR = Path.home() / ".telemux"
MESSAGE_QUEUE_DIR = TELEMUX_DIR / "message_queue"
CONFIG_FILE = TELEMUX_DIR / "telegram_config"
LOG_FILE = TELEMUX_DIR / "telegram_listener.log"
TMUX_SOCKET = "telemux"  # Custom socket to isolate from user's tmux sessions
TMUX_SESSION = "listener"  # Session name within the custom socket

# Re-export listener functions for backward compatibility with tests
from .listener import (
    tmux_cmd,
    tmux_user_cmd,
    load_state,
    save_state,
    get_telegram_updates,
    send_telegram_message,
    parse_message_id,
    process_update,
    OUTGOING_LOG,
    INCOMING_LOG,
    LISTENER_STATE,
    logger,
    ERROR_LOG_FILE,
)

__all__ = [
    "__version__",
    "TELEMUX_DIR",
    "MESSAGE_QUEUE_DIR",
    "CONFIG_FILE",
    "LOG_FILE",
    "TMUX_SOCKET",
    "TMUX_SESSION",
    # Listener exports
    "tmux_cmd",
    "tmux_user_cmd",
    "load_state",
    "save_state",
    "get_telegram_updates",
    "send_telegram_message",
    "parse_message_id",
    "process_update",
    "OUTGOING_LOG",
    "INCOMING_LOG",
    "LISTENER_STATE",
    "logger",
    "ERROR_LOG_FILE",
]
