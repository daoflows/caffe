#!/usr/bin/env bash
# ==============================================================================
# PyCaffe Customer Distribution Image Build Script
# Usage: Run from vendor/ directory, or the script auto-locates paths.
# Builds a self-contained customer-ready image (no dependency on pre-built images).
# ==============================================================================

set -euo pipefail

log_info()    { echo -e "\033[34m[INFO]\033[0m $*"; }
log_success() { echo -e "\033[32m[OK]\033[0m $*"; }
log_warn()    { echo -e "\033[33m[WARN]\033[0m $*"; }
log_error()   { echo -e "\033[31m[ERROR]\033[0m $*" >&2; }
log_header()  { echo -e "\n\033[1;36m========================================\033[0m"; echo -e "\033[1;36m $* \033[0m"; echo -e "\033[1;36m========================================\033[0m"; }
log_section() { echo -e "\n\033[1;37m--- $* ---\033[0m"; }
log_kv()      { echo -e "  \033[37m$1:\033[0m $2"; }
log_blank()   { echo ""; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
VENDOR_DIR="$(cd "${SCRIPT_DIR}/../../../.." && pwd -P)"

DEFAULT_IMAGE_NAME="caffe-cpu"
DEFAULT_TAG="customer"
DEFAULT_DOCKERFILE="${SCRIPT_DIR}/Dockerfile"
DEFAULT_TARGET="customer-runtime"

IMAGE_NAME="${DEFAULT_IMAGE_NAME}"
TAG="${DEFAULT_TAG}"
DOCKERFILE="${DEFAULT_DOCKERFILE}"
TARGET="${DEFAULT_TARGET}"
NO_CACHE=""
BUILD_ARGS=()
USE_CHINA_MIRROR=""
BUILD_DATE="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
IMAGE_VERSION="1.0.0"

show_help() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Build PyCaffe Customer Distribution Docker image (self-contained).

Options:
  -t TAG               Image tag (default: ${DEFAULT_TAG})
  --target TARGET      Build target stage (default: ${DEFAULT_TARGET})
  --no-cache           Build without cache
  --china              Use China mirrors (Aliyun for apt + PyPI)
  --build-arg K=V      Pass build argument (can be used multiple times)
  --version VER        Set image version label (default: ${IMAGE_VERSION})
  -h, --help           Show this help

Examples:
  $(basename "$0")                           # Build with default settings
  $(basename "$0") -t v1.0.0                 # Build with custom tag
  $(basename "$0") --china                   # Build using China mirrors
  $(basename "$0") --no-cache                # Clean rebuild
  $(basename "$0") -t customer --china       # China mirror build with default tag

Notes:
  - Build context is automatically set to vendor/ (needs caffe/ and tvm-ffi/)
  - Ensure submodules are initialized: git submodule update --init --recursive
  - Docker BuildKit is required (for Dockerfile.dockerignore support)
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help)
            show_help
            exit 0
            ;;
        -t)
            TAG="$2"
            shift 2
            ;;
        --target)
            TARGET="$2"
            shift 2
            ;;
        --no-cache)
            NO_CACHE="--no-cache"
            shift
            ;;
        --china)
            USE_CHINA_MIRROR="yes"
            shift
            ;;
        --build-arg)
            BUILD_ARGS+=("--build-arg" "$2")
            shift 2
            ;;
        --version)
            IMAGE_VERSION="$2"
            shift 2
            ;;
        *)
            log_error "Unknown option: $1"
            log_info "Use -h for help"
            exit 1
            ;;
    esac
done

IMAGE_SPEC="${IMAGE_NAME}:${TAG}"

log_header "PyCaffe Customer Distribution Image Build"

log_section "Environment Checks"

if ! command -v docker &>/dev/null; then
    log_error "docker command not found. Please install Docker first."
    exit 1
fi
log_success "Docker found: $(docker --version)"

if ! docker info &>/dev/null; then
    log_error "Docker is installed but not running. Start Docker Desktop first."
    exit 1
fi
log_success "Docker daemon is running"

if [[ ! -f "${DOCKERFILE}" ]]; then
    log_error "Dockerfile not found: ${DOCKERFILE}"
    exit 1
fi
log_success "Dockerfile: ${DOCKERFILE}"

if [[ ! -d "${VENDOR_DIR}/caffe/caffe-slim" ]]; then
    log_error "caffe-slim source not found: ${VENDOR_DIR}/caffe/caffe-slim"
    log_info "Initialize submodules: git submodule update --init --recursive"
    exit 1
fi
log_success "caffe-slim source: present"

