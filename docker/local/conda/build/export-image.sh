#!/usr/bin/env bash
# ==============================================================================
# Caffe Runtime Docker 镜像导出脚本
# 功能：将 Caffe 运行时镜像导出为 tar 文件
# 用法：在 docker/local/conda 目录执行 ./build/export-image.sh [选项]
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/../../../.." && pwd -P)"
CONDA_DIR="${SCRIPT_DIR}/.."
LOCAL_DIR="${SCRIPT_DIR}/../.."
LIB_DIR="${LOCAL_DIR}/lib"

source "${LIB_DIR}/log.sh"
source "${LIB_DIR}/check_env.sh"

DEFAULT_TAG="caffe-cpu:latest"

TAG="${DEFAULT_TAG}"
OUTPUT=""
COMPRESS=false

show_help() {
    cat <<EOF
用法: $(basename "$0") [选项]

导出 Caffe Runtime Docker 镜像为 tar 文件

建议执行位置:
  cd docker/local/conda
  ./build/$(basename "$0") [选项]

选项:
  --tag <tag>      要导出的镜像标签 (默认: ${DEFAULT_TAG})
  --output <path>  输出 tar 文件路径 (默认: docker/local/dist/caffe-cpu-<version>.tar)
  --compress       使用 gzip 压缩，输出 .tar.gz 文件
  -h, --help       显示此帮助信息

示例:
  ./build/$(basename "$0")                                      # 使用默认参数导出
  ./build/$(basename "$0") --tag my-caffe:v1.0                  # 导出自定义标签镜像
  ./build/$(basename "$0") --output /path/to/output.tar         # 指定输出路径
  ./build/$(basename "$0") --compress                           # 导出并压缩

导入命令:
  docker load -i <输出文件路径>
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help)
            show_help
            exit 0
            ;;
        --tag)
            if [[ -z "${2:-}" ]]; then
                log_error "--tag 需要指定镜像标签"
                exit 1
            fi
            TAG="$2"
            shift 2
            ;;
        --output)
            if [[ -z "${2:-}" ]]; then
                log_error "--output 需要指定输出路径"
                exit 1
            fi
            OUTPUT="$2"
            shift 2
            ;;
        --compress)
            COMPRESS=true
            shift
            ;;
        *)
            log_error "未知选项: $1"
            log_info "使用 -h 或 --help 查看帮助信息"
            exit 1
            ;;
    esac
done

DIST_DIR="${PROJECT_DIR}/docker/local/dist"

if [[ -z "${OUTPUT}" ]]; then
    if [[ "${COMPRESS}" == true ]]; then
        OUTPUT="docker/local/dist/caffe-cpu-runtime.tar.gz"
    else
        OUTPUT="docker/local/dist/caffe-cpu-runtime.tar"
    fi
fi

if [[ "${OUTPUT}" = /* ]]; then
    OUTPUT_PATH="${OUTPUT}"
else
    OUTPUT_PATH="${PROJECT_DIR}/${OUTPUT}"
fi

OUTPUT_DIR="$(dirname "${OUTPUT_PATH}")"

log_header "Caffe Runtime 镜像导出"

log_section "环境检查"
CONTAINER_TOOL=$(detect_container_tool)
if [[ -z "${CONTAINER_TOOL}" ]]; then
    log_error "未找到 docker/wslc 命令"
    exit 1
fi
log_success "容器工具: ${CONTAINER_TOOL}"

if [[ "${CONTAINER_TOOL}" == "docker" ]]; then
    if ! docker info &>/dev/null; then
        log_error "Docker 已安装但未运行"
        exit 1
    fi
    log_success "Docker 服务运行中"
fi

cd "${PROJECT_DIR}"
log_success "项目根目录: ${PROJECT_DIR}"

log_section "镜像检查"
log_info "检查镜像: ${TAG}"
if ! ${CONTAINER_TOOL} image inspect "${TAG}" &>/dev/null; then
    log_error "镜像不存在: ${TAG}"
    log_troubleshoot <<EOF
1. 先构建镜像:
     cd ${PROJECT_DIR}/docker/local/conda
     ./build.sh --target runtime
2. 查看本地镜像列表: docker images
3. 确认镜像标签是否正确
EOF
    exit 1
fi

IMAGE_ID=$(${CONTAINER_TOOL} images -q "${TAG}")
IMAGE_SIZE=$(${CONTAINER_TOOL} image inspect "${TAG}" --format='{{.Size}}' 2>/dev/null || echo "0")
if [[ "${IMAGE_SIZE}" != "0" ]]; then
    IMAGE_SIZE_MB=$((IMAGE_SIZE / 1024 / 1024))
    log_success "镜像存在: ${TAG} (${IMAGE_ID}, ${IMAGE_SIZE_MB} MB)"
else
    log_success "镜像存在: ${TAG} (${IMAGE_ID})"
fi

log_section "导出配置"
log_kv "镜像标签" "${TAG}"
log_kv "镜像 ID" "${IMAGE_ID}"
log_kv "输出路径" "${OUTPUT_PATH}"
log_kv "压缩输出" "$([[ "${COMPRESS}" == true ]] && echo "是 (gzip)" || echo "否")"
log_blank

log_section "准备输出目录"
log_info "创建输出目录: ${OUTPUT_DIR}"
mkdir -p "${OUTPUT_DIR}"
log_success "输出目录已就绪"

log_section "导出阶段"
log_warn "导出过程可能需要一些时间，请耐心等待..."
log_blank

EXPORT_START_TS=$(date +%s)

if [[ "${COMPRESS}" == true ]]; then
    log_info "正在导出并压缩镜像..."
    ${CONTAINER_TOOL} save "${TAG}" | gzip > "${OUTPUT_PATH}"
else
    log_info "正在导出镜像..."
    ${CONTAINER_TOOL} save -o "${OUTPUT_PATH}" "${TAG}"
fi

EXPORT_END_TS=$(date +%s)
EXPORT_DURATION=$((EXPORT_END_TS - EXPORT_START_TS))
EXPORT_MINUTES=$((EXPORT_DURATION / 60))
EXPORT_SECONDS=$((EXPORT_DURATION % 60))

log_blank

log_header "导出成功"
log_kv "镜像标签" "${TAG}"
log_kv "导出耗时" "${EXPORT_MINUTES}分${EXPORT_SECONDS}秒"

if [[ -f "${OUTPUT_PATH}" ]]; then
    FILE_SIZE=$(ls -lh "${OUTPUT_PATH}" | awk '{print $5}')
    log_kv "文件大小" "${FILE_SIZE}"
    log_kv "文件路径" "${OUTPUT_PATH}"
fi

log_blank

log_section "导入命令"
log_info "在目标机器上执行以下命令导入镜像:"
log_blank
echo -e "  ${_CLR_GREEN}docker load -i ${OUTPUT_PATH}${_CLR_RESET}"
log_blank
log_success "🎉 Caffe Runtime 镜像导出完成！"
