#!/usr/bin/env bash
# ==============================================================================
# Caffe Docker 多阶段构建脚本
# 功能：一键构建 runtime 镜像，含详细日志输出、进度追踪、可选验证与导出
# 用法：在 docker/local/conda 目录执行 ./build/build-multistage.sh [选项]
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/../../../.." && pwd -P)"
CONDA_DIR="${SCRIPT_DIR}/.."
LOCAL_DIR="${SCRIPT_DIR}/../.."
LIB_DIR="${LOCAL_DIR}/lib"

source "${LIB_DIR}/log.sh"
source "${LIB_DIR}/check_env.sh"

# ------------------------------------------------------------------------------
# 默认参数
# ------------------------------------------------------------------------------
DEFAULT_IMAGE_NAME="caffe-cpu"
DEFAULT_TAG="runtime"
DEFAULT_TARGET="runtime"
DEFAULT_DOCKERFILE="${CONDA_DIR}/Dockerfile"

IMAGE_NAME="${DEFAULT_IMAGE_NAME}"
TAG="${DEFAULT_TAG}"
DOCKERFILE="${DEFAULT_DOCKERFILE}"
TARGET="${DEFAULT_TARGET}"
NO_CACHE=""
BUILD_ARGS=()
VERIFY=false
EXPORT=false
EXPORT_COMPRESS=false
VERBOSE=false
LOG_FILE=""
LOG_DIR="${PROJECT_DIR}/docker/local/logs"
JOBS=""

# Dockerfile 各阶段列表（用于日志上下文）
readonly ALL_STAGES=("base-system" "base-builder" "builder-dev" "builder" "runtime")

# ------------------------------------------------------------------------------
# 帮助信息
# ------------------------------------------------------------------------------
show_help() {
    cat <<EOF
用法: $(basename "$0") [选项]

一键构建 Caffe runtime Docker 镜像（含详细日志输出）

建议执行位置:
  cd docker/local/conda
  ./build/$(basename "$0") [选项]

选项:
  -t TAG              指定镜像标签 (默认: ${DEFAULT_TAG})
  --target TARGET     指定构建目标阶段 (默认: ${DEFAULT_TARGET})
                      可选: base-system, base-builder, builder-dev, builder, runtime
  --no-cache          无缓存构建
  --jobs N            并行编译任务数 (默认: nproc 自动检测)
  --verify            构建后运行验证
  --export            构建后导出镜像
  --compress          导出时使用 gzip 压缩
  --verbose           输出详细构建日志（docker build --progress=plain）
  --log-file PATH     将构建日志保存到指定文件 (默认: docker/local/logs/<tag>-<timestamp>.log)
  --build-arg KEY=VAL 传递构建参数 (可多次使用)
  -h, --help          显示此帮助信息

示例:
  ./build/$(basename "$0")                                    # 默认构建 runtime
  ./build/$(basename "$0") --verbose                          # 详细日志输出
  ./build/$(basename "$0") --verify                           # 构建并验证
  ./build/$(basename "$0") --verify --export --compress       # 构建、验证、导出
  ./build/$(basename "$0") --log-file /tmp/caffe-build.log    # 指定日志文件
  ./build/$(basename "$0") --no-cache --verbose               # 无缓存详细构建
  ./build/$(basename "$0") --jobs 4                           # 限制并行编译数为 4
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
        --jobs)
            if [[ -z "${2:-}" ]]; then
                log_error "--jobs 需要指定并行任务数"
                exit 1
            fi
            JOBS="$2"
            shift 2
            ;;
        --verify)
            VERIFY=true
            shift
            ;;
        --export)
            EXPORT=true
            shift
            ;;
        --compress)
            EXPORT_COMPRESS=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --log-file)
            if [[ -z "${2:-}" ]]; then
                log_error "--log-file 需要指定日志文件路径"
                exit 1
            fi
            LOG_FILE="$2"
            shift 2
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
# 派生的配置
# ------------------------------------------------------------------------------
IMAGE_SPEC="${IMAGE_NAME}:${TAG}"
BUILD_TIMESTAMP=$(date +"%Y%m%d-%H%M%S")

# 如果没指定日志文件，自动生成路径
if [[ -z "${LOG_FILE}" ]]; then
    mkdir -p "${LOG_DIR}"
    LOG_FILE="${LOG_DIR}/build-${TAG}-${BUILD_TIMESTAMP}.log"
