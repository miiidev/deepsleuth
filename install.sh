#!/usr/bin/env bash
set -euo pipefail

SCRIPT_VERSION="1.0"
WEIGHTS_URL="https://github.com/miiidev/deepsleuth/releases/download/v${SCRIPT_VERSION}/weights-v${SCRIPT_VERSION}.zip"
WEIGHTS_DIR="weights"
MIN_PYTHON="3.11"
MIN_NODE="18"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

err()  { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }
info() { echo -e "${GREEN}[$1/6]${NC} $2"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }

ver_ge() {
    [ "$(printf '%s\n' "$1" "$2" | sort -V | head -n1)" = "$2" ]
}

check_python() {
    local cmd py_ver
    for cmd in python3 python; do
        if command -v "$cmd" &>/dev/null; then
            py_ver="$($cmd --version 2>&1 | grep -oP '\d+\.\d+')"
            if ver_ge "$py_ver" "$MIN_PYTHON"; then
                PYTHON="$cmd"
                echo "$py_ver"
                return 0
            fi
        fi
    done
    err "Python $MIN_PYTHON+ not found. Install from https://python.org"
}

check_node() {
    local node_ver
    if command -v node &>/dev/null; then
        node_ver="$(node --version | grep -oP '\d+' | head -1)"
        if [ "$node_ver" -ge "$MIN_NODE" ] 2>/dev/null; then
            echo "$(node --version)"
            return 0
        fi
    fi
    err "Node.js $MIN_NODE+ not found. Install from https://nodejs.org"
}

check_cuda() {
    if command -v nvidia-smi &>/dev/null; then
        local cuda_ver
        cuda_ver="$(nvidia-smi --query-gpu=driver_version --format=csv,noheader 2>/dev/null | head -1)"
        if [ -n "$cuda_ver" ]; then
            echo "found (driver $cuda_ver)"
            HAS_CUDA=1
            return 0
        fi
    fi
    echo "not detected (CPU-only mode)"
    HAS_CUDA=0
}

step1_prereqs() {
    info 1 "Checking prerequisites..."
    local py_ver node_ver cuda_status
    py_ver=$(check_python)
    node_ver=$(check_node)
    cuda_status=$(check_cuda)
    echo "  Python : $py_ver"
    echo "  Node   : $node_ver"
    echo "  CUDA   : $cuda_status"
}

step2_venv() {
    info 2 "Creating virtual environment..."
    if [ -d ".venv" ]; then
        echo "  .venv already exists, skipping."
        return 0
    fi
    "$PYTHON" -m venv .venv
    echo "  Virtual environment created."
}

activate_venv() {
    # shellcheck disable=SC1091
    source .venv/bin/activate
}

step3_deps() {
    info 3 "Installing dependencies..."
    activate_venv
    pip install --upgrade pip -q

    if [ "$HAS_CUDA" -eq 1 ]; then
        echo "  Installing PyTorch with CUDA support..."
        pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
    else
        echo "  Installing CPU-only PyTorch..."
        pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
    fi

    echo "  Installing remaining packages..."
    pip install -e .
}

step4_weights() {
    info 4 "Downloading model weights..."
    if [ -f "$WEIGHTS_DIR/xception_best.pth" ] && [ -f "$WEIGHTS_DIR/face_landmarker.task" ] && [ -s "$WEIGHTS_DIR/xception_best.pth" ] && [ -s "$WEIGHTS_DIR/face_landmarker.task" ]; then
        echo "  Weights already present, skipping."
        return 0
    fi
    mkdir -p "$WEIGHTS_DIR"
    local tmpzip
    tmpzip=$(mktemp)
    echo "  Downloading from $WEIGHTS_URL"
    curl -L --progress-bar -o "$tmpzip" "$WEIGHTS_URL"
    unzip -o -q "$tmpzip" -d "$WEIGHTS_DIR"
    rm -f "$tmpzip"
    echo "  Weights extracted to $WEIGHTS_DIR/"
}

step5_frontend() {
    info 5 "Building frontend..."
    if [ ! -d "frontend" ]; then
        warn "frontend/ directory not found, skipping frontend build."
        return 0
    fi
    cd frontend
    npm install --silent
    npm run build
    cd ..
    echo "  Frontend built."
}

step6_done() {
    info 6 "Installation complete!"
    echo ""
    echo -e "${BOLD}DeepSleuth installed successfully!${NC}"
    echo ""
    echo "  Run:  deepsleuth"
    echo "  Or:   python -m backend.cli"
    echo ""
    echo "  Open http://127.0.0.1:8000 in your browser."
}

main() {
    echo "DeepSleuth Installer v${SCRIPT_VERSION}"
    echo "================================"
    echo ""

    step1_prereqs
    step2_venv
    step3_deps
    step4_weights
    step5_frontend
    step6_done
}

main "$@"
