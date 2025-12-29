#!/bin/bash

# Exit on error
set -e

echo "========================================"
echo "  Wan2.2 I2V-A14B Setup and Run"
echo "========================================"
echo ""

# Step 1: Run installation
echo "Starting I2V-A14B installation..."
bash install_14B.sh

# Step 2: Run worker (only if installation succeeded)
echo ""
echo "Installation complete! Starting worker with I2V-A14B..."
echo ""
bash run_worker_14B.sh
