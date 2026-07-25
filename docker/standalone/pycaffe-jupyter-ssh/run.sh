#!/usr/bin/env bash
# ==============================================================================
# PyCaffe Jupyter SSH 容器启动脚本
# 功能：封装 docker run 命令，自动检测端口、配置密码、挂载目录等
# 用法：./run.sh [选项]
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

find_available_port() {
    local start_port=$1
    local max_attempts=20
    local port=$start_port
    for ((i=0; i<max_attempts; i++)); do
        if command -v netstat &>/dev/null; then
            if ! netstat -tln 2>/dev/null | grep -q ":${port} "; then
                echo "$port"
                return
            fi
        elif command -v ss &>/dev/null; then
            if ! ss -tln 2>/dev/null | grep -q ":${port} "; then
                echo "$port"
                return
            fi
        elif command -v lsof &>/dev/null; then
            if ! lsof -i :${port} -sTCP:LISTEN &>/dev/null; then
                echo "$port"
                return
            fi
        else
            echo "$port"
            return
        fi
        port=$((port + 1))
    done
    echo ""
}

# ------------------------------------------------------------------------------
# 默认参数
# ------------------------------------------------------------------------------
DEFAULT_IMAGE_NAME="caffe-cpu"
DEFAULT_TAG="pycaffe-jupyter-ssh"
DEFAULT_CONTAINER_NAME="pycaffe-jupyter-ssh"
DEFAULT_WORKDIR=""
DEFAULT_MOUNTS=()
DEFAULT_NETWORK="bridge"

IMAGE_NAME="${DEFAULT_IMAGE_NAME}"
TAG="${DEFAULT_TAG}"
CONTAINER_NAME="${DEFAULT_CONTAINER_NAME}"
SSH_PORT=""
JUPYTER_PORT=""
WORKDIR=""
MOUNTS=()
ENV_VARS=()
USER_PASSWORD=""
JUPYTER_TOKEN=""
JUPYTER_PASSWORD=""
GRANT_SUDO="yes"
ROOT_LOGIN="no"
DETACH="true"
NETWORK="${DEFAULT_NETWORK}"
EXTRA_ARGS=()
FOLLOW_LOGS="false"

generate_random_string() {
    local length=${1:-16}
    if command -v openssl &>/dev/null; then
        openssl rand -hex "${length}" 2>/dev/null | tr -dc 'a-zA-Z0-9' | head -c "${length}"
    elif [[ -f /dev/urandom ]]; then
        tr -dc 'a-zA-Z0-9' < /dev/urandom | head -c "${length}"
    else
        echo "caffe$(date +%s)"
    fi
}

show_help() {
    cat <<EOF
用法: $(basename "$0") [选项]

启动 PyCaffe + SSH + Jupyter 容器

选项:
  镜像配置:
    -i IMAGE        指定镜像名 (默认: ${DEFAULT_IMAGE_NAME})
    -t TAG          指定镜像标签 (默认: ${DEFAULT_TAG})
    --name NAME     指定容器名 (默认: ${DEFAULT_CONTAINER_NAME})

  端口配置:
    -p PORT         指定 SSH 端口 (自动检测可用端口)
    -j PORT         指定 Jupyter 端口 (自动检测可用端口)

  数据挂载:
    -v HOST:CONTAINER  挂载卷 (可多次使用)
    -w, --workdir DIR  指定宿主机工作目录挂载到 /workspace

  安全配置:
    --user-password PWD   设置 SSH 用户密码 (默认自动生成)
    --jupyter-token TOK   设置 Jupyter token (默认自动生成)
    --jupyter-password P  设置 Jupyter 密码 (默认不设置，使用 token)
    --no-sudo             禁用 sudo 权限 (默认启用)
    --root-login          允许 root SSH 登录 (默认禁止)

  运行模式:
    -it, --interactive    前台交互模式 (默认后台运行)
    -a, --attach          启动后立即跟踪日志
    --network NET         网络模式 (默认: bridge)
    -e KEY=VAL            传递环境变量 (可多次使用)
    -- EXTRA_ARGS         传递额外参数给 docker run (-- 后全部传递)
    -h, --help            显示此帮助信息

示例:
  $(basename "$0")                          # 自动配置端口和密码启动
  $(basename "$0") -p 2222 -j 8888          # 指定端口启动
  $(basename "$0") -w ~/notebooks           # 挂载本地工作目录
  $(basename "$0") --user-password mypass   # 设置密码
  $(basename "$0") -it bash                 # 交互模式启动 bash
  $(basename "$0") -a                       # 启动后跟踪日志
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
            IMAGE_NAME="$2"
            shift 2
            ;;
        -t)
            TAG="$2"
            shift 2
            ;;
        --name)
            CONTAINER_NAME="$2"
            shift 2
            ;;
        -p)
            SSH_PORT="$2"
            shift 2
            ;;
        -j)
            JUPYTER_PORT="$2"
            shift 2
            ;;
        -v)
            MOUNTS+=(-v "$2")
            shift 2
            ;;
        -w|--workdir)
            WORKDIR="$2"
            shift 2
            ;;
        --user-password)
            USER_PASSWORD="$2"
            shift 2
            ;;
        --jupyter-token)
            JUPYTER_TOKEN="$2"
            shift 2
            ;;
        --jupyter-password)
            JUPYTER_PASSWORD="$2"
            shift 2
            ;;
        --no-sudo)
            GRANT_SUDO="no"
            shift
            ;;
        --root-login)
            ROOT_LOGIN="yes"
            shift
            ;;
        -it|--interactive)
            DETACH="false"
            shift
            ;;
        -a|--attach)
            FOLLOW_LOGS="true"
            shift
            ;;
        --network)
            NETWORK="$2"
            shift 2
            ;;
        -e)
            ENV_VARS+=(-e "$2")
            shift 2
            ;;
        --)
            shift
            EXTRA_ARGS+=("$@")
            break
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
log_header "PyCaffe Jupyter SSH 容器启动"

