#!/bin/bash
# Long-Running Build with Notifications
# Example: Notify when build starts and completes

PROJECT_NAME="${1:-MyApp}"

START_TIME=$(date +%s)

# Notify build start
tg_alert "🔨 Starting build: $PROJECT_NAME"

echo "Building $PROJECT_NAME..."
echo ""

# Simulate build steps
STEPS=(
    "Installing dependencies..."
    "Compiling TypeScript..."
    "Running tests..."
    "Building production bundle..."
    "Optimizing assets..."
)

for STEP in "${STEPS[@]}"; do
    echo "$STEP"
    sleep $((RANDOM % 5 + 3))  # Random delay 3-7 seconds
    echo "  ✓ Done"
done

# Calculate duration
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
MINUTES=$((DURATION / 60))
SECONDS=$((DURATION % 60))

echo ""
echo "✅ Build complete!"

# Notify completion
if [ $MINUTES -gt 0 ]; then
    tg_alert "✅ Build complete: $PROJECT_NAME (${MINUTES}m ${SECONDS}s)"
else
    tg_alert "✅ Build complete: $PROJECT_NAME (${SECONDS}s)"
fi