fi

# 如果指定了 --jobs，添加到构建参数
if [[ -n "${JOBS}" ]]; then
    BUILD_ARGS+=("--build-arg" "BUILD_JOBS=${JOBS}")
fi

# verbose 模式下使用 --progress=plain
DOCKER_PROGRESS=""
if ${VERBOSE}; then
    DOCKER_PROGRESS="--progress=plain"
fi

# ------------------------------------------------------------------------------
# 辅助函数: 阶段计时
# ------------------------------------------------------------------------------
declare -A _STAGE_START
declare -A _STAGE_END

_stage_start() {
    local stage="$1"
    _STAGE_START["${stage}"]=$(date +%s)
    log_step "${stage}" "开始..."
}

_stage_end() {
    local stage="$1"
    local status="${2:-0}"
    _STAGE_END["${stage}"]=$(date +%s)
    local duration=$((${_STAGE_END["${stage}"]} - ${_STAGE_START["${stage}"]}))
    local m=$((duration / 60))
    local s=$((duration % 60))
    if [[ "${status}" == "0" ]]; then
        log_step "${stage}" "完成 (耗时 ${m}分${s}秒)"
    else
        log_step "${stage}" "失败 (耗时 ${m}分${s}秒)"
    fi
}

# ------------------------------------------------------------------------------
# 辅助函数: 磁盘空间检查
# ------------------------------------------------------------------------------
_check_disk_space() {
    local path="$1"
    local min_gb="${2:-5}"
    if command -v df &>/dev/null; then
        local avail_kb
        avail_kb=$(df -k "${path}" 2>/dev/null | awk 'NR==2 {print $4}')
        if [[ -n "${avail_kb}" ]] && [[ "${avail_kb}" =~ ^[0-9]+$ ]]; then
            local avail_gb=$((avail_kb / 1024 / 1024))
            log_info "磁盘可用空间: ${avail_gb} GB (路径: ${path})"
            if [[ ${avail_gb} -lt ${min_gb} ]]; then
                log_warn "磁盘可用空间不足 ${min_gb} GB，构建可能失败"
                return 1
            fi
        fi
    fi
    return 0
}

# ------------------------------------------------------------------------------
# 辅助函数: 已有镜像检查
# ------------------------------------------------------------------------------
_check_existing_image() {
    local spec="$1"
    if ${CONTAINER_TOOL} image inspect "${spec}" &>/dev/null; then
        local img_id
        img_id=$(${CONTAINER_TOOL} images -q "${spec}" 2>/dev/null)
        local img_size
        img_size=$(${CONTAINER_TOOL} image inspect "${spec}" --format='{{.Size}}' 2>/dev/null || echo "0")
        if [[ "${img_size}" != "0" ]]; then
            local img_size_mb=$((img_size / 1024 / 1024))
            log_info "已存在同名镜像: ${spec} (ID: ${img_id:0:12}, 大小: ${img_size_mb} MB)"
        else
            log_info "已存在同名镜像: ${spec} (ID: ${img_id:0:12})"
        fi
        return 0
    fi
    return 1
}

# ------------------------------------------------------------------------------
# 辅助函数: 列出本地相关镜像
# ------------------------------------------------------------------------------
_list_related_images() {
    log_info "本地相关 Caffe 镜像:"
    ${CONTAINER_TOOL} images --filter "reference=caffe-cpu*" --format "  {{.Repository}}:{{.Tag}}  {{.ID}}  {{.Size}}  {{.CreatedAt}}" 2>/dev/null || true
}

# ------------------------------------------------------------------------------
# 辅助函数: 阶段完成摘要
# ------------------------------------------------------------------------------
_print_stage_summary() {
    echo ""
    log_section "各阶段耗时汇总"
    for stage in "${ALL_STAGES[@]}"; do
        if [[ -n "${_STAGE_START[${stage}]:-}" ]] && [[ -n "${_STAGE_END[${stage}]:-}" ]]; then
            local duration=$((${_STAGE_END[${stage}]} - ${_STAGE_START[${stage}]}))
            local m=$((duration / 60))
            local s=$((duration % 60))
            printf "  %-16s %3d分%02d秒\n" "${stage}:" "${m}" "${s}"
        fi
    done
    echo ""
}

# ==============================================================================
# 主流程
# ==============================================================================

