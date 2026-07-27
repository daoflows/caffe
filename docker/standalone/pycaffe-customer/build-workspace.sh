#!/bin/bash
set -e

CAFFE_ROOT="/mnt/d/spaces/SpecWeave/projects/xuanspace/vendor/caffe"

# Clean up old containers and images
docker rm -f caffe-test caffe-ws-builder 2>/dev/null || true
docker rmi caffe-cpu:customer-workspace 2>/dev/null || true

# Create temp build directory
TMPDIR=$(mktemp -d)
echo "Temp build dir: $TMPDIR"

# Helper: copy a directory while excluding junk
copy_dir() {
    local src="$1"
    local dst="$2"
    local name="$3"
    echo "Copying $name: $src -> $dst"
    mkdir -p "$dst"
    cp -r "$src"/. "$dst"/
    # Remove junk files
    find "$dst" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find "$dst" -type d -name ".ipynb_checkpoints" -exec rm -rf {} + 2>/dev/null || true
    find "$dst" -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
    find "$dst" -type f -name "*.pyc" -delete 2>/dev/null || true
    find "$dst" -type f -name ".gitkeep" -delete 2>/dev/null || true
    find "$dst" -type d -name "build" -exec rm -rf {} + 2>/dev/null || true
}

# Create Dockerfile
cat > "$TMPDIR/Dockerfile" << 'DOCKERFILE'
FROM caffe-cpu:customer
USER root

# Fix /home/builder ownership (base image incorrectly sets it to ubuntu:ubuntu)
RUN chown -R builder:builder /home/builder && \
    mkdir -p /home/builder/.local/share/jupyter/runtime && \
    chown -R builder:builder /home/builder/.local

# Copy user workspace (Jupyter notebooks, demo models/scripts)
COPY workspace/ /workspace/user-data/

# Copy project test suites
COPY tests/ /workspace/tests/
COPY caffe-slim-tests/ /workspace/caffe-slim-tests/

# Set permissions for all copied content
RUN chown -R builder:builder /workspace/user-data /workspace/tests /workspace/caffe-slim-tests

WORKDIR /workspace
DOCKERFILE

# Copy source directories into build context
copy_dir "$CAFFE_ROOT/workspace"         "$TMPDIR/workspace"         "workspace (notebooks & demos)"
copy_dir "$CAFFE_ROOT/tests"             "$TMPDIR/tests"             "tests (project test suites)"
copy_dir "$CAFFE_ROOT/caffe-slim/tests"  "$TMPDIR/caffe-slim-tests"  "caffe-slim/tests"

echo ""
echo "=== Build context summary ==="
echo "workspace/user-data/:"
ls -la "$TMPDIR/workspace/"
echo ""
echo "workspace/tests/:"
ls -la "$TMPDIR/tests/"
echo ""
echo "workspace/tests/ops/:"
ls -la "$TMPDIR/tests/ops/"
echo ""
echo "workspace/caffe-slim-tests/:"
ls -la "$TMPDIR/caffe-slim-tests/"

# Build image
cd "$TMPDIR"
docker build -t caffe-cpu:customer-workspace .

# Cleanup
rm -rf "$TMPDIR"

echo ""
echo "Build complete! Image info:"
docker images caffe-cpu:customer-workspace --format 'table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedSince}}'
echo ""
echo "Container layout:"
echo "  /workspace/user-data/         - Jupyter notebooks, caffe_demo models"
echo "  /workspace/tests/             - Project tests (ops/, scripts/, caffex/, etc.)"
echo "  /workspace/caffe-slim-tests/  - caffe-slim built-in tests"
