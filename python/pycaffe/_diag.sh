#!/bin/bash
set -e
echo "=== Check Python version and ABI ==="
ls /opt/conda/envs/pycaffe-py314/bin/python* 2>/dev/null || true
echo ""
echo "=== Python include dirs ==="
ls -la /opt/conda/envs/pycaffe-py314/include/ | grep python || true
echo ""
echo "=== Python libs ==="
ls -la /opt/conda/envs/pycaffe-py314/lib/ | grep -i python | head -20 || true
echo ""
echo "=== Check which python ==="
which python || true
echo ""
echo "=== Python version (via symlink) ==="
/opt/conda/envs/pycaffe-py314/bin/python --version 2>&1 || true
echo ""
echo "=== Check for free-threaded ==="
ls /opt/conda/envs/pycaffe-py314/lib/python3.14t/ 2>/dev/null && echo "FREE-THREADED DETECTED" || echo "No free-threaded directory"
ls /opt/conda/envs/pycaffe-py314/lib/python3.14/ 2>/dev/null | head -5 || echo "No python3.14 dir"
echo ""
echo "=== Check wheel contents ==="
ls -la /workspace/pycaffe/dist/ 2>/dev/null || true
echo ""
echo "=== Check _caffe.so links ==="
if [ -d /workspace/pycaffe/dist ]; then
    cd /tmp && cp /workspace/pycaffe/dist/*.whl . && unzip -o *.whl -d wheel_extract > /dev/null 2>&1 && \
    find wheel_extract -name "_caffe*" -exec ls -la {} \; && \
    echo "--- ldd _caffe*.so ---" && \
    find wheel_extract -name "_caffe*" -exec ldd {} \; && \
    rm -rf wheel_extract *.whl
fi
