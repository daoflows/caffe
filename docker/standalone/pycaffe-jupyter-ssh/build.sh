#!/usr/bin/env bash
# ==============================================================================
# PyCaffe Jupyter SSH Docker 镜像构建脚本
# 功能：封装 docker build 命令，构建 caffe-cpu:pycaffe-jupyter-ssh 镜像
# 用法：在 vendor/ 目录下运行，或通过脚本自动定位
# ==============================================================================

set -euo pipefail

# ------------------------------------------------------------------------------
# 日志函数
# ------------------------------------------------------------------------------
log_info()    { echo -e "\033[34m[INFO]\033[0m $*"; }
log_success() { echo -e "\033[32m[OK]\033[0m $*"; }
log_warn()    { echo -e "\033[33m[WARN]\033[0m $*"; }
log_error()   { echo -e "\033[31m[ERROR]\033[0m $*" >&2; }
log_header()  { echo -e "\n\033[1;36m========================================\033[0m"; echo -e "\033[1;36m $* \033[0m"; echo -e "\033[1;36m========================================\033[0m"; }
log_section() { echo -e "\n\033[1;37m--- $* ---\033[0m"; }
log_kv()      { echo -e "  \033[37m$1:\033[0m $2"; }
log_blank()   { echo ""; }

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
# SCRIPT_DIR = docker/standalone/pycaffe-jupyter-ssh/
# VENDOR_DIR = vendor/  (build context root, needs access to caffe/ and tvm-ffi/)
# ------------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
VENDOR_DIR="$(cd "${SCRIPT_DIR}/../../../.." && pwd -P)"

# ------------------------------------------------------------------------------
# 默认值
# ------------------------------------------------------------------------------
DEFAULT_IMAGE_NAME="caffe-cpu"
DEFAULT_TAG="pycaffe-jupyter-ssh"
DEFAULT_DOCKERFILE="${SCRIPT_DIR}/Dockerfile"
DEFAULT_TARGET="runtime"

IMAGE_NAME="${DEFAULT_IMAGE_NAME}"
TAG="${DEFAULT_TAG}"
DOCKERFILE="${DEFAULT_DOCKERFILE}"
TARGET="${DEFAULT_TARGET}"
NO_CACHE=""
BUILD_ARGS=()

show_help() {
    cat <<EOF
用法: $(basename "$0") [选项]

构建 PyCaffe + SSH + Jupyter Docker 镜像

选项:
  -t TAG              指定镜像标签 (默认: ${DEFAULT_TAG})
  --target TARGET     指定构建目标阶段 (默认: ${DEFAULT_TARGET})
  --no-cache          无缓存构建
  --build-arg KEY=VAL 传递构建参数 (可多次使用)
  -h, --help          显示此帮助信息

示例:
  $(basename "$0")                           # 使用默认参数构建
  $(basename "$0") -t mytag                  # 构建标签为 mytag 的镜像
  $(basename "$0") --no-cache                # 无缓存构建
  $(basename "$0") --build-arg BUILDER_UID=1000  # 传递构建参数

注意:
  - 构建上下文自动设置为 vendor/ 目录（需要同时访问 caffe/ 和 tvm-ffi/）
  - 确保子模块已初始化: git submodule update --init --recursive
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
        -t)
            TAG="$2"
            shift 2
            ;;
        --target)
            TARGET="$2"
            shift 2
            ;;
        --no-cache)
            NO_CACHE="--no-cache"
            shift
            ;;
        --build-arg)
            BUILD_ARGS+=("--build-arg" "$2")
            shift 2
            ;;
        *)
            log_error "未知选项: $1"
            log_info "使用 -h 查看帮助信息"
            exit 1
            ;;
    esac
done

IMAGE_SPEC="${IMAGE_NAME}:${TAG}"

# ------------------------------------------------------------------------------
# 前置检查
# ------------------------------------------------------------------------------
log_header "PyCaffe Jupyter SSH 镜像构建"

log_section "环境检查"
CONTAINER_TOOL=$(detect_container_tool)
if [[ -z "${CONTAINER_TOOL}" ]]; then
    log_error "未找到 docker 或 wslc 命令"
    exit 1
fi
log_success "容器工具: ${CONTAINER_TOOL}"

