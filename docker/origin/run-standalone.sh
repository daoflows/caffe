#!/usr/bin/env bash
# ==============================================================================
# Caffe Docker 独立容器运行脚本 (origin)
# 功能：运行完全自包含的 Caffe 镜像，不挂载宿主机目录
# 用法：./run-standalone.sh <runtime|jupyter> [选项] [-- 命令]
# 自包含版本：不依赖其他脚本
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
# Docker 环境检查
# ------------------------------------------------------------------------------
check_docker() {
    local CONTAINER_TOOL
    CONTAINER_TOOL=$(detect_container_tool)
    if [[ -z "${CONTAINER_TOOL}" ]]; then
        log_error "未找到 docker 或 wslc 命令"
        cat <<'EOF'
1. 安装 Docker Desktop 并启用 WSL2 后端
2. 确认 docker --version 可以运行
3. Windows 环境推荐使用 Docker Desktop + WSL2 后端
EOF
        exit 1
    fi

    if [[ "${CONTAINER_TOOL}" == "docker" ]]; then
        if ! docker info &>/dev/null; then
            log_error "Docker 已安装但未运行"
            cat <<'EOF'
1. 启动 Docker Desktop
2. 等待 Docker 服务就绪 (系统托盘图标变绿)
3. 运行 docker info 验证
EOF
            exit 1
        fi
    fi
    echo "${CONTAINER_TOOL}"
}

# ------------------------------------------------------------------------------
# 镜像存在性检查
# ------------------------------------------------------------------------------
check_image() {
    local CONTAINER_TOOL="$1"
    local IMAGE="$2"
    local BUILD_HINT="$3"

    if ! ${CONTAINER_TOOL} image inspect "${IMAGE}" &>/dev/null; then
        log_error "镜像 ${IMAGE} 不存在，请先构建"
        log_info "  ${BUILD_HINT}"
        exit 1
    fi
}

# ------------------------------------------------------------------------------
# 检查容器是否存在
# ------------------------------------------------------------------------------
container_exists() {
    local CONTAINER_TOOL="$1"
    local NAME="$2"
    ${CONTAINER_TOOL} inspect "${NAME}" &>/dev/null || return 1
}

# ------------------------------------------------------------------------------
# 检查容器是否运行中
# ------------------------------------------------------------------------------
container_running() {
    local CONTAINER_TOOL="$1"
    local NAME="$2"
    local status
    status=$(${CONTAINER_TOOL} inspect -f '{{.State.Running}}' "${NAME}" 2>/dev/null || echo "false")
    [[ "${status}" == "true" ]] || return 1
}

# ------------------------------------------------------------------------------
# 显示帮助
# ------------------------------------------------------------------------------
show_help() {
    cat <<EOF
用法: $(basename "$0") <子命令> [选项] [-- 命令]

运行完全自包含的 Caffe Docker 镜像（不挂载宿主机目录）

子命令:
  runtime             启动基础运行时环境 (交互式 bash 或执行一次性命令)
  jupyter             启动 Jupyter Notebook + SSH 服务 (后台运行)

通用选项:
  -i IMAGE            指定自定义镜像标签
  -n NAME             指定容器名
  -h, --help          显示此帮助信息

runtime 子命令说明:
  默认镜像: caffe-cpu:origin-runtime
  默认容器名: caffe-runtime
  工作目录: /workspace
  交互模式: 启动交互式 bash shell (不自动删除容器)
  一次性命令: 在 -- 后传递命令，执行完自动删除容器 (--rm)

  示例:
    $(basename "$0") runtime                           # 启动交互式 bash
    $(basename "$0") runtime -n mycaffe                # 指定容器名
    $(basename "$0") runtime -- python3 -c "import caffe; print('OK')"
    $(basename "$0") runtime -i myimage:tag -- ls -la  # 使用自定义镜像

jupyter 子命令说明:
  默认镜像: caffe-cpu:origin-jupyter
  默认容器名: caffe-jupyter
  端口映射: 127.0.0.1:8888:8888 (Jupyter), 127.0.0.1:2222:22 (SSH)
  后台运行: 使用 -d 参数，启动后显示访问信息

  环境变量 (从当前 shell 继承):
    USER_PASSWORD     SSH 密码 (默认: pass)
    JUPYTER_TOKEN     Jupyter Token (默认: mysecret)
    GRANT_SUDO        是否授予 sudo (默认: yes)
    RESTART_POLICY    重启策略 (默认: no，可选: unless-stopped/always/on-failure)

  示例:
    $(basename "$0") jupyter                           # 启动 Jupyter 服务
    $(basename "$0") jupyter -n myjupyter              # 指定容器名
    USER_PASSWORD=mypass JUPYTER_TOKEN=mytoken $(basename "$0") jupyter
    RESTART_POLICY=unless-stopped $(basename "$0") jupyter
EOF
}

