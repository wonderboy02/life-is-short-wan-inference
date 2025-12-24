#!/bin/bash

# Exit on error
set -e

echo "========================================"
echo "  Wan2.2 Setup and Run"
echo "========================================"
echo ""

# Step 1: Run installation
echo "Starting installation..."
bash install.sh

# Step 2: Run worker (only if installation succeeded)
echo ""
echo "Installation complete! Starting worker..."
echo ""
bash run_worker.sh