if [[ "${CONTAINER_TOOL}" == "docker" ]]; then
    if ! docker info &>/dev/null; then
        log_error "Docker 已安装但未运行，请启动 Docker Desktop"
        exit 1
    fi
    log_success "Docker 服务运行中"
fi

if [[ ! -f "${DOCKERFILE}" ]]; then
    log_error "Dockerfile 不存在: ${DOCKERFILE}"
    exit 1
fi
log_success "Dockerfile: ${DOCKERFILE}"

if [[ ! -d "${VENDOR_DIR}/caffe/caffe-slim" ]]; then
    log_error "caffe-slim 源码目录不存在: ${VENDOR_DIR}/caffe/caffe-slim"
    log_info "请先初始化子模块: git submodule update --init --recursive"
    exit 1
fi
log_success "caffe-slim 源码: ${VENDOR_DIR}/caffe/caffe-slim"

if [[ ! -d "${VENDOR_DIR}/tvm-ffi" ]]; then
    log_error "tvm-ffi 子模块目录不存在: ${VENDOR_DIR}/tvm-ffi"
    log_info "请先初始化子模块: git submodule update --init --recursive"
    exit 1
fi
log_success "tvm-ffi 源码: ${VENDOR_DIR}/tvm-ffi"

# ------------------------------------------------------------------------------
# 构建配置
# ------------------------------------------------------------------------------
log_section "构建配置"
log_kv "构建上下文" "${VENDOR_DIR}"
log_kv "Dockerfile" "${DOCKERFILE}"
log_kv "目标阶段" "${TARGET}"
log_kv "镜像标签" "${IMAGE_SPEC}"
log_blank

# ------------------------------------------------------------------------------
# 执行构建
# ------------------------------------------------------------------------------
log_section "构建阶段"
log_warn "首次构建可能需要 15-30 分钟，请耐心等待..."
log_blank

BUILD_START_TS=$(date +%s)

set +e
${CONTAINER_TOOL} build \
    --target "${TARGET}" \
    -t "${IMAGE_SPEC}" \
    -f "${DOCKERFILE}" \
    ${NO_CACHE} \
    "${BUILD_ARGS[@]}" \
    "${VENDOR_DIR}"
BUILD_EXIT_CODE=$?
set -e

BUILD_END_TS=$(date +%s)
BUILD_DURATION=$((BUILD_END_TS - BUILD_START_TS))
BUILD_MINUTES=$((BUILD_DURATION / 60))
BUILD_SECONDS=$((BUILD_DURATION % 60))

log_blank

# ------------------------------------------------------------------------------
# 构建结果
# ------------------------------------------------------------------------------
if [[ ${BUILD_EXIT_CODE} -eq 0 ]]; then
    log_header "构建成功"
    log_kv "镜像标签" "${IMAGE_SPEC}"
    log_kv "构建耗时" "${BUILD_MINUTES}分${BUILD_SECONDS}秒"
    log_blank

    IMAGE_SIZE=$(${CONTAINER_TOOL} image inspect "${IMAGE_SPEC}" --format='{{.Size}}' 2>/dev/null || echo "0")
    if [[ "${IMAGE_SIZE}" != "0" ]]; then
        IMAGE_SIZE_MB=$((IMAGE_SIZE / 1024 / 1024))
        log_kv "镜像大小" "${IMAGE_SIZE_MB} MB"
    fi

    log_blank
    log_section "下一步操作"
    log_info "  启动容器(开发): $(dirname $0)/run.sh"
    log_info "  快速启动:       docker run -d -p 2222:22 -p 8888:8888 -e USER_PASSWORD=caffe123 -e JUPYTER_TOKEN=mydevtoken ${IMAGE_SPEC}"
    log_info "  查看镜像详情:   ${CONTAINER_TOOL} image inspect ${IMAGE_SPEC}"
    log_blank
    log_success "镜像构建完成！"
else
    log_header "构建失败"
    log_error "镜像构建失败，退出码: ${BUILD_EXIT_CODE}"
    log_kv "构建耗时" "${BUILD_MINUTES}分${BUILD_SECONDS}秒"
    exit ${BUILD_EXIT_CODE}
fi
