"""
TeleMux Interactive Installer
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import requests

from . import TELEMUX_DIR, MESSAGE_QUEUE_DIR, CONFIG_FILE
from .config import ensure_directories, save_config


def check_prerequisites() -> bool:
    """Check if required tools are installed."""
    print("Checking prerequisites...")

    required = {
        'tmux': 'tmux -V',
        'python3': 'python3 --version',
        'curl': 'curl --version'
    }

    all_present = True
    for name, cmd in required.items():
        try:
            result = subprocess.run(
                cmd.split(),
                capture_output=True,
                check=False
            )
            if result.returncode == 0:
                continue
        except FileNotFoundError:
            pass

        print(f"ERROR: {name} is required but not installed. Aborting.")
        all_present = False

    if all_present:
        # Check Python version
        result = subprocess.run(
            ['python3', '--version'],
            capture_output=True,
            text=True,
            check=False
        )
        print(f"Python version: {result.stdout.strip().split()[1]}")
        print("All prerequisites met")

    print("")
    return all_present


def get_bot_info(bot_token: str) -> Optional[Dict]:
    """Get bot information from Telegram."""
    try:
        response = requests.get(
            f"https://api.telegram.org/bot{bot_token}/getMe",
            timeout=10
        )
        data = response.json()
        if data.get("ok"):
            return data["result"]
    except Exception:
        pass
    return None


def get_available_chats(bot_token: str) -> List[Dict]:
    """Fetch available chats from Telegram."""
    try:
        response = requests.get(
            f"https://api.telegram.org/bot{bot_token}/getUpdates",
            timeout=10
        )
        data = response.json()

        if not data.get("ok"):
            return []

        # Extract unique chats
        chats = {}
        for update in data.get("result", []):
            if "message" in update:
                chat = update["message"]["chat"]
                chat_id = str(chat["id"])

                if chat_id not in chats:
                    chat_info = {
                        "id": chat_id,
                        "type": chat["type"],
                        "name": chat.get("title") or
                                f"{chat.get('first_name', '')} {chat.get('last_name', '')}".strip() or
                                "Unknown"
                    }
                    chats[chat_id] = chat_info

        return list(chats.values())

    except Exception as e:
        print(f"Error fetching chats: {e}")
        return []


def display_chats(chats: List[Dict]):
    """Display available chats to the user."""
    print("Available chats (send a message to your bot first if empty):")
    print("-" * 60)

    for chat in chats:
        print(f"  Chat ID: {chat['id']}")
        print(f"  Type: {chat['type']}")
        print(f"  Name: {chat['name']}")
        print("-" * 60)

    print("")
    print("Note: Group chat IDs are negative, personal chat IDs are positive")
    print("")


def get_chat_id_interactive(bot_token: str) -> Optional[str]:
    """Interactively get chat ID from user with retry logic."""
    chats = get_available_chats(bot_token)

    if chats:
        display_chats(chats)

        # If exactly one chat, offer to use it
        if len(chats) == 1:
            chat = chats[0]
            print(f"Found only one chat: {chat['name']} (ID: {chat['id']})")
            response = input("Use this chat? (y/n): ").strip().lower()
            if response == 'y':
                return chat['id']
            else:
                return input("Enter your Chat ID manually: ").strip()
        else:
            return input("Enter your Chat ID (from above): ").strip()
    else:
        # No chats found - offer retry
        print("  No chats found. You need to:")
        print("  1. Start a conversation with your bot (send any message)")
        print("  2. Or add the bot to a group and send a message")
        print("")

        while True:
            choice = input("Try again after sending a message? (y/n/manual): ").strip().lower()

            if choice == 'y':
                print("")
                print("Checking for new chats...")
                chats = get_available_chats(bot_token)

                if chats:
                    print("Found chats! Displaying available options...")
                    display_chats(chats)

                    if len(chats) == 1:
                        chat = chats[0]
                        print(f"Found only one chat: {chat['name']} (ID: {chat['id']})")
                        response = input("Use this chat? (y/n): ").strip().lower()
                        if response == 'y':
                            return chat['id']
                        else:
                            return input("Enter your Chat ID manually: ").strip()
                    else:
                        return input("Enter your Chat ID (from above): ").strip()
                else:
                    print("  Still no chats found. Make sure you sent a message to your bot.")
                    print("")

            elif choice == 'n':
                print("Exiting installation. Run the installer again when ready.")
                sys.exit(0)

            elif choice == 'manual' or choice == 'm':
                print("")
                return input("Enter your Chat ID manually: ").strip()

            else:
                print("Please enter 'y' to try again, 'n' to exit, or 'manual' to enter chat ID manually.")


def test_telegram_connection(bot_token: str, chat_id: str) -> bool:
    """Send a test message to verify configuration."""
    print("Verifying chat ID...")
    test_message = f"TeleMux installation test - {subprocess.run(['date'], capture_output=True, text=True).stdout.strip()}"

    try:
        response = requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": test_message,
                "parse_mode": "HTML"
            },
            timeout=10
        )
        data = response.json()

        if data.get("ok"):
            print(f"Test message sent successfully to chat {chat_id}")
            return True
        else:
            print("ERROR: Failed to send test message. Please verify your chat ID.")
            print(f"Response: {data}")
            return False

    except Exception as e:
        print(f"ERROR: Failed to send test message: {e}")
        return False


def install_shell_functions(shell_rc: Path) -> bool:
    """Install shell functions to user's rc file."""
    # Check if already installed
    if shell_rc.exists():
        with open(shell_rc, 'r') as f:
            content = f.read()
            if "# TELEGRAM NOTIFICATIONS" in content or "TELEMUX" in content:
                print(f"WARNING: Shell functions already exist in {shell_rc}")
                response = input("Overwrite? (y/n): ").strip().lower()
                if response != 'y':
                    print("Skipping shell function installation")
                    return True

    # Copy shell_functions.sh to ~/.telemux/
    print("Deploying shell functions...")
    import telemux
    package_dir = Path(telemux.__file__).parent
    source_functions = package_dir / "shell_functions.sh"

    if not source_functions.exists():
        print(f"WARNING: shell_functions.sh not found at {source_functions}")
        print("Shell functions will not be installed")
        return False

    # Copy to ~/.telemux/
    import shutil
    dest_functions = TELEMUX_DIR / "shell_functions.sh"
    shutil.copy(source_functions, dest_functions)
    dest_functions.chmod(0o755)
    print(f"Shell functions deployed to {dest_functions}")

    # Add sourcing line to shell RC
    print(f"Adding shell functions to {shell_rc}...")
    with open(shell_rc, 'a') as f:
        f.write('\n')
        f.write('# ' + '=' * 77 + '\n')
        f.write('# TELEGRAM NOTIFICATIONS (TeleMux)\n')
        f.write('# ' + '=' * 77 + '\n')
        f.write('# Source TeleMux shell functions (single source of truth)\n')
        f.write('if [[ -f "$HOME/.telemux/shell_functions.sh" ]]; then\n')
        f.write('    source "$HOME/.telemux/shell_functions.sh"\n')
        f.write('fi\n')
        f.write('\n')

    print(f"Shell functions added (sourced from {dest_functions})")
    return True