if [[ ! -d "${VENDOR_DIR}/tvm-ffi" ]]; then
    log_error "tvm-ffi submodule not found: ${VENDOR_DIR}/tvm-ffi"
    log_info "Initialize submodules: git submodule update --init --recursive"
    exit 1
fi
log_success "tvm-ffi source: present"

DOCKER_BUILDKIT_VAL="${DOCKER_BUILDKIT:-1}"
export DOCKER_BUILDKIT="${DOCKER_BUILDKIT_VAL}"
log_success "BuildKit: ${DOCKER_BUILDKIT_VAL}"

log_section "Build Configuration"
log_kv "Build context" "${VENDOR_DIR}"
log_kv "Dockerfile"     "${DOCKERFILE}"
log_kv "Target stage"   "${TARGET}"
log_kv "Image tag"      "${IMAGE_SPEC}"
log_kv "Image version"  "${IMAGE_VERSION}"
log_kv "Build date"     "${BUILD_DATE}"
if [[ -n "${USE_CHINA_MIRROR}" ]]; then
    log_kv "Mirror" "China (Aliyun)"
    BUILD_ARGS+=("--build-arg" "APTPROXY=mirrors.aliyun.com")
    BUILD_ARGS+=("--build-arg" "PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple")
    BUILD_ARGS+=("--build-arg" "PIP_TRUSTED_HOST=mirrors.aliyun.com")
else
    log_kv "Mirror" "Official sources (default)"
fi
BUILD_ARGS+=("--build-arg" "BUILD_DATE=${BUILD_DATE}")
BUILD_ARGS+=("--build-arg" "IMAGE_VERSION=${IMAGE_VERSION}")
log_blank

log_section "Building"
log_warn "This is a FULL self-contained build (compiles Caffe from source)."
log_warn "First build may take 15-30 minutes. Subsequent builds use cache."
log_blank

BUILD_START_TS=$(date +%s)

set +e
docker build \
    --target "${TARGET}" \
    -t "${IMAGE_SPEC}" \
    -f "${DOCKERFILE}" \
    ${NO_CACHE} \
    "${BUILD_ARGS[@]}" \
    "${VENDOR_DIR}"
BUILD_EXIT_CODE=$?
set -e

BUILD_END_TS=$(date +%s)
BUILD_DURATION=$((BUILD_END_TS - BUILD_START_TS))
BUILD_MINUTES=$((BUILD_DURATION / 60))
BUILD_SECONDS=$((BUILD_DURATION % 60))

log_blank

if [[ ${BUILD_EXIT_CODE} -eq 0 ]]; then
    log_header "BUILD SUCCESSFUL"
    log_kv "Image"      "${IMAGE_SPEC}"
    log_kv "Duration"   "${BUILD_MINUTES}m ${BUILD_SECONDS}s"

    IMAGE_SIZE=$(docker image inspect "${IMAGE_SPEC}" --format='{{.Size}}' 2>/dev/null || echo "0")
    if [[ "${IMAGE_SIZE}" != "0" ]]; then
        IMAGE_SIZE_MB=$((IMAGE_SIZE / 1024 / 1024))
        IMAGE_SIZE_GB=$(awk "BEGIN {printf \"%.2f\", ${IMAGE_SIZE_MB}/1024}")
        log_kv "Image size" "${IMAGE_SIZE_MB} MB (${IMAGE_SIZE_GB} GB)"
        if [[ ${IMAGE_SIZE_MB} -gt 3072 ]]; then
            log_warn "Image size exceeds 3GB target. Consider optimization."
        else
            log_success "Image size within 3GB target"
        fi
    fi

    log_blank
    log_section "Quick Start"
    log_info "  Run container:"
    log_info "    docker run -d -p 8888:8888 -p 2222:22 --name caffe ${IMAGE_SPEC}"
    log_info ""
    log_info "  View logs (get credentials):"
    log_info "    docker logs caffe"
    log_info ""
    log_info "  Jupyter URL:  http://localhost:8888/ (token: caffe-token)"
    log_info "  SSH:          ssh builder@localhost -p 2222 (password: caffepass)"
    log_info ""
    log_info "  Verify:"
    log_info "    docker exec caffe caffe-verify"
    log_info ""
    log_info "  Export for customer distribution:"
    log_info "    $(dirname $0)/export.sh -t ${TAG}"
    log_blank
    log_success "Build complete!"
else
    log_header "BUILD FAILED"
    log_error "Build failed with exit code: ${BUILD_EXIT_CODE}"
    log_kv "Duration" "${BUILD_MINUTES}m ${BUILD_SECONDS}s"
    exit ${BUILD_EXIT_CODE}
fi
