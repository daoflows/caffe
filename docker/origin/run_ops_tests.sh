#!/usr/bin/env bash
# ==============================================================================
# Caffe Docker 算子测试运行脚本 (origin)
# 功能：使用 caffe-cpu:origin-runtime 镜像运行算子测试
# 用法：./run_ops_tests.sh [选项]
# 自包含版本：不依赖 docker/local/lib 中的日志与环境检查函数
# ==============================================================================

set -euo pipefail

# ------------------------------------------------------------------------------
# 内联日志函数（自包含，不 source 外部文件）
# ------------------------------------------------------------------------------
log_info()    { echo -e "\033[34m[INFO]\033[0m $*"; }
log_success() { echo -e "\033[32m[OK]\033[0m $*"; }
log_warn()    { echo -e "\033[33m[WARN]\033[0m $*"; }
log_error()   { echo -e "\033[31m[ERROR]\033[0m $*" >&2; }
log_header()  { echo -e "\n\033[1;36m========================================\033[0m"; echo -e "\033[1;36m $* \033[0m"; echo -e "\033[1;36m========================================\033[0m"; }
log_section() { echo -e "\n\033[1;37m--- $* ---\033[0m"; }
log_kv()      { echo -e "  \033[37m$1:\033[0m $2"; }
log_blank()   { echo ""; }
log_troubleshoot() { echo -e "$*"; }

# ------------------------------------------------------------------------------
# 内联容器工具探测函数（自包含）
# ------------------------------------------------------------------------------
detect_container_tool() {
    if command -v docker &>/dev/null; then
        echo "docker"
    elif command -v wslc &>/dev/null; then
        echo "wslc"
    else
        echo ""
    fi
}

# ------------------------------------------------------------------------------
# 路径变量
# 注意：origin/run_ops_tests.sh 位于 docker/origin/ 下，项目根目录是 ../../
# ------------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd -P)"
TESTS_OPS_DIR="${PROJECT_DIR}/tests/ops"
VERIFY_SCRIPT="${SCRIPT_DIR}/scripts/verify-caffe.sh"
RESULTS_DIR="${SCRIPT_DIR}/test-results"

# ------------------------------------------------------------------------------
# 默认值
# ------------------------------------------------------------------------------
DEFAULT_IMAGE="caffe-cpu:origin-runtime"
DEFAULT_TEST_TYPE="all"

IMAGE="${DEFAULT_IMAGE}"
TEST_TYPE="${DEFAULT_TEST_TYPE}"
NO_BUILD=false

# ------------------------------------------------------------------------------
# 帮助信息
# ------------------------------------------------------------------------------
show_help() {
    cat <<EOF
用法: $(basename "$0") [选项]

使用 caffe-cpu:origin-runtime 镜像运行 Caffe 算子测试

选项:
  --test-type=TYPE   指定测试类型 (默认: ${DEFAULT_TEST_TYPE})
                     可选值: correctness, performance, memory, edge, all
  --image=IMAGE      指定自定义镜像名 (默认: ${DEFAULT_IMAGE})
  --no-build         跳过镜像存在性检查 (假设镜像已存在)
  -h, --help         显示此帮助信息

测试类型说明:
  correctness   正确性测试 (默认测试，排除 slow 标记的测试)
  performance   性能测试 (仅运行 slow 标记的测试)
  memory        内存测试 (仅运行 test_memory.py)
  edge          边界测试 (运行包含 edge 关键字的测试)
  all           运行所有测试 (包括 slow 测试)

示例:
  $(basename "$0")                                    # 运行所有测试
  $(basename "$0") --test-type=correctness            # 仅运行正确性测试
  $(basename "$0") --test-type=performance            # 仅运行性能测试
  $(basename "$0") --image=my-caffe:latest            # 使用自定义镜像
  $(basename "$0") --no-build                         # 跳过镜像检查

环境变量:
  CAFFE_TEST_DIR  测试目录 (容器内挂载点: /workspace/test-results)
EOF
}

