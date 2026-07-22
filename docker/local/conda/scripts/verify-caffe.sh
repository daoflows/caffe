#!/bin/bash
set -e

echo "========================================"
echo "  Verifying Caffe Installation"
echo "========================================"

CAFFE_ROOT="${CAFFE_ROOT:-/workspace/caffex}"
export LD_LIBRARY_PATH="${CAFFE_ROOT}/build/lib:${LD_LIBRARY_PATH:-}"
export PYTHONPATH="${CAFFE_ROOT}/python:${PYTHONPATH:-}"

echo ""
echo "=== Environment ==="
echo "CAFFE_ROOT: ${CAFFE_ROOT}"
echo "Python: $(python3 --version)"

echo ""
echo "=== Checking Caffe Library Files ==="
ls -lh ${CAFFE_ROOT}/build/lib/libcaffe.so* 2>/dev/null || true
ls -lh ${CAFFE_ROOT}/python/caffe/_caffe*.so 2>/dev/null || true

echo ""
echo "=== Checking Core Python Dependencies ==="
python3 -c "import numpy; print('  numpy:', numpy.__version__)"
python3 -c "import scipy; print('  scipy:', scipy.__version__)"
python3 -c "import google.protobuf; print('  protobuf:', google.protobuf.__version__)"

echo ""
echo "=== Testing Caffe Import ==="
python3 -c "
import sys
sys.path.insert(0, '${CAFFE_ROOT}/python')
import caffe
print('  Caffe imported successfully!')
print('  Caffe version:', caffe.__version__)
print('  Net class:', caffe.Net)
print('  SGDSolver:', caffe.SGDSolver)
print('  set_mode_cpu:', caffe.set_mode_cpu)
"

echo ""
echo "=== Checking Caffe Proto ==="
python3 -c "
import sys
sys.path.insert(0, '${CAFFE_ROOT}/python')
from caffe.proto import caffe_pb2
print('  caffe_pb2 imported successfully')
print('  NetParameter:', caffe_pb2.NetParameter)
print('  BlobProto:', caffe_pb2.BlobProto)
"

echo ""
echo "=== Checking Caffe Tools ==="
for tool in caffe compute_image_mean convert_imageset upgrade_net_proto_text; do
    TOOL_PATH="${CAFFE_ROOT}/build/tools/${tool}"
    if [ -x "${TOOL_PATH}" ]; then
        echo "  [OK] ${tool}"
    else
        echo "  [--] ${tool}: not found"
    fi
done

echo ""
echo "========================================"
echo "  Verification Complete!"
echo "========================================"