log_section "环境检查"
CONTAINER_TOOL=$(detect_container_tool)
if [[ -z "${CONTAINER_TOOL}" ]]; then
    log_error "未找到 docker 或 wslc 命令"
    exit 1
fi
log_success "容器工具: ${CONTAINER_TOOL}"

if ! ${CONTAINER_TOOL} image inspect "${IMAGE_SPEC}" &>/dev/null; then
    log_error "镜像不存在: ${IMAGE_SPEC}"
    log_info "请先构建镜像: $(dirname $0)/build.sh"
    exit 1
fi
log_success "镜像存在: ${IMAGE_SPEC}"

# ------------------------------------------------------------------------------
# 检查并停止同名容器
# ------------------------------------------------------------------------------
if ${CONTAINER_TOOL} ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    log_warn "发现同名容器 ${CONTAINER_NAME}，正在停止并删除..."
    ${CONTAINER_TOOL} stop "${CONTAINER_NAME}" &>/dev/null || true
    ${CONTAINER_TOOL} rm -f "${CONTAINER_NAME}" &>/dev/null || true
    log_success "旧容器已清理"
fi

# ------------------------------------------------------------------------------
# 端口检测
# ------------------------------------------------------------------------------
log_section "端口配置"
if [[ -z "${SSH_PORT}" ]]; then
    SSH_PORT=$(find_available_port 2222)
    if [[ -z "${SSH_PORT}" ]]; then
        log_error "无法找到可用 SSH 端口"
        exit 1
    fi
    log_info "SSH 端口自动分配: ${SSH_PORT}"
else
    EXISTING=$(find_available_port ${SSH_PORT})
    if [[ "${EXISTING}" != "${SSH_PORT}" ]]; then
        log_warn "端口 ${SSH_PORT} 已被占用，自动切换到 ${EXISTING}"
        SSH_PORT="${EXISTING}"
    fi
fi
log_kv "SSH 端口" "${SSH_PORT} (-> 容器 22)"

if [[ -z "${JUPYTER_PORT}" ]]; then
    JUPYTER_PORT=$(find_available_port 8888)
    if [[ -z "${JUPYTER_PORT}" ]]; then
        log_error "无法找到可用 Jupyter 端口"
        exit 1
    fi
    log_info "Jupyter 端口自动分配: ${JUPYTER_PORT}"
else
    EXISTING=$(find_available_port ${JUPYTER_PORT})
    if [[ "${EXISTING}" != "${JUPYTER_PORT}" ]]; then
        log_warn "端口 ${JUPYTER_PORT} 已被占用，自动切换到 ${EXISTING}"
        JUPYTER_PORT="${EXISTING}"
    fi
fi
log_kv "Jupyter 端口" "${JUPYTER_PORT} (-> 容器 8888)"

# ------------------------------------------------------------------------------
# 密码/Token 生成
# ------------------------------------------------------------------------------
log_section "安全配置"
if [[ -z "${USER_PASSWORD}" ]]; then
    USER_PASSWORD=$(generate_random_string 12)
    log_info "SSH 用户密码自动生成"
else
    log_info "SSH 用户密码: 用户指定"
fi
log_kv "SSH 用户" "builder"
log_kv "SSH 密码" "${USER_PASSWORD}"

if [[ -z "${JUPYTER_TOKEN}" ]] && [[ -z "${JUPYTER_PASSWORD}" ]]; then
    JUPYTER_TOKEN=$(generate_random_string 24)
    log_info "Jupyter Token 自动生成"
fi
if [[ -n "${JUPYTER_TOKEN}" ]]; then
    log_kv "Jupyter Token" "${JUPYTER_TOKEN}"
else
    log_kv "Jupyter 密码" "${JUPYTER_PASSWORD}"
fi
log_kv "sudo 权限" "${GRANT_SUDO}"
log_kv "root 登录" "${ROOT_LOGIN}"

