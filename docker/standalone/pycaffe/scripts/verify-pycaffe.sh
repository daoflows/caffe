#!/bin/bash
# ==============================================================================
# PyCaffe 验证脚本
# 验证 pycaffe 导入、版本、常量、类以及各子模块的可用性
# ==============================================================================
set -euo pipefail

PASS=0
FAIL=0
SKIP=0

red()    { echo -e "\033[31m$*\033[0m"; }
green()  { echo -e "\033[32m$*\033[0m"; }
yellow() { echo -e "\033[33m$*\033[0m"; }
blue()   { echo -e "\033[34m$*\033[0m"; }

pass_msg() { green "  [PASS] $1"; PASS=$((PASS + 1)); }
fail_msg() { red   "  [FAIL] $1"; FAIL=$((FAIL + 1)); }
skip_msg() { yellow "  [SKIP] $1"; SKIP=$((SKIP + 1)); }

echo "=============================================="
echo "  PyCaffe Verification Suite"
echo "=============================================="
echo ""

# -------------------------------------------------------------------
# 1. 验证 pycaffe 导入和版本
# -------------------------------------------------------------------
blue "--- 1. PyCaffe Import & Version ---"

if python -c "import pycaffe" 2>/dev/null; then
    pass_msg "import pycaffe succeeded"

    VERSION=$(python -c "import pycaffe; print(pycaffe.__version__)" 2>/dev/null)
    if [ -n "${VERSION}" ]; then
        pass_msg "pycaffe.__version__ = ${VERSION}"
    else
        fail_msg "pycaffe.__version__ is empty or not defined"
    fi
else
    fail_msg "import pycaffe failed"
fi

# -------------------------------------------------------------------
# 2. 验证 pycaffe.TRAIN 和 pycaffe.TEST 常量
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
# 3. 验证 pycaffe.Net 类可用
# -------------------------------------------------------------------
blue "--- 3. Net Class ---"

if python -c "from pycaffe import Net; print('Net class available')" 2>/dev/null; then
    pass_msg "pycaffe.Net class available"
else
    fail_msg "pycaffe.Net class not available"
fi

# -------------------------------------------------------------------
# 4. 验证 pycaffe.set_mode_cpu 可用
# -------------------------------------------------------------------
blue "--- 4. set_mode_cpu ---"

if python -c "import pycaffe; pycaffe.set_mode_cpu(); print('set_mode_cpu OK')" 2>/dev/null; then
    pass_msg "pycaffe.set_mode_cpu() succeeded"
else
    fail_msg "pycaffe.set_mode_cpu() failed"
fi

# -------------------------------------------------------------------
# 5. LeNet 前向传播测试（如果 prototxt 存在）
# -------------------------------------------------------------------
blue "--- 5. LeNet Forward Pass ---"

LENET_PROTO="${WORKSPACE_DIR:-/workspace}/pycaffe/lenet_deploy.prototxt"
if [ -f "${LENET_PROTO}" ]; then
    if python -c "
import pycaffe
pycaffe.set_mode_cpu()
net = pycaffe.Net('${LENET_PROTO}', pycaffe.TEST)
print('Net created successfully')
# 尝试前向传播
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
# 6. 验证 pycaffe 各子模块
# -------------------------------------------------------------------
blue "--- 6. Submodules ---"

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
        # draw 需要可选的 pydotplus 依赖，未安装时跳过
        if python -c "import pydotplus" 2>/dev/null; then
            if python -c "import pycaffe.${submod}; print('${submod} OK')" 2>/dev/null; then
                pass_msg "pycaffe.${submod} import succeeded"
            else
                fail_msg "pycaffe.${submod} import failed"
            fi
        else
            skip_msg "pycaffe.${submod} skipped (pydotplus not installed, optional dependency)"
        fi
    elif python -c "import pycaffe.${submod}; print('${submod} OK')" 2>/dev/null; then
        pass_msg "pycaffe.${submod} import succeeded"
    else
        fail_msg "pycaffe.${submod} import failed"
    fi
done

# -------------------------------------------------------------------
# 7. 验证 pycaffe Solver 类（具体类型，无泛型 Solver 基类）
# -------------------------------------------------------------------
blue "--- 7. Solver Classes ---"

SOLVER_CLASSES=("SGDSolver" "AdamSolver" "NesterovSolver" "AdaGradSolver" "RMSPropSolver" "AdaDeltaSolver")
for solver_cls in "${SOLVER_CLASSES[@]}"; do
    if python -c "from pycaffe import ${solver_cls}; print('${solver_cls} available')" 2>/dev/null; then
        pass_msg "pycaffe.${solver_cls} class available"
    else
        fail_msg "pycaffe.${solver_cls} class not available"
    fi
done

# -------------------------------------------------------------------
# 总结
# -------------------------------------------------------------------
echo ""
echo "=============================================="
TOTAL=$((PASS + FAIL + SKIP))
echo "  Results: ${PASS} PASS / ${FAIL} FAIL / ${SKIP} SKIP (${TOTAL} total)"
echo "=============================================="

if [ "${FAIL}" -gt 0 ]; then
    red "  Verification FAILED: ${FAIL} test(s) failed"
    exit 1
else
    green "  Verification PASSED: all tests passed"
    exit 0
fi