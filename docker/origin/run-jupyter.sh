#!/usr/bin/env bash
# ==============================================================================
# Caffe Jupyter + SSH Docker 容器一键启动脚本
# 功能：一键启动/停止/查看 caffe-cpu:jupyter 容器（含 SSH + Jupyter）
# 用法：
#   ./run-jupyter.sh start    # 启动容器
#   ./run-jupyter.sh stop     # 停止容器
#   ./run-jupyter.sh status   # 查看容器状态
#   ./run-jupyter.sh restart  # 重启容器
#   ./run-jupyter.sh logs     # 查看容器日志
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

# ------------------------------------------------------------------------------
# 配置变量
# ------------------------------------------------------------------------------
IMAGE="caffe-cpu:jupyter"
CONTAINER_NAME="caffe-jupyter"
SSH_PORT=2222
JUPYTER_PORT=8888
WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)/workspace"
CONTAINER_WORKSPACE="/workspace/notebooks"
USER_PASSWORD="${USER_PASSWORD:-pass}"
JUPYTER_TOKEN="${JUPYTER_TOKEN:-mysecret}"
GRANT_SUDO="${GRANT_SUDO:-yes}"
FORCE_RECREATE=false

# ------------------------------------------------------------------------------
# 前置检查
# ------------------------------------------------------------------------------
detect_wsl_distro() {
    local default_distro=""
    local available_distros=()
    local wsl_distro=""

    if grep -qE "(Microsoft|WSL)" /proc/version 2>/dev/null; then
        wsl_distro=$(cat /etc/hostname 2>/dev/null || echo "unknown")
        log_kv "当前 WSL 环境" "${wsl_distro}"
        return 0
    fi

    if command -v wsl &>/dev/null; then
        while IFS= read -r line; do
            if [[ "${line}" =~ ^\* ]]; then
                default_distro=$(echo "${line}" | awk '{print $2}')
            else
                available_distros+=("$(echo "${line}" | awk '{print $1}')")
            fi
        done < <(wsl --list --all 2>/dev/null | grep -v "^NAME\|^----\|^\s*$")

        if [[ -n "${default_distro}" ]]; then
            log_kv "默认 WSL 发行版" "${default_distro}"
            return 0
        elif [[ ${#available_distros[@]} -gt 0 ]]; then
            log_kv "可用 WSL 发行版" "${available_distros[*]}"
            log_warn "未设置默认发行版，请运行 'wsl --set-default <发行版名>'"
            return 0
        else
            log_warn "未检测到 WSL 发行版"
            return 1
        fi
    else
        log_warn "未安装 WSL"
        return 1
    fi
}

check_environment() {
    log_section "环境检查"

    detect_wsl_distro

    if ! command -v docker &>/dev/null; then
        log_error "未找到 docker 命令"
        echo "请先安装 Docker Desktop 并启用 WSL2 后端"
        exit 1
    fi
    log_success "Docker 已安装"

    if ! docker info &>/dev/null; then
        log_error "Docker 服务未运行"
        echo "请启动 Docker Desktop 并等待服务就绪"
        exit 1
    fi
    log_success "Docker 服务运行中"

    if ! docker image inspect "${IMAGE}" &>/dev/null; then
        log_error "镜像 ${IMAGE} 不存在，请先构建"
        echo "  cd $(dirname "$0") && docker build -t ${IMAGE} --target runtime-jupyter -f Dockerfile.jupyter-ssh ."
        exit 1
    fi
    log_success "镜像 ${IMAGE} 存在"
}

# ------------------------------------------------------------------------------
# 检查容器是否运行
# ------------------------------------------------------------------------------
is_container_running() {
    docker inspect -f '{{.State.Running}}' "${CONTAINER_NAME}" 2>/dev/null || echo "false"
}

# ------------------------------------------------------------------------------
# 检查容器是否存在
# ------------------------------------------------------------------------------
is_container_exists() {
    docker inspect "${CONTAINER_NAME}" &>/dev/null
}

# ------------------------------------------------------------------------------
# 启动容器
# ------------------------------------------------------------------------------
start_container() {
    log_header "启动 Caffe Jupyter 容器"

    check_environment

    if [[ "${FORCE_RECREATE}" == "true" ]]; then
        log_info "启用 --force-recreate 模式，将重建容器"
        if is_container_exists; then
            log_info "删除旧容器 ${CONTAINER_NAME}..."
            docker rm -f "${CONTAINER_NAME}"
            log_success "旧容器已删除"
        fi
    fi

    if [[ "$(is_container_running)" == "true" ]]; then
        log_warn "容器 ${CONTAINER_NAME} 已在运行中"
        print_access_info
        return 0
    fi

    if is_container_exists; then
        log_info "容器已存在，启动中..."
        docker start "${CONTAINER_NAME}"
    else
        log_info "创建并启动新容器..."

        mkdir -p "${WORKSPACE_DIR}"

        docker run -d \
            --name "${CONTAINER_NAME}" \
            --hostname "${CONTAINER_NAME}" \
            -p "${SSH_PORT}:22" \
            -p "${JUPYTER_PORT}:8888" \
            -v "${WORKSPACE_DIR}:${CONTAINER_WORKSPACE}" \
            -e "USER_PASSWORD=${USER_PASSWORD}" \
            -e "JUPYTER_TOKEN=${JUPYTER_TOKEN}" \
            -e "GRANT_SUDO=${GRANT_SUDO}" \
            --restart unless-stopped \
            "${IMAGE}"
    fi

    log_success "容器启动成功"
    print_access_info
}

# ------------------------------------------------------------------------------
# 停止容器
# ------------------------------------------------------------------------------
stop_container() {
    log_header "停止 Caffe Jupyter 容器"

    if ! is_container_exists; then
        log_warn "容器 ${CONTAINER_NAME} 不存在"
        return 0
    fi

    if [[ "$(is_container_running)" != "true" ]]; then
        log_warn "容器 ${CONTAINER_NAME} 未在运行"
        return 0
    fi

    log_info "停止容器 ${CONTAINER_NAME}..."
    docker stop "${CONTAINER_NAME}"
    log_success "容器已停止"
}

# ------------------------------------------------------------------------------
# 重启容器
# ------------------------------------------------------------------------------
restart_container() {
    log_header "重启 Caffe Jupyter 容器"
    stop_container
    start_container
}

# ------------------------------------------------------------------------------
# 查看状态
# ------------------------------------------------------------------------------
status_container() {
    log_header "Caffe Jupyter 容器状态"

    if ! is_container_exists; then
        log_warn "容器 ${CONTAINER_NAME} 不存在"
        return 1
    fi

    local status
    status=$(docker inspect -f '{{.State.Status}}' "${CONTAINER_NAME}" 2>/dev/null || echo "unknown")
    local running
    running=$(is_container_running)

    log_section "基本信息"
    log_kv "容器名" "${CONTAINER_NAME}"
    log_kv "镜像" "${IMAGE}"
    log_kv "状态" "${status}"

    if [[ "${running}" == "true" ]]; then
        log_success "容器运行中"
        print_access_info
    else
        log_warn "容器未运行"
    fi

    log_blank
}

# ------------------------------------------------------------------------------
# 查看日志
# ------------------------------------------------------------------------------
logs_container() {
    if ! is_container_exists; then
        log_error "容器 ${CONTAINER_NAME} 不存在"
        return 1
    fi

    log_info "查看容器日志 (Ctrl+C 退出)..."
    docker logs -f --tail 100 "${CONTAINER_NAME}"
}

# ------------------------------------------------------------------------------
# 打印访问信息
# ------------------------------------------------------------------------------
print_access_info() {
    log_section "访问信息"
    log_kv "Jupyter Notebook" "http://localhost:${JUPYTER_PORT}"
    log_kv "Jupyter Token" "${JUPYTER_TOKEN}"
    log_kv "Notebook 工作目录" "notebooks/ (Jupyter 内)"
    log_kv "SSH 地址" "ssh -p ${SSH_PORT} caffe-origin@localhost"
    log_kv "SSH 密码" "${USER_PASSWORD}"
    log_kv "工作目录挂载" "${WORKSPACE_DIR} -> ${CONTAINER_WORKSPACE}"
    log_kv "Caffe 源码目录" "/workspace/caffex/ (容器内，只读)"
    log_blank
    log_info "提示：首次访问 Jupyter 需输入 Token，用户文件请保存在 notebooks/ 目录中"
}

# ------------------------------------------------------------------------------
# 显示帮助
# ------------------------------------------------------------------------------
show_help() {
    cat <<EOF
用法: $(basename "$0") <命令> [选项]

Caffe Jupyter + SSH Docker 容器一键管理脚本

命令:
  start     启动容器（不存在则创建）
  stop      停止容器
  restart   重启容器
  status    查看容器状态和访问信息
  logs      查看容器日志（实时）
  help      显示此帮助信息

选项:
  --force-recreate    启动时强制删除旧容器并重新创建（解决配置不兼容问题）

环境变量:
  USER_PASSWORD   SSH 用户密码 (默认: pass)
  JUPYTER_TOKEN   Jupyter 访问令牌 (默认: mysecret)
  GRANT_SUDO      是否授予 sudo 权限 (默认: yes)

示例:
  $(basename "$0") start
  $(basename "$0") start --force-recreate
  $(basename "$0") stop
  $(basename "$0") status
  USER_PASSWORD=mypassword JUPYTER_TOKEN=mytoken $(basename "$0") start
EOF
}

# ------------------------------------------------------------------------------
# 主函数
# ------------------------------------------------------------------------------
main() {
    local cmd="${1:-help}"
    local opt="${2:-}"

    if [[ "${opt}" == "--force-recreate" ]]; then
        FORCE_RECREATE=true
    fi

    case "${cmd}" in
        start)
            start_container
            ;;
        stop)
            stop_container
            ;;
        restart)
            restart_container
            ;;
        status)
            status_container
            ;;
        logs)
            logs_container
            ;;
        help|-h|--help)
            show_help
            ;;
        *)
            log_error "未知命令: ${cmd}"
            echo "使用 '$(basename "$0") help' 查看帮助"
            exit 1
            ;;
    esac
}

main "$@"
