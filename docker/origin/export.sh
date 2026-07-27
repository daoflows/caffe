#!/usr/bin/env bash
# ==============================================================================
# Caffe Docker 镜像导出脚本 (origin)
# 功能：封装 docker save 命令，导出 caffe-cpu 镜像为 tar 文件
# 用法：./export.sh [选项]
# 自包含版本：内联日志函数，不依赖外部文件
# ==============================================================================

set -uo pipefail

# ------------------------------------------------------------------------------
# 内联日志函数（自包含，参考 build.sh 风格）
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
# 工具函数
# ------------------------------------------------------------------------------
human_size() {
    local bytes=$1
    if [[ ${bytes} -ge $((1024*1024*1024)) ]]; then
        echo "$(awk "BEGIN {printf \"%.2f\", ${bytes}/1024/1024/1024}") GB"
    elif [[ ${bytes} -ge $((1024*1024)) ]]; then
        echo "$(awk "BEGIN {printf \"%.2f\", ${bytes}/1024/1024}") MB"
    elif [[ ${bytes} -ge 1024 ]]; then
        echo "$(awk "BEGIN {printf \"%.2f\", ${bytes}/1024}") KB"
    else
        echo "${bytes} B"
    fi
}

check_docker_available() {
    if ! command -v docker &>/dev/null; then
        log_error "未找到 docker 命令"
        log_troubleshoot <<'EOF'
1. 安装 Docker Desktop 并启用 WSL2 后端
2. 确认 docker --version 可以运行
3. Windows 环境推荐使用 Docker Desktop + WSL2 后端
EOF
        return 1
    fi
    if ! docker info &>/dev/null; then
        log_error "Docker 已安装但未运行"
        log_troubleshoot <<'EOF'
1. 启动 Docker Desktop
2. 等待 Docker 服务就绪 (系统托盘图标变绿)
3. 运行 docker info 验证
EOF
        return 1
    fi
    return 0
}

check_image_exists() {
    local image="$1"
    if docker image inspect "${image}" &>/dev/null; then
        return 0
    else
        return 1
    fi
}

check_disk_space() {
    local dir="$1"
    local required_gb=8
    local required_bytes=$((required_gb * 1024 * 1024 * 1024))

    local available
    if command -v df &>/dev/null; then
        available=$(df -P "${dir}" 2>/dev/null | awk 'NR==2 {print $4 * 512}')
        if [[ -z "${available}" ]] || [[ "${available}" -eq 0 ]]; then
            available=$(df -P "${dir}" 2>/dev/null | awk 'NR==2 {print $4 * 1024}')
        fi
    else
        available=0
    fi

    if [[ -z "${available}" ]] || [[ "${available}" -lt ${required_bytes} ]]; then
        log_error "磁盘可用空间不足，需要至少 ${required_gb}GB"
        if [[ -n "${available}" ]] && [[ "${available}" -gt 0 ]]; then
            log_kv "当前可用空间" "$(human_size ${available})"
        fi
        log_troubleshoot <<'EOF'
1. 清理磁盘空间：清理旧镜像 docker image prune -a
2. 清理容器：docker container prune
3. 清理卷：docker volume prune
4. 更换输出目录到空间充足的磁盘：-o DIR
EOF
        return 1
    fi
    log_success "磁盘空间充足: $(human_size ${available}) 可用"
    return 0
}

calculate_sha256() {
    local file="$1"
    if command -v sha256sum &>/dev/null; then
        sha256sum "${file}" | awk '{print $1}'
    elif command -v shasum &>/dev/null; then
        shasum -a 256 "${file}" | awk '{print $1}'
    elif command -v powershell.exe &>/dev/null; then
        powershell.exe -Command "(Get-FileHash -Path '${file}' -Algorithm SHA256).Hash.ToLower()" 2>/dev/null | tr -d '\r'
    else
        echo "N/A (no sha256 tool found)"
    fi
}

verify_tar_manifest() {
    local file="$1"
    if [[ "${file}" == *.tar.gz ]] || [[ "${file}" == *.tgz ]]; then
        if gzip -t "${file}" 2>/dev/null && tar -tzf "${file}" 2>/dev/null | grep -q manifest.json; then
            return 0
        else
            return 1
        fi
    else
        if tar -tf "${file}" 2>/dev/null | grep -q manifest.json; then
            return 0
        else
            return 1
        fi
    fi
}

# ------------------------------------------------------------------------------
# 路径变量
# ------------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
DEFAULT_OUTPUT_DIR="${SCRIPT_DIR}/dist"

