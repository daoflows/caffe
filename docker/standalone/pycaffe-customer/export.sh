#!/usr/bin/env bash
# ==============================================================================
# PyCaffe Customer Distribution Image Export Script
# Exports the Docker image as a tar file for customer distribution.
# Optionally generates SHA256 checksum for integrity verification.
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
DEFAULT_OUTPUT_DIR="${SCRIPT_DIR}/dist"
DEFAULT_VERSION="1.0.0"

IMAGE_NAME="${DEFAULT_IMAGE_NAME}"
TAG="${DEFAULT_TAG}"
OUTPUT_DIR="${DEFAULT_OUTPUT_DIR}"
VERSION="${DEFAULT_VERSION}"
NO_CHECKSUM=""
COMPRESS=""

show_help() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Export PyCaffe Customer Docker image as a tar file for distribution.

Options:
  -t TAG          Image tag to export (default: ${DEFAULT_TAG})
  -n NAME         Image name (default: ${DEFAULT_IMAGE_NAME})
  -o DIR          Output directory (default: ${DEFAULT_OUTPUT_DIR})
  --version VER   Version string for filename (default: ${DEFAULT_VERSION})
  --no-checksum   Skip SHA256 checksum generation
  -z, --gzip      Compress with gzip (produces .tar.gz)
  -h, --help      Show this help

Examples:
  $(basename "$0")                           # Export with default settings
  $(basename "$0") -t v1.0.0                 # Export specific tag
  $(basename "$0") -t customer -z            # Export and gzip compress
  $(basename "$0") -o /tmp/                  # Export to specific directory

Customer instructions (include these with the tar file):
  1. Load:   docker load -i caffe-cpu-customer-<version>.tar
  2. Run:    docker run -d -p 8888:8888 -p 2222:22 caffe-cpu:customer
  3. Access: http://localhost:8888/ (token: caffe-token)
  4. Verify: docker exec <container> caffe-verify
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
        -n)
            IMAGE_NAME="$2"
            shift 2
            ;;
        -o)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --version)
            VERSION="$2"
            shift 2
            ;;
        --no-checksum)
            NO_CHECKSUM="yes"
            shift
            ;;
        -z|--gzip)
            COMPRESS="gzip"
            shift
            ;;
        *)
            log_error "Unknown option: $1"
            log_info "Use -h for help"
            exit 1
            ;;
    esac
done

IMAGE_SPEC="${IMAGE_NAME}:${TAG}"
DATE_STR=$(date +%Y%m%d)

if [[ -n "${COMPRESS}" ]]; then
    OUTPUT_FILE="${OUTPUT_DIR}/caffe-cpu-customer-${VERSION}-${DATE_STR}.tar.gz"
else
    OUTPUT_FILE="${OUTPUT_DIR}/caffe-cpu-customer-${VERSION}-${DATE_STR}.tar"
fi

log_header "PyCaffe Customer Image Export"

log_section "Pre-flight Checks"

if ! command -v docker &>/dev/null; then
    log_error "docker command not found"
    exit 1
fi
log_success "Docker found"

if ! docker image inspect "${IMAGE_SPEC}" &>/dev/null; then
    log_error "Image '${IMAGE_SPEC}' not found"
    log_info "Build it first:  ${SCRIPT_DIR}/build.sh"
    exit 1
fi
log_success "Image exists: ${IMAGE_SPEC}"

IMAGE_SIZE=$(docker image inspect "${IMAGE_SPEC}" --format='{{.Size}}' 2>/dev/null || echo "0")
IMAGE_SIZE_MB=$((IMAGE_SIZE / 1024 / 1024))
log_kv "Image size" "${IMAGE_SIZE_MB} MB"

mkdir -p "${OUTPUT_DIR}"
log_success "Output directory: ${OUTPUT_DIR}"

log_section "Exporting"
log_info "Exporting ${IMAGE_SPEC} -> ${OUTPUT_FILE}"
log_warn "This may take several minutes depending on image size..."
log_blank

EXPORT_START_TS=$(date +%s)

if [[ -n "${COMPRESS}" ]]; then
    docker save "${IMAGE_SPEC}" | gzip > "${OUTPUT_FILE}"
else
    docker save "${IMAGE_SPEC}" -o "${OUTPUT_FILE}"
fi

EXPORT_END_TS=$(date +%s)
EXPORT_DURATION=$((EXPORT_END_TS - EXPORT_START_TS))
EXPORT_MINUTES=$((EXPORT_DURATION / 60))
EXPORT_SECONDS=$((EXPORT_DURATION % 60))

log_blank

if [[ ! -f "${OUTPUT_FILE}" ]]; then
    log_error "Export failed: output file not created"
    exit 1
fi

FILE_SIZE=$(stat -c%s "${OUTPUT_FILE}" 2>/dev/null || stat -f%z "${OUTPUT_FILE}" 2>/dev/null || echo "0")
FILE_SIZE_MB=$((FILE_SIZE / 1024 / 1024))

log_success "Export complete!"
log_kv "Output file" "${OUTPUT_FILE}"
log_kv "File size"   "${FILE_SIZE_MB} MB"
log_kv "Duration"    "${EXPORT_MINUTES}m ${EXPORT_SECONDS}s"

if [[ -z "${NO_CHECKSUM}" ]]; then
    log_section "Checksum"
    CHECKSUM_FILE="${OUTPUT_FILE}.sha256"
    if command -v sha256sum &>/dev/null; then
        sha256sum "${OUTPUT_FILE}" > "${CHECKSUM_FILE}"
        log_success "SHA256 checksum: $(cat ${CHECKSUM_FILE})"
        log_info "Checksum saved to: ${CHECKSUM_FILE}"
    elif command -v shasum &>/dev/null; then
        shasum -a 256 "${OUTPUT_FILE}" > "${CHECKSUM_FILE}"
        log_success "SHA256 checksum: $(cat ${CHECKSUM_FILE})"
        log_info "Checksum saved to: ${CHECKSUM_FILE}"
    else
        log_warn "No sha256sum/shasum tool found; skipping checksum"
    fi
fi

log_section "Customer Instructions"
echo ""
echo "  Send these files to the customer:"
echo "    1. ${OUTPUT_FILE}"
if [[ -z "${NO_CHECKSUM}" && -f "${CHECKSUM_FILE:-}" ]]; then
echo "    2. ${CHECKSUM_FILE}"
fi
echo ""
echo "  Customer quick start:"
echo "    1. Load image:   docker load -i $(basename ${OUTPUT_FILE})"
if [[ -z "${NO_CHECKSUM}" && -f "${CHECKSUM_FILE:-}" ]]; then
echo "       (verify with: sha256sum -c $(basename ${CHECKSUM_FILE}))"
fi
echo "    2. Run:"
echo "       docker run -d -p 8888:8888 -p 2222:22 --name caffe ${IMAGE_SPEC}"
echo "    3. Jupyter:     http://localhost:8888/  (token: caffe-token)"
echo "    4. SSH:         ssh builder@localhost -p 2222  (password: caffepass)"
echo "    5. Verify:      docker exec caffe caffe-verify"
echo ""
echo "  See README.md for complete documentation."
echo ""
log_success "Export finished!"
