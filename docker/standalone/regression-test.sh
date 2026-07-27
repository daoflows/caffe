#!/bin/bash
set -euo pipefail

# ==============================================================================
# Caffe Standalone 一键回归测试脚本
# 用法：cd /path/to/vendor && bash caffe/docker/standalone/regression-test.sh
# ==============================================================================

red()    { echo -e "\033[31mFAIL: $*\033[0m"; }
green()  { echo -e "\033[32mPASS: $*\033[0m"; }
yellow() { echo -e "\033[33mWARN: $*\033[0m"; }
blue()   { echo -e "\033[34m==> $*\033[0m"; }

PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0

pass() { green "$1"; PASS_COUNT=$((PASS_COUNT+1)); }
fail() { red "$1"; FAIL_COUNT=$((FAIL_COUNT+1)); }
warn() { yellow "$1"; WARN_COUNT=$((WARN_COUNT+1)); }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENDOR_DIR="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
cd "${VENDOR_DIR}"

blue "Caffe Standalone Regression Test"
blue "Working directory: ${VENDOR_DIR}"
echo ""

# --- T1: 源码检查 ---
blue "Phase 1: Source & Config Check"

if grep -rn "caffex" caffe/docker/standalone/ --include="Dockerfile*" --include="*.sh" \
   | grep -v "不依赖 caffex" | grep -v "Parity check not applicable" | grep -v "caffex/、" | grep -v "for full BVLC" >/dev/null; then
    fail "Found unexpected caffex references"
    grep -rn "caffex" caffe/docker/standalone/ --include="Dockerfile*" --include="*.sh" | grep -v "不依赖\|Parity check not applicable\|caffex/、\|for full BVLC"
else
    pass "No functional caffex references"
fi

if grep -q "tvm-ffi/3rdparty/libbacktrace/$" .dockerignore; then
    fail ".dockerignore excludes entire libbacktrace directory"
else
    pass ".dockerignore does not over-exclude libbacktrace"
fi

bash -n caffe/docker/standalone/pycaffe/scripts/verify-pycaffe.sh && pass "verify-pycaffe.sh syntax OK" || fail "verify-pycaffe.sh syntax error"
bash -n caffe/docker/standalone/pycaffe/scripts/verify-parity.sh && pass "verify-parity.sh syntax OK" || fail "verify-parity.sh syntax error"

echo ""

# --- T2: 构建测试 ---
blue "Phase 2: Build Test"

blue "Building pycaffe image..."
if docker build -t caffe-cpu:regression-pycaffe --target runtime \
     --no-cache -f caffe/docker/standalone/pycaffe/Dockerfile . >/tmp/reg-build-pycaffe.log 2>&1; then
    pass "pycaffe image built successfully"
else
    fail "pycaffe image build failed (see /tmp/reg-build-pycaffe.log)"
    tail -30 /tmp/reg-build-pycaffe.log
fi

echo ""

# --- T3: 运行时功能测试 ---
blue "Phase 3: Runtime Function Test"

docker rm -f reg-pycaffe 2>/dev/null || true
docker run -d --name reg-pycaffe caffe-cpu:regression-pycaffe sleep infinity >/dev/null
sleep 2

VERIFY_OUT=$(docker exec reg-pycaffe verify-pycaffe.sh 2>&1)
VERIFY_EXIT=$?
echo "${VERIFY_OUT}"
if [ ${VERIFY_EXIT} -eq 0 ]; then
    pass "verify-pycaffe.sh exit code 0"
else
    fail "verify-pycaffe.sh exit code ${VERIFY_EXIT}"
fi

P=$(echo "${VERIFY_OUT}" | grep -oP '\d+(?= PASS)' || echo "0")
F=$(echo "${VERIFY_OUT}" | grep -oP '\d+(?= FAIL)' || echo "0")
W=$(echo "${VERIFY_OUT}" | grep -oP '\d+(?= WARN)' || echo "0")
echo "  Results: ${P} PASS / ${F} FAIL / ${W} WARN"
if [ "${F}" -gt 0 ]; then
    fail "Verification has ${F} FAIL(s)"
else
    pass "All core tests passed (${P} PASS, ${W} WARN)"
fi

if docker exec reg-pycaffe python -c "
import pycaffe, numpy
assert pycaffe.__version__ == '1.0.0-slim'
assert int(numpy.__version__.split('.')[0]) >= 2
pycaffe.set_mode_cpu()
net = pycaffe.Net('/workspace/pycaffe/lenet_deploy.prototxt', pycaffe.TEST)
net.forward()
print('Core inference OK')
" 2>/dev/null; then
    pass "Python core inference test passed"
else
    fail "Python core inference test failed"
fi

echo ""

# --- T4: 隔离性验证 ---
blue "Phase 4: Isolation Test"

CAFFEX_FILES=$(docker exec reg-pycaffe bash -c "find / -name '*caffex*' -type f 2>/dev/null | wc -l")
if [ "${CAFFEX_FILES}" -eq 0 ]; then
    pass "No caffex files in container"
else
    fail "Found ${CAFFEX_FILES} caffex file(s) in container"
fi

echo ""

# --- Cleanup ---
blue "Cleanup"
docker rm -f reg-pycaffe 2>/dev/null || true

# --- Summary ---
echo ""
echo "=============================================="
echo "  Regression Test Summary"
echo "=============================================="
echo "  PASS: ${PASS_COUNT}"
echo "  FAIL: ${FAIL_COUNT}"
echo "  WARN: ${WARN_COUNT}"
echo "=============================================="

if [ "${FAIL_COUNT}" -gt 0 ]; then
    red "REGRESSION TEST FAILED"
    exit 1
else
    green "REGRESSION TEST PASSED"
    exit 0
fi
