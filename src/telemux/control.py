"""
Control commands for TeleMux listener daemon
"""

import sys
import time
import subprocess
import requests
from pathlib import Path

from . import TELEMUX_DIR, LOG_FILE, TMUX_SESSION
from .config import load_config


def is_listener_running() -> bool:
    """Check if the listener tmux session is running."""
    try:
        result = subprocess.run(
            ['tmux', 'has-session', '-t', TMUX_SESSION],
            capture_output=True,
            check=False
        )
        return result.returncode == 0
    except FileNotFoundError:
        print("Error: tmux is not installed")
        sys.exit(1)


def start():
    """Start the Telegram listener daemon."""
    if is_listener_running():
        print("Telegram listener is already running")
        print(f"   Use: telemux-status")
        sys.exit(1)

    print("Starting Telegram listener...")

    # Start tmux session with the listener module
    # Use -m flag to run as module, which handles imports correctly
    subprocess.run(
        ['tmux', 'new-session', '-d', '-s', TMUX_SESSION, 'python3', '-m', 'telemux.listener'],
        check=False
    )
    time.sleep(1)

    if is_listener_running():
        print("Telegram listener started successfully")
        print(f"   Session: {TMUX_SESSION}")
        print(f"   Log: {LOG_FILE}")
        print("")
        print("Commands:")
        print("   telemux-status   - Check status")
        print("   telemux-logs     - View logs")
        print("   telemux-attach   - Attach to session")
        print("   telemux-stop     - Stop listener")
    else:
        print("Failed to start listener")
        sys.exit(1)


def stop():
    """Stop the Telegram listener daemon."""
    if not is_listener_running():
        print("Telegram listener is not running")
        sys.exit(0)

    print("Stopping Telegram listener...")
    subprocess.run(['tmux', 'kill-session', '-t', TMUX_SESSION], check=False)
    print("Telegram listener stopped")


def restart():
    """Restart the Telegram listener daemon."""
    stop()
    time.sleep(2)
    start()


def status():
    """Check the status of the listener daemon."""
    if is_listener_running():
        print("Telegram listener is RUNNING")
        print(f"   Session: {TMUX_SESSION}")
        print(f"   Log: {LOG_FILE}")
        print("")
        print("Recent activity:")

        if LOG_FILE.exists():
            try:
                with open(LOG_FILE, 'r') as f:
                    lines = f.readlines()
                    recent = lines[-10:] if len(lines) >= 10 else lines
                    for line in recent:
                        print(line.rstrip())
            except Exception as e:
                print(f"Error reading log: {e}")
        else:
            print("No logs yet")
    else:
        print("Telegram listener is NOT running")
        print("   Start with: telemux-start")


def logs():
    """Tail the log file."""
    if LOG_FILE.exists():
        try:
            subprocess.run(['tail', '-f', str(LOG_FILE)])
        except KeyboardInterrupt:
            print("\nLog streaming stopped")
    else:
        print(f"No log file found at {LOG_FILE}")


def attach():
    """Attach to the listener tmux session."""
    if is_listener_running():
        subprocess.run(['tmux', 'attach-session', '-t', TMUX_SESSION])
    else:
        print("Telegram listener is not running")
        sys.exit(1)


