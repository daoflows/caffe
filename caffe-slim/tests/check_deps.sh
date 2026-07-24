#!/bin/bash
set -e
CAFFE_PY=/mnt/d/spaces/SpecWeave/external/chaos/caffe/python
BUILD_DIR=$CAFFE_PY/build

echo "=== Dependency Residue Check ==="
echo ""

echo "=== 1. Checking for boost #include in src/ and include/ ==="
BOOST_HITS=$(grep -rn '#include.*<boost/' $CAFFE_PY/include $CAFFE_PY/src 2>/dev/null | grep -v '.pyc' | wc -l)
echo "  boost #include count: $BOOST_HITS"
if [ "$BOOST_HITS" -gt 0 ]; then
  echo "  WARNING: residual boost includes found:"
  grep -rn '#include.*<boost/' $CAFFE_PY/include $CAFFE_PY/src 2>/dev/null | grep -v '.pyc'
else
  echo "  PASS: No boost #include found"
fi
echo ""

echo "=== 2. Checking for glog #include in src/ and include/ ==="
GLOG_HITS=$(grep -rn '#include.*<glog/' $CAFFE_PY/include $CAFFE_PY/src 2>/dev/null | grep -v '.pyc' | wc -l)
echo "  glog #include count: $GLOG_HITS"
if [ "$GLOG_HITS" -gt 0 ]; then
  echo "  WARNING: residual glog includes found:"
  grep -rn '#include.*<glog/' $CAFFE_PY/include $CAFFE_PY/src 2>/dev/null | grep -v '.pyc'
else
  echo "  PASS: No glog #include found"
fi
echo ""

echo "=== 3. Checking for gflags #include in src/ and include/ ==="
GFLAGS_HITS=$(grep -rn '#include.*<gflags/' $CAFFE_PY/include $CAFFE_PY/src 2>/dev/null | grep -v '.pyc' | wc -l)
echo "  gflags #include count: $GFLAGS_HITS"
if [ "$GFLAGS_HITS" -gt 0 ]; then
  echo "  WARNING: residual gflags includes found:"
  grep -rn '#include.*<gflags/' $CAFFE_PY/include $CAFFE_PY/src 2>/dev/null | grep -v '.pyc'
else
  echo "  PASS: No gflags #include found"
fi
echo ""

echo "=== 4. Checking for boost namespace usage in src/ and include/ ==="
BOOST_NS_HITS=$(grep -rn 'boost::' $CAFFE_PY/include $CAFFE_PY/src 2>/dev/null | grep -v '.pyc' | grep -v 'fboost' | grep -v 'reboost' | wc -l)
echo "  boost:: namespace count: $BOOST_NS_HITS"
if [ "$BOOST_NS_HITS" -gt 0 ]; then
  echo "  WARNING: residual boost:: usage found:"
  grep -rn 'boost::' $CAFFE_PY/include $CAFFE_PY/src 2>/dev/null | grep -v '.pyc' | grep -v 'fboost' | grep -v 'reboost'
else
  echo "  PASS: No boost:: namespace usage found"
fi
echo ""

echo "=== 5. Checking for LOG/DLOG from glog (LOG(INFO) etc should use compat layer) ==="
# Check that LOG is used via compat/logging.hpp, not glog
LOG_HITS=$(grep -rn '#include.*logging\.h' $CAFFE_PY/include $CAFFE_PY/src 2>/dev/null | grep -v 'compat/logging.hpp' | grep -v '.pyc' | wc -l)
echo "  Non-compat logging.h include count: $LOG_HITS"
if [ "$LOG_HITS" -gt 0 ]; then
  echo "  WARNING: non-compat logging includes found:"
  grep -rn '#include.*logging\.h' $CAFFE_PY/include $CAFFE_PY/src 2>/dev/null | grep -v 'compat/logging.hpp' | grep -v '.pyc'
else
  echo "  PASS: All logging uses compat/logging.hpp"
fi
echo ""

echo "=== 6. Dynamic library dependencies of _caffe.so ==="
echo "  _caffe.so linked libraries:"
ldd $BUILD_DIR/python/caffe/_caffe.so 2>&1 | grep -v "linux-vdso\|ld-linux" | sed 's/^/    /'
echo ""
HAS_BOOST=$(ldd $BUILD_DIR/python/caffe/_caffe.so 2>&1 | grep -c boost || true)
HAS_GLOG=$(ldd $BUILD_DIR/python/caffe/_caffe.so 2>&1 | grep -c glog || true)
HAS_GFLAGS=$(ldd $BUILD_DIR/python/caffe/_caffe.so 2>&1 | grep -c gflags || true)
echo "  linked against boost: $([ "$HAS_BOOST" -gt 0 ] && echo YES || echo NO)"
echo "  linked against glog: $([ "$HAS_GLOG" -gt 0 ] && echo YES || echo NO)"
echo "  linked against gflags: $([ "$HAS_GFLAGS" -gt 0 ] && echo YES || echo NO)"
echo ""

echo "=== 7. Dynamic library dependencies of test_caffe_slim ==="
echo "  test_caffe_slim linked libraries:"
ldd $BUILD_DIR/tests/test_caffe_slim 2>&1 | grep -v "linux-vdso\|ld-linux" | sed 's/^/    /'
echo ""
HAS_BOOST2=$(ldd $BUILD_DIR/tests/test_caffe_slim 2>&1 | grep -c boost || true)
HAS_GLOG2=$(ldd $BUILD_DIR/tests/test_caffe_slim 2>&1 | grep -c glog || true)
HAS_GFLAGS2=$(ldd $BUILD_DIR/tests/test_caffe_slim 2>&1 | grep -c gflags || true)
echo "  linked against boost: $([ "$HAS_BOOST2" -gt 0 ] && echo YES || echo NO)"
echo "  linked against glog: $([ "$HAS_GLOG2" -gt 0 ] && echo YES || echo NO)"
echo "  linked against gflags: $([ "$HAS_GFLAGS2" -gt 0 ] && echo YES || echo NO)"
echo ""

echo "=== 8. CMakeLists.txt checks ==="
CMAKE_HAS_BOOST=$(grep -c 'find_package(Boost\|boost' $CAFFE_PY/CMakeLists.txt 2>/dev/null || true)
CMAKE_HAS_GLOG=$(grep -c 'glog\|gflags' $CAFFE_PY/CMakeLists.txt 2>/dev/null || true)
echo "  CMake references to boost: $CMAKE_HAS_BOOST (expected 0)"
echo "  CMake references to glog/gflags: $CMAKE_HAS_GLOG (expected 0)"
echo ""

echo "=== Summary ==="
TOTAL_RESIDUE=$((BOOST_HITS + GLOG_HITS + GFLAGS_HITS + BOOST_NS_HITS + LOG_HITS + HAS_BOOST + HAS_GLOG + HAS_GFLAGS + HAS_BOOST2 + HAS_GLOG2 + HAS_GFLAGS2))
echo "  Total residue issues found: $TOTAL_RESIDUE"
if [ "$TOTAL_RESIDUE" -eq 0 ]; then
  echo "  *** NO RESIDUAL DEPENDENCIES - CLEAN ***"
else
  echo "  *** WARNING: Residual dependencies found ***"
fi
