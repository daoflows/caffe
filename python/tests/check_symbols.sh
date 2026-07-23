#!/bin/bash
set -e
BUILD_DIR=/mnt/d/spaces/SpecWeave/external/chaos/caffe/python/build
CAFFE_SO=$BUILD_DIR/python/caffe/_caffe.so
LIBTVM_FFI=$BUILD_DIR/lib/libtvm_ffi.so

echo "=== Build outputs ==="
ls -la $BUILD_DIR/lib/
echo ""
ls -la $BUILD_DIR/python/caffe/
echo ""

echo "=== _caffe.so dependencies ==="
ldd $CAFFE_SO
echo ""

echo "=== libtvm_ffi.so exists? ==="
ls -la $LIBTVM_FFI
echo ""

echo "=== Exported functions in _caffe.so (C ABI) ==="
nm -D $CAFFE_SO | grep -E " (T|t) " | grep -viE "(_ZN|_ZTV|_ZNK|_ZThn|__cxa|__gxx|_Jv)" | head -60
