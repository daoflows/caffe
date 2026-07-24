#!/bin/bash
set -e
CAFFE_PY=/mnt/d/spaces/SpecWeave/external/chaos/caffe/python
BUILD_DIR=$CAFFE_PY/build

echo "=== Cleaning build ==="
rm -rf $BUILD_DIR
mkdir -p $BUILD_DIR
cd $BUILD_DIR

echo "=== CMake configure ==="
cmake .. -G Ninja -DCMAKE_BUILD_TYPE=Release 2>&1

echo ""
echo "=== Building (ninja) ==="
ninja -j$(nproc) 2>&1

echo ""
echo "=== Build artifacts ==="
ls -la $BUILD_DIR/lib/
echo ""
ls -la $BUILD_DIR/python/caffe/
echo ""
ls -la $BUILD_DIR/tests/

echo ""
echo "=== Running unit tests ==="
export LD_LIBRARY_PATH=$BUILD_DIR/lib:$LD_LIBRARY_PATH
cd $BUILD_DIR/tests
./test_caffe_slim $CAFFE_PY/tests 2>&1
