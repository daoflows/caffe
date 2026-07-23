#!/usr/bin/env bash
# ============================================================================
# verify-python-module.sh — python-module Docker 镜像验证脚本
# ============================================================================
set -euo pipefail

PASS=0
FAIL=0
SKIP=0

green()  { printf '\033[32m%s\033[0m\n' "$1"; }
red()    { printf '\033[31m%s\033[0m\n' "$1"; }
yellow() { printf '\033[33m%s\033[0m\n' "$1"; }

check() {
    local desc="$1"
    shift
    printf '[TEST] %s ... ' "$desc"
    if "$@" >/dev/null 2>&1; then
        green 'PASS'
        PASS=$((PASS + 1))
    else
        red 'FAIL'
        FAIL=$((FAIL + 1))
    fi
}

check_skip() {
    local desc="$1"
    shift
    printf '[TEST] %s ... ' "$desc"
    if "$@" >/dev/null 2>&1; then
        green 'PASS'
        PASS=$((PASS + 1))
    else
        yellow 'SKIP (TVM not available)'
        SKIP=$((SKIP + 1))
    fi
}

echo '============================================'
echo ' python-module 镜像验证'
echo '============================================'
echo ''

# ---- caffe 导入 ----
check 'import caffe and print __version__' \
    python -c "import caffe; print(caffe.__version__)"

# ---- caffeproto 导入 ----
check 'from caffeproto import caffe_pb2' \
    python -c "from caffeproto import caffe_pb2; print('OK')"

# ---- operators 导入（TVM 可能不可用，失败不报错） ----
check_skip 'from operators.layers import L2Norm' \
    python -c "from operators.layers import L2Norm; print('OK')"

# ---- caffe.Net API ----
check 'caffe.Net API' \
    python -c "import caffe; print(caffe.Net)"

# ---- caffe.SGDSolver API ----
check 'caffe.SGDSolver API' \
    python -c "import caffe; print(caffe.SGDSolver)"

# ---- caffe.proto 导入 ----
check 'caffe.proto import' \
    python -c "import caffe.proto; print('OK')"

# ---- 可选：执行 run_test.sh ----
if [ -f /workspace/python/scripts/run_test.sh ]; then
    echo ''
    echo '--- 执行 run_test.sh ---'
    if bash /workspace/python/scripts/run_test.sh; then
        green 'run_test.sh PASS'
        PASS=$((PASS + 1))
    else
        red 'run_test.sh FAIL'
        FAIL=$((FAIL + 1))
    fi
fi

# ---- 汇总 ----
echo ''
echo '============================================'
printf ' 结果: %s 通过, %s 失败, %s 跳过\n' "$PASS" "$FAIL" "$SKIP"
echo '============================================'

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
exit 0