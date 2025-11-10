"""
TeleMux Log Rotation and Cleanup
Automatically rotates large log files and archives old data
"""

import sys
import gzip
import shutil
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

from . import TELEMUX_DIR, MESSAGE_QUEUE_DIR, LOG_FILE


# Configuration
MAX_SIZE_MB = 10
MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024


def log_info(message: str):
    """Print info message."""
    print(f"✓ {message}")


def log_warning(message: str):
    """Print warning message."""
    print(f"⚠ {message}")


def rotate_log(log_file: Path):
    """Rotate a log file if it exceeds size limit."""
    if not log_file.exists():
        return

    file_size = log_file.stat().st_size

    if file_size > MAX_SIZE_BYTES:
        # Create archive directory
        archive_month = datetime.now().strftime("%Y-%m")
        archive_dir = MESSAGE_QUEUE_DIR / "archive" / archive_month
        archive_dir.mkdir(parents=True, exist_ok=True)

        # Create archive filename
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        archive_file = archive_dir / f"{log_file.name}.{timestamp}"

        size_mb = file_size / (1024 * 1024)
        log_warning(f"Rotating {log_file.name} ({size_mb:.2f}MB > {MAX_SIZE_MB}MB)")

        # Move to archive
        shutil.move(str(log_file), str(archive_file))

        # Compress archive
        with open(archive_file, 'rb') as f_in:
            with gzip.open(str(archive_file) + '.gz', 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)

        # Remove uncompressed archive
        archive_file.unlink()

        # Create new empty log file
        log_file.touch()

        log_info(f"Archived to {archive_file}.gz")
    else:
        size_mb = file_size / (1024 * 1024)
        log_info(f"{log_file.name} is {size_mb:.2f}MB (under {MAX_SIZE_MB}MB limit)")


def cleanup_old_archives():
    """Remove archives older than 6 months."""
    archive_base = MESSAGE_QUEUE_DIR / "archive"
    if not archive_base.exists():
        return

    # Calculate cutoff date (6 months ago)
    cutoff_date = datetime.now() - timedelta(days=180)
    cutoff_str = cutoff_date.strftime("%Y-%m")

    # Find and remove old archives
    removed_count = 0
    for archive_dir in archive_base.iterdir():
        if archive_dir.is_dir() and archive_dir.name < cutoff_str:
            log_warning(f"Removing {archive_dir.name}")
            shutil.rmtree(archive_dir)
            removed_count += 1

    if removed_count > 0:
        print("")


def install_cron():
    """Install cron job for monthly log rotation."""
    print("")
    print("Installing cron job for monthly log rotation...")

    # Get the path to this script
    import telemux.cleanup
    cleanup_path = telemux.cleanup.__file__

    cron_cmd = f"0 0 1 * * python3 -m telemux.cleanup"

    try:
        # Get current crontab
        result = subprocess.run(
            ['crontab', '-l'],
            capture_output=True,
            text=True,
            check=False
        )

        # Filter out existing cleanup entries
        existing_lines = []
        if result.returncode == 0:
            existing_lines = [
                line for line in result.stdout.splitlines()
                if 'telemux' not in line.lower() and 'cleanup' not in line.lower()
            ]

        # Add new cron job
        new_crontab = '\n'.join(existing_lines + [cron_cmd]) + '\n'

        # Install new crontab
        subprocess.run(
            ['crontab', '-'],
            input=new_crontab,
            text=True,
            check=True
        )

        log_info("Cron job installed (runs 1st of each month at midnight)")
        print("To remove: crontab -e")

    except subprocess.CalledProcessError as e:
        print(f"Failed to install cron job: {e}")
    except FileNotFoundError:
        print("crontab command not found (cron may not be available)")


def main():
    """Main cleanup entry point."""
    print("TeleMux Log Rotation")
    print("=" * 60)
    print("")

    # Log files to rotate
    outgoing_log = MESSAGE_QUEUE_DIR / "outgoing.log"
    incoming_log = MESSAGE_QUEUE_DIR / "incoming.log"

    # Rotate logs if they exceed size limit
    rotate_log(outgoing_log)
    rotate_log(incoming_log)
    rotate_log(LOG_FILE)

    print("")

    # Clean up old archives
    cleanup_old_archives()

    # Summary
    print("Summary")
    print("-" * 60)

    archive_dir = MESSAGE_QUEUE_DIR / "archive"
    if archive_dir.exists():
        # Count archived files
        archive_count = sum(1 for _ in archive_dir.rglob("*.gz"))

        # Calculate total size
        total_size = sum(f.stat().st_size for f in archive_dir.rglob("*.gz"))
        size_mb = total_size / (1024 * 1024)

        print(f"Archive directory: {archive_dir}")
        print(f"Archived files: {archive_count}")
        print(f"Total archive size: {size_mb:.2f} MB")
    else:
        print("No archives yet")

    print("")
    log_info("Log rotation complete!")

    # Optional: Install cron job
    if len(sys.argv) > 1 and sys.argv[1] == "--install-cron":
        install_cron()


if __name__ == "__main__":
    main()
