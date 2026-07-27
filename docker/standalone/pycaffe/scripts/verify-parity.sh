#!/bin/bash
# ==============================================================================
# PyCaffe 验证脚本 - 独立版本
#
# 说明：本脚本为 standalone 镜像的兼容性占位脚本。
#       standalone 镜像使用 caffe-slim 进行推理，不包含完整 BVLC Caffe 训练功能，
#       因此无需与 caffex/python 进行对标验证。
# ==============================================================================
set -euo pipefail

echo "=============================================="
echo "  PyCaffe Standalone Build"
echo "=============================================="
echo ""
echo "  Parity check not applicable for slim inference-only build."
echo "  This standalone image uses caffe-slim for inference only."
echo "  For full BVLC Caffe training support, use the origin image."
echo ""
echo "=============================================="
echo "  Running basic verification instead..."
echo "=============================================="
echo ""

if command -v verify-pycaffe.sh &>/dev/null; then
    verify-pycaffe.sh
else
    echo "verify-pycaffe.sh not found, running basic import check..."
    python -c "import pycaffe; print('pycaffe version:', pycaffe.__version__)"
    echo ""
    echo "Basic verification PASSED"
fi

exit 0