def doctor():
    """Run health check and diagnose issues."""
    print("TeleMux Health Check")
    print("=" * 60)
    print("")

    # Check tmux
    print("Checking tmux...")
    try:
        result = subprocess.run(['tmux', '-V'], capture_output=True, text=True, check=False)
        if result.returncode == 0:
            print(f"   tmux is installed ({result.stdout.strip()})")
        else:
            print("   tmux is NOT installed")
    except FileNotFoundError:
        print("   tmux is NOT installed")
    print("")

    # Check Python
    print("Checking Python...")
    result = subprocess.run(['python3', '--version'], capture_output=True, text=True, check=False)
    if result.returncode == 0:
        print(f"   Python is installed ({result.stdout.strip()})")
    else:
        print("   Python3 is NOT installed")
    print("")

    # Check dependencies
    print("Checking Python dependencies...")
    try:
        import requests
        print(f"   requests library is installed (v{requests.__version__})")
    except ImportError:
        print("   requests library is NOT installed")
        print("   Install with: pip install telemux")
    print("")

    # Check config file
    print("Checking configuration...")
    from . import CONFIG_FILE
    if CONFIG_FILE.exists():
        print(f"   Config file exists: {CONFIG_FILE}")

        # Check permissions
        import stat
        perms = oct(CONFIG_FILE.stat().st_mode)[-3:]
        if perms == "600":
            print(f"   Config file permissions are secure (600)")
        else:
            print(f"   Config file permissions: {perms} (should be 600)")
            print(f"   Fix with: chmod 600 {CONFIG_FILE}")

        # Check if credentials are set
        bot_token, chat_id = load_config()
        if bot_token:
            print("   Bot token is set")
        else:
            print("   Bot token is NOT set")

        if chat_id:
            print("   Chat ID is set")
            # Validate format
            if chat_id.lstrip('-').isdigit():
                if chat_id.startswith('-'):
                    print(f"   (Group chat: {chat_id})")
                else:
                    print(f"   (Personal chat: {chat_id})")
            else:
                print("   Chat ID format may be invalid")
        else:
            print("   Chat ID is NOT set")
    else:
        print(f"   Config file NOT found: {CONFIG_FILE}")
        print("   Run: telemux-install")
    print("")

    # Test bot connection
    print("Testing Telegram bot connection...")
    bot_token, chat_id = load_config()
    if bot_token:
        try:
            response = requests.get(f"https://api.telegram.org/bot{bot_token}/getMe", timeout=10)
            data = response.json()
            if data.get("ok"):
                bot_name = data["result"].get("first_name", "")
                bot_username = data["result"].get("username", "")
                print("   Bot connection successful!")
                print(f"   Bot name: {bot_name}")
                print(f"   Username: @{bot_username}")
            else:
                print("   Bot connection failed")
                print(f"   Response: {data}")
                print("   Check your bot token")
        except Exception as e:
            print(f"   Connection failed: {e}")
    else:
        print("   Skipping (no bot token configured)")
    print("")

    # Check listener process
    print("Checking listener daemon...")
    if is_listener_running():
        print(f"   Listener is RUNNING (session: {TMUX_SESSION})")
    else:
        print("   Listener is NOT running")
        print("   Start with: telemux-start")
    print("")

    # Check log files
    print("Checking log files...")
    if LOG_FILE.exists():
        size = LOG_FILE.stat().st_size
        size_mb = size / (1024 * 1024)
        with open(LOG_FILE, 'r') as f:
            line_count = sum(1 for _ in f)
        print(f"   Listener log exists: {LOG_FILE}")
        print(f"   Size: {size_mb:.2f} MB ({line_count} lines)")
    else:
        print("   No listener log file yet")

    from . import MESSAGE_QUEUE_DIR
    outgoing_log = MESSAGE_QUEUE_DIR / "outgoing.log"
    if outgoing_log.exists():
        with open(outgoing_log, 'r') as f:
            count = sum(1 for _ in f)
        print(f"   Outgoing message log exists ({count} messages)")
    else:
        print("   No outgoing messages yet")

    incoming_log = MESSAGE_QUEUE_DIR / "incoming.log"
    if incoming_log.exists():
        with open(incoming_log, 'r') as f:
            count = sum(1 for _ in f)
        print(f"   Incoming message log exists ({count} messages)")
    else:
        print("   No incoming messages yet")
    print("")

    # Summary
    print("=" * 60)
    print("Health Check Complete")
    print("=" * 60)


def main():
    """Main control CLI entry point."""
    if len(sys.argv) < 2:
        print("TeleMux Control")
        print("")
        print(f"Usage: telemux <command>")
        print("")
        print("Commands:")
        print("  start    - Start the listener daemon")
        print("  stop     - Stop the listener daemon")
        print("  restart  - Restart the listener daemon")
        print("  status   - Check if listener is running")
        print("  logs     - Tail the log file")
        print("  attach   - Attach to the tmux session")
        print("  doctor   - Run health check and diagnose issues")
        print("")
        print("You can also use:")
        print("  telemux-start, telemux-stop, telemux-status, telemux-logs, etc.")
        sys.exit(1)

    command = sys.argv[1]
    if command == "start":
        start()
    elif command == "stop":
        stop()
    elif command == "restart":
        restart()
    elif command == "status":
        status()
    elif command == "logs":
        logs()
    elif command == "attach":
        attach()
    elif command == "doctor":
        doctor()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