# ------------------------------------------------------------------------------
# runtime 子命令主逻辑
# ------------------------------------------------------------------------------
run_runtime() {
    local DEFAULT_IMAGE="caffe-cpu:origin-runtime"
    local DEFAULT_CONTAINER_NAME="caffe-runtime"
    local CONTAINER_WORKSPACE="/workspace"

    local IMAGE="${DEFAULT_IMAGE}"
    local CONTAINER_NAME="${DEFAULT_CONTAINER_NAME}"
    local COMMAND=()
    local EXTRA_ARGS=()

    while [[ $# -gt 0 ]]; do
        case "$1" in
            -h|--help)
                show_help
                exit 0
                ;;
            -i)
                if [[ -z "${2:-}" ]]; then
                    log_error "-i 需要指定镜像参数"
                    exit 1
                fi
                IMAGE="$2"
                shift 2
                ;;
            -n)
                if [[ -z "${2:-}" ]]; then
                    log_error "-n 需要指定容器名参数"
                    exit 1
                fi
                CONTAINER_NAME="$2"
                shift 2
                ;;
            --)
                shift
                COMMAND=("$@")
                break
                ;;
            -*)
                log_error "未知选项: $1"
                log_info "使用 -h 查看帮助信息"
                exit 1
                ;;
            *)
                COMMAND=("$@")
                break
                ;;
        esac
    done

    local IS_ONESHOT=false
    if [[ ${#COMMAND[@]} -gt 0 ]]; then
        IS_ONESHOT=true
    else
        COMMAND=(bash)
    fi

    log_header "Caffe 独立运行时容器 (origin)"

    log_section "环境检查"
    local CONTAINER_TOOL
    CONTAINER_TOOL=$(check_docker)
    log_success "容器工具: ${CONTAINER_TOOL}"

    check_image "${CONTAINER_TOOL}" "${IMAGE}" "cd $(dirname "$0") && ./build.sh"

    if container_exists "${CONTAINER_TOOL}" "${CONTAINER_NAME}"; then
        if container_running "${CONTAINER_TOOL}" "${CONTAINER_NAME}"; then
            log_warn "容器 ${CONTAINER_NAME} 已在运行中"
            log_info "  进入运行中容器: docker exec -it ${CONTAINER_NAME} bash"
            log_info "  停止容器: docker stop ${CONTAINER_NAME}"
            log_info "  删除容器: docker rm -f ${CONTAINER_NAME}"
            exit 0
        else
            log_warn "容器 ${CONTAINER_NAME} 已存在但未运行"
            log_info "  启动已有容器: docker start -ai ${CONTAINER_NAME}"
            log_info "  删除容器后重新创建: docker rm ${CONTAINER_NAME}"
            exit 1
        fi
    fi

    log_section "运行配置"
    log_kv "镜像" "${IMAGE}"
    log_kv "容器名" "${CONTAINER_NAME}"
    log_kv "工作目录" "${CONTAINER_WORKSPACE}"
    if ${IS_ONESHOT}; then
        log_kv "模式" "一次性命令"
    else
        log_kv "模式" "交互式 bash"
    fi
    if ${IS_ONESHOT}; then
        log_kv "命令" "${COMMAND[*]}"
        log_kv "自动删除" "是 (--rm)"
    else
        log_kv "自动删除" "否 (退出后容器保留)"
    fi
    log_blank

    local DOCKER_ARGS=(
        --name "${CONTAINER_NAME}"
        --hostname "${CONTAINER_NAME}"
        -w "${CONTAINER_WORKSPACE}"
    )

    if ${IS_ONESHOT}; then
        DOCKER_ARGS+=(--rm)
        DOCKER_ARGS+=(-i)
        if [[ -t 0 ]] && [[ -t 1 ]]; then
            DOCKER_ARGS+=(-t)
        fi
    else
        DOCKER_ARGS+=(-it)
    fi

    if ${IS_ONESHOT}; then
        log_info "执行一次性命令..."
        log_blank
    else
        log_success "启动交互式容器..."
        log_info "提示: 输入 'exit' 退出容器（容器将保留，可再次启动）"
        log_info "  重新启动: docker start -ai ${CONTAINER_NAME}"
        log_info "  删除容器: docker rm ${CONTAINER_NAME}"
        log_blank
    fi

    exec "${CONTAINER_TOOL}" run \
        "${DOCKER_ARGS[@]}" \
        "${IMAGE}" \
        "${COMMAND[@]}"
}

# ------------------------------------------------------------------------------
# jupyter 子命令主逻辑
# ------------------------------------------------------------------------------
run_jupyter() {
    local DEFAULT_IMAGE="caffe-cpu:origin-jupyter"
    local DEFAULT_CONTAINER_NAME="caffe-jupyter"
    local SSH_PORT=2222
    local JUPYTER_PORT=8888
    local DEFAULT_USER_PASSWORD="pass"
    local DEFAULT_JUPYTER_TOKEN="mysecret"
    local DEFAULT_GRANT_SUDO="yes"
    local DEFAULT_RESTART_POLICY="no"

    local IMAGE="${DEFAULT_IMAGE}"
    local CONTAINER_NAME="${DEFAULT_CONTAINER_NAME}"
    local USER_PASSWORD="${USER_PASSWORD:-${DEFAULT_USER_PASSWORD}}"
    local JUPYTER_TOKEN="${JUPYTER_TOKEN:-${DEFAULT_JUPYTER_TOKEN}}"
    local GRANT_SUDO="${GRANT_SUDO:-${DEFAULT_GRANT_SUDO}}"
    local RESTART_POLICY="${RESTART_POLICY:-${DEFAULT_RESTART_POLICY}}"

    while [[ $# -gt 0 ]]; do
        case "$1" in
            -h|--help)
                show_help
                exit 0
                ;;
            -i)
                if [[ -z "${2:-}" ]]; then
                    log_error "-i 需要指定镜像参数"
                    exit 1
                fi
                IMAGE="$2"
                shift 2
                ;;
            -n)
                if [[ -z "${2:-}" ]]; then
                    log_error "-n 需要指定容器名参数"
                    exit 1
                fi
                CONTAINER_NAME="$2"
                shift 2
                ;;
            -*)
                log_error "未知选项: $1"
                log_info "使用 -h 查看帮助信息"
                exit 1
                ;;
            *)
                log_error "未知参数: $1"
                exit 1
                ;;
        esac
    done

    log_header "Caffe Jupyter 独立容器 (origin)"

    log_section "环境检查"
    local CONTAINER_TOOL
    CONTAINER_TOOL=$(check_docker)
    log_success "容器工具: ${CONTAINER_TOOL}"

    check_image "${CONTAINER_TOOL}" "${IMAGE}" "cd $(dirname "$0") && ./build.sh --jupyter"

    if container_exists "${CONTAINER_TOOL}" "${CONTAINER_NAME}"; then
        if container_running "${CONTAINER_TOOL}" "${CONTAINER_NAME}"; then
            log_warn "容器 ${CONTAINER_NAME} 已在运行中"
            print_jupyter_access_info "${CONTAINER_NAME}" "${USER_PASSWORD}" "${JUPYTER_TOKEN}"
            exit 0
        else
            log_warn "容器 ${CONTAINER_NAME} 已存在但未运行，启动中..."
            ${CONTAINER_TOOL} start "${CONTAINER_NAME}"
            sleep 3
            print_jupyter_access_info "${CONTAINER_NAME}" "${USER_PASSWORD}" "${JUPYTER_TOKEN}"
            exit 0
        fi
    fi

    log_section "运行配置"
    log_kv "镜像" "${IMAGE}"
    log_kv "容器名" "${CONTAINER_NAME}"
    log_kv "Jupyter 端口" "127.0.0.1:${JUPYTER_PORT}:8888"
    log_kv "SSH 端口" "127.0.0.1:${SSH_PORT}:22"
    log_kv "SSH 密码" "${USER_PASSWORD}"
    log_kv "Jupyter Token" "${JUPYTER_TOKEN}"
    log_kv "授予 sudo" "${GRANT_SUDO}"
    log_kv "重启策略" "${RESTART_POLICY}"
    log_blank

    local DOCKER_ARGS=(
        -d
        --name "${CONTAINER_NAME}"
        --hostname "${CONTAINER_NAME}"
        -p "127.0.0.1:${JUPYTER_PORT}:8888"
        -p "127.0.0.1:${SSH_PORT}:22"
        -e "USER_PASSWORD=${USER_PASSWORD}"
        -e "JUPYTER_TOKEN=${JUPYTER_TOKEN}"
        -e "GRANT_SUDO=${GRANT_SUDO}"
    )

    if [[ "${RESTART_POLICY}" != "no" ]]; then
        DOCKER_ARGS+=(--restart "${RESTART_POLICY}")
    fi

    log_info "启动容器中..."
    ${CONTAINER_TOOL} run "${DOCKER_ARGS[@]}" "${IMAGE}"

    log_success "容器启动命令已发送，等待服务就绪..."
    sleep 5

    print_jupyter_access_info "${CONTAINER_NAME}" "${USER_PASSWORD}" "${JUPYTER_TOKEN}"
}