# ------------------------------------------------------------------------------
# 参数解析
# ------------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help)
            show_help
            exit 0
            ;;
        --test-type=*)
            TEST_TYPE="${1#*=}"
            shift
            ;;
        --test-type)
            if [[ -z "${2:-}" ]]; then
                log_error "--test-type 需要指定类型参数"
                exit 1
            fi
            TEST_TYPE="$2"
            shift 2
            ;;
        --image=*)
            IMAGE="${1#*=}"
            shift
            ;;
        --image)
            if [[ -z "${2:-}" ]]; then
                log_error "--image 需要指定镜像名"
                exit 1
            fi
            IMAGE="$2"
            shift 2
            ;;
        --no-build)
            NO_BUILD=true
            shift
            ;;
        *)
            log_error "未知选项: $1"
            log_info "使用 -h 查看帮助信息"
            exit 1
            ;;
    esac
done

# ------------------------------------------------------------------------------
# 验证测试类型参数
# ------------------------------------------------------------------------------
VALID_TEST_TYPES=("correctness" "performance" "memory" "edge" "all")
TEST_TYPE_VALID=false
for valid_type in "${VALID_TEST_TYPES[@]}"; do
    if [[ "${TEST_TYPE}" == "${valid_type}" ]]; then
        TEST_TYPE_VALID=true
        break
    fi
done
if [[ "${TEST_TYPE_VALID}" == "false" ]]; then
    log_error "无效的测试类型: ${TEST_TYPE}"
    log_info "有效类型: ${VALID_TEST_TYPES[*]}"
    exit 1
fi

# ------------------------------------------------------------------------------
# 前置检查
# ------------------------------------------------------------------------------
log_header "Caffe Docker 算子测试运行 (origin)"

log_section "环境检查"
CONTAINER_TOOL=$(detect_container_tool)
if [[ -z "${CONTAINER_TOOL}" ]]; then
    log_error "未找到 docker 或 wslc 命令"
    log_troubleshoot <<'EOF'
1. 安装 Docker Desktop 并启用 WSL2 后端
2. 确认 docker --version 可以运行
3. Windows 环境推荐使用 Docker Desktop + WSL2 后端
EOF
    exit 1
fi
log_success "容器工具: ${CONTAINER_TOOL}"

if [[ "${CONTAINER_TOOL}" == "docker" ]]; then
    if ! docker info &>/dev/null; then
        log_error "Docker 已安装但未运行"
        log_troubleshoot <<'EOF'
1. 启动 Docker Desktop
2. 等待 Docker 服务就绪 (系统托盘图标变绿)
3. 运行 docker info 验证
EOF
        exit 1
    fi
    log_success "Docker 服务运行中"
fi

log_section "目录检查"
if [[ ! -d "${TESTS_OPS_DIR}" ]]; then
    log_error "测试目录不存在: ${TESTS_OPS_DIR}"
    exit 1
fi
log_success "测试目录: ${TESTS_OPS_DIR}"

if [[ ! -f "${VERIFY_SCRIPT}" ]]; then
    log_error "验证脚本不存在: ${VERIFY_SCRIPT}"
    exit 1
fi
log_success "验证脚本: ${VERIFY_SCRIPT}"

log_section "镜像检查"
if [[ "${NO_BUILD}" == "false" ]]; then
    if ! ${CONTAINER_TOOL} image inspect "${IMAGE}" &> /dev/null; then
        log_error "镜像 ${IMAGE} 不存在，请先构建"
        log_info "  cd $(dirname "$0") && ./build.sh"
        exit 1
    fi
    log_success "镜像存在: ${IMAGE}"
else
    log_warn "跳过镜像检查 (--no-build)"
fi

log_section "运行配置"
log_kv "镜像" "${IMAGE}"
log_kv "测试类型" "${TEST_TYPE}"
log_kv "项目目录" "${PROJECT_DIR}"
log_kv "测试目录" "${TESTS_OPS_DIR}"
log_kv "结果目录" "${RESULTS_DIR}"
log_blank

# ------------------------------------------------------------------------------
# 创建本地结果目录
# ------------------------------------------------------------------------------
log_section "准备结果目录"
mkdir -p "${RESULTS_DIR}"
log_success "结果目录已创建: ${RESULTS_DIR}"

# ------------------------------------------------------------------------------
# 运行容器
# ------------------------------------------------------------------------------
log_section "运行测试容器"
log_warn "首次运行需要安装 pytest 依赖，可能需要一点时间..."
log_blank

TEST_START_TS=$(date +%s)