# ------------------------------------------------------------------------------
# 默认值
# ------------------------------------------------------------------------------
DEFAULT_IMAGE_NAME="caffe-cpu"
DEFAULT_RUNTIME_TAG="origin-runtime"
DEFAULT_JUPYTER_TAG="origin-jupyter"

IMAGE_NAME="${DEFAULT_IMAGE_NAME}"
OUTPUT_DIR="${DEFAULT_OUTPUT_DIR}"
EXPORT_RUNTIME=true
EXPORT_JUPYTER=true
COMPRESS=false
CUSTOM_TAG_SUFFIX=""
DATE_SUFFIX="$(date +%Y%m%d)"

show_help() {
    cat <<EOF
用法: $(basename "$0") [选项]

导出 Caffe Docker 镜像 (origin) 为 tar 文件

镜像类型:
  (默认)              导出所有镜像 (先 runtime，再 jupyter)
  --runtime           只导出 runtime 镜像 (${IMAGE_NAME}:${DEFAULT_RUNTIME_TAG})
  --jupyter           只导出 jupyter 镜像 (${IMAGE_NAME}:${DEFAULT_JUPYTER_TAG})

选项:
  -o, --output DIR    指定输出目录 (默认: ${DEFAULT_OUTPUT_DIR})
  --runtime           只导出 runtime 镜像
  --jupyter           只导出 jupyter 镜像
  -z, --compress      使用 gzip 压缩，导出为 .tar.gz 文件
  -t TAG              自定义镜像标签后缀 (用于非默认标签构建的镜像)
  -h, --help          显示此帮助信息

导出文件命名:
  runtime:  caffe-cpu-origin-runtime_{YYYYMMDD}.tar[.gz]
  jupyter:  caffe-cpu-origin-jupyter_{YYYYMMDD}.tar[.gz]

示例:
  $(basename "$0")                           # 导出所有镜像到 dist/
  $(basename "$0") --runtime                 # 只导出 runtime 镜像
  $(basename "$0") --jupyter -z              # 只导出 jupyter 镜像并压缩
  $(basename "$0") -o /tmp/exports           # 导出到指定目录
  $(basename "$0") -t v1.0                   # 导出自定义标签的镜像
  $(basename "$0") --all -z                  # 导出所有镜像并压缩

加载命令:
  docker load -i <file.tar>
  docker load -i <file.tar.gz>
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
        -o|--output)
            if [[ -z "${2:-}" ]]; then
                log_error "-o/--output 需要指定目录参数"
                exit 1
            fi
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --runtime)
            EXPORT_RUNTIME=true
            EXPORT_JUPYTER=false
            shift
            ;;
        --jupyter)
            EXPORT_RUNTIME=false
            EXPORT_JUPYTER=true
            shift
            ;;
        -z|--compress)
            COMPRESS=true
            shift
            ;;
        -t)
            if [[ -z "${2:-}" ]]; then
                log_error "-t 需要指定标签参数"
                exit 1
            fi
            CUSTOM_TAG_SUFFIX="$2"
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
# 确定镜像标签
# ------------------------------------------------------------------------------
if [[ -n "${CUSTOM_TAG_SUFFIX}" ]]; then
    RUNTIME_TAG="${CUSTOM_TAG_SUFFIX}"
    JUPYTER_TAG="${CUSTOM_TAG_SUFFIX}"
else
    RUNTIME_TAG="${DEFAULT_RUNTIME_TAG}"
    JUPYTER_TAG="${DEFAULT_JUPYTER_TAG}"
fi

RUNTIME_IMAGE="${IMAGE_NAME}:${RUNTIME_TAG}"
JUPYTER_IMAGE="${IMAGE_NAME}:${JUPYTER_TAG}"

