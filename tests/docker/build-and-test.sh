#!/bin/bash
# ==============================================================================
# build-and-test.sh — 一键编译 pycaffe 并运行算子测试
#
# 用法：
#   cd projects/xuanspace/vendor/caffe
#   bash tests/docker/build-and-test.sh [--no-cache] [--quick]
#
# 选项：
#   --no-cache  Docker build 不使用缓存（重新构建）
#   --quick     构建后快速验证 import（不跑全部测试）
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CAFFE_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${CAFFE_DIR}"

IMAGE_NAME="caffe-pycaffe:full"
NO_CACHE=""
QUICK_MODE=false

for arg in "$@"; do
    case $arg in
        --no-cache) NO_CACHE="--no-cache" ;;
        --quick) QUICK_MODE=true ;;
        *) echo "Unknown option: $arg"; exit 1 ;;
    esac
done

echo "========================================"
echo "  Caffe PyCaffe Full Build & Test"
echo "========================================"
echo "  Caffe dir: ${CAFFE_DIR}"
echo "  Image:     ${IMAGE_NAME}"
echo "  No cache:  ${NO_CACHE:-false}"
echo "  Quick mode: ${QUICK_MODE}"
echo ""

# Step 1: Build Docker image
echo "[1/3] Building Docker image..."
docker build ${NO_CACHE} -t "${IMAGE_NAME}" -f tests/docker/Dockerfile .
echo ""

# Step 2: Verify pycaffe import
echo "[2/3] Verifying pycaffe import..."
docker run --rm "${IMAGE_NAME}" python -c "
import caffe
from caffe import layers as L, params as P
print('Caffe version:', getattr(caffe, '__version__', 'BVLC'))
print('SGDSolver:', caffe.SGDSolver)
print('NetSpec:', caffe.NetSpec)
print('Net:', caffe.Net)
print('Pooling.MAX:', P.Pooling.MAX)
print('All core APIs available!')
"
echo ""

# Step 3: Run tests
echo "[3/3] Running operator tests..."
if [ "${QUICK_MODE}" = true ]; then
    echo "Quick mode: running import check only"
    docker run --rm -v "${CAFFE_DIR}/tests/ops:/workspace/tests" "${IMAGE_NAME}" \
        bash -c "cd /workspace/tests && python -m pytest --collect-only 2>&1 | tail -20"
else
    echo "Running full test suite with coverage..."
    docker run --rm -v "${CAFFE_DIR}/tests/ops:/workspace/tests" "${IMAGE_NAME}" \
        bash -c "
            cd /workspace/tests
            echo '=== Environment Check ==='
            python -c 'import caffe; print(\"Caffe OK\")'
            echo ''
            echo '=== Running Tests (CAFFE_LOG_LEVEL=INFO) ==='
            CAFFE_LOG_LEVEL=INFO python -m pytest -v \
                --cov=. \
                --cov-report=term-missing \
                --cov-report=html:/workspace/coverage/htmlcov \
                --cov-report=xml:/workspace/coverage/coverage.xml \
                -x 2>&1
            echo ''
            echo '=== Coverage report location: tests/coverage/ ==='
        "
    echo ""
    echo "Coverage HTML report: ${CAFFE_DIR}/tests/coverage/htmlcov/index.html"
fi

echo ""
echo "========================================"
echo "  Done!"
echo "========================================"
echo ""
echo "To enter interactive shell:"
echo "  docker run --rm -it -v ${CAFFE_DIR}/tests/ops:/workspace/tests ${IMAGE_NAME} bash"
echo ""
echo "To run tests manually:"
echo "  docker run --rm -v ${CAFFE_DIR}/tests/ops:/workspace/tests ${IMAGE_NAME} \\"
echo "    bash -c 'cd /workspace/tests && CAFFE_LOG_LEVEL=DEBUG pytest -v'"
