#!/bin/bash

# Exit on error
set -e

echo "========================================"
echo "  Wan2.2 I2V-A14B Installation Script"
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
    print("      GPU Memory:", torch.cuda.get_device_properties(0).total_memory / 1024**3, "GB")
else:
    print("      WARNING: CUDA is not available, running on CPU")
PY
echo "      ✓ PyTorch verified"
echo ""

# Step 4: Install flash_attn with no-build-isolation
echo "[4/8] Installing flash_attn..."
echo "      ⚠️  IMPORTANT: This step takes 10-20 minutes!"
echo "      You will see compilation progress like [2/73], [3/73], etc."
echo "      Please be patient and DO NOT interrupt (Ctrl+C)"
echo ""
echo "      Using MAX_JOBS=16 for faster compilation"
echo "      Starting compilation... (grab a coffee ☕)"
echo ""
MAX_JOBS=16 pip install flash-attn --no-build-isolation
echo ""
echo "      ✓ flash_attn installed successfully!"
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

# Step 7: Download I2V-A14B model from Hugging Face
echo "[7/8] Downloading Wan2.2-I2V-A14B model from Hugging Face..."
echo "      This may take a long time depending on network speed"
echo "      Model size: ~27GB (14B active parameters)"
pip install "huggingface_hub[cli]"
huggingface-cli download Wan-AI/Wan2.2-I2V-A14B --local-dir ../Wan2.2-I2V-A14B
echo "      ✓ Model downloaded to Wan2.2-I2V-A14B"
echo ""

# Step 8: Create inputs folder
echo "[8/9] Creating inputs folder..."
mkdir -p inputs
echo "      ✓ inputs folder created"
echo ""

# Return to project root
cd ..

# Step 9: Install worker dependencies
echo "[9/9] Installing worker dependencies..."
pip install -r worker_requirements.txt
echo "      ✓ Worker dependencies installed"
echo ""

# Cleanup
echo "Cleaning up temporary files..."
rm -f Wan2.2/requirements.noflash.txt
echo "      ✓ Cleanup complete"
echo ""

echo "========================================"
echo "  Installation Complete!"
echo "========================================"
echo ""
echo "Model:               Wan2.2-I2V-A14B (14B Image-to-Video)"
echo "Model location:      Wan2.2-I2V-A14B/"
echo "Inputs folder:       Wan2.2/inputs"
echo "Worker config:       worker/config_14B.yaml"
echo ""
echo "GPU Requirements:    80GB+ VRAM recommended"
echo "                     (A100, H100, or equivalent)"
echo ""
echo "Next steps:"
echo "  1. Edit worker/config_14B.yaml with your Vercel API settings"
echo "  2. Run the worker: bash run_worker_14B.sh"
echo ""
