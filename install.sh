#!/bin/bash

# Exit on error
set -e

echo "========================================"
echo "  Wan2.2 Installation Script"
echo "========================================"
echo ""

# Check if Wan2.2 directory exists
if [ ! -d "Wan2.2" ]; then
    echo "ERROR: Wan2.2 directory not found!"
    echo "Please run this script from the repository root."
    exit 1
fi

# Navigate to Wan2.2 directory
cd Wan2.2

# Step 1: Create requirements without flash_attn
echo "[1/8] Creating requirements file without flash_attn..."
grep -vE '^\s*flash_attn\s*$' requirements.txt > requirements.noflash.txt
echo "      ✓ requirements.noflash.txt created"
echo ""

# Step 2: Install base requirements
echo "[2/8] Installing base requirements..."
echo "      This may take several minutes..."
pip install -r requirements.noflash.txt
echo "      ✓ Base requirements installed"
echo ""

# Step 3: Verify torch installation
echo "[3/8] Verifying PyTorch installation..."
python - <<'PY'
import torch
print("      Torch version:", torch.__version__)
print("      CUDA available:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("      GPU:", torch.cuda.get_device_name(0))
else:
    print("      WARNING: CUDA is not available, running on CPU")
PY
echo "      ✓ PyTorch verified"
echo ""

# Step 4: Install flash_attn with no-build-isolation
echo "[4/8] Installing flash_attn..."
echo "      This step may take 10-20 minutes"
echo "      Using MAX_JOBS=4 to limit CPU/memory usage"
MAX_JOBS=4 pip install flash-attn --no-build-isolation
echo "      ✓ flash_attn installed"
echo ""

# Step 5: Install additional requirements
echo "[5/8] Installing additional requirements (requirements_s2v.txt)..."
pip install -r requirements_s2v.txt
echo "      ✓ Additional requirements installed"
echo ""

# Step 6: Install peft related dependencies
echo "[6/8] Installing peft and related dependencies..."
pip install peft
pip install accelerate transformers sentencepiece einops safetensors
pip install -U transformers peft accelerate safetensors einops sentencepiece
echo "      ✓ peft dependencies installed"
echo ""

# Step 7: Download model from Hugging Face
echo "[7/8] Downloading Wan2.2-TI2V-5B model from Hugging Face..."
echo "      This may take a long time depending on network speed"
pip install "huggingface_hub[cli]"
huggingface-cli download Wan-AI/Wan2.2-TI2V-5B --local-dir ./Wan2.2-TI2V-5B
echo "      ✓ Model downloaded to Wan2.2/Wan2.2-TI2V-5B"
echo ""

# Step 8: Create inputs folder
echo "[8/8] Creating inputs folder..."
mkdir -p inputs
echo "      ✓ inputs folder created"
echo ""

# Cleanup
echo "Cleaning up temporary files..."
rm -f requirements.noflash.txt
echo "      ✓ Cleanup complete"
echo ""

echo "========================================"
echo "  Installation Complete!"
echo "========================================"
echo ""
echo "Model location: Wan2.2/Wan2.2-TI2V-5B"
echo "Inputs folder:  Wan2.2/inputs"
echo ""
echo "To use the model, navigate to the Wan2.2 directory:"
echo "  cd Wan2.2"
echo "  python generate.py"
echo ""
