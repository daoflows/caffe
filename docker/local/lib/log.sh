#!/usr/bin/env bash
# shellcheck shell=bash
# ==============================================================================
# Caffe 构建系统 - Shell 日志辅助函数库
#
# 使用方法:
#   SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
#   source "${SCRIPT_DIR}/../lib/log.sh"
#
# 日志级别: INFO / WARN / ERROR / SUCCESS / STEP / HEADER
# 颜色自动检测: 非TTY输出时自动禁用颜色
# ==============================================================================

if [[ -t 1 ]] && [[ -z "${NO_COLOR:-}" ]] && [[ "${TERM:-}" != "dumb" ]]; then
    _CLR_RESET='\033[0m'
    _CLR_RED='\033[0;31m'
    _CLR_GREEN='\033[0;32m'
    _CLR_YELLOW='\033[0;33m'
    _CLR_BLUE='\033[0;34m'
    _CLR_CYAN='\033[0;36m'
    _CLR_BOLD='\033[1m'
else
    _CLR_RESET=''
    _CLR_RED=''
    _CLR_GREEN=''
    _CLR_YELLOW=''
    _CLR_BLUE=''
    _CLR_CYAN=''
    _CLR_BOLD=''
fi

_log_timestamp() {
    date +"%H:%M:%S"
}

log_header() {
    local title="$1"
    local width=60
    echo ""
    echo -e "${_CLR_BOLD}${_CLR_BLUE}$(printf '=%.0s' $(seq 1 ${width}))${_CLR_RESET}"
    echo -e "${_CLR_BOLD}${_CLR_BLUE}  ${title}${_CLR_RESET}"
    echo -e "${_CLR_BOLD}${_CLR_BLUE}$(printf '=%.0s' $(seq 1 ${width}))${_CLR_RESET}"
}

log_section() {
    local title="$1"
    echo ""
    echo -e "${_CLR_CYAN}--- ${title} ---${_CLR_RESET}"
}

log_step() {
    local stage="$1"
    local message="$2"
    local ts
    ts=$(_log_timestamp)
    echo -e "${_CLR_BOLD}[${ts}] [${stage}]${_CLR_RESET} ${message}"
}

log_info() {
    local message="$1"
    local ts
    ts=$(_log_timestamp)
    echo -e "[${ts}] ${_CLR_CYAN}[INFO]${_CLR_RESET} ${message}"
}

log_warn() {
    local message="$1"
    local ts
    ts=$(_log_timestamp)
    echo -e "[${ts}] ${_CLR_YELLOW}[WARN] ⚠️  ${message}${_CLR_RESET}" >&2
}

log_error() {
    local message="$1"
    local ts
    ts=$(_log_timestamp)
    echo -e "[${ts}] ${_CLR_RED}[ERROR] ❌ ${message}${_CLR_RESET}" >&2
}

log_success() {
    local message="$1"
    local ts
    ts=$(_log_timestamp)
    echo -e "[${ts}] ${_CLR_GREEN}[OK] ✅ ${message}${_CLR_RESET}"
}

log_kv() {
    local key="$1"
    local value="$2"
    printf "  %-14s %s\n" "${key}:" "${value}"
}

log_blank() {
    echo ""
}

log_troubleshoot() {
    echo ""
    echo -e "${_CLR_YELLOW}--- 排查建议 ---${_CLR_RESET}"
    while IFS= read -r line; do
        echo -e "  ${line}"
    done
    echo ""
}
