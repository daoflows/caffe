# ==============================================================================
# PyCaffe 独立 Dockerfile (CPU-only, Ubuntu 24.04)
#
# 说明：基于 ubuntu:24.04，仅使用 caffe-slim/ 目录（含 C++ 源码、头文件、pycaffe、
#       caffeproto）和 tvm-ffi/ 子模块，从零构建。不依赖 caffex/、
#       python-module 或任何内部预构建镜像。
# 构建上下文：vendor/（caffe 的父目录，以便同时访问 caffe/caffe-slim/ 和 tvm-ffi/）
#
# 构建目标 (--target):
#   base-system      公共基础层（apt换源、CA证书、基础工具）
#   base-builder     基础构建环境（系统构建依赖 + Python 科学计算包）
#   caffe-builder    Caffe + tvm-ffi 构建阶段（CMake + Ninja）
#   runtime          完整运行时镜像（安装 pycaffe + 验证）
#
# 使用示例:
#   cd vendor && docker build -t caffe-cpu:standalone-pycaffe --target runtime -f caffe/docker/standalone/pycaffe/Dockerfile .
# ==============================================================================

# ==============================================================================
# 阶段 0: base-system — 公共基础层（Ubuntu 24.04）
# ==============================================================================
FROM ubuntu:24.04 AS base-system

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple \
    PIP_TRUSTED_HOST=mirrors.aliyun.com \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

# 阿里云镜像源
RUN set -eux; \
    cp /etc/apt/sources.list /etc/apt/sources.list.bak; \
    cat > /etc/apt/sources.list << 'EOF'
deb http://mirrors.aliyun.com/ubuntu/ noble main restricted universe multiverse
deb http://mirrors.aliyun.com/ubuntu/ noble-updates main restricted universe multiverse
deb http://mirrors.aliyun.com/ubuntu/ noble-backports main restricted universe multiverse
deb http://mirrors.aliyun.com/ubuntu/ noble-security main restricted universe multiverse
EOF

# 基础工具
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        libgomp1 \
        procps \
        tzdata \
        wget \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# ==============================================================================
# 阶段 1: base-builder — 构建工具链 + Python 科学计算包
# ==============================================================================
FROM base-system AS base-builder

ARG BUILDER_USER=builder
ARG BUILDER_UID=1000
ARG BUILDER_GID=1000
ARG WORKSPACE_DIR=/workspace

LABEL stage=base-builder
LABEL maintainer="Caffe Standalone Docker (Ubuntu 24.04)"
LABEL description="PyCaffe standalone build environment (caffe-slim/ only)"

# 安装 C++ 编译工具链和构建依赖
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        bash-completion \
        build-essential \
        cmake \
        gdb \
        git \
        less \
        ninja-build \
        libopenblas-dev \
        libprotobuf-dev \
        pkg-config \
        protobuf-compiler \
        python3-dev \
        python3-pip \
        python3-setuptools \
        python3-wheel \
        python3-venv \
        sudo \
        vim \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 设置 python3 为默认 python
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3 1 && \
    update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 1 && \
    python --version && \
    pip --version

# 安装 Python 科学计算包 + 构建工具
RUN pip install --break-system-packages --no-cache-dir \
        "numpy<2" \
        "scipy>=1.7" \
        "matplotlib>=3.5" \
        "scikit-image>=0.19" \
        "h5py>=3.6" \
        "networkx>=2.6" \
        "pandas>=1.4" \
        "pyyaml>=6.0" \
        "pillow>=9.0" \
        "six>=1.16" \
        "Cython>=3.2.8" \
        "protobuf" \
        "python-dateutil>=2.8" \
        "typing-extensions>=4.5" \
        "setuptools-scm" \
        "scikit-build-core>=0.10"

# 验证核心包导入
RUN python -c "import numpy; print('numpy:', numpy.__version__)" && \
    python -c "import scipy; print('scipy:', scipy.__version__)" && \
    python -c "import google.protobuf; print('protobuf:', google.protobuf.__version__)" && \
    echo "All core packages imported successfully"

# 环境变量
ENV WORKSPACE_DIR=/workspace \
    LD_LIBRARY_PATH=/usr/local/lib:/usr/lib:/usr/lib/x86_64-linux-gnu

# 创建 builder 用户
RUN set -eux; \
    if ! getent group ${BUILDER_USER} >/dev/null; then \
        if getent group ${BUILDER_GID} >/dev/null; then \
            groupadd ${BUILDER_USER}; \
        else \
            groupadd -g ${BUILDER_GID} ${BUILDER_USER}; \
        fi; \
    fi; \
    if id -u ${BUILDER_USER} >/dev/null 2>&1; then \
        usermod -g ${BUILDER_USER} -s /bin/bash ${BUILDER_USER}; \
    else \
        if getent passwd ${BUILDER_UID} >/dev/null; then \
            useradd -m -s /bin/bash -g ${BUILDER_USER} ${BUILDER_USER}; \
        else \
            useradd -m -s /bin/bash -u ${BUILDER_UID} -g ${BUILDER_GID} ${BUILDER_USER}; \
        fi; \
    fi; \
    usermod -aG sudo ${BUILDER_USER}; \
    echo "${BUILDER_USER} ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/90-${BUILDER_USER}; \
    chmod 0440 /etc/sudoers.d/90-${BUILDER_USER}; \
    mkdir -p ${WORKSPACE_DIR}; \
    chown -R ${BUILDER_UID}:${BUILDER_GID} ${WORKSPACE_DIR}

# ==============================================================================
# 阶段 2: caffe-builder — 构建 tvm-ffi + caffe-slim
# ==============================================================================
FROM base-builder AS caffe-builder

ARG CAFFE_VERSION=1.0.0
ARG WORKSPACE_DIR=/workspace

LABEL stage=caffe-builder
LABEL caffe.version=${CAFFE_VERSION}-slim

USER root

# 创建正确的目录结构（caffe-slim 期望在 caffe/caffe-slim/，tvm-ffi 在同级目录）
RUN mkdir -p ${WORKSPACE_DIR}/caffe

# 复制 tvm-ffi 源码
COPY tvm-ffi ${WORKSPACE_DIR}/tvm-ffi

# 复制 caffe-slim 源码（放到 caffe/caffe-slim/ 以符合 CMakeLists.txt 的路径预期）
COPY caffe/caffe-slim ${WORKSPACE_DIR}/caffe/caffe-slim

# ========== 构建 tvm-ffi (Python 包 + 共享库) ==========
WORKDIR ${WORKSPACE_DIR}/tvm-ffi

# setuptools-scm 需要从 git 标签检测版本，Docker COPY 不包含 .git 目录
# 设置 SETUPTOOLS_SCM_PRETEND_VERSION 提供版本号
# 同时禁用 libbacktrace 以避免 3rdparty 编译问题（Windows 文件系统上 configure 脚本权限/换行符问题）
# 注意：SKBUILD_CMAKE_ARGS 会覆盖 pyproject.toml 中的默认 cmake.args，必须包含 TVM_FFI_BUILD_PYTHON_MODULE=ON
ENV SETUPTOOLS_SCM_PRETEND_VERSION=0.1.0 \
    SKBUILD_CMAKE_ARGS="-DTVM_FFI_ATTACH_DEBUG_SYMBOLS=ON;-DTVM_FFI_BUILD_TESTS=OFF;-DTVM_FFI_BUILD_PYTHON_MODULE=ON;-DTVM_FFI_USE_LIBBACKTRACE=OFF"

RUN set -eux; \
    echo "========================================"; \
    echo "  Building tvm-ffi (Cython + CMake)"; \
    echo "========================================"; \
    pip install --break-system-packages --no-cache-dir -v . --no-build-isolation; \
    echo "tvm-ffi build complete"; \
    python -c "import tvm_ffi; print('tvm_ffi version:', tvm_ffi.__version__)"

# ========== 构建 caffe-slim (_caffe.so) ==========
WORKDIR ${WORKSPACE_DIR}/caffe/caffe-slim

