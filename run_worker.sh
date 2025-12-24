#!/bin/bash

# Wan Worker Simple Runner
# This script runs the worker with automatic restart on crash

echo "========================================"
echo "  Wan Worker Runner"
echo "========================================"
echo ""

# Check if config exists
if [ ! -f "worker/config.yaml" ]; then
    echo "ERROR: worker/config.yaml not found!"
    echo "Please create config file first"
    exit 1
fi

echo "Starting worker..."
echo "Press Ctrl+C to stop"
echo ""

# Run worker with auto-restart
while true; do
    python worker/worker.py

    EXIT_CODE=$?
    echo ""
    echo "Worker exited with code: $EXIT_CODE"

    # If exit code is 0 (clean shutdown), don't restart
    if [ $EXIT_CODE -eq 0 ]; then
        echo "Clean shutdown detected"
        break
    fi

    # Otherwise restart after delay
    echo "Restarting in 5 seconds..."
    sleep 5
done

echo "Worker stopped"
