#!/bin/bash
# Run batch_inference_demo.py in WSL with correct environment
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
export PYTHONPATH="$HOME/.local/lib/python3.12/site-packages:$SCRIPT_DIR/python:$PYTHONPATH"
cd "$SCRIPT_DIR"
exec /usr/bin/python3 batch_inference_demo.py "$@"