RUN set -eux; \
    echo "Checking directory structure:"; \
    ls -la ${WORKSPACE_DIR}/; \
    ls -la ${WORKSPACE_DIR}/tvm-ffi/CMakeLists.txt 2>/dev/null || echo "tvm-ffi/CMakeLists.txt NOT FOUND"; \
    echo "Expected tvm-ffi path: ${WORKSPACE_DIR}/caffe/caffe-slim/../../tvm-ffi = $(realpath ${WORKSPACE_DIR}/caffe/caffe-slim/../../tvm-ffi 2>/dev/null || echo 'INVALID')"; \
    echo "========================================"; \
    echo "  Building caffe-slim (_caffe.so)"; \
    echo "========================================"; \
    cmake -B build -G Ninja \
        -DCMAKE_BUILD_TYPE=Release \
        -DCAFFE_CPU_ONLY=ON \
        -DCAFFE_VERSION="${CAFFE_VERSION}-slim" \
        -DTVM_FFI_USE_LIBBACKTRACE=OFF \
        -DTVM_FFI_BACKTRACE_ON_SEGFAULT=OFF \
        -DCMAKE_INSTALL_PREFIX=${WORKSPACE_DIR}/caffe-install; \
    cmake --build build --parallel; \
    echo "caffe-slim build complete"; \
    ls -lh build/python/caffe/; \
    echo "Checking _caffe.so:"; \
    file build/python/caffe/_caffe.so || true

# 收集构建产物（包括 tvm-ffi 共享库和 Python 包）
RUN set -eux; \
    echo "Collecting build artifacts..."; \
    mkdir -p ${WORKSPACE_DIR}/build-output/lib ${WORKSPACE_DIR}/build-output/python; \
    cp build/python/caffe/_caffe.so ${WORKSPACE_DIR}/build-output/lib/; \
    echo "Locating libtvm_ffi.so..."; \
    find /usr -name "libtvm_ffi.so*" 2>/dev/null; \
    TVM_FFI_LIB=$(find /usr -name "libtvm_ffi.so" -type f 2>/dev/null | head -1 || true); \
    if [ -n "${TVM_FFI_LIB}" ]; then \
        cp "${TVM_FFI_LIB}" ${WORKSPACE_DIR}/build-output/lib/; \
        cp "${TVM_FFI_LIB}".* ${WORKSPACE_DIR}/build-output/lib/ 2>/dev/null || true; \
        echo "Copied libtvm_ffi.so from ${TVM_FFI_LIB}"; \
    fi; \
    echo "Collecting tvm_ffi Python package..."; \
    for sp in $(python -c "import site; print(' '.join(site.getsitepackages()))"); do \
        echo "Checking $sp for tvm_ffi..."; \
        if [ -d "$sp/tvm_ffi" ]; then \
            cp -r "$sp"/tvm_ffi* ${WORKSPACE_DIR}/build-output/python/; \
            echo "Found and copied tvm_ffi from $sp"; \
            ls -lh "$sp"/tvm_ffi* 2>/dev/null || true; \
            break; \
        fi; \
    done; \
    echo "Artifacts collected:"; \
    ls -lh ${WORKSPACE_DIR}/build-output/lib/; \
    echo "Python artifacts:"; \
    ls -lh ${WORKSPACE_DIR}/build-output/python/ 2>/dev/null || true

# ==============================================================================
# 阶段 3: runtime — 完整运行时镜像
# ==============================================================================
FROM base-builder AS runtime

ARG CAFFE_VERSION=1.0.0
ARG WORKSPACE_DIR=/workspace

LABEL maintainer="Caffe Standalone Docker (Ubuntu 24.04)"
LABEL description="PyCaffe CPU-only standalone runtime (caffe-slim/ + tvm-ffi)"
LABEL caffe.version=${CAFFE_VERSION}-slim

USER root

# 从 caffe-builder 复制构建产物
COPY --from=caffe-builder ${WORKSPACE_DIR}/build-output ${WORKSPACE_DIR}/build-output
COPY --from=caffe-builder ${WORKSPACE_DIR}/caffe ${WORKSPACE_DIR}/caffe

