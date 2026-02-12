#!/bin/bash
# Download SenseVoice model script
# Downloads the stable 2024-07-17 int8 model (228MB)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
MODEL_DIR="$PROJECT_ROOT/PythonService/runtime/models/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17"

MODEL_URL="https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17.tar.bz2"
ARCHIVE_NAME="sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17.tar.bz2"

echo "📦 SenseVoice Model Download Script"
echo "================================"
echo ""
echo "This will download:"
echo "  - SenseVoice Small (int8 quantized)"
echo "  - Size: ~228MB"
echo "  - Languages: Chinese, English, Japanese, Korean, Cantonese"
echo "  - Latency: ~70ms for 10 seconds of audio"
echo ""
read -p "Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled"
    exit 0
fi

# Create model directory
mkdir -p "$MODEL_DIR"

# Check if already downloaded
if [ -f "$MODEL_DIR/model.int8.onnx" ]; then
    echo "✅ Model already exists at: $MODEL_DIR"
    read -p "Re-download? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Using existing model"
        exit 0
    fi
    rm -rf "$MODEL_DIR"
    mkdir -p "$MODEL_DIR"
fi

# Download
echo "📥 Downloading from GitHub..."
echo ""

TMP_FILE="/tmp/$ARCHIVE_NAME"

if command -v curl &> /dev/null; then
    curl -L -o "$TMP_FILE" "$MODEL_URL" --progress-bar
elif command -v wget &> /dev/null; then
    wget -O "$TMP_FILE" "$MODEL_URL" --show-progress
else
    echo "❌ Neither curl nor wget found"
    exit 1
fi

# Extract
echo ""
echo "📂 Extracting to: $MODEL_DIR"
echo ""

if command -v pbzip2 &> /dev/null; then
    # Use pbzip2 for faster extraction
    tar -xjf "$TMP_FILE" -C "$(dirname "$MODEL_DIR")"
else
    # Fallback to standard tar
    tar -xf "$TMP_FILE" -C "$(dirname "$MODEL_DIR")"
fi

# Cleanup
rm -f "$TMP_FILE"

# Verify
if [ -f "$MODEL_DIR/model.int8.onnx" ] && [ -f "$MODEL_DIR/tokens.txt" ]; then
    echo ""
    echo "✅ Download successful!"
    echo ""
    echo "Model files:"
    ls -lh "$MODEL_DIR"
    echo ""
    echo "Total size:"
    du -sh "$MODEL_DIR"
else
    echo ""
    echo "❌ Download incomplete - missing files"
    exit 1
fi

echo ""
echo "🚀 Next steps:"
echo "   1. Install sherpa-onnx: uv add sherpa-onnx"
echo "   2. Set MODEL_TYPE='sensevoice' in src/asr/__init__.py"
echo "   3. Restart backend: cd PythonService && ./start.sh"
echo ""