# ------------------------------------------------------------------------------
# 数据挂载
# ------------------------------------------------------------------------------
log_section "数据挂载"
ALL_MOUNTS=()
if [[ -n "${WORKDIR}" ]]; then
    WORKDIR_ABS="$(cd "${WORKDIR}" 2>/dev/null && pwd -P || echo "${WORKDIR}")"
    ALL_MOUNTS+=(-v "${WORKDIR_ABS}:/workspace")
    log_kv "工作目录" "${WORKDIR_ABS} -> /workspace"
else
    log_kv "工作目录" "使用容器内部卷（不挂载宿主机目录）"
fi

for m in "${MOUNTS[@]}"; do
    ALL_MOUNTS+=("${m}")
done

# ------------------------------------------------------------------------------
# 构建 docker run 命令
# ------------------------------------------------------------------------------
DOCKER_ARGS=(
    --name "${CONTAINER_NAME}"
    --hostname "pycaffe-dev"
    -p "${SSH_PORT}:22"
    -p "${JUPYTER_PORT}:8888"
    -e "USER_PASSWORD=${USER_PASSWORD}"
    -e "GRANT_SUDO=${GRANT_SUDO}"
    -e "ALLOW_ROOT_SSH=${ROOT_LOGIN}"
    --network "${NETWORK}"
    --restart unless-stopped
    --shm-size=1g
    --ulimit nofile=65536:65536
    --security-opt seccomp=unconfined
)

if [[ "${DETACH}" == "true" ]]; then
    DOCKER_ARGS+=(-d)
else
    DOCKER_ARGS+=(-it --rm)
fi

if [[ -n "${JUPYTER_TOKEN}" ]]; then
    DOCKER_ARGS+=(-e "JUPYTER_TOKEN=${JUPYTER_TOKEN}")
fi

if [[ -n "${JUPYTER_PASSWORD}" ]]; then
    DOCKER_ARGS+=(-e "JUPYTER_PASSWORD=${JUPYTER_PASSWORD}")
fi

for e in "${ENV_VARS[@]}"; do
    DOCKER_ARGS+=("${e}")
done

for m in "${ALL_MOUNTS[@]}"; do
    DOCKER_ARGS+=("${m}")
done

DOCKER_ARGS+=("${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"}")
DOCKER_ARGS+=("${IMAGE_SPEC}")

# ------------------------------------------------------------------------------
# 执行启动
# ------------------------------------------------------------------------------
log_section "启动容器"
log_info "执行: ${CONTAINER_TOOL} run ${DOCKER_ARGS[*]}"
log_blank

CONTAINER_ID=$(${CONTAINER_TOOL} run "${DOCKER_ARGS[@]}")

# ------------------------------------------------------------------------------
# 显示连接信息
# ------------------------------------------------------------------------------
sleep 3

if [[ "${DETACH}" == "true" ]]; then
    log_header "容器已启动"
    log_kv "容器 ID" "${CONTAINER_ID:0:12}"
    log_kv "容器名称" "${CONTAINER_NAME}"
    log_kv "镜像" "${IMAGE_SPEC}"
    log_blank

    CONTAINER_IP=$(${CONTAINER_TOOL} inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "${CONTAINER_NAME}" 2>/dev/null || echo "")

    log_section "访问信息"
    echo ""
    echo "  🐍 PyCaffe (SSH):"
    echo "     ssh builder@localhost -p ${SSH_PORT}"
    echo "     密码: ${USER_PASSWORD}"
    echo ""
    echo "  📓 Jupyter Notebook:"
    echo "     http://localhost:${JUPYTER_PORT}"
    if [[ -n "${JUPYTER_TOKEN}" ]]; then
        echo "     Token: ${JUPYTER_TOKEN}"
        echo "     直接访问: http://localhost:${JUPYTER_PORT}/?token=${JUPYTER_TOKEN}"
    fi
    echo ""
    echo "  🔧 常用命令:"
    echo "     查看日志: ${CONTAINER_TOOL} logs -f ${CONTAINER_NAME}"
    echo "     进入容器: ${CONTAINER_TOOL} exec -it ${CONTAINER_NAME} bash"
    echo "     停止容器: ${CONTAINER_TOOL} stop ${CONTAINER_NAME}"
    echo "     删除容器: ${CONTAINER_TOOL} rm -f ${CONTAINER_NAME}"
    echo ""

    CONTAINER_STATUS=$(${CONTAINER_TOOL} inspect -f '{{.State.Status}}' "${CONTAINER_NAME}" 2>/dev/null || echo "unknown")
    log_kv "容器状态" "${CONTAINER_STATUS}"

    if [[ "${FOLLOW_LOGS}" == "true" ]]; then
        log_blank
        log_info "正在跟踪容器日志 (Ctrl+C 退出)..."
        ${CONTAINER_TOOL} logs -f "${CONTAINER_NAME}"
    fi
else
    log_info "交互模式启动，退出容器后将自动删除"
fi
