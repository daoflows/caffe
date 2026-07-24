#!/bin/bash
set -e

PASS=0
FAIL=0
SKIP=0
RESULTS=()

pass_test() {
    echo "[PASS] $1"
    RESULTS+=("[PASS] $1")
    PASS=$((PASS + 1))
}

fail_test() {
    echo "[FAIL] $1: $2"
    RESULTS+=("[FAIL] $1: $2")
    FAIL=$((FAIL + 1))
}

skip_test() {
    echo "[SKIP] $1: $2"
    RESULTS+=("[SKIP] $1: $2")
    SKIP=$((SKIP + 1))
}

echo "=========================================="
echo " python-module 综合测试套件"
echo "=========================================="

# Test 1: Environment
echo ""
echo "--- 1. Environment Check ---"
python_version=$(python --version 2>&1)
pass_test "Python version: $python_version"

if python -c "import numpy" 2>/dev/null; then
    np_ver=$(python -c "import numpy; print(numpy.__version__)")
    pass_test "NumPy version: $np_ver"
else
    fail_test "NumPy import" "NumPy not available"
fi

if python -c "import google.protobuf" 2>/dev/null; then
    pb_ver=$(python -c "import google.protobuf; print(google.protobuf.__version__)")
    pass_test "Protobuf version: $pb_ver"
else
    fail_test "Protobuf import" "Protobuf not available"
fi

# Test 2: Core imports
echo ""
echo "--- 2. Core Module Imports ---"
if python -c "import caffe; print(caffe.__version__)" 2>/dev/null; then
    caffe_ver=$(python -c "import caffe; print(caffe.__version__)")
    pass_test "caffe import (v$caffe_ver)"
else
    fail_test "caffe import" "Failed to import caffe"
fi

if python -c "from caffeproto import caffe_pb2" 2>/dev/null; then
    pass_test "caffeproto.caffe_pb2 import"
else
    fail_test "caffeproto.caffe_pb2 import" "Failed"
fi

if python -c "from caffeproto.caffe_utils import unity_struct" 2>/dev/null; then
    pass_test "caffe_utils import"
else
    fail_test "caffe_utils import" "Failed"
fi

if python -c "from caffeproto.caffe_fuse import fuse_bn_scale" 2>/dev/null; then
    pass_test "caffe_fuse import"
else
    fail_test "caffe_fuse import" "Failed"
fi

# Test 3: Protobuf functionality
echo ""
echo "--- 3. Protobuf Functionality ---"
python -c "
from caffeproto import caffe_pb2
from google.protobuf import text_format

# Create network
net = caffe_pb2.NetParameter()
net.name = 'test_network'
net.input.append('data')
net.input_dim.extend([1, 3, 32, 32])

# Add Conv layer
conv = net.layer.add()
conv.name = 'conv1'
conv.type = 'Convolution'
conv.bottom.append('data')
conv.top.append('conv1')
conv.convolution_param.num_output = 32
conv.convolution_param.kernel_size.append(5)

# Add ReLU
relu = net.layer.add()
relu.name = 'relu1'
relu.type = 'ReLU'
relu.bottom.append('conv1')
relu.top.append('conv1')

# Serialization test
binary = net.SerializeToString()
net2 = caffe_pb2.NetParameter()
net2.ParseFromString(binary)
assert net2.name == net.name
assert len(net2.layer) == 2

# Text format test
text = text_format.MessageToString(net)
net3 = caffe_pb2.NetParameter()
text_format.Parse(text, net3)
assert net3.name == net.name
print('OK')
" 2>/dev/null && pass_test "Protobuf serialization/deserialization" || fail_test "Protobuf serialization" "Failed"

# Test 4: caffe_utils
echo ""
echo "--- 4. caffe_utils Functions ---"
python -c "
import numpy as np
from caffeproto import caffe_pb2
from caffeproto.caffe_utils import unity_struct, unity_inputs, convert_num_to_name

net = caffe_pb2.NetParameter()
net.name = 'test'
net.input.append('data')
net.input_dim.extend([1, 3, 32, 32])

# Add layers
for i in range(2):
    l = net.layer.add()
    l.name = f'layer{i}'
    l.type = 'Convolution'
    l.bottom.append('data' if i == 0 else 'layer0')
    l.top.append(f'layer{i}')
    l.convolution_param.num_output = 16
    l.convolution_param.kernel_size.append(3)

net = unity_struct(net)
assert len(net.layer) >= 2
print('OK')
" 2>/dev/null && pass_test "caffe_utils unity_struct" || fail_test "caffe_utils unity_struct" "Failed"

# Test 5: BN-Scale Fusion
echo ""
echo "--- 5. BN-Scale Fusion ---"
python -c "
import numpy as np
from caffeproto import caffe_pb2
from caffeproto.caffe_fuse import fuse_bn_scale