# 安装 tvm-ffi Python 包（直接复制已编译好的包）
RUN set -eux; \
    for sp in $(python -c "import site; print(' '.join(site.getsitepackages()))"); do \
        if [ -d "$sp" ]; then \
            cp -r ${WORKSPACE_DIR}/build-output/python/* $sp/ 2>/dev/null || true; \
            echo "Copied Python packages to $sp"; \
        fi; \
    done; \
    cp ${WORKSPACE_DIR}/build-output/lib/*.so* /usr/local/lib/; \
    ldconfig; \
    echo "tvm-ffi installed from cached build"; \
    python -c "import tvm_ffi; print('tvm_ffi version:', tvm_ffi.__version__)"

# 安装 Python 包：protos, caffeproto, caffe
# protos 包（caffe_pb2.py）
RUN set -eux; \
    SITE_PACKAGES=$(python -c "import site; print(site.getsitepackages()[0])"); \
    echo "Site packages: ${SITE_PACKAGES}"; \
    mkdir -p ${SITE_PACKAGES}/protos; \
    cp ${WORKSPACE_DIR}/caffe/caffe-slim/protos/caffe_pb2.py ${SITE_PACKAGES}/protos/; \
    cp ${WORKSPACE_DIR}/caffe/caffe-slim/protos/caffe.proto ${SITE_PACKAGES}/protos/; \
    touch ${SITE_PACKAGES}/protos/__init__.py; \
    echo "protos package installed"

# caffeproto 包
RUN set -eux; \
    SITE_PACKAGES=$(python -c "import site; print(site.getsitepackages()[0])"); \
    mkdir -p ${SITE_PACKAGES}/caffeproto; \
    cp ${WORKSPACE_DIR}/caffe/caffe-slim/caffeproto/__init__.py ${SITE_PACKAGES}/caffeproto/; \
    cp ${WORKSPACE_DIR}/caffe/caffe-slim/caffeproto/caffe_utils.py ${SITE_PACKAGES}/caffeproto/ 2>/dev/null || true; \
    cp ${WORKSPACE_DIR}/caffe/caffe-slim/caffeproto/caffe_fuse.py ${SITE_PACKAGES}/caffeproto/ 2>/dev/null || true; \
    echo "caffeproto package installed"

# caffe 包（新 tvm-ffi 版本）
RUN set -eux; \
    SITE_PACKAGES=$(python -c "import site; print(site.getsitepackages()[0])"); \
    mkdir -p ${SITE_PACKAGES}/caffe; \
    cp ${WORKSPACE_DIR}/caffe/caffe-slim/python/caffe/__init__.py ${SITE_PACKAGES}/caffe/; \
    cp /usr/local/lib/_caffe.so ${SITE_PACKAGES}/caffe/; \
    echo "caffe package installed"

# 创建 pycaffe 兼容包（适配旧 API）
RUN SITE_PACKAGES=$(python -c "import site; print(site.getsitepackages()[0])") && \
    mkdir -p ${SITE_PACKAGES}/pycaffe

RUN SITE_PACKAGES=$(python -c "import site; print(site.getsitepackages()[0])") && \
    cat > ${SITE_PACKAGES}/pycaffe/__init__.py << 'PYEOF'
"""pycaffe compatibility package - wraps caffe (tvm-ffi inference) with old API."""
from __future__ import annotations

import caffe as _caffe_mod

# Phase constants
TRAIN = 0
TEST = 1

# Re-export from caffe package
Net = _caffe_mod.Net
set_mode_cpu = _caffe_mod.set_mode_cpu
set_mode_gpu = _caffe_mod.set_mode_gpu if hasattr(_caffe_mod, 'set_mode_gpu') else lambda: None
set_device = _caffe_mod.set_device if hasattr(_caffe_mod, 'set_device') else lambda x: None
set_random_seed = _caffe_mod.set_random_seed
layer_type_list = _caffe_mod.layer_type_list
__version__ = _caffe_mod.version()

# Solver stubs (not available in slim inference-only build)
class _SolverStub:
    def __init__(self, *args, **kwargs):
        raise NotImplementedError(
            "Solver classes are not available in the slim inference-only build. "
            "Use origin image for full training support."
        )

SGDSolver = type("SGDSolver", (_SolverStub,), {})
NesterovSolver = type("NesterovSolver", (_SolverStub,), {})
AdaGradSolver = type("AdaGradSolver", (_SolverStub,), {})
RMSPropSolver = type("RMSPropSolver", (_SolverStub,), {})
AdaDeltaSolver = type("AdaDeltaSolver", (_SolverStub,), {})
AdamSolver = type("AdamSolver", (_SolverStub,), {})
NCCL = None
Timer = None

# Submodules
from . import transforms
from .transforms import DataProcessor, Transformer, load_image, load_image_batch, resize_image, oversample

try:
    from . import classifier
    from .classifier import Classifier
except ImportError:
    Classifier = None

try:
    from . import detector
    from .detector import Detector
except ImportError:
    Detector = None

try:
    from . import draw
except ImportError:
    pass

try:
    from . import net_spec
    from .net_spec import layers, params, NetSpec, to_proto
except ImportError:
    NetSpec = None

try:
    from . import coord_map
except ImportError:
    pass

# Logging stubs
import logging
log = logging.getLogger("pycaffe")

def init_log(name="pycaffe"):
    logging.basicConfig(level=logging.INFO)
    return logging.getLogger(name)

# Stub functions
def get_solver(*args, **kwargs):
    raise NotImplementedError("get_solver is not available in slim build")

def solver_count():
    return 1

def set_solver_count(val):
    pass

def solver_rank():
    return 0

def set_solver_rank(val):
    pass

def set_multiprocess(val):
    pass

def has_nccl():
    return False
PYEOF
RUN echo "pycaffe __init__.py created"

# 复制 pycaffe 子模块（旧 BVLC 风格的辅助模块）
RUN set -eux; \
    SITE_PACKAGES=$(python -c "import site; print(site.getsitepackages()[0])"); \
    PYCAFFE_PY=${WORKSPACE_DIR}/caffe/caffe-slim/pycaffe/python/pycaffe; \
    for f in transforms.py classifier.py detector.py draw.py net_spec.py coord_map.py data_types.py; do \
        if [ -f "${PYCAFFE_PY}/$f" ]; then \
            cp "${PYCAFFE_PY}/$f" ${SITE_PACKAGES}/pycaffe/; \
            echo "Copied $f"; \
        fi; \
    done; \
    touch ${SITE_PACKAGES}/pycaffe/py.typed 2>/dev/null || true; \
    echo "pycaffe submodules installed"

# 复制验证用的 LeNet prototxt
RUN mkdir -p ${WORKSPACE_DIR}/pycaffe && \
    cp ${WORKSPACE_DIR}/caffe/caffe-slim/pycaffe/lenet_deploy.prototxt ${WORKSPACE_DIR}/pycaffe/

# 创建验证脚本
RUN cat > /usr/local/bin/verify-pycaffe.sh << 'VEOF'
#!/bin/bash
set -euo pipefail

PASS=0
FAIL=0
SKIP=0

red()    { echo -e "\033[31m$*\033[0m"; }
green()  { echo -e "\033[32m$*\033[0m"; }
yellow() { echo -e "\033[33m$*\033[0m"; }
blue()   { echo -e "\033[34m$*\033[0m"; }

pass_msg() { green "  [PASS] $1"; PASS=$((PASS + 1)); }
fail_msg() { red   "  [FAIL] $1"; FAIL=$((FAIL + 1)); }
skip_msg() { yellow "  [SKIP] $1"; SKIP=$((SKIP + 1)); }

echo "=============================================="
echo "  PyCaffe Verification Suite (slim/inference)"
echo "=============================================="
echo ""

# 1. Import & Version
blue "--- 1. Import & Version ---"
if python -c "import pycaffe" 2>&1; then
    pass_msg "import pycaffe succeeded"
    VERSION=$(python -c "import pycaffe; print(pycaffe.__version__)" 2>&1)
    if [ -n "${VERSION}" ]; then
        pass_msg "pycaffe.__version__ = ${VERSION}"
    else
        fail_msg "pycaffe.__version__ is empty"
    fi
else
    fail_msg "import pycaffe failed"
fi

# 2. Constants
blue "--- 2. Phase Constants ---"
TRAIN_VAL=$(python -c "import pycaffe; print(pycaffe.TRAIN)" 2>/dev/null)
TEST_VAL=$(python -c "import pycaffe; print(pycaffe.TEST)" 2>/dev/null)
[ -n "${TRAIN_VAL}" ] && pass_msg "pycaffe.TRAIN = ${TRAIN_VAL}" || fail_msg "pycaffe.TRAIN not available"
[ -n "${TEST_VAL}" ] && pass_msg "pycaffe.TEST = ${TEST_VAL}" || fail_msg "pycaffe.TEST not available"

# 3. Net class
blue "--- 3. Net Class ---"
if python -c "from pycaffe import Net; print('Net class available')" 2>&1; then
    pass_msg "pycaffe.Net class available"
else
    fail_msg "pycaffe.Net class not available"
fi

# 4. set_mode_cpu
blue "--- 4. set_mode_cpu ---"
if python -c "import pycaffe; pycaffe.set_mode_cpu(); print('set_mode_cpu OK')" 2>&1; then
    pass_msg "pycaffe.set_mode_cpu() succeeded"
else
    fail_msg "pycaffe.set_mode_cpu() failed"
fi

# 5. LeNet forward pass
blue "--- 5. LeNet Forward Pass ---"
LENET_PROTO="${WORKSPACE_DIR}/pycaffe/lenet_deploy.prototxt"
if [ -f "${LENET_PROTO}" ]; then
    if python -c "
import pycaffe
pycaffe.set_mode_cpu()
net = pycaffe.Net('${LENET_PROTO}', pycaffe.TEST)
print('Net created successfully')
net.forward()
print('Forward pass OK')
print('Blob names:', net.blob_names)
print('Output names:', net.outputs)
" 2>&1; then
        pass_msg "LeNet Net creation and forward pass succeeded"
    else
        fail_msg "LeNet Net creation or forward pass failed"
    fi
else
    skip_msg "LeNet prototxt not found"
fi

# 6. Submodules
blue "--- 6. Submodules ---"
for submod in transforms classifier detector net_spec draw coord_map; do
    if python -c "import pycaffe.${submod}; print('${submod} OK')" 2>/dev/null; then
        pass_msg "pycaffe.${submod} import succeeded"
    else
        skip_msg "pycaffe.${submod} not available (optional)"
    fi
done

# 7. Solvers (stubbed in slim)
blue "--- 7. Solver Classes (stubbed in slim) ---"
for solver_cls in SGDSolver AdamSolver; do
    if python -c "from pycaffe import ${solver_cls}; print('${solver_cls} available (stub)')" 2>/dev/null; then
        pass_msg "pycaffe.${solver_cls} stub available"
    else
        fail_msg "pycaffe.${solver_cls} stub not available"
    fi
done

# Summary
echo ""
echo "=============================================="
TOTAL=$((PASS + FAIL + SKIP))
echo "  Results: ${PASS} PASS / ${FAIL} FAIL / ${SKIP} SKIP (${TOTAL} total)"
echo "=============================================="

if [ "${FAIL}" -gt 0 ]; then
    red "  Verification FAILED: ${FAIL} test(s) failed"
    exit 1
else
    green "  Verification PASSED"
    exit 0
fi
VEOF
RUN chmod +x /usr/local/bin/verify-pycaffe.sh

# 创建 parity 脚本（占位）
RUN cat > /usr/local/bin/verify-parity.sh << 'VEOF'
#!/bin/bash
echo "Parity check not applicable for slim inference-only build."
echo "Use origin image for full BVLC Caffe parity."
exit 0
VEOF
RUN chmod +x /usr/local/bin/verify-parity.sh

# 设置环境变量
ENV PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python \
    WORKSPACE_DIR=/workspace \
    LD_LIBRARY_PATH=/usr/local/lib:/usr/lib:/usr/lib/x86_64-linux-gnu

WORKDIR ${WORKSPACE_DIR}

# 验证 pycaffe 导入
RUN set -eux; \
    echo "=== Verifying pycaffe import ==="; \
    python -c "import pycaffe; print('pycaffe version:', pycaffe.__version__)"; \
    echo ""; \
    echo "=== Verifying caffe import ==="; \
    python -c "import caffe; print('caffe loaded successfully')"; \
    echo ""; \
    echo "=== Running pycaffe verification ==="; \
    verify-pycaffe.sh; \
    echo ""; \
    echo "=== Verification completed ==="

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD python -c "import pycaffe; print(pycaffe.__version__)" || exit 1

USER ${BUILDER_USER}

CMD ["/bin/bash"]
