#!/bin/bash
set -e

echo "=== Generating Makefile.config for Caffe ==="

if [ -n "${CAFFE_ROOT:-}" ]; then
    cd "${CAFFE_ROOT}"
elif [ -f "Makefile" ]; then
    CAFFE_ROOT="$(pwd)"
else
    CAFFE_ROOT="/workspace/caffex"
    cd "${CAFFE_ROOT}"
fi

echo "Caffe root: ${CAFFE_ROOT}"

PYTHON_EXEC="${PYTHON_EXEC:-python3}"
PYTHON_VERSION=$(${PYTHON_EXEC} -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PYTHON_INCLUDE_DIR=$(${PYTHON_EXEC} -c "import sysconfig; print(sysconfig.get_path('include'))")
PYTHON_LIB_DIR="/usr/lib/x86_64-linux-gnu"
NUMPY_INCLUDE_DIR=$(${PYTHON_EXEC} -c "import numpy; print(numpy.get_include())")

echo "Python version: ${PYTHON_VERSION}"
echo "Python include: ${PYTHON_INCLUDE_DIR}"
echo "Python lib dir: ${PYTHON_LIB_DIR}"
echo "NumPy include: ${NUMPY_INCLUDE_DIR}"

BOOST_PYTHON_LIB=""
for cand in "boost_python${PYTHON_VERSION//./}" "boost_python3" "boost_python-py${PYTHON_VERSION//./}"; do
    if ldconfig -p 2>/dev/null | grep -q "lib${cand}\.so "; then
        BOOST_PYTHON_LIB="${cand}"
        echo "Found Boost.Python: lib${cand}.so"
        break
    fi
done

if [ -z "${BOOST_PYTHON_LIB}" ]; then
    PYVER_NODOT="${PYTHON_VERSION//./}"
    case "${PYVER_NODOT}" in
        38)  BOOST_PYTHON_LIB="boost_python38" ;;
        39)  BOOST_PYTHON_LIB="boost_python39" ;;
        310) BOOST_PYTHON_LIB="boost_python310" ;;
        311) BOOST_PYTHON_LIB="boost_python311" ;;
        *)   BOOST_PYTHON_LIB="boost_python3" ;;
    esac
    echo "Using default Boost.Python: lib${BOOST_PYTHON_LIB}.so"
fi

HDF5_INCLUDE_DIR=""
HDF5_LIB_DIR=""
if [ -d "/usr/include/hdf5/serial" ]; then
    HDF5_INCLUDE_DIR="/usr/include/hdf5/serial"
    HDF5_LIB_DIR="/usr/lib/x86_64-linux-gnu/hdf5/serial"
    echo "Found HDF5 (serial): ${HDF5_INCLUDE_DIR}"
fi

PY_LIB_NAME="python${PYTHON_VERSION}"

cat > Makefile.config << EOF
# Makefile.config for BVLC Caffe - Auto-generated for Docker (Ubuntu 22.04)

CPU_ONLY := 1

OPENCV_VERSION := 4

CUDA_DIR := /usr/local/cuda
CUDA_ARCH := -gencode arch=compute_35,code=sm_35 \\
		-gencode arch=compute_50,code=sm_50 \\
		-gencode arch=compute_60,code=sm_60 \\
		-gencode arch=compute_61,code=sm_61 \\
		-gencode arch=compute_70,code=sm_70 \\
		-gencode arch=compute_75,code=sm_75 \\
		-gencode arch=compute_80,code=sm_80 \\
		-gencode arch=compute_86,code=sm_86

BLAS := open

PYTHON_LIBRARIES := ${BOOST_PYTHON_LIB} ${PY_LIB_NAME}
PYTHON_INCLUDE := ${PYTHON_INCLUDE_DIR} \\
		${NUMPY_INCLUDE_DIR}
PYTHON_LIB := ${PYTHON_LIB_DIR}

INCLUDE_DIRS := \$(PYTHON_INCLUDE) ${HDF5_INCLUDE_DIR} /usr/include/opencv4 /usr/local/include /usr/include
LIBRARY_DIRS := \$(PYTHON_LIB) ${HDF5_LIB_DIR} /usr/local/lib /usr/lib /usr/lib/x86_64-linux-gnu

BUILD_DIR := build
DISTRIBUTE_DIR := distribute

TEST_GPUID := 0

Q ?= @

CXXFLAGS += -std=c++14 -Wno-deprecated-declarations -Wno-register -Wno-unused-variable -Wno-sign-compare -Wno-unused-function -Wno-strict-aliasing -Wno-unused-local-typedefs -Wno-ignored-qualifiers
LDFLAGS += -Wl,--no-as-needed
EOF

echo ""
echo "=== Makefile.config generated successfully ==="
echo ""
cat Makefile.config
echo ""
echo "=== Ready to build Caffe ==="
