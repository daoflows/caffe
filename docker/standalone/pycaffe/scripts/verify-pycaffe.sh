#!/bin/bash
# ==============================================================================
# PyCaffe 验证脚本
# 验证 pycaffe 导入、版本、常量、类以及核心推理功能的可用性
# 适配 caffe-slim 推理-only 版本：训练相关 Solver 和辅助子模块不可用时标记 WARN
# ==============================================================================
set -uo pipefail

PASS=0
FAIL=0
SKIP=0
WARN=0

red()    { echo -e "\033[31m$*\033[0m"; }
green()  { echo -e "\033[32m$*\033[0m"; }
yellow() { echo -e "\033[33m$*\033[0m"; }
blue()   { echo -e "\033[34m$*\033[0m"; }

pass_msg() { green "  [PASS] $1"; PASS=$((PASS + 1)); }
fail_msg() { red   "  [FAIL] $1"; FAIL=$((FAIL + 1)); }
skip_msg() { yellow "  [SKIP] $1"; SKIP=$((SKIP + 1)); }
warn_msg() { yellow "  [WARN] $1"; WARN=$((WARN + 1)); }

echo "=============================================="
echo "  PyCaffe Verification Suite (slim inference)"
echo "=============================================="
echo ""

# -------------------------------------------------------------------
# 1. 验证 pycaffe 导入和版本（核心 - 必须通过）
# -------------------------------------------------------------------
blue "--- 1. PyCaffe Import & Version ---"

if python -c "import pycaffe" 2>/dev/null; then
    pass_msg "import pycaffe succeeded"

    VERSION=$(python -c "import pycaffe; print(pycaffe.__version__)" 2>/dev/null)
    if [ -n "${VERSION}" ]; then
        pass_msg "pycaffe.__version__ = ${VERSION}"
    else
        warn_msg "pycaffe.__version__ is empty or not defined"
    fi
else
    fail_msg "import pycaffe failed"
fi

# -------------------------------------------------------------------
# 2. 验证 pycaffe.TRAIN 和 pycaffe.TEST 常量（核心 - 必须通过）
# -------------------------------------------------------------------
blue "--- 2. Phase Constants (TRAIN / TEST) ---"

TRAIN_VAL=$(python -c "import pycaffe; print(pycaffe.TRAIN)" 2>/dev/null)
if [ -n "${TRAIN_VAL}" ]; then
    pass_msg "pycaffe.TRAIN = ${TRAIN_VAL}"
else
    fail_msg "pycaffe.TRAIN not available"
fi

TEST_VAL=$(python -c "import pycaffe; print(pycaffe.TEST)" 2>/dev/null)
if [ -n "${TEST_VAL}" ]; then
    pass_msg "pycaffe.TEST = ${TEST_VAL}"
else
    fail_msg "pycaffe.TEST not available"
fi

# -------------------------------------------------------------------
# 3. 验证 pycaffe.Net 类可用（核心 - 必须通过）
# -------------------------------------------------------------------
blue "--- 3. Net Class ---"

if python -c "from pycaffe import Net; print('Net class available')" 2>/dev/null; then
    pass_msg "pycaffe.Net class available"
else
    fail_msg "pycaffe.Net class not available"
fi

# -------------------------------------------------------------------
# 4. 验证 pycaffe.set_mode_cpu 可用（核心 - 必须通过）
# -------------------------------------------------------------------
blue "--- 4. set_mode_cpu ---"

if python -c "import pycaffe; pycaffe.set_mode_cpu(); print('set_mode_cpu OK')" 2>/dev/null; then
    pass_msg "pycaffe.set_mode_cpu() succeeded"
else
    fail_msg "pycaffe.set_mode_cpu() failed"
fi

# -------------------------------------------------------------------
# 5. LeNet 前向传播测试（核心 - 推理功能验证）
# -------------------------------------------------------------------
blue "--- 5. LeNet Forward Pass ---"

LENET_PROTO="${WORKSPACE_DIR:-/workspace}/pycaffe/lenet_deploy.prototxt"
if [ -f "${LENET_PROTO}" ]; then
    if python -c "
import pycaffe
pycaffe.set_mode_cpu()
net = pycaffe.Net('${LENET_PROTO}', pycaffe.TEST)
print('Net created successfully')
out = net.forward()
if out:
    print('Forward pass OK, output keys:', sorted(out.keys()))
else:
    print('Forward pass returned empty, but no error')
" 2>/dev/null; then
        pass_msg "LeNet Net creation and forward pass succeeded"
    else
        fail_msg "LeNet Net creation or forward pass failed"
    fi
else
    skip_msg "LeNet deploy prototxt not found at ${LENET_PROTO}"
fi

# -------------------------------------------------------------------
# 6. 验证 pycaffe 各子模块（辅助功能 - 不可用时 WARN 不阻断）
# -------------------------------------------------------------------
blue "--- 6. Submodules (auxiliary, non-blocking) ---"

SUBMODULES=(
    "classifier"
    "detector"
    "draw"
    "io"
    "net_spec"
    "coord_map"
)

for submod in "${SUBMODULES[@]}"; do
    if [ "${submod}" = "draw" ]; then
        if python -c "import pydotplus" 2>/dev/null; then
            if python -c "import pycaffe.${submod}; print('${submod} OK')" 2>/dev/null; then
                pass_msg "pycaffe.${submod} import succeeded"
            else
                warn_msg "pycaffe.${submod} import failed (optional)"
            fi
        else
            skip_msg "pycaffe.${submod} skipped (pydotplus not installed)"
        fi
    elif python -c "import pycaffe.${submod}; print('${submod} OK')" 2>/dev/null; then
        pass_msg "pycaffe.${submod} import succeeded"
    else
        warn_msg "pycaffe.${submod} not available (slim build, optional auxiliary module)"
    fi
done

# -------------------------------------------------------------------
# 7. 验证 pycaffe Solver 类（训练用 - slim 版本不可用时 SKIP）
# -------------------------------------------------------------------
blue "--- 7. Solver Classes (training, optional for slim inference) ---"

SOLVER_CLASSES=("SGDSolver" "AdamSolver" "NesterovSolver" "AdaGradSolver" "RMSPropSolver" "AdaDeltaSolver")
for solver_cls in "${SOLVER_CLASSES[@]}"; do
    if python -c "from pycaffe import ${solver_cls}; print('${solver_cls} available')" 2>/dev/null; then
        pass_msg "pycaffe.${solver_cls} class available"
    else
        warn_msg "pycaffe.${solver_cls} not available (slim inference-only build)"
    fi
done

# -------------------------------------------------------------------
# 总结
# -------------------------------------------------------------------
echo ""
echo "=============================================="
TOTAL=$((PASS + FAIL + SKIP + WARN))
echo "  Results: ${PASS} PASS / ${FAIL} FAIL / ${WARN} WARN / ${SKIP} SKIP (${TOTAL} total)"
echo "=============================================="

if [ "${FAIL}" -gt 0 ]; then
    red "  Verification FAILED: ${FAIL} core test(s) failed"
    exit 1
else
    green "  Verification PASSED: all core inference tests passed"
    if [ "${WARN}" -gt 0 ]; then
        yellow "  (${WARN} optional feature warnings - expected for slim inference-only build)"
    fi
    exit 0
fi
