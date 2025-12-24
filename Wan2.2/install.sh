#!/bin/bash

# Exit on error
set -e

echo "========================================"
echo "Wan2.2 Installation Script"
echo "========================================"
echo ""

# Step 1: Create requirements without flash_attn
echo "[1/8] Creating requirements file without flash_attn..."
grep -vE '^\s*flash_attn\s*$' requirements.txt > requirements.noflash.txt
echo "[1/8] DONE - requirements.noflash.txt created"
echo ""

# Step 2: Install base requirements
echo "[2/8] Installing base requirements (this may take several minutes)..."
pip install -r requirements.noflash.txt
echo "[2/8] DONE - Base requirements installed"
echo ""

# Step 3: Verify torch installation
echo "[3/8] Verifying torch installation..."
python - <<'PY'
import torch
print("Torch version:", torch.__version__)
print("CUDA available:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))
else:
    print("WARNING: CUDA is not available, running on CPU")
PY
echo "[3/8] DONE - Torch verified"
echo ""

# Step 4: Install flash_attn with no-build-isolation
echo "[4/8] Installing flash_attn with --no-build-isolation..."
echo "This step may take 10-20 minutes and will use significant CPU/memory"
MAX_JOBS=4 pip install flash-attn --no-build-isolation
echo "[4/8] DONE - flash_attn installed"
echo ""

# Step 5: Install additional requirements
echo "[5/8] Installing additional requirements (requirements_s2v.txt)..."
pip install -r requirements_s2v.txt
echo "[5/8] DONE - Additional requirements installed"
echo ""

# Step 6: Install peft related dependencies
echo "[6/8] Installing peft related dependencies..."
pip install peft
pip install accelerate transformers sentencepiece einops safetensors
pip install -U transformers peft accelerate safetensors einops sentencepiece
echo "[6/8] DONE - peft dependencies installed"
echo ""

# Step 7: Download model from Hugging Face
echo "[7/8] Downloading Wan2.2-TI2V-5B model from Hugging Face..."
echo "This may take a long time depending on network speed"
pip install "huggingface_hub[cli]"
huggingface-cli download Wan-AI/Wan2.2-TI2V-5B --local-dir ./Wan2.2-TI2V-5B
echo "[7/8] DONE - Model downloaded to ./Wan2.2-TI2V-5B"
echo ""

# Step 8: Create inputs folder
echo "[8/8] Creating inputs folder..."
mkdir -p inputs
echo "[8/8] DONE - inputs folder created"
echo ""

# Cleanup
echo "Cleaning up temporary files..."
rm -f requirements.noflash.txt
echo ""

echo "========================================"
echo "Installation completed successfully!"
echo "========================================"
echo "Model location: ./Wan2.2-TI2V-5B"
echo "Inputs folder: ./inputs"
