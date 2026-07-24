#!/usr/bin/env bash
# ==============================================================================
# Caffe Conda 多阶段构建脚本 (Python 3.14)
#
# 构建 conda + Python 3.14 版本的 Caffe Docker 镜像。
# 先构建 builder 阶段（Caffe 编译），再构建 runtime-conda（pycaffe + Python 3.14）。
#
# 使用示例:
#   ./build-conda.sh                    # 构建 runtime-conda 目标
#   ./build-conda.sh --verify           # 构建并运行推理验证
#   ./build-conda.sh --target builder   # 仅构建 builder 阶段
#   ./build-conda.sh --export           # 构建并导出 wheel 到本地
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/../../../.." && pwd -P)"
DOCKERFILE="${SCRIPT_DIR}/../Dockerfile.conda"
ORIG_DOCKERFILE="${SCRIPT_DIR}/../Dockerfile"

BUILDER_IMAGE="caffe-cpu:builder"
RUNTIME_IMAGE="caffe-cpu:conda-py314"
TARGET="runtime-conda"

# ---------------------------------------------------------------------------
# 检测容器工具
# ---------------------------------------------------------------------------
detect_container_tool() {
    if command -v docker &>/dev/null; then
        echo "docker"
    elif command -v wslc &>/dev/null; then
        echo "wslc"
    else
        echo "ERROR: No container tool found (docker or wslc)" >&2
        exit 1
    fi
}

# ---------------------------------------------------------------------------
# 构建 builder 阶段
# ---------------------------------------------------------------------------
build_builder() {
    local tool="$1"
    echo "=== Building Caffe builder stage ==="
    echo "  Image: ${BUILDER_IMAGE}"
    echo "  Dockerfile: ${ORIG_DOCKERFILE}"

    if [ "${tool}" = "docker" ]; then
        docker build \
            --target builder \
            -t "${BUILDER_IMAGE}" \
            -f "${ORIG_DOCKERFILE}" \
            "${PROJECT_DIR}"
    else
        wslc build \
            --target builder \
            -t "${BUILDER_IMAGE}" \
            -f "${ORIG_DOCKERFILE}" \
            "${PROJECT_DIR}"
    fi

    echo "=== Builder stage complete ==="
}

# ---------------------------------------------------------------------------
# 构建 conda 阶段
# ---------------------------------------------------------------------------
build_conda() {
    local tool="$1"
    local target="${2:-runtime-conda}"
    echo "=== Building conda ${target} stage ==="
    echo "  Image: ${RUNTIME_IMAGE}"
    echo "  Dockerfile: ${DOCKERFILE}"

    if [ "${tool}" = "docker" ]; then
        docker build \
            --target "${target}" \
            -t "${RUNTIME_IMAGE}" \
            -f "${DOCKERFILE}" \
            "${PROJECT_DIR}"
    else
        wslc build \
            --target "${target}" \
            -t "${RUNTIME_IMAGE}" \
            -f "${DOCKERFILE}" \
            "${PROJECT_DIR}"
    fi

    echo "=== Conda ${target} stage complete ==="
}

# ---------------------------------------------------------------------------
# 验证推理功能
# ---------------------------------------------------------------------------
verify_inference() {
    local tool="$1"
    echo "=== Verifying pycaffe inference (Python 3.14) ==="

    if [ "${tool}" = "docker" ]; then
        docker run --rm "${RUNTIME_IMAGE}" \
            bash -c "source /opt/conda/etc/profile.d/conda.sh && conda activate pycaffe-py314 && python /workspace/pycaffe/test_inference.py"
    else
        wslc run --rm "${RUNTIME_IMAGE}" \
            bash -c "source /opt/conda/etc/profile.d/conda.sh && conda activate pycaffe-py314 && python /workspace/pycaffe/test_inference.py"
    fi
}

# ---------------------------------------------------------------------------
# 导出 wheel
# ---------------------------------------------------------------------------
export_wheel() {
    local tool="$1"
    local output_dir="${PROJECT_DIR}/python/pycaffe/dist"
    mkdir -p "${output_dir}"

    echo "=== Exporting pycaffe wheel ==="
    if [ "${tool}" = "docker" ]; then
        docker run --rm -v "${output_dir}:/output" "${RUNTIME_IMAGE}" \
            bash -c "cp /workspace/pycaffe/dist/*.whl /output/"
    else
        echo "WARNING: wslc does not support volume mounts. Skipping wheel export."
    fi
    echo "=== Wheel exported to: ${output_dir} ==="
    ls -lh "${output_dir}"/*.whl 2>/dev/null || echo "No wheel files found"
}

# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
main() {
    local do_verify=false
    local do_export=false
    local target="${TARGET}"

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --verify)   do_verify=true; shift ;;
            --export)   do_export=true; shift ;;
            --target)   target="$2"; shift 2 ;;
            --help|-h)  usage; exit 0 ;;
            *)          echo "Unknown option: $1"; usage; exit 1 ;;
        esac
    done

    local tool
    tool=$(detect_container_tool)
    echo "  Container tool: ${tool}"
    echo "  Project dir:    ${PROJECT_DIR}"
    echo "  Target:         ${target}"
    echo ""

    # Step 1: Build builder stage
    build_builder "${tool}"

    # Step 2: Build conda stage
    build_conda "${tool}" "${target}"

    # Step 3: Verify (optional)
    if [ "${do_verify}" = true ]; then
        verify_inference "${tool}"
    fi

    # Step 4: Export wheel (optional)
    if [ "${do_export}" = true ]; then
        export_wheel "${tool}"
    fi

    echo ""
    echo "=========================================="
    echo "  Build complete!"
    echo "  Image: ${RUNTIME_IMAGE}"
    echo "=========================================="
}

usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --verify       Build and run inference verification"
    echo "  --export       Build and export wheel to local dist/"
    echo "  --target NAME  Build specific target (default: runtime-conda)"
    echo "  --help, -h     Show this help"
    echo ""
    echo "Examples:"
    echo "  $0                           # Build runtime-conda"
    echo "  $0 --verify                  # Build and verify"
    echo "  $0 --target pycaffe-builder-conda  # Build only wheel builder"
}

main "$@"