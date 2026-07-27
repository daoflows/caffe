#!/usr/bin/env bash
# ==============================================================================
# PyCaffe Customer - One-click Build & Export (Bash/WSL/Linux)
# Builds the Docker image and automatically exports as .tar / .tar.gz
#
# Usage:
#   ./build-and-export.sh                     # Build + export (default: .tar)
#   ./build-and-export.sh -z                  # Build + gzip compress (.tar.gz)
#   ./build-and-export.sh --china             # Use China mirrors
#   ./build-and-export.sh -t v1.0.0 -z        # Custom tag + compression
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"

# Forward all arguments to build.sh first, then run export.sh with matching flags
# Parse key flags to pass through to export.sh
TAG="customer"
IMAGE_NAME="caffe-cpu"
VERSION="1.0.0"
COMPRESS=""
NO_CHECKSUM=""
OUTPUT_DIR=""
CHINA_FLAG=""
NO_CACHE=""
EXTRA_BUILD_ARGS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        -t)       TAG="$2"; EXTRA_BUILD_ARGS+=("$1" "$2"); shift 2 ;;
        -n)       IMAGE_NAME="$2"; EXTRA_BUILD_ARGS+=("$1" "$2"); shift 2 ;;
        --version) VERSION="$2"; EXTRA_BUILD_ARGS+=("$1" "$2"); shift 2 ;;
        -o)       OUTPUT_DIR="$2"; shift 2 ;;
        -z|--gzip) COMPRESS="-z"; shift ;;
        --no-checksum) NO_CHECKSUM="--no-checksum"; shift ;;
        --china) CHINA_FLAG="--china"; EXTRA_BUILD_ARGS+=("$1"); shift ;;
        --no-cache) NO_CACHE="--no-cache"; EXTRA_BUILD_ARGS+=("$1"); shift ;;
        --build-arg) EXTRA_BUILD_ARGS+=("$1" "$2"); shift 2 ;;
        -h|--help)
            cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Build & export PyCaffe Customer Docker image in one step.

Options:
  -t TAG               Image tag (default: customer)
  -n NAME              Image name (default: caffe-cpu)
  -o DIR               Output directory (default: ./dist)
  --version VER        Version string for filename (default: 1.0.0)
  -z, --gzip           Compress with gzip (.tar.gz)
  --no-checksum        Skip SHA256 checksum generation
  --china              Use China mirrors (Aliyun)
  --no-cache           Build without cache
  --build-arg K=V      Pass additional build argument
  -h, --help           Show this help

Examples:
  $(basename "$0")                           # Build + export as .tar
  $(basename "$0") -z                        # Build + gzip compress
  $(basename "$0") --china -z                # China mirror + gzip
  $(basename "$0") -t v1.0.0 -z --no-cache   # Clean rebuild + compress

Customer instructions after export:
  1. Load:   docker load -i caffe-cpu-customer-<version>-<date>.tar
  2. Run:    docker run -d -p 8888:8888 -p 2222:22 caffe-cpu:customer
  3. Access: http://localhost:8888/ (token: caffe-token)
  4. Verify: docker exec <container> caffe-verify
EOF
            exit 0 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

echo "========================================"
echo " Step 1/2: Building Docker image"
echo "========================================"

BUILD_ARGS=()
[[ -n "$NO_CACHE" ]] && BUILD_ARGS+=("--no-cache")
[[ -n "$CHINA_FLAG" ]] && BUILD_ARGS+=("--china")
[[ -n "$TAG" ]] && BUILD_ARGS+=("-t" "$TAG")
[[ -n "$VERSION" ]] && BUILD_ARGS+=("--version" "$VERSION")
for ba in "${EXTRA_BUILD_ARGS[@]}"; do
    BUILD_ARGS+=("$ba")
done

"${SCRIPT_DIR}/build.sh" "${BUILD_ARGS[@]}"

echo ""
echo "========================================"
echo " Step 2/2: Exporting to tarball"
echo "========================================"

EXPORT_ARGS=()
EXPORT_ARGS+=("-t" "$TAG")
EXPORT_ARGS+=("-n" "$IMAGE_NAME")
EXPORT_ARGS+=("--version" "$VERSION")
[[ -n "$OUTPUT_DIR" ]] && EXPORT_ARGS+=("-o" "$OUTPUT_DIR")
[[ -n "$COMPRESS" ]] && EXPORT_ARGS+=("$COMPRESS")
[[ -n "$NO_CHECKSUM" ]] && EXPORT_ARGS+=("$NO_CHECKSUM")

"${SCRIPT_DIR}/export.sh" "${EXPORT_ARGS[@]}"