log_header "Caffe Docker 多阶段构建"
log_kv "开始时间" "$(date '+%Y-%m-%d %H:%M:%S')"
log_blank

# ---- 阶段 0: 环境检查 ----
_stage_start "env-check"

log_section "环境检查"
CONTAINER_TOOL=$(detect_container_tool)
if [[ -z "${CONTAINER_TOOL}" ]]; then
    log_error "未找到 wslc 或 docker 命令"
    log_troubleshoot <<'EOF'
1. 安装 Docker Desktop 或 WSL Containers
2. 确认 docker --version 或 wslc --version 可以运行
3. Windows 环境推荐使用 Docker Desktop + WSL2 后端
EOF
    exit 1
fi
log_success "容器工具: ${CONTAINER_TOOL}"

# 检查容器工具版本
if command -v "${CONTAINER_TOOL}" &>/dev/null; then
    tool_ver=$("${CONTAINER_TOOL}" --version 2>/dev/null | head -1)
    log_info "容器工具版本: ${tool_ver}"
fi

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

    # Docker 详细信息
    docker_server_ver=$(docker version --format '{{.Server.Version}}' 2>/dev/null || echo "未知")
    docker_os=$(docker version --format '{{.Server.Os}}' 2>/dev/null || echo "未知")
    log_info "Docker 服务端版本: ${docker_server_ver} (${docker_os})"

    # 磁盘空间
    _check_disk_space "${PROJECT_DIR}" 5 || true
fi

# 检查 Dockerfile
if [[ ! -f "${DOCKERFILE}" ]]; then
    log_error "Dockerfile 不存在: ${DOCKERFILE}"
    exit 1
fi
log_success "Dockerfile: ${DOCKERFILE}"

# 检查 Dockerfile 大小和行数
dockerfile_lines=$(wc -l < "${DOCKERFILE}")
log_info "Dockerfile 行数: ${dockerfile_lines}"

# 检查源码目录
if [[ ! -d "${PROJECT_DIR}/caffex" ]]; then
    log_error "Caffe 源码目录不存在: ${PROJECT_DIR}/caffex"
    exit 1
fi
log_success "Caffe 源码: ${PROJECT_DIR}/caffex"

# 源码统计
src_files=$(find "${PROJECT_DIR}/caffex" -type f 2>/dev/null | wc -l)
log_info "Caffe 源码文件数: ${src_files}"

_stage_end "env-check"

# ---- 阶段 0.5: 构建配置 ----
_stage_start "config"

log_section "构建配置"
log_kv "项目根目录" "${PROJECT_DIR}"
log_kv "Dockerfile" "${DOCKERFILE}"
log_kv "目标阶段" "${TARGET}"
log_kv "镜像标签" "${IMAGE_SPEC}"
log_kv "构建时间戳" "${BUILD_TIMESTAMP}"
log_kv "容器工具" "${CONTAINER_TOOL}"
log_kv "无缓存构建" "$([[ -n "${NO_CACHE}" ]] && echo "是" || echo "否")"
log_kv "详细日志" "$(${VERBOSE} && echo "是" || echo "否")"
log_kv "日志文件" "${LOG_FILE}"
log_kv "构建后验证" "$(${VERIFY} && echo "是" || echo "否")"
log_kv "构建后导出" "$(${EXPORT} && echo "是" || echo "否")"
if ${EXPORT_COMPRESS}; then
    log_kv "导出压缩" "是 (gzip)"
fi
if [[ -n "${JOBS}" ]]; then
    log_kv "并行编译" "${JOBS} 任务"