set +e
${CONTAINER_TOOL} run --rm \
    -v "${TESTS_OPS_DIR}:/workspace/tests/ops" \
    -v "${RESULTS_DIR}:/workspace/test-results" \
    -w /workspace/tests/ops \
    -e "GLOG_minloglevel=2" \
    -e "CAFFE_TEST_DIR=/workspace/test-results" \
    -e "PYTHONPATH=/workspace/caffex/python:/workspace/tests" \
    -e "LD_LIBRARY_PATH=/workspace/caffex/build/lib:/usr/lib/x86_64-linux-gnu" \
    -e "TEST_TYPE=${TEST_TYPE}" \
    "${IMAGE}" \
    bash -c '
set -e

echo "[容器内] 设置环境变量..."
export GLOG_minloglevel=2
export CAFFE_TEST_DIR=/workspace/test-results
export PYTHONPATH=/workspace/caffex/python:/workspace/tests
export LD_LIBRARY_PATH=/workspace/caffex/build/lib:/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH:-}

echo "[容器内] 验证 Caffe 环境..."
verify-caffe.sh
VERIFY_EXIT=$?
if [ $VERIFY_EXIT -ne 0 ]; then
    echo "[ERROR] Caffe 环境验证失败"
    exit $VERIFY_EXIT
fi

echo "[容器内] 安装测试依赖..."
pip install -i https://mirrors.aliyun.com/pypi/simple/ pytest pytest-cov --quiet
export PATH="/home/builder/.local/bin:$PATH"

echo "[容器内] 切换到测试目录..."
cd /workspace/tests/ops

echo "[容器内] 运行 pytest (测试类型: ${TEST_TYPE})..."
PYTEST_EXIT_CODE=0

case "${TEST_TYPE}" in
    correctness)
        python3 -m pytest -m "correctness and not slow" --tb=long --junitxml=/workspace/test-results/junit.xml -v || PYTEST_EXIT_CODE=$?
        ;;
    performance)
        python3 -m pytest -m "slow" --tb=short --junitxml=/workspace/test-results/junit.xml -v || PYTEST_EXIT_CODE=$?
        ;;
    memory)
        python3 -m pytest test_memory.py --tb=short --junitxml=/workspace/test-results/junit.xml -v || PYTEST_EXIT_CODE=$?
        ;;
    edge)
        python3 -m pytest -m "edge" --tb=long --junitxml=/workspace/test-results/junit.xml -v || PYTEST_EXIT_CODE=$?
        ;;
    all)
        python3 -m pytest --tb=short --junitxml=/workspace/test-results/junit.xml -v || PYTEST_EXIT_CODE=$?
        ;;
esac

echo "[容器内] pytest 退出码: ${PYTEST_EXIT_CODE}"
exit ${PYTEST_EXIT_CODE}
'
TEST_EXIT_CODE=$?
set -e

TEST_END_TS=$(date +%s)
TEST_DURATION=$((TEST_END_TS - TEST_START_TS))
TEST_MINUTES=$((TEST_DURATION / 60))
TEST_SECONDS=$((TEST_DURATION % 60))

log_blank

# ------------------------------------------------------------------------------
# 结果汇总
# ------------------------------------------------------------------------------
log_header "测试结果汇总"
log_kv "测试类型" "${TEST_TYPE}"
log_kv "测试耗时" "${TEST_MINUTES}分${TEST_SECONDS}秒"
log_kv "退出码" "${TEST_EXIT_CODE}"
log_kv "结果目录" "${RESULTS_DIR}"
log_blank

if [[ -f "${RESULTS_DIR}/junit.xml" ]]; then
    log_success "JUnit 报告: ${RESULTS_DIR}/junit.xml"
fi
if [[ -d "${RESULTS_DIR}/coverage-html" ]]; then
    log_success "Coverage HTML: ${RESULTS_DIR}/coverage-html/index.html"
fi
if [[ -f "${RESULTS_DIR}/coverage.xml" ]]; then
    log_success "Coverage XML: ${RESULTS_DIR}/coverage.xml"
fi

log_blank

if [[ ${TEST_EXIT_CODE} -eq 0 ]]; then
    log_success "🎉 所有测试通过！"
else
    log_error "❌ 测试失败 (退出码: ${TEST_EXIT_CODE})"
    log_info "请查看上方日志和 ${RESULTS_DIR} 目录中的报告了解详情"
fi

log_blank
exit ${TEST_EXIT_CODE}