def update_claude_config():
    """Optionally add TeleMux documentation to Claude Code config."""
    claude_config = Path.home() / ".claude" / "CLAUDE.md"

    if not claude_config.exists():
        return

    print("")
    print("=" * 60)
    print("Claude Code Integration")
    print("=" * 60)
    print("")
    print(f"Found Claude Code configuration at {claude_config}")
    print("")

    response = input("Add TeleMux documentation to Claude config? (y/n): ").strip().lower()
    if response != 'y':
        print("Skipped Claude config update")
        return

    # Check if already exists
    with open(claude_config, 'r') as f:
        content = f.read()
        if "# TeleMux" in content:
            print("WARNING: TeleMux section already exists in Claude config")
            return

    # Add TeleMux documentation
    with open(claude_config, 'a') as f:
        f.write('\n')
        f.write('---\n')
        f.write('\n')
        f.write('# TeleMux - Telegram Integration\n')
        f.write('\n')
        f.write('TeleMux is installed and available for bidirectional communication with Telegram.\n')
        f.write('\n')
        f.write('## Available Functions\n')
        f.write('\n')
        f.write('- `tg_alert "message"` - Send one-way notifications to Telegram\n')
        f.write('- `tg_agent "agent-name" "message"` - Send message and receive replies\n')
        f.write('- `tg_done` - Alert when previous command completes\n')
        f.write('\n')
        f.write('## Control Commands\n')
        f.write('\n')
        f.write('- `tg-start` - Start the listener daemon\n')
        f.write('- `tg-stop` - Stop the listener daemon\n')
        f.write('- `tg-status` - Check daemon status\n')
        f.write('- `tg-logs` - View listener logs\n')
        f.write('\n')
        f.write('## Usage in Agents\n')
        f.write('\n')
        f.write('When running in tmux, agents can use `tg_agent` to ask questions and receive user replies via Telegram. Replies are delivered directly back to the tmux session.\n')
        f.write('\n')
        f.write('**Example:**\n')
        f.write('```bash\n')
        f.write('tg_agent "deploy-agent" "Ready to deploy to production?"\n')
        f.write('# User replies via Telegram: "session-name: yes"\n')
        f.write('# Reply appears in terminal\n')
        f.write('```\n')
        f.write('\n')
        f.write('See: `~/.telemux/` for configuration and logs.\n')
        f.write('\n')

    print("TeleMux documentation added to Claude config")


