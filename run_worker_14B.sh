#!/bin/bash

# Wan Worker Runner - 14B Version
# This script runs the worker with I2V-A14B model configuration

echo "========================================"
echo "  Wan Worker Runner - I2V-A14B (14B)"
echo "========================================"
echo ""

# Check if 14B config exists
if [ ! -f "worker/config_14B.yaml" ]; then
    echo "ERROR: worker/config_14B.yaml not found!"
    echo "Please create config file first"
    exit 1
fi

# Check if model exists
if [ ! -d "Wan2.2-I2V-A14B" ]; then
    echo "ERROR: Wan2.2-I2V-A14B model not found!"
    echo "Please run: bash install_14B.sh"
    exit 1
fi

echo "Configuration: worker/config_14B.yaml"
echo "Model: Wan2.2-I2V-A14B"
echo ""
echo "Starting worker..."
echo "Press Ctrl+C to stop"
echo ""

# Run worker with 14B config and auto-restart
while true; do
    python worker/worker.py worker/config_14B.yaml

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