net = caffe_pb2.NetParameter()
net.name = 'bn_test'

# Conv-BN-Scale-ReLU chain
conv = net.layer.add()
conv.name = 'conv1'
conv.type = 'Convolution'
conv.bottom.append('data')
conv.top.append('conv1')
conv.convolution_param.num_output = 16
conv.convolution_param.kernel_size.append(3)

bn = net.layer.add()
bn.name = 'bn1'
bn.type = 'BatchNorm'
bn.bottom.append('conv1')
bn.top.append('conv1')

scale = net.layer.add()
scale.name = 'scale1'
scale.type = 'Scale'
scale.bottom.append('conv1')
scale.top.append('conv1')
scale.scale_param.bias_term = True

relu = net.layer.add()
relu.name = 'relu1'
relu.type = 'ReLU'
relu.bottom.append('conv1')
relu.top.append('conv1')

fused = fuse_bn_scale(net)
has_bn = any(l.type == 'BatchNorm' for l in fused.layer)
has_scale = any(l.type == 'Scale' for l in fused.layer)
assert not has_bn and not has_scale
print('OK')
" 2>/dev/null && pass_test "BN-Scale fusion" || fail_test "BN-Scale fusion" "Failed"

# Test 6: Blob operations
echo ""
echo "--- 6. Blob Operations ---"
python -c "
import numpy as np
import caffe

blob = caffe.Blob([2, 3, 4, 5])
assert blob.data.shape == (2, 3, 4, 5)

test_data = np.random.randn(2, 3, 4, 5).astype(np.float32)
blob.data[...] = test_data
assert np.allclose(blob.data, test_data)

test_diff = np.random.randn(2, 3, 4, 5).astype(np.float32)
blob.diff[...] = test_diff
assert np.allclose(blob.diff, test_diff)

print('OK')
" 2>/dev/null && pass_test "Blob data/diff operations" || fail_test "Blob operations" "Failed"

# Test 7: Caffe Net API
echo ""
echo "--- 7. Net API ---"
python -c "
import caffe
# Test that Net class is available and can be inspected
print(type(caffe.Net))
assert hasattr(caffe.Net, '__init__')
print('OK')
" 2>/dev/null && pass_test "caffe.Net class available" || fail_test "caffe.Net" "Failed"

# Test 8: Solver API
echo ""
echo "--- 8. Solver API ---"
python -c "
import caffe
assert hasattr(caffe, 'SGDSolver')
assert hasattr(caffe, 'AdamSolver')
print('OK')
" 2>/dev/null && pass_test "Solver classes available" || fail_test "Solver API" "Failed"

# Test 9: TVM-dependent features
echo ""
echo "--- 9. TVM Integration ---"
if python -c "import tvm" 2>/dev/null; then
    python -c "
from operators.layers import L2Norm
print('OK')
" 2>/dev/null && pass_test "TVM L2Norm operator" || fail_test "TVM L2Norm" "Failed"
else
    skip_test "TVM operators" "TVM not installed in this image (expected)"
fi

# Test 10: caffe.io utilities
echo ""
echo "--- 10. IO Utilities ---"
python -c "
import caffe.io
# Check that IO functions exist
assert hasattr(caffe.io, 'load_image')
assert hasattr(caffe.io, 'Transformer')
print('OK')
" 2>/dev/null && pass_test "caffe.io module" || fail_test "caffe.io" "Failed"

# Test 11: Python path configuration
echo ""
echo "--- 11. Python Path ---"
python -c "
import sys
paths = [p for p in sys.path if 'caffe' in p or 'workspace' in p]
print('Caffe-related paths:', paths)
assert '/workspace/caffex/python' in sys.path
assert '/workspace/python' in sys.path
print('OK')
" 2>/dev/null && pass_test "PYTHONPATH configured correctly" || fail_test "PYTHONPATH" "Incorrect"

# Test 12: Library loading
echo ""
echo "--- 12. Shared Library Loading ---"
python -c "
import caffe
# Check that _caffe.so is loaded (the C++ extension)
assert hasattr(caffe, '_caffe') or hasattr(caffe, 'Net')
print('OK')
" 2>/dev/null && pass_test "C++ extension loaded" || fail_test "C++ extension" "Failed to load _caffe.so"

# Summary
echo ""
echo "=========================================="
echo " 测试结果汇总"
echo "=========================================="
echo ""
for r in "${RESULTS[@]}"; do
    echo "  $r"
done
echo ""
echo "  通过: $PASS"
echo "  失败: $FAIL"
echo "  跳过: $SKIP"
echo "  总计: $((PASS + FAIL + SKIP))"
echo ""
echo "=========================================="

if [ $FAIL -gt 0 ]; then
    echo " 状态: 存在失败测试"
    exit 1
else
    echo " 状态: 所有关键测试通过"
    exit 0
fi