def main():
    """Main installer entry point."""
    print("=" * 60)
    print("TeleMux Installation")
    print("=" * 60)
    print("")

    # Check prerequisites
    if not check_prerequisites():
        sys.exit(1)

    # Get Telegram credentials
    print("=== Telegram Configuration ===")
    print("")
    bot_token = input("Enter your Telegram Bot Token: ").strip()

    # Test bot token and fetch chats
    print("")
    print("Testing bot token and fetching available chats...")
    bot_info = get_bot_info(bot_token)

    if not bot_info:
        print("ERROR: Invalid bot token. Please check and try again.")
        sys.exit(1)

    bot_name = bot_info.get("first_name", "Unknown")
    print(f"Bot token valid: {bot_name}")
    print("")

    # Get chat ID (with retry logic)
    chat_id = get_chat_id_interactive(bot_token)

    if not chat_id:
        print("ERROR: Chat ID is required")
        sys.exit(1)

    # Create TeleMux directory structure
    print("")
    print("Creating ~/.telemux directory...")
    ensure_directories()
    print("Directory structure created")
    print("")

    # Save configuration
    print("Creating ~/.telemux/telegram_config...")
    save_config(bot_token, chat_id)
    print("Config file created and secured")
    print("")

    # Detect shell and install functions
    shell_name = os.environ.get('SHELL', '').split('/')[-1]
    if shell_name == 'zsh':
        shell_rc = Path.home() / ".zshrc"
    elif shell_name == 'bash':
        shell_rc = Path.home() / ".bashrc"
    else:
        print("WARNING: Could not detect shell (bash/zsh). Unsupported shell.")
        print("   Please manually add functions to your rc file.")
        print("   See shell_functions.sh in ~/.telemux/")
        shell_rc = None

    if shell_rc:
        install_shell_functions(shell_rc)
        print("")

    # Test installation
    print("=== Testing Installation ===")
    if not test_telegram_connection(bot_token, chat_id):
        sys.exit(1)

    print("")
    print("=" * 60)
    print("Installation Complete!")
    print("=" * 60)
    print("")
    print("Next steps:")
    if shell_rc:
        print(f"  1. Reload your shell: source {shell_rc}")
    print("  2. Start the listener: telemux-start (or tg-start)")
    print("")
    print("For full documentation, visit: https://github.com/malmazan/telemux")
    print("")

    # Optional: Update Claude config
    update_claude_config()


if __name__ == "__main__":
    main()