# ------------------------------------------------------------------------------
# 打印 Jupyter 访问信息
# ------------------------------------------------------------------------------
print_jupyter_access_info() {
    local CONTAINER_NAME="$1"
    local USER_PASSWORD="$2"
    local JUPYTER_TOKEN="$3"

    log_section "访问信息"
    log_kv "Jupyter 访问 URL" "http://localhost:8888"
    log_kv "Jupyter Token" "${JUPYTER_TOKEN}"
    log_kv "SSH 连接命令" "ssh -p 2222 caffe-origin@localhost"
    log_kv "SSH 密码" "${USER_PASSWORD}"
    log_blank
    log_section "常用命令"
    log_info "  查看日志: docker logs -f ${CONTAINER_NAME}"
    log_info "  停止容器: docker stop ${CONTAINER_NAME}"
    log_info "  启动容器: docker start ${CONTAINER_NAME}"
    log_info "  删除容器: docker rm -f ${CONTAINER_NAME}"
    log_info "  进入容器: docker exec -it ${CONTAINER_NAME} bash"
    log_blank
}

# ------------------------------------------------------------------------------
# 主入口
# ------------------------------------------------------------------------------
main() {
    if [[ $# -eq 0 ]]; then
        show_help
        exit 1
    fi

    local subcmd="$1"
    shift

    case "${subcmd}" in
        runtime)
            run_runtime "$@"
            ;;
        jupyter)
            run_jupyter "$@"
            ;;
        help|-h|--help)
            show_help
            ;;
        *)
            log_error "未知子命令: ${subcmd}"
            log_info "使用 -h 查看帮助信息"
            exit 1
            ;;
    esac
}

main "$@"
