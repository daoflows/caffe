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
DEFAULT_TAG="latest"
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

构建 Caffe Docker 镜像 (origin)

选项:
  -t TAG              指定镜像标签 (默认: ${DEFAULT_TAG})
  -f DOCKERFILE       指定 Dockerfile 路径 (默认: Dockerfile)
  --target TARGET     指定构建目标阶段 (默认: ${DEFAULT_TARGET})
  --no-cache          无缓存构建
  --build-arg KEY=VAL 传递构建参数 (可多次使用)
  -h, --help          显示此帮助信息

示例:
  $(basename "$0")                           # 使用默认参数构建 runtime
  $(basename "$0") -t v1.0                   # 构建标签为 v1.0 的镜像
  $(basename "$0") --target runtime          # 构建 runtime 运行时镜像
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
        -t)
            if [[ -z "${2:-}" ]]; then
                log_error "-t 需要指定标签参数"
                exit 1
            fi
            TAG="$2"
            shift 2
            ;;
        -f)
            if [[ -z "${2:-}" ]]; then
                log_error "-f 需要指定 Dockerfile 路径"
                exit 1
            fi
            DOCKERFILE="$2"
            shift 2
            ;;
        --target)
            if [[ -z "${2:-}" ]]; then
                log_error "--target 需要指定构建目标阶段"
                exit 1
            fi
            TARGET="$2"
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

IMAGE_SPEC="${IMAGE_NAME}:${TAG}"

# ------------------------------------------------------------------------------
# 前置检查
# ------------------------------------------------------------------------------
log_header "Caffe Docker 镜像构建 (origin)"

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

if [[ ! -f "${DOCKERFILE}" ]]; then
    log_error "Dockerfile 不存在: ${DOCKERFILE}"
    exit 1
fi
log_success "Dockerfile: ${DOCKERFILE}"

if [[ ! -d "${PROJECT_DIR}/caffex" ]]; then
    log_error "Caffe 源码目录不存在: ${PROJECT_DIR}/caffex"
    log_info "请确认在正确的目录下运行此脚本"
    exit 1
fi
log_success "Caffe 源码: ${PROJECT_DIR}/caffex"

# ------------------------------------------------------------------------------
# 构建配置
# ------------------------------------------------------------------------------
log_section "构建配置"
log_kv "项目根目录" "${PROJECT_DIR}"
log_kv "Dockerfile" "${DOCKERFILE}"
log_kv "目标阶段" "${TARGET}"
log_kv "镜像标签" "${IMAGE_SPEC}"
log_kv "容器工具" "${CONTAINER_TOOL}"
log_kv "无缓存构建" "$([[ -n "${NO_CACHE}" ]] && echo "是" || echo "否")"
if [[ ${#BUILD_ARGS[@]} -gt 0 ]]; then
    log_info "构建参数:"
    i=0
    while [[ $i -lt ${#BUILD_ARGS[@]} ]]; do
        if [[ "${BUILD_ARGS[$i]}" == "--build-arg" ]]; then
            log_info "  - ${BUILD_ARGS[$((i+1))]}"
        fi
        i=$((i+1))
    done
fi
log_blank

# ------------------------------------------------------------------------------
# 执行构建
# ------------------------------------------------------------------------------
log_section "构建阶段"
log_warn "首次构建可能需要 15-40 分钟，请耐心等待..."
log_info "如果构建失败，请向上滚动查看第一个 error 行"
log_blank

BUILD_START_TS=$(date +%s)

set +e
${CONTAINER_TOOL} build \
    --target "${TARGET}" \
    -t "${IMAGE_SPEC}" \
    -f "${DOCKERFILE}" \
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
    log_info "  启动开发容器:   ./run.sh"
    log_info "  导出镜像:       docker save ${IMAGE_SPEC} -o caffe-cpu.tar"
    log_info "  查看镜像详情:   ${CONTAINER_TOOL} image inspect ${IMAGE_SPEC}"
    log_blank
    log_success "🎉 镜像构建完成！"
else
    log_header "构建失败"
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
    exit ${BUILD_EXIT_CODE}
fi
