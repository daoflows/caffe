#!/bin/bash
set -e
CAFFE_PY=/mnt/d/spaces/SpecWeave/external/chaos/caffe/python
BUILD_DIR=$CAFFE_PY/build

echo "=== Cleaning and rebuilding ==="
rm -rf $BUILD_DIR
mkdir -p $BUILD_DIR
cd $BUILD_DIR
cmake .. -G Ninja -DCMAKE_BUILD_TYPE=Release 2>&1 | tail -15
echo ""
ninja -j$(nproc) 2>&1

echo ""
echo "=== Running unit tests ==="
export LD_LIBRARY_PATH=$BUILD_DIR/lib:$LD_LIBRARY_PATH
cd $BUILD_DIR/tests
./test_caffe_slim $CAFFE_PY/tests 2>&1
