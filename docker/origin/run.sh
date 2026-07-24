#!/usr/bin/env bash
# ==============================================================================
# Caffe Docker 容器启动脚本 (origin)
# 功能：启动 caffe-cpu 容器并挂载源码目录进行开发
# 用法：./run.sh [选项] [命令]
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
# 注意：origin/run.sh 位于 docker/origin/ 下，项目根目录是 ../../
# ------------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd -P)"

# ------------------------------------------------------------------------------
# 默认值
# ------------------------------------------------------------------------------
DEFAULT_IMAGE="caffe-cpu:latest"
DEFAULT_CONTAINER_NAME="caffe-dev"
CONTAINER_WORKSPACE="/workspace"
CAFFE_CONTAINER_ROOT="${CONTAINER_WORKSPACE}/caffex"

IMAGE="${DEFAULT_IMAGE}"
CONTAINER_NAME="${DEFAULT_CONTAINER_NAME}"
AUTO_RM=true
INTERACTIVE=true
TTY=true
COMMAND=()
EXTRA_DOCKER_ARGS=()

show_help() {
    cat <<EOF
用法: $(basename "$0") [选项] [命令]

启动 caffe-cpu 容器并挂载源码目录进行开发
交互式 bash 默认接入 Caffe 源码环境

选项:
  -i IMAGE        指定镜像名 (默认: ${DEFAULT_IMAGE})
  -n NAME         指定容器名 (默认: ${DEFAULT_CONTAINER_NAME})
  --rm            运行后自动删除容器 (默认开启)
  --no-rm         不自动删除容器
  --non-interactive 非交互式模式（关闭 TTY，用于 CI/测试）
  -h, --help      显示此帮助信息
  --              后续参数作为命令透传

命令:
  不指定命令时默认启动 bash。命令前可加 -- 传递带横杠的参数。

示例:
  $(basename "$0")                           # 启动交互式 bash，可直接 import caffe
  $(basename "$0") -n my-build               # 指定容器名启动
  $(basename "$0") -- ls -la                 # 执行 ls 命令
  $(basename "$0") -- python3 -c "import caffe; print(caffe.__version__)"
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
        -i)
            IMAGE="$2"
            shift 2
            ;;
        -n)
            CONTAINER_NAME="$2"
            shift 2
            ;;
        --rm)
            AUTO_RM=true
            shift
            ;;
        --no-rm)
            AUTO_RM=false
            shift
            ;;
        --non-interactive)
            INTERACTIVE=false
            TTY=false
            shift
            ;;
        --)
            shift
            COMMAND=("$@")
            break
            ;;
        -*)
            log_error "未知选项: $1"
            exit 1
            ;;
        *)
            COMMAND=("$@")
            break
            ;;
    esac
done

if [[ ${#COMMAND[@]} -eq 0 ]]; then
    COMMAND=(bash)
fi

# ------------------------------------------------------------------------------
# 前置检查
# ------------------------------------------------------------------------------
log_header "Caffe Docker 容器启动 (origin)"

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

log_section "运行配置"
log_kv "镜像" "${IMAGE}"
log_kv "容器名" "${CONTAINER_NAME}"
log_kv "项目目录" "${PROJECT_DIR}"
log_kv "挂载点" "${CAFFE_CONTAINER_ROOT}"
log_blank

if ! ${CONTAINER_TOOL} image inspect "${IMAGE}" &> /dev/null; then
    log_error "镜像 ${IMAGE} 不存在，请先构建"
    log_info "  cd $(dirname "$0") && ./build.sh"
    exit 1
fi

# ------------------------------------------------------------------------------
# 构造 DOCKER_ARGS 数组
# ------------------------------------------------------------------------------
DOCKER_ARGS=(
    --name "${CONTAINER_NAME}"
    --hostname "${CONTAINER_NAME}"
    -w "${CAFFE_CONTAINER_ROOT}"
    -v "${PROJECT_DIR}:${CONTAINER_WORKSPACE}"
    -e "CAFFE_ROOT=${CAFFE_CONTAINER_ROOT}"
    -e "PYTHONPATH=${CAFFE_CONTAINER_ROOT}/python"
    -e "LD_LIBRARY_PATH=${CAFFE_CONTAINER_ROOT}/build/lib:/usr/lib/x86_64-linux-gnu"
)

if $AUTO_RM; then
    DOCKER_ARGS+=(--rm)
fi
if $INTERACTIVE; then
    DOCKER_ARGS+=(-i)
fi
if $TTY; then
    DOCKER_ARGS+=(-t)
fi

log_success "启动容器..."
log_info "提示: 输入 'exit' 退出容器"
log_blank

exec "${CONTAINER_TOOL}" run \
    "${DOCKER_ARGS[@]}" \
    "${IMAGE}" \
    "${COMMAND[@]}"
