#!/bin/bash
# Caffe Installation Verification Script
# Robust container validation tool with colored output and summary

# Color definitions (ANSI escape codes, compatible with bash 3+)
if [ -t 1 ]; then
    COLOR_GREEN='\033[0;32m'
    COLOR_RED='\033[0;31m'
    COLOR_BLUE='\033[0;34m'
    COLOR_CYAN='\033[0;36m'
    COLOR_YELLOW='\033[0;33m'
    COLOR_RESET='\033[0m'
else
    COLOR_GREEN=''
    COLOR_RED=''
    COLOR_BLUE=''
    COLOR_CYAN=''
    COLOR_YELLOW=''
    COLOR_RESET=''
fi

# Counters
TOTAL_CHECKS=0
PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0
FAILED_ITEMS=""
WARNED_ITEMS=""

# Environment setup
CAFFE_ROOT="${CAFFE_ROOT:-/workspace/caffex}"
export LD_LIBRARY_PATH="${CAFFE_ROOT}/build/lib:${LD_LIBRARY_PATH:-}"
export PYTHONPATH="${CAFFE_ROOT}/python:${PYTHONPATH:-}"

# Helper functions
print_title() {
    echo -e "${COLOR_CYAN}${1}${COLOR_RESET}"
}

print_info() {
    echo -e "${COLOR_BLUE}[INFO]${COLOR_RESET} $1"
}

print_pass() {
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    PASS_COUNT=$((PASS_COUNT + 1))
    echo -e "${COLOR_GREEN}[PASS]${COLOR_RESET} $1"
}

print_fail() {
    local msg="$1"
    local detail="$2"
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    FAIL_COUNT=$((FAIL_COUNT + 1))
    FAILED_ITEMS="${FAILED_ITEMS}  - ${msg}"
    if [ -n "$detail" ]; then
        FAILED_ITEMS="${FAILED_ITEMS}: ${detail}"
    fi
    FAILED_ITEMS="${FAILED_ITEMS}"$'\n'
    echo -e "${COLOR_RED}[FAIL]${COLOR_RESET} ${msg}"
    if [ -n "$detail" ]; then
        echo -e "       ${COLOR_RED}${detail}${COLOR_RESET}"
    fi
}

print_warn() {
    local msg="$1"
    local detail="$2"
    WARN_COUNT=$((WARN_COUNT + 1))
    WARNED_ITEMS="${WARNED_ITEMS}  - ${msg}"
    if [ -n "$detail" ]; then
        WARNED_ITEMS="${WARNED_ITEMS}: ${detail}"
    fi
    WARNED_ITEMS="${WARNED_ITEMS}"$'\n'
    echo -e "${COLOR_YELLOW}[WARN]${COLOR_RESET} ${msg}"
    if [ -n "$detail" ]; then
        echo -e "       ${COLOR_YELLOW}${detail}${COLOR_RESET}"
    fi
}

run_check() {
    local description="$1"
    shift
    if "$@" > /dev/null 2>&1; then
        print_pass "$description"
        return 0
    else
        print_fail "$description" "Command failed: $*"
        return 1
    fi
}

run_python_check() {
    local description="$1"
    local python_code="$2"
    local version_check="$3"
    local result
    result=$(python3 -c "$python_code" 2>&1)
    local exit_code=$?
    if [ $exit_code -eq 0 ]; then
        if [ -n "$version_check" ]; then
            local ver
            ver=$(echo "$result" | head -1)
            if echo "$ver" | grep -qE "^$version_check"; then
                print_pass "$description ($ver)"
                return 0
            else
                print_fail "$description" "Version mismatch: got $ver, expected $version_check.x"
                return 1
            fi
        else
            print_pass "$description"
            return 0
        fi
    else
        print_fail "$description" "$result"
        return 1
    fi
}

# Main header
echo ""
echo -e "${COLOR_CYAN}========================================${COLOR_RESET}"
echo -e "${COLOR_CYAN}  Caffe Installation Verification${COLOR_RESET}"
echo -e "${COLOR_CYAN}========================================${COLOR_RESET}"
echo ""