# ------------------------------------------------------------------------------
# 导出单个镜像的函数
# ------------------------------------------------------------------------------
export_image() {
    local image_type="$1"
    local image_spec="$2"
    local output_file="$3"
    local compress="$4"

    local export_failed=false

    log_header "导出 ${image_type} 镜像"

    log_section "前置检查"

    if ! check_docker_available; then
        return 1
    fi
    log_success "Docker 服务运行中"

    if ! check_image_exists "${image_spec}"; then
        log_error "镜像不存在: ${image_spec}"
        log_info "请先使用 ./build.sh 构建镜像"
        return 1
    fi
    log_success "镜像存在: ${image_spec}"

    local image_size
    image_size=$(docker image inspect "${image_spec}" --format='{{.Size}}' 2>/dev/null || echo "0")
    if [[ "${image_size}" != "0" ]]; then
        log_kv "镜像大小" "$(human_size ${image_size})"
    fi

    if [[ ! -d "${OUTPUT_DIR}" ]]; then
        log_info "创建输出目录: ${OUTPUT_DIR}"
        mkdir -p "${OUTPUT_DIR}" || {
            log_error "无法创建输出目录: ${OUTPUT_DIR}"
            return 1
        }
    fi
    log_success "输出目录: ${OUTPUT_DIR}"

    if ! check_disk_space "${OUTPUT_DIR}"; then
        return 1
    fi

    log_section "导出配置"
    log_kv "镜像类型" "${image_type}"
    log_kv "镜像标签" "${image_spec}"
    log_kv "输出文件" "$(basename "${output_file}")"
    log_kv "输出路径" "${output_file}"
    log_kv "启用压缩" "$([[ "${compress}" == "true" ]] && echo "是 (gzip)" || echo "否")"
    log_blank

    if [[ -f "${output_file}" ]]; then
        log_warn "输出文件已存在，将覆盖: ${output_file}"
        rm -f "${output_file}"
    fi

    log_section "导出阶段"
    log_info "开始导出 ${image_type} 镜像..."
    if [[ "${compress}" == "true" ]]; then
        log_info "使用 docker save | gzip 压缩导出..."
    else
        log_info "使用 docker save 导出..."
    fi
    log_blank

    local EXPORT_START_TS EXPORT_END_TS EXPORT_DURATION EXPORT_MINUTES EXPORT_SECONDS EXPORT_EXIT_CODE
    EXPORT_START_TS=$(date +%s)

    set +e
    if [[ "${compress}" == "true" ]]; then
        docker save "${image_spec}" | gzip > "${output_file}"
        EXPORT_EXIT_CODE=$?
    else
        docker save -o "${output_file}" "${image_spec}"
        EXPORT_EXIT_CODE=$?
    fi
    set -e

    EXPORT_END_TS=$(date +%s)
    EXPORT_DURATION=$((EXPORT_END_TS - EXPORT_START_TS))
    EXPORT_MINUTES=$((EXPORT_DURATION / 60))
    EXPORT_SECONDS=$((EXPORT_DURATION % 60))

    log_blank

    if [[ ${EXPORT_EXIT_CODE} -ne 0 ]]; then
        log_error "导出失败，退出码: ${EXPORT_EXIT_CODE}"
        log_kv "耗时" "${EXPORT_MINUTES}分${EXPORT_SECONDS}秒"
        log_troubleshoot <<'EOF'
常见导出失败原因:
1. Docker 守护进程未运行或异常
2. 磁盘空间不足（导出过程中空间耗尽）
3. 镜像损坏或不存在
4. 权限问题（无法写入输出目录）
EOF
        rm -f "${output_file}" 2>/dev/null || true
        return ${EXPORT_EXIT_CODE}
    fi

    log_section "导出后验证"

    if [[ ! -f "${output_file}" ]]; then
        log_error "导出文件不存在: ${output_file}"
        return 1
    fi

    local file_size
    file_size=$(stat -c%s "${output_file}" 2>/dev/null || stat -f%z "${output_file}" 2>/dev/null || wc -c < "${output_file}" | tr -d ' ')
    if [[ -z "${file_size}" ]] || [[ "${file_size}" -eq 0 ]]; then
        log_error "导出文件大小为 0"
        return 1
    fi
    log_success "文件大小: $(human_size ${file_size})"
    log_kv "导出耗时" "${EXPORT_MINUTES}分${EXPORT_SECONDS}秒"

    log_info "验证 tar 文件结构..."
    if verify_tar_manifest "${output_file}"; then
        log_success "tar 结构验证通过 (包含 manifest.json)"
    else
        if [[ "${compress}" == "true" ]]; then
            log_warn "无法验证压缩包内 manifest.json（gzip 或 tar 工具可能不兼容）"
        else
            log_error "tar 结构验证失败：未找到 manifest.json"
            export_failed=true
        fi
    fi

    log_info "计算 SHA256 校验和..."
    local sha256
    sha256=$(calculate_sha256 "${output_file}")
    log_kv "SHA256" "${sha256}"

    log_blank

    if [[ "${export_failed}" == "true" ]]; then
        log_error "导出验证失败: ${image_type}"
        return 1
    fi

    log_success "导出成功: ${image_type}"

    EXPORT_RESULTS+=("${image_type}|${image_spec}|${output_file}|${file_size}|${sha256}")
    return 0
}

# ------------------------------------------------------------------------------
# 主流程
# ------------------------------------------------------------------------------
log_header "Caffe Docker 镜像导出 (origin)"

EXPORT_START_TS=$(date +%s)

EXPORT_RESULTS=()
RUNTIME_SUCCESS=false
JUPYTER_SUCCESS=false
RUNTIME_EXIT_CODE=0
JUPYTER_EXIT_CODE=0
SUCCESS_COUNT=0
FAIL_COUNT=0