fi
if [[ ${#BUILD_ARGS[@]} -gt 0 ]]; then
    log_info "构建参数:"
    _i=0
    while [[ ${_i} -lt ${#BUILD_ARGS[@]} ]]; do
        if [[ "${BUILD_ARGS[${_i}]}" == "--build-arg" ]]; then
            log_info "  - ${BUILD_ARGS[$((_i+1))]}"
        fi
        _i=$((_i+1))
    done
fi

# 检查已有镜像
_check_existing_image "${IMAGE_SPEC}" || log_info "未找到同名镜像，将全新构建"

# 列出本地相关镜像
_list_related_images

_stage_end "config"

# ---- 阶段 1: Docker 构建 ----
log_section "构建阶段"
log_info "所有 Docker 构建层输出将同时写入: ${LOG_FILE}"
log_warn "首次构建可能需要 15-40 分钟，请耐心等待..."
log_info "提示: 构建过程中可打开另一个终端执行 'tail -f ${LOG_FILE}' 查看实时日志"
log_blank

_stage_start "docker-build"

BUILD_START_TS=$(date +%s)

# 构建 Docker 镜像，同时输出到终端和日志文件
log_info "Docker build 命令:"
log_info "  ${CONTAINER_TOOL} build --target ${TARGET} -t ${IMAGE_SPEC} -f ${DOCKERFILE} ${DOCKER_PROGRESS} ${NO_CACHE} ${PROJECT_DIR}"
log_blank

set +e
# 使用 tee 同时输出到终端和日志文件
${CONTAINER_TOOL} build \
    --target "${TARGET}" \
    -t "${IMAGE_SPEC}" \
    -f "${DOCKERFILE}" \
    ${DOCKER_PROGRESS} \
    ${NO_CACHE} \
    "${BUILD_ARGS[@]}" \
    "${PROJECT_DIR}" 2>&1 | tee "${LOG_FILE}"
BUILD_EXIT_CODE=${PIPESTATUS[0]}
set -e

BUILD_END_TS=$(date +%s)
BUILD_DURATION=$((BUILD_END_TS - BUILD_START_TS))
BUILD_MINUTES=$((BUILD_DURATION / 60))
BUILD_SECONDS=$((BUILD_DURATION % 60))

_stage_end "docker-build" "${BUILD_EXIT_CODE}"

log_blank

# ---- 阶段 2: 构建结果 ----
if [[ ${BUILD_EXIT_CODE} -ne 0 ]]; then
    log_header "构建失败"
    log_error "镜像构建失败，退出码: ${BUILD_EXIT_CODE}"
    log_kv "构建耗时" "${BUILD_MINUTES}分${BUILD_SECONDS}秒"
    log_kv "完整日志" "${LOG_FILE}"
    log_blank

    # 自动分析日志中的错误
    log_section "错误诊断"
    log_info "正在分析构建日志中的错误..."
    if [[ -f "${LOG_FILE}" ]]; then
        log_info "--- 日志中的 ERROR 行 ---"
        grep -i -n "error" "${LOG_FILE}" 2>/dev/null | tail -20 || log_info "  (未找到明确的 error 行)"
        log_info "--- 日志最后 30 行 ---"
        tail -30 "${LOG_FILE}" 2>/dev/null
    fi
    log_blank

    log_troubleshoot <<'EOF'
常见构建失败原因及解决方案:

1. 网络问题 (包下载失败)
   → 检查网络连接，配置的阿里云镜像源应该能正常访问
   → 重试构建: ./build/build-multistage.sh (Docker 会使用缓存)
   → 如镜像源不稳定，可临时切换: 修改 Dockerfile 中 sources.list 的镜像地址

2. 磁盘空间不足
   → 清理旧镜像: docker image prune -a
   → 清理构建缓存: docker builder prune -a
   → 查看磁盘占用: df -h

3. 内存不足
   → 增加 Docker Desktop 内存限制 (设置 → Resources → Memory)
   → 建议分配至少 8GB 内存
   → 或限制并行编译: ./build/build-multistage.sh --jobs 2

4. 依赖版本冲突
   → 查看具体报错行，确认包版本兼容性
   → 尝试无缓存重建: ./build/build-multistage.sh --no-cache

5. Caffe 编译错误
   → 查看日志中 Makefile.config 是否生成正确
   → 查看 Boost.Python 库是否找到: grep boost_python 日志文件
   → 查看 HDF5 头文件是否正确: grep hdf5 日志文件

6. 查看完整构建日志
   → 日志文件: ${LOG_FILE}
   → 或在终端查看: less ${LOG_FILE}
EOF
    exit ${BUILD_EXIT_CODE}
fi

log_header "构建成功"

# ---- 阶段 3: 镜像信息 ----
_stage_start "image-info"

log_section "镜像信息"
log_kv "镜像标签" "${IMAGE_SPEC}"

# 获取镜像详细信息
IMAGE_ID=$(${CONTAINER_TOOL} images -q "${IMAGE_SPEC}" 2>/dev/null || echo "未知")
log_kv "镜像 ID" "${IMAGE_ID:0:12}"

IMAGE_SIZE=$(${CONTAINER_TOOL} image inspect "${IMAGE_SPEC}" --format='{{.Size}}' 2>/dev/null || echo "0")
if [[ "${IMAGE_SIZE}" != "0" ]]; then
    IMAGE_SIZE_MB=$((IMAGE_SIZE / 1024 / 1024))
    log_kv "镜像大小" "${IMAGE_SIZE_MB} MB"
fi

IMAGE_CREATED=$(${CONTAINER_TOOL} image inspect "${IMAGE_SPEC}" --format='{{.Created}}' 2>/dev/null || echo "未知")
log_kv "创建时间" "${IMAGE_CREATED}"

log_kv "构建耗时" "${BUILD_MINUTES}分${BUILD_SECONDS}秒"
log_kv "完整日志" "${LOG_FILE}"

# 检查镜像层数
layer_count=$(${CONTAINER_TOOL} image inspect "${IMAGE_SPEC}" --format='{{len .RootFS.Layers}}' 2>/dev/null || echo "未知")
log_kv "镜像层数" "${layer_count}"

_stage_end "image-info"

log_blank

# ---- 阶段 4: 验证 ----
if ${VERIFY} && [[ "${TARGET}" == "runtime" || "${TARGET}" == "builder-dev" ]]; then
    _stage_start "verify"

    log_section "验证阶段"
    log_info "运行 Caffe 验证脚本..."
    log_blank

    # 验证并记录输出
    VERIFY_LOG="${LOG_DIR}/verify-${TAG}-${BUILD_TIMESTAMP}.log"
    ${CONTAINER_TOOL} run --rm "${IMAGE_SPEC}" verify-caffe.sh 2>&1 | tee "${VERIFY_LOG}"
    VERIFY_EXIT_CODE=${PIPESTATUS[0]}

    if [[ ${VERIFY_EXIT_CODE} -eq 0 ]]; then
        log_success "验证通过！"
        log_info "验证日志: ${VERIFY_LOG}"
    else
        log_error "验证失败 (退出码: ${VERIFY_EXIT_CODE})"
        log_info "验证日志: ${VERIFY_LOG}"
    fi
    _stage_end "verify" "${VERIFY_EXIT_CODE}"
    log_blank
fi

# ---- 阶段 5: 导出 ----
if ${EXPORT}; then
    _stage_start "export"

    log_section "导出阶段"
    EXPORT_ARGS=("--tag" "${IMAGE_SPEC}")
    if ${EXPORT_COMPRESS}; then
        EXPORT_ARGS+=("--compress")
    fi
    "${SCRIPT_DIR}/export-image.sh" "${EXPORT_ARGS[@]}"
    _stage_end "export"
    log_blank
fi

# ---- 阶段 6: 最终摘要 ----
_stage_start "summary"

log_header "构建完成摘要"
log_kv "开始时间" "$(date -d @${BUILD_START_TS} '+%Y-%m-%d %H:%M:%S' 2>/dev/null || date '+%Y-%m-%d %H:%M:%S')"
log_kv "结束时间" "$(date '+%Y-%m-%d %H:%M:%S')"
log_kv "总耗时" "${BUILD_MINUTES}分${BUILD_SECONDS}秒"
log_kv "镜像标签" "${IMAGE_SPEC}"
log_kv "镜像大小" "${IMAGE_SIZE_MB} MB"
log_blank

# 打印各阶段耗时
_print_stage_summary

# 列出最终镜像
log_section "本地 Caffe 镜像列表"
${CONTAINER_TOOL} images --filter "reference=caffe-cpu*" --format "  {{.Repository}}:{{.Tag}}  {{.ID}}  {{.Size}}" 2>/dev/null || true
log_blank

# 下一步操作
log_section "下一步操作"
log_info "  启动开发容器:   cd ${CONDA_DIR} && ./run.sh"
log_info "  构建 runtime:   ${SCRIPT_DIR}/build-multistage.sh --target runtime --verify"
log_info "  导出镜像:       ${SCRIPT_DIR}/export-image.sh --compress"
log_info "  查看使用指南:   ${CONDA_DIR}/RUNTIME_IMAGE_USAGE.md"
log_info "  查看构建日志:   less ${LOG_FILE}"
log_blank
log_success "Caffe Docker 镜像构建完成！"

_stage_end "summary"