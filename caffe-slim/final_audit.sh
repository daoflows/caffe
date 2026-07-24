#!/bin/bash
set -e

cd /mnt/d/spaces/SpecWeave/projects/xuanspace/vendor/caffe/python

echo "=== FINAL COMPREHENSIVE AUDIT ==="
echo ""

echo "=== 1. Checking ALL source files for boost/glog/gflags references ==="
echo "--- boost includes ---"
grep -rn "#include.*boost" include/ src/ pycaffe/ --include="*.hpp" --include="*.cpp" --include="*.h" 2>/dev/null || true
echo "boost include count: $(grep -rn "#include.*boost" include/ src/ pycaffe/ --include="*.hpp" --include="*.cpp" --include="*.h" 2>/dev/null | wc -l)"

echo ""
echo "--- boost:: namespace ---"
grep -rn "boost::" include/ src/ pycaffe/ --include="*.hpp" --include="*.cpp" --include="*.h" 2>/dev/null | grep -v "//.*boost::" | head -20 || true
echo "boost:: usage count: $(grep -rn "boost::" include/ src/ pycaffe/ --include="*.hpp" --include="*.cpp" --include="*.h" 2>/dev/null | grep -v "//.*boost::" | wc -l)"

echo ""
echo "--- glog includes ---"
grep -rn "#include.*glog" include/ src/ pycaffe/ --include="*.hpp" --include="*.cpp" --include="*.h" 2>/dev/null || true
echo "glog include count: $(grep -rn "#include.*glog" include/ src/ pycaffe/ --include="*.hpp" --include="*.cpp" --include="*.h" 2>/dev/null | wc -l)"

echo ""
echo "--- gflags includes ---"
grep -rn "#include.*gflags" include/ src/ pycaffe/ --include="*.hpp" --include="*.cpp" --include="*.h" 2>/dev/null || true
echo "gflags include count: $(grep -rn "#include.*gflags" include/ src/ pycaffe/ --include="*.hpp" --include="*.cpp" --include="*.h" 2>/dev/null | wc -l)"

echo ""
echo "--- LOG/CHECK macros from glog (should be zero outside compat layer) ---"
grep -rn "LOG(" include/ src/ pycaffe/ --include="*.hpp" --include="*.cpp" 2>/dev/null | grep -v "compat/logging.hpp" | head -10 || true
echo "LOG() usage outside compat layer: $(grep -rn "LOG(" include/ src/ pycaffe/ --include="*.hpp" --include="*.cpp" 2>/dev/null | grep -v "compat/logging.hpp" | wc -l)"

echo ""
echo "=== 2. Verifying tvm-ffi IS used ==="
echo "tvm/ffi includes:"
grep -rn "#include.*tvm/ffi" include/ src/ pycaffe/ --include="*.hpp" --include="*.cpp" 2>/dev/null || true
echo "tvm-ffi include count: $(grep -rn "#include.*tvm/ffi" include/ src/ pycaffe/ --include="*.hpp" --include="*.cpp" 2>/dev/null | wc -l)"

echo ""
echo "TVM_FFI macros used:"
grep -rn "TVM_FFI_" include/ src/ pycaffe/ --include="*.hpp" --include="*.cpp" 2>/dev/null | wc -l
echo "TVM_FFI_ macro count: $(grep -rn "TVM_FFI_" include/ src/ pycaffe/ --include="*.hpp" --include="*.cpp" 2>/dev/null | wc -l)"

echo ""
echo "=== 3. Final rebuild verification ==="
rm -rf build && mkdir -p build && cd build
cmake .. -G Ninja -DCMAKE_BUILD_TYPE=Release 2>&1 | tail -20
echo ""
echo "Building with ninja..."
ninja -j$(nproc) 2>&1 | tail -30

echo ""
echo "=== 4. Check build outputs ==="
echo "Libraries:"
ls -la lib/ 2>/dev/null || true
echo ""
echo "FFI module:"
ls -la python/caffe/ 2>/dev/null || true
echo ""
echo "Test binary:"
ls -la tests/ 2>/dev/null || true

echo ""
echo "=== 5. Run all tests ==="
ctest --output-on-failure 2>&1

echo ""
echo "=== 6. Final Python inference smoke test ==="
cd /mnt/d/spaces/SpecWeave/projects/xuanspace/vendor/caffe/python
cp build/python/caffe/_caffe.so python/caffe/ 2>/dev/null || true
export PYTHONPATH="/mnt/d/spaces/SpecWeave/projects/xuanspace/vendor/caffe/python/python:/mnt/d/spaces/SpecWeave/projects/xuanspace/vendor/tvm-ffi/python:$PYTHONPATH"
export LD_LIBRARY_PATH="/mnt/d/spaces/SpecWeave/projects/xuanspace/vendor/caffe/python/build/lib:$LD_LIBRARY_PATH"
python3 << 'PYEOF'
import numpy as np
import caffe

print("=== Final Python Verification ===")
print(f"Caffe version: {caffe.version()}")
print(f"Registered layers: {len(caffe.layer_type_list())}")

proto = '/mnt/d/spaces/SpecWeave/projects/xuanspace/vendor/caffe/python/tests/lenet_deploy.prototxt'
net = caffe.Net(proto, caffe.TEST)

rng = np.random.RandomState(42)
inp = rng.randn(*net.blob_shape('data')).astype(np.float32)
net.set_input_data('data', inp)
net.forward()

out = net.blob_data('prob')
assert out.shape == (64, 10), f"Expected (64,10), got {out.shape}"
assert (out >= 0).all(), "Probabilities must be non-negative"
assert (out <= 1).all(), "Probabilities must be <= 1"
assert np.allclose(out.sum(axis=1), 1.0), "Probabilities must sum to 1"

print(f"Output shape: {out.shape}")
print(f"Output valid: all in [0,1], sums to 1.0")
print("=== ALL CHECKS PASSED ===")
PYEOF

echo ""
echo "=== AUDIT COMPLETE ==="