# Environment information
print_title "=== Environment Information ==="
print_info "CAFFE_ROOT: ${CAFFE_ROOT}"
print_info "LD_LIBRARY_PATH: ${LD_LIBRARY_PATH}"
print_info "PYTHONPATH: ${PYTHONPATH}"
echo ""

# Check 1: Python version
print_title "=== Python Environment ==="
PYTHON_VERSION_OUTPUT=$(python3 --version 2>&1)
if echo "$PYTHON_VERSION_OUTPUT" | grep -qE "^Python 3\."; then
    print_pass "Python version check ($PYTHON_VERSION_OUTPUT)"
else
    print_fail "Python version check" "$PYTHON_VERSION_OUTPUT"
fi

# Check 2: numpy
run_python_check "numpy import and version" \
    "import numpy; print(numpy.__version__)"

# Check 3: scipy
run_python_check "scipy import and version" \
    "import scipy; print(scipy.__version__)"

# Check 4: protobuf (3.x required, not 4.x)
PROTOBUF_VERSION=$(python3 -c "import google.protobuf; print(google.protobuf.__version__)" 2>&1)
PROTOBUF_EXIT=$?
if [ $PROTOBUF_EXIT -eq 0 ]; then
    if echo "$PROTOBUF_VERSION" | grep -qE "^3\."; then
        print_pass "google.protobuf import and version (${PROTOBUF_VERSION}) - 3.x compatible"
    else
        print_fail "google.protobuf version check" "Got ${PROTOBUF_VERSION}, Caffe requires protobuf 3.x (4.x is incompatible)"
    fi
else
    print_fail "google.protobuf import" "$PROTOBUF_VERSION"
fi

echo ""
print_title "=== Caffe Library Files ==="

# Check 5: libcaffe.so exists
if ls ${CAFFE_ROOT}/build/lib/libcaffe.so* > /dev/null 2>&1; then
    LIBCAFFE_FILES=$(ls -lh ${CAFFE_ROOT}/build/lib/libcaffe.so* 2>/dev/null | awk '{print $NF}' | head -1)
    print_pass "libcaffe.so dynamic library exists (${LIBCAFFE_FILES})"
else
    print_fail "libcaffe.so dynamic library check" "Not found in ${CAFFE_ROOT}/build/lib/"
fi

# Check 6: _caffe Python extension exists
if ls ${CAFFE_ROOT}/python/caffe/_caffe*.so > /dev/null 2>&1; then
    _CAFFE_FILES=$(ls -lh ${CAFFE_ROOT}/python/caffe/_caffe*.so 2>/dev/null | awk '{print $NF}' | head -1)
    print_pass "_caffe*.so Python extension exists (${_CAFFE_FILES})"
else
    print_fail "_caffe*.so Python extension check" "Not found in ${CAFFE_ROOT}/python/caffe/"
fi

echo ""
print_title "=== Caffe Python Module ==="

# Check 7: caffe module import
CAFFE_IMPORT_RESULT=$(python3 -c "import caffe; print('OK')" 2>&1)
if [ $? -eq 0 ]; then
    print_pass "caffe module import (sys.path correctly set)"
else
    print_fail "caffe module import" "$CAFFE_IMPORT_RESULT"
fi

# Check 8: caffe version
CAFFE_VERSION_RESULT=$(python3 -c "import caffe; print(caffe.__version__)" 2>&1)
if [ $? -eq 0 ]; then
    print_pass "caffe version (${CAFFE_VERSION_RESULT})"
else
    print_fail "caffe version check" "$CAFFE_VERSION_RESULT"
fi

# Check 9: caffe.proto/caffe_pb2 import
CAFFE_PB2_RESULT=$(python3 -c "from caffe.proto import caffe_pb2; print('NetParameter:', caffe_pb2.NetParameter)" 2>&1)
if [ $? -eq 0 ]; then
    print_pass "caffe.proto (caffe_pb2) module import"
else
    print_fail "caffe.proto (caffe_pb2) import" "$CAFFE_PB2_RESULT"
fi

echo ""
print_title "=== Caffe Runtime Tests ==="

