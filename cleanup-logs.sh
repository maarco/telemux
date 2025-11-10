#!/bin/bash
# TeleMux Log Rotation and Cleanup Script
# Automatically rotates large log files and archives old data

set -e

TELEMUX_DIR="$HOME/.telemux"
MESSAGE_QUEUE_DIR="$TELEMUX_DIR/message_queue"
ARCHIVE_DIR="$MESSAGE_QUEUE_DIR/archive"
OUTGOING_LOG="$MESSAGE_QUEUE_DIR/outgoing.log"
INCOMING_LOG="$MESSAGE_QUEUE_DIR/incoming.log"
LISTENER_LOG="$TELEMUX_DIR/telegram_listener.log"

# Configuration
MAX_SIZE_MB=10
MAX_SIZE_BYTES=$((MAX_SIZE_MB * 1024 * 1024))
ARCHIVE_MONTH=$(date +%Y-%m)

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Create archive directory if it doesn't exist
mkdir -p "$ARCHIVE_DIR/$ARCHIVE_MONTH"

rotate_log() {
    local log_file="$1"
    local log_name=$(basename "$log_file")

    if [ ! -f "$log_file" ]; then
        return
    fi

    local file_size=$(stat -f%z "$log_file" 2>/dev/null || stat -c%s "$log_file" 2>/dev/null)

    if [ "$file_size" -gt "$MAX_SIZE_BYTES" ]; then
        local archive_file="$ARCHIVE_DIR/$ARCHIVE_MONTH/${log_name}.$(date +%Y%m%d-%H%M%S)"

        log_warning "Rotating $log_name ($(echo "scale=2; $file_size / 1024 / 1024" | bc)MB > ${MAX_SIZE_MB}MB)"

        # Move to archive
        mv "$log_file" "$archive_file"

        # Compress archive
        gzip "$archive_file"

        # Create new empty log file
        touch "$log_file"

        log_info "Archived to ${archive_file}.gz"
    else
        local size_mb=$(echo "scale=2; $file_size / 1024 / 1024" | bc)
        log_info "$log_name is ${size_mb}MB (under ${MAX_SIZE_MB}MB limit)"
    fi
}

# Rotate logs if they exceed size limit
echo "TeleMux Log Rotation"
echo "===================="
echo ""

rotate_log "$OUTGOING_LOG"
rotate_log "$INCOMING_LOG"
rotate_log "$LISTENER_LOG"

echo ""

# Clean up old archives (keep last 6 months)
CUTOFF_DATE=$(date -d '6 months ago' +%Y-%m 2>/dev/null || date -v-6m +%Y-%m 2>/dev/null)

if [ -d "$ARCHIVE_DIR" ]; then
    OLD_ARCHIVES=$(find "$ARCHIVE_DIR" -maxdepth 1 -type d -name "????-??" | while read dir; do
        ARCHIVE_MONTH=$(basename "$dir")
        if [[ "$ARCHIVE_MONTH" < "$CUTOFF_DATE" ]]; then
            echo "$dir"
        fi
    done)

    if [ -n "$OLD_ARCHIVES" ]; then
        echo "Cleaning up old archives (older than 6 months):"
        echo "$OLD_ARCHIVES" | while read dir; do
            log_warning "Removing $(basename "$dir")"
            rm -rf "$dir"
        done
        echo ""
    fi
fi

# Summary
echo "Summary"
echo "-------"
ARCHIVE_COUNT=$(find "$ARCHIVE_DIR" -name "*.gz" 2>/dev/null | wc -l | xargs)
ARCHIVE_SIZE=$(du -sh "$ARCHIVE_DIR" 2>/dev/null | cut -f1 || echo "0B")

echo "Archive directory: $ARCHIVE_DIR"
echo "Archived files: $ARCHIVE_COUNT"
echo "Total archive size: $ARCHIVE_SIZE"
echo ""
log_info "Log rotation complete!"

# Optional: Add to crontab
if [ "$1" = "--install-cron" ]; then
    echo ""
    echo "Installing cron job for monthly log rotation..."

    CRON_CMD="0 0 1 * * $HOME/.telemux/cleanup-logs.sh"

    (crontab -l 2>/dev/null | grep -v "cleanup-logs.sh"; echo "$CRON_CMD") | crontab -

    log_info "Cron job installed (runs 1st of each month at midnight)"
    echo "To remove: crontab -e"
fi
