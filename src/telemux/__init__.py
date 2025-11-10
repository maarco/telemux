"""
TeleMux - Bidirectional Telegram integration for tmux sessions
"""

__version__ = "1.0.2"
__author__ = "Marco Almazan"

from pathlib import Path

# Package-level constants
TELEMUX_DIR = Path.home() / ".telemux"
MESSAGE_QUEUE_DIR = TELEMUX_DIR / "message_queue"
CONFIG_FILE = TELEMUX_DIR / "telegram_config"
LOG_FILE = TELEMUX_DIR / "telegram_listener.log"
TMUX_SESSION = "telegram-listener"

__all__ = [
    "__version__",
    "TELEMUX_DIR",
    "MESSAGE_QUEUE_DIR",
    "CONFIG_FILE",
    "LOG_FILE",
    "TMUX_SESSION",
]
