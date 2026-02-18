"""
Main CLI entry point for TeleMux
"""

import sys
from . import control, __version__


def main():
    """Main CLI dispatcher."""
    if len(sys.argv) < 2:
        print("TeleMux - Bidirectional Telegram Integration for tmux")
        print("")
        print("Usage: telemux <command>")
        print("")
        print("Commands:")
        print("  install  - Run interactive installer")
        print("  start    - Start the listener daemon")
        print("  stop     - Stop the listener daemon")
        print("  restart  - Restart the listener daemon")
        print("  status   - Check if listener is running")
        print("  logs     - Tail the log file")
        print("  attach   - Attach to the listener tmux session")
        print("  cleanup  - Rotate and clean up log files")
        print("  doctor   - Run health check and diagnose issues")
        print("  version  - Show version information")
        print("")
        print("Shell Functions (available after installation):")
        print("  tg_alert \"message\"         - Send notification to Telegram")
        print("  tg_agent \"name\" \"message\"  - Send message and receive replies")
        print("  tg_done                     - Alert when previous command completes")
        print("")
        print("Shortcuts:")
        print("  tg-start, tg-stop, tg-status, tg-logs")
        print("")
        print("Examples:")
        print("  telemux install              # Run installer")
        print("  telemux start                # Start listener")
        print("  telemux --version            # Show version")
        print("  tg_alert \"Build complete\"    # Send notification")
        print("")
        print("Documentation: https://github.com/malmazan/telemux")
        sys.exit(0)

    command = sys.argv[1]

    # Handle version flags
    if command in ["--version", "-v", "version"]:
        print(f"telemux {__version__}")
        sys.exit(0)
    elif command == "install":
        from .installer import main as installer_main
        installer_main()
    elif command == "start":
        control.start()
    elif command == "stop":
        control.stop()
    elif command == "restart":
        control.restart()
    elif command == "status":
        control.status()
    elif command == "logs":
        control.logs()
    elif command == "attach":
        control.attach()
    elif command == "cleanup":
        from .cleanup import main as cleanup_main
        cleanup_main()
    elif command == "doctor":
        control.doctor()
    elif command in ["-h", "--help", "help"]:
        # Remove command argument and show help
        sys.argv.pop(1)
        main()
    else:
        print(f"Unknown command: {command}")
        print("Run 'telemux' with no arguments for usage information")
        sys.exit(1)


if __name__ == "__main__":
    main()
