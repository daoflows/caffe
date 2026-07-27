#!/bin/bash
set -e

SRC_DIR="/opt/caffe-examples"
DEST_DIR="/workspace/notebooks"

echo "[caffe-customer] Preparing example notebooks..."
mkdir -p "${DEST_DIR}"

for f in "${SRC_DIR}"/*.ipynb; do
    if [ -f "$f" ]; then
        fname="$(basename "$f")"
        if [ ! -f "${DEST_DIR}/${fname}" ]; then
            cp "$f" "${DEST_DIR}/"
            echo "[caffe-customer] Copied ${fname} -> ${DEST_DIR}/"
        else
            echo "[caffe-customer] ${fname} already exists, skipping"
        fi
    fi
done

chown -R caffe-origin:caffe-origin "${DEST_DIR}" 2>/dev/null || true

echo "[caffe-customer] Starting Caffe Jupyter services..."
exec /usr/local/bin/entrypoint-jupyter.sh "$@"