RUNTIME_EXT="tar"
JUPYTER_EXT="tar"
if [[ "${COMPRESS}" == "true" ]]; then
    RUNTIME_EXT="tar.gz"
    JUPYTER_EXT="tar.gz"
fi

RUNTIME_FILENAME="caffe-cpu-origin-runtime_${DATE_SUFFIX}.${RUNTIME_EXT}"
JUPYTER_FILENAME="caffe-cpu-origin-jupyter_${DATE_SUFFIX}.${JUPYTER_EXT}"
RUNTIME_FILE="${OUTPUT_DIR}/${RUNTIME_FILENAME}"
JUPYTER_FILE="${OUTPUT_DIR}/${JUPYTER_FILENAME}"

log_section "导出配置"
log_kv "输出目录" "${OUTPUT_DIR}"
log_kv "日期后缀" "${DATE_SUFFIX}"
log_kv "导出 runtime" "$([[ "${EXPORT_RUNTIME}" == "true" ]] && echo "是" || echo "否")"
log_kv "导出 jupyter" "$([[ "${EXPORT_JUPYTER}" == "true" ]] && echo "是" || echo "否")"
log_kv "启用压缩" "$([[ "${COMPRESS}" == "true" ]] && echo "是 (gzip)" || echo "否")"
log_kv "Runtime 镜像" "${RUNTIME_IMAGE}"
log_kv "Jupyter 镜像" "${JUPYTER_IMAGE}"
log_blank

if [[ "${EXPORT_RUNTIME}" == "true" ]]; then
    if export_image "origin-runtime (基础运行时)" "${RUNTIME_IMAGE}" "${RUNTIME_FILE}" "${COMPRESS}"; then
        RUNTIME_SUCCESS=true
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    else
        RUNTIME_EXIT_CODE=$?
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
fi

if [[ "${EXPORT_JUPYTER}" == "true" ]]; then
    if export_image "origin-jupyter (Jupyter+SSH)" "${JUPYTER_IMAGE}" "${JUPYTER_FILE}" "${COMPRESS}"; then
        JUPYTER_SUCCESS=true
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    else
        JUPYTER_EXIT_CODE=$?
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
fi

EXPORT_END_TS=$(date +%s)
EXPORT_DURATION=$((EXPORT_END_TS - EXPORT_START_TS))
EXPORT_MINUTES=$((EXPORT_DURATION / 60))
EXPORT_SECONDS=$((EXPORT_DURATION % 60))

log_blank
log_header "导出汇总"
log_kv "总耗时" "${EXPORT_MINUTES}分${EXPORT_SECONDS}秒"
log_kv "成功" "${SUCCESS_COUNT} 个"
log_kv "失败" "${FAIL_COUNT} 个"
log_blank

if [[ ${#EXPORT_RESULTS[@]} -gt 0 ]]; then
    log_section "导出文件清单"
    for result in "${EXPORT_RESULTS[@]}"; do
        IFS='|' read -r img_type img_spec out_file f_size sha <<< "${result}"
        log_blank
        log_success "✓ ${img_type}"
        log_kv "镜像" "${img_spec}"
        log_kv "文件" "$(basename "${out_file}")"
        log_kv "路径" "${out_file}"
        log_kv "大小" "$(human_size ${f_size})"
        log_kv "SHA256" "${sha}"
    done
    log_blank

    log_section "加载命令"
    for result in "${EXPORT_RESULTS[@]}"; do
        IFS='|' read -r img_type img_spec out_file f_size sha <<< "${result}"
        log_info "docker load -i \"${out_file}\""
    done
    log_blank
fi

if [[ ${FAIL_COUNT} -gt 0 ]]; then
    log_section "失败详情"
    if [[ "${EXPORT_RUNTIME}" == "true" ]] && [[ "${RUNTIME_SUCCESS}" == "false" ]]; then
        log_error "✗ origin-runtime: 导出失败 (退出码: ${RUNTIME_EXIT_CODE})"
    fi
    if [[ "${EXPORT_JUPYTER}" == "true" ]] && [[ "${JUPYTER_SUCCESS}" == "false" ]]; then
        log_error "✗ origin-jupyter: 导出失败 (退出码: ${JUPYTER_EXIT_CODE})"
    fi
    log_blank
fi

if [[ ${FAIL_COUNT} -eq 0 ]]; then
    log_success "🎉 镜像导出完成！成功: ${SUCCESS_COUNT} 个"
    exit 0
else
    log_error "❌ 导出完成，但有 ${FAIL_COUNT} 个镜像失败"
    exit 1
fi
