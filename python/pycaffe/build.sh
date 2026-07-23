#!/bin/bash
# PyCaffe Build Script
# Builds the pycaffe wheel using scikit-build-core + CMake + Ninja
#
# Prerequisites:
#   - conda environment with Python 3.9+
#   - Caffe C++ library installed (libcaffe.so)
#   - Boost.Python, protobuf, glog, gflags installed
#
# Usage:
#   chmod +x build.sh
#   ./build.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIST_DIR="${SCRIPT_DIR}/dist"

echo "=== PyCaffe Build Script ==="
echo "Working directory: ${SCRIPT_DIR}"

# Ensure pip and build tools are available
echo "[1/3] Installing build dependencies..."
pip install --quiet scikit-build-core ninja build

# Build the wheel
echo "[2/3] Building wheel..."
cd "${SCRIPT_DIR}"
python -m build --wheel --outdir "${DIST_DIR}"

# Show result
echo "[3/3] Build complete!"
echo ""
echo "Wheel file(s):"
ls -la "${DIST_DIR}"/*.whl 2>/dev/null || echo "  No wheel files found in ${DIST_DIR}"
echo ""
echo "To install: pip install ${DIST_DIR}/pycaffe-*.whl"