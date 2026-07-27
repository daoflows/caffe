#!/usr/bin/env bash
# ==============================================================================
# Caffe Docker 镜像构建脚本 (origin)
# 功能：封装 docker build 命令，构建 caffe-cpu 镜像
# 用法：./build.sh [选项]
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
# 注意：origin/build.sh 位于 docker/origin/ 下，项目根目录是 ../../
# ------------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd -P)"

# ------------------------------------------------------------------------------
# 默认值
# ------------------------------------------------------------------------------
DEFAULT_IMAGE_NAME="caffe-cpu"
DEFAULT_RUNTIME_TAG="origin-runtime"
DEFAULT_JUPYTER_TAG="origin-jupyter"
DEFAULT_RUNTIME_DOCKERFILE="${SCRIPT_DIR}/Dockerfile"
DEFAULT_JUPYTER_DOCKERFILE="${SCRIPT_DIR}/Dockerfile.jupyter-ssh"
DEFAULT_RUNTIME_TARGET="runtime"
DEFAULT_JUPYTER_TARGET="runtime-jupyter"

IMAGE_NAME="${DEFAULT_IMAGE_NAME}"
CUSTOM_TAG=""
CUSTOM_DOCKERFILE=""
CUSTOM_TARGET=""
NO_CACHE=""
BUILD_ARGS=()
BUILD_RUNTIME=true
BUILD_JUPYTER=false

show_help() {
    cat <<EOF
用法: $(basename "$0") [选项]

构建 Caffe Docker 镜像 (origin)

镜像类型:
  (默认)              构建基础运行时镜像 (${DEFAULT_IMAGE_NAME}:${DEFAULT_RUNTIME_TAG})
  --jupyter           构建 Jupyter+SSH 镜像 (${DEFAULT_IMAGE_NAME}:${DEFAULT_JUPYTER_TAG})
  --all               构建所有镜像 (先 runtime，再 jupyter)

选项:
  -t TAG              指定镜像标签 (覆盖默认标签)
  -f DOCKERFILE       指定 Dockerfile 路径 (覆盖默认 Dockerfile)
  --target TARGET     指定构建目标阶段 (覆盖默认目标阶段)
  --no-cache          无缓存构建
  --build-arg KEY=VAL 传递构建参数 (可多次使用)
  -h, --help          显示此帮助信息

镜像说明:
  origin-runtime      基础运行时镜像，仅包含 Caffe CPU 运行环境
                      - Dockerfile: Dockerfile
                      - 目标阶段: runtime
                      - 用途: 命令行运行、脚本执行、开发环境

  origin-jupyter      Jupyter+SSH 完整镜像，在 runtime 基础上增加:
                      - Jupyter Notebook/Lab (端口 8888)
                      - SSH 服务 (端口 22)
                      - Supervisord 进程管理
                      - 中文 locale 和时区配置
                      - Dockerfile: Dockerfile.jupyter-ssh
                      - 目标阶段: runtime-jupyter
                      - 用途: 交互式开发、远程访问、Notebook 环境

示例:
  $(basename "$0")                           # 构建 origin-runtime 镜像
  $(basename "$0") --jupyter                 # 构建 origin-jupyter 镜像
  $(basename "$0") --all                     # 构建所有镜像
  $(basename "$0") -t v1.0                   # 构建标签为 v1.0 的 runtime 镜像
  $(basename "$0") --jupyter -t my-jupyter   # 构建自定义标签的 jupyter 镜像
  $(basename "$0") --no-cache                # 无缓存构建
  $(basename "$0") --build-arg BUILDER_UID=1001  # 传递构建参数
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
        --jupyter)
            BUILD_RUNTIME=false
            BUILD_JUPYTER=true
            shift
            ;;
        --all)
            BUILD_RUNTIME=true
            BUILD_JUPYTER=true
            shift
            ;;
        -t)
            if [[ -z "${2:-}" ]]; then
                log_error "-t 需要指定标签参数"
                exit 1
            fi
            CUSTOM_TAG="$2"
            shift 2
            ;;
        -f)
            if [[ -z "${2:-}" ]]; then
                log_error "-f 需要指定 Dockerfile 路径"
                exit 1
            fi
            CUSTOM_DOCKERFILE="$2"
            shift 2
            ;;
        --target)
            if [[ -z "${2:-}" ]]; then
                log_error "--target 需要指定构建目标阶段"
                exit 1
            fi
            CUSTOM_TARGET="$2"
            shift 2
            ;;
        --no-cache)
            NO_CACHE="--no-cache"
            shift
            ;;
        --build-arg)
            if [[ -z "${2:-}" ]]; then
                log_error "--build-arg 需要指定 KEY=VAL 参数"
                exit 1
            fi
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

# ------------------------------------------------------------------------------
# 构建单个镜像的函数
# ------------------------------------------------------------------------------
build_image() {
    local build_type="$1"
    local dockerfile="$2"
    local target="$3"
    local tag="$4"
    local image_spec="${IMAGE_NAME}:${tag}"

    log_header "构建 ${build_type} 镜像"

    log_section "环境检查"
    local CONTAINER_TOOL
    CONTAINER_TOOL=$(detect_container_tool)
    if [[ -z "${CONTAINER_TOOL}" ]]; then
        log_error "未找到 docker 或 wslc 命令"
        log_troubleshoot <<'EOF'
1. 安装 Docker Desktop 并启用 WSL2 后端
2. 确认 docker --version 可以运行
3. Windows 环境推荐使用 Docker Desktop + WSL2 后端
EOF
        return 1
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
            return 1
        fi
        log_success "Docker 服务运行中"
    fi

    if [[ ! -f "${dockerfile}" ]]; then
        log_error "Dockerfile 不存在: ${dockerfile}"
        return 1
    fi
    log_success "Dockerfile: ${dockerfile}"

    if [[ ! -d "${PROJECT_DIR}/caffex" ]]; then
        log_error "Caffe 源码目录不存在: ${PROJECT_DIR}/caffex"
        log_info "请确认在正确的目录下运行此脚本"
        return 1
    fi
    log_success "Caffe 源码: ${PROJECT_DIR}/caffex"

    log_section "构建配置"
    log_kv "项目根目录" "${PROJECT_DIR}"
    log_kv "镜像类型" "${build_type}"
    log_kv "Dockerfile" "${dockerfile}"
    log_kv "目标阶段" "${target}"
    log_kv "镜像标签" "${image_spec}"
    log_kv "容器工具" "${CONTAINER_TOOL}"
    log_kv "无缓存构建" "$([[ -n "${NO_CACHE}" ]] && echo "是" || echo "否")"
    if [[ ${#BUILD_ARGS[@]} -gt 0 ]]; then
        log_info "构建参数:"
        local i=0
        while [[ $i -lt ${#BUILD_ARGS[@]} ]]; do
            if [[ "${BUILD_ARGS[$i]}" == "--build-arg" ]]; then
                log_info "  - ${BUILD_ARGS[$((i+1))]}"
            fi
            i=$((i+1))
        done
    fi
    log_blank

    log_section "构建阶段"
    log_warn "首次构建可能需要 15-40 分钟，请耐心等待..."
    log_info "如果构建失败，请向上滚动查看第一个 error 行"
    log_blank

    local BUILD_START_TS BUILD_END_TS BUILD_DURATION BUILD_MINUTES BUILD_SECONDS BUILD_EXIT_CODE
    BUILD_START_TS=$(date +%s)

    set +e
    ${CONTAINER_TOOL} build \
        --target "${target}" \
        -t "${image_spec}" \
        -f "${dockerfile}" \
        ${NO_CACHE} \
        "${BUILD_ARGS[@]}" \
        "${PROJECT_DIR}"
    BUILD_EXIT_CODE=$?
    set -e

    BUILD_END_TS=$(date +%s)
    BUILD_DURATION=$((BUILD_END_TS - BUILD_START_TS))
    BUILD_MINUTES=$((BUILD_DURATION / 60))
    BUILD_SECONDS=$((BUILD_DURATION % 60))

    log_blank

    if [[ ${BUILD_EXIT_CODE} -eq 0 ]]; then
        log_header "构建成功: ${build_type}"
        log_kv "镜像标签" "${image_spec}"
        log_kv "构建耗时" "${BUILD_MINUTES}分${BUILD_SECONDS}秒"
        log_blank

        local IMAGE_SIZE IMAGE_SIZE_MB
        IMAGE_SIZE=$(${CONTAINER_TOOL} image inspect "${image_spec}" --format='{{.Size}}' 2>/dev/null || echo "0")
        if [[ "${IMAGE_SIZE}" != "0" ]]; then
            IMAGE_SIZE_MB=$((IMAGE_SIZE / 1024 / 1024))
            log_kv "镜像大小" "${IMAGE_SIZE_MB} MB"
        fi

        log_blank
        return 0
    else
        log_header "构建失败: ${build_type}"
        log_error "镜像构建失败，退出码: ${BUILD_EXIT_CODE}"
        log_kv "构建耗时" "${BUILD_MINUTES}分${BUILD_SECONDS}秒"
        log_blank

        log_troubleshoot <<'EOF'
常见构建失败原因及解决方案:

1. 网络问题 (包下载失败)
   → 检查网络连接，配置的清华/阿里云镜像源应该能正常访问
   → 重试构建: ./build.sh (Docker 会使用缓存)

2. 磁盘空间不足
   → 清理旧镜像: docker image prune -a
   → 查看磁盘占用: df -h

3. 内存不足
   → 增加 Docker Desktop 内存限制 (设置 → Resources → Memory)
   → 建议分配至少 8GB 内存

4. 依赖冲突
   → 查看具体报错行，确认包版本兼容性
   → 尝试无缓存重建: ./build.sh --no-cache

5. Python 版本兼容性
   → Caffe 较老，如遇 Boost.Python 相关错误，可能需要调整 Python 版本
   → 检查 Dockerfile 中 PYTHON_VERSION 构建参数

6. 查看详细构建日志
   → 手动执行带 --progress=plain 的 docker build 命令查看完整输出
   → 向上滚动找到第一个红色 error: 行
EOF
        return ${BUILD_EXIT_CODE}
    fi
}

# ------------------------------------------------------------------------------
# 主流程
# ------------------------------------------------------------------------------
log_header "Caffe Docker 镜像构建 (origin)"

RUNTIME_DOCKERFILE="${DEFAULT_RUNTIME_DOCKERFILE}"
RUNTIME_TARGET="${DEFAULT_RUNTIME_TARGET}"
RUNTIME_TAG="${DEFAULT_RUNTIME_TAG}"

JUPYTER_DOCKERFILE="${DEFAULT_JUPYTER_DOCKERFILE}"
JUPYTER_TARGET="${DEFAULT_JUPYTER_TARGET}"
JUPYTER_TAG="${DEFAULT_JUPYTER_TAG}"

if [[ -n "${CUSTOM_DOCKERFILE}" ]]; then
    RUNTIME_DOCKERFILE="${CUSTOM_DOCKERFILE}"
    JUPYTER_DOCKERFILE="${CUSTOM_DOCKERFILE}"
fi

if [[ -n "${CUSTOM_TARGET}" ]]; then
    RUNTIME_TARGET="${CUSTOM_TARGET}"
    JUPYTER_TARGET="${CUSTOM_TARGET}"
fi

if [[ -n "${CUSTOM_TAG}" ]]; then
    RUNTIME_TAG="${CUSTOM_TAG}"
    JUPYTER_TAG="${CUSTOM_TAG}"
fi

BUILD_START_TS=$(date +%s)
RUNTIME_SUCCESS=false
JUPYTER_SUCCESS=false
RUNTIME_EXIT_CODE=0
JUPYTER_EXIT_CODE=0

if [[ "${BUILD_RUNTIME}" == "true" ]]; then
    if build_image "origin-runtime (基础运行时)" "${RUNTIME_DOCKERFILE}" "${RUNTIME_TARGET}" "${RUNTIME_TAG}"; then
        RUNTIME_SUCCESS=true
    else
        RUNTIME_EXIT_CODE=$?
    fi
fi

if [[ "${BUILD_JUPYTER}" == "true" ]]; then
    if [[ "${RUNTIME_SUCCESS}" == "true" ]] || [[ "${BUILD_RUNTIME}" == "false" ]]; then
        if build_image "origin-jupyter (Jupyter+SSH)" "${JUPYTER_DOCKERFILE}" "${JUPYTER_TARGET}" "${JUPYTER_TAG}"; then
            JUPYTER_SUCCESS=true
        else
            JUPYTER_EXIT_CODE=$?
        fi
    else
        log_warn "跳过 Jupyter 镜像构建（runtime 构建失败）"
    fi
fi

BUILD_END_TS=$(date +%s)
BUILD_DURATION=$((BUILD_END_TS - BUILD_START_TS))
BUILD_MINUTES=$((BUILD_DURATION / 60))
BUILD_SECONDS=$((BUILD_DURATION % 60))

log_blank
log_header "构建汇总"
log_kv "总耗时" "${BUILD_MINUTES}分${BUILD_SECONDS}秒"
log_blank

SUCCESS_COUNT=0
FAIL_COUNT=0

if [[ "${BUILD_RUNTIME}" == "true" ]]; then
    if [[ "${RUNTIME_SUCCESS}" == "true" ]]; then
        log_success "✓ origin-runtime: ${IMAGE_NAME}:${RUNTIME_TAG}"
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    else
        log_error "✗ origin-runtime: 构建失败 (退出码: ${RUNTIME_EXIT_CODE})"
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
fi

if [[ "${BUILD_JUPYTER}" == "true" ]]; then
    if [[ "${JUPYTER_SUCCESS}" == "true" ]]; then
        log_success "✓ origin-jupyter: ${IMAGE_NAME}:${JUPYTER_TAG}"
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    else
        log_error "✗ origin-jupyter: 构建失败 (退出码: ${JUPYTER_EXIT_CODE})"
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
fi

log_blank

if [[ ${FAIL_COUNT} -eq 0 ]]; then
    log_section "下一步操作"
    if [[ "${RUNTIME_SUCCESS}" == "true" ]]; then
        log_info "  启动 runtime 容器:  ./run.sh"
    fi
    if [[ "${JUPYTER_SUCCESS}" == "true" ]]; then
        log_info "  启动 Jupyter 容器:  ./run-jupyter.sh"
    fi
    log_info "  导出 runtime 镜像:  docker save ${IMAGE_NAME}:${RUNTIME_TAG} -o caffe-cpu-runtime.tar"
    if [[ "${JUPYTER_SUCCESS}" == "true" ]]; then
        log_info "  导出 Jupyter 镜像:  docker save ${IMAGE_NAME}:${JUPYTER_TAG} -o caffe-cpu-jupyter.tar"
    fi
    log_blank
    log_success "🎉 镜像构建完成！成功: ${SUCCESS_COUNT} 个"
else
    log_error "❌ 构建完成，但有 ${FAIL_COUNT} 个镜像失败"
    exit 1
fi