# Check 10: Blob creation and shape test
BLOB_TEST_CODE="
import caffe
import numpy as np
blob = caffe.Blob([1, 1, 1, 1])
shape = blob.shape
if list(shape) == [1, 1, 1, 1]:
    print('OK: shape =', shape)
else:
    raise Exception('Unexpected shape: {}'.format(shape))
"
BLOB_TEST_RESULT=$(python3 -c "$BLOB_TEST_CODE" 2>&1)
if [ $? -eq 0 ]; then
    print_pass "Blob creation test (1x1x1x1 shape verified)"
else
    print_fail "Blob creation test" "$BLOB_TEST_RESULT"
fi

# Check 11: Blob data read/write test (simple forward-like operation)
BLOB_DATA_TEST_CODE="
import caffe
import numpy as np
blob = caffe.Blob([1, 1, 2, 2])
data = np.array([[[[1.0, 2.0], [3.0, 4.0]]]], dtype=np.float32)
blob.data[...] = data
read_back = np.array(blob.data)
if np.allclose(read_back, data):
    print('OK: data read/write verified, sum =', read_back.sum())
else:
    raise Exception('Data mismatch after write/read')
"
BLOB_DATA_RESULT=$(python3 -c "$BLOB_DATA_TEST_CODE" 2>&1)
if [ $? -eq 0 ]; then
    print_pass "Blob data read/write test (forward computation readiness)"
else
    print_fail "Blob data read/write test" "$BLOB_DATA_RESULT"
fi

echo ""
print_title "=== Caffe Command Line Tools (Optional) ==="

# Check 12: caffe CLI tools (WARN only, not FAIL)
CAFFE_TOOLS="caffe compute_image_mean convert_imageset upgrade_net_proto_text upgrade_solver_proto_text"
MISSING_TOOLS=""
for tool in $CAFFE_TOOLS; do
    TOOL_PATH="${CAFFE_ROOT}/build/tools/${tool}"
    if [ -x "${TOOL_PATH}" ]; then
        print_info "  CLI tool found: ${tool}"
    else
        MISSING_TOOLS="${MISSING_TOOLS} ${tool}"
    fi
done
if [ -n "$MISSING_TOOLS" ]; then
    print_warn "Some CLI tools not found" "Missing:${MISSING_TOOLS} (not required for Python usage)"
else
    print_pass "All CLI tools present"
fi

echo ""
echo -e "${COLOR_CYAN}========================================${COLOR_RESET}"
print_title "=== Verification Summary ==="
echo ""

print_info "Total checks: ${TOTAL_CHECKS}"
echo -e "  ${COLOR_GREEN}PASSED:${COLOR_RESET} ${PASS_COUNT}"
echo -e "  ${COLOR_RED}FAILED:${COLOR_RESET} ${FAIL_COUNT}"
if [ $WARN_COUNT -gt 0 ]; then
    echo -e "  ${COLOR_YELLOW}WARNINGS:${COLOR_RESET} ${WARN_COUNT}"
fi
echo ""

if [ $FAIL_COUNT -gt 0 ]; then
    echo -e "${COLOR_RED}Failed items:${COLOR_RESET}"
    echo -e "${COLOR_RED}${FAILED_ITEMS}${COLOR_RESET}"
fi

if [ $WARN_COUNT -gt 0 ]; then
    echo -e "${COLOR_YELLOW}Warning items:${COLOR_RESET}"
    echo -e "${COLOR_YELLOW}${WARNED_ITEMS}${COLOR_RESET}"
fi

echo ""
if [ $FAIL_COUNT -eq 0 ]; then
    echo -e "${COLOR_GREEN}========================================${COLOR_RESET}"
    echo -e "${COLOR_GREEN}  ALL CHECKS PASSED${COLOR_RESET}"
    echo -e "${COLOR_GREEN}========================================${COLOR_RESET}"
    echo ""
    exit 0
else
    echo -e "${COLOR_RED}========================================${COLOR_RESET}"
    echo -e "${COLOR_RED}  VERIFICATION FAILED${COLOR_RESET}"
    echo -e "${COLOR_RED}  ${FAIL_COUNT} check(s) failed${COLOR_RESET}"
    echo -e "${COLOR_RED}========================================${COLOR_RESET}"
    echo ""
    exit 1
fi
