#!/usr/bin/env bash
# shellcheck shell=bash
# ==============================================================================
# Caffe 构建系统 - 环境检查辅助函数库
#
# 使用方法:
#   SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
#   source "${SCRIPT_DIR}/../lib/log.sh"
#   source "${SCRIPT_DIR}/../lib/check_env.sh"
#
# 依赖: log.sh (必须先source)
# ==============================================================================

detect_container_tool() {
    if command -v wslc &> /dev/null; then
        echo "wslc"
    elif command -v docker &> /dev/null; then
        echo "docker"
    else
        echo ""
    fi
}

check_command() {
    local cmd="$1"
    command -v "$cmd" >/dev/null 2>&1
}

check_command_version() {
    local cmd="$1"
    local version_arg="${2:---version}"

    if ! check_command "$cmd"; then
        log_warn "  ✗ ${cmd}: 未找到"
        return 1
    fi

    local cmd_path
    cmd_path=$(command -v "$cmd")
    local version
    version=$("$cmd" $version_arg 2>/dev/null | head -1)
    if [[ -z "$version" ]]; then
        version="版本未知"
    fi
    log_info "  ✓ ${cmd}: ${version}"
    return 0
}

check_directory() {
    local dir="$1"
    local desc="${2:-目录}"

    if [[ -d "$dir" ]]; then
        log_info "  ✓ ${desc}: ${dir}"
        return 0
    else
        log_error "  ✗ ${desc}不存在: ${dir}"
        return 1
    fi
}

check_file() {
    local file="$1"
    local desc="${2:-文件}"

    if [[ -f "$file" ]]; then
        log_info "  ✓ ${desc}: ${file}"
        return 0
    else
        log_error "  ✗ ${desc}不存在: ${file}"
        return 1
    fi
}

check_docker_running() {
    local container_tool
    container_tool=$(detect_container_tool)
    if [[ -z "$container_tool" ]]; then
        log_error "  ✗ docker/wslc: 未安装"
        return 1
    fi
    if [[ "$container_tool" == "docker" ]]; then
        if docker info >/dev/null 2>&1; then
            log_info "  ✓ Docker: 已运行"
            return 0
        else
            log_error "  ✗ Docker: 已安装但未运行，请启动 Docker 服务"
            return 1
        fi
    else
        log_info "  ✓ wslc: 已检测到"
        return 0
    fi
}

check_build_environment() {
    local skip_docker=0
    if [[ "${1:-}" == "--skip-docker" ]]; then
        skip_docker=1
    fi

    log_section "环境检查"

    local all_ok=1
    local tools=(
        "make:--version"
        "cmake:--version"
        "python3:--version"
    )

    for tool_spec in "${tools[@]}"; do
        local cmd="${tool_spec%%:*}"
        local ver_arg="${tool_spec#*:}"
        if ! check_command_version "$cmd" "$ver_arg"; then
            all_ok=0
        fi
    done

    if [[ $skip_docker -eq 0 ]]; then
        if ! check_docker_running; then
            all_ok=0
        fi
    fi

    local cpu_count
    cpu_count=$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo "未知")
    log_info "  CPU 核心数: ${cpu_count}"

    if [[ -n "${PROJECT_DIR:-}" ]]; then
        log_info "  工作目录: ${PROJECT_DIR}"
    fi

    if [[ $all_ok -eq 0 ]]; then
        log_warn "部分工具未找到或未运行，可能导致构建失败"
        return 1
    else
        log_success "环境检查通过"
        return 0
    fi
}
