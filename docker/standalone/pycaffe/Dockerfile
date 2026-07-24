# ==============================================================================
# PyCaffe 独立 Dockerfile (CPU-only, Ubuntu 26.04)
#
# 说明：基�?ubuntu:26.04，仅使用 浠?caffe-slim/ 目录（含 C++ 源码、头文件、pycaffe�?#       �?tvm-ffi/ 子模块，从零构建 pycaffe wheel。不依赖 caffex/�?#
# 构建上下�? vendor/（caffe 的父目录，以便同时访�?caffe/caffe-slim/ �?tvm-ffi/�?#
# 构建目标 (--target):
#   base-system      公共基础层（apt换源、CA证书、基础工具�?#   base-builder     基础构建环境（系统构建依�?+ Python 科学计算包）
#   pycaffe-builder  PyCaffe wheel 构建阶段（CMake + Ninja，自包含编译�?#   runtime          完整运行时镜像（pycaffe wheel�?#
# 使用示例:
#   cd vendor && docker build -t caffe-cpu:standalone-pycaffe --target runtime -f caffe/docker/standalone/pycaffe/Dockerfile .
# ==============================================================================

# ==============================================================================
# 阶段 0: base-system �?公共基础层（Ubuntu 26.04�?# ==============================================================================
FROM ubuntu:26.04 AS base-system

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple \
    PIP_TRUSTED_HOST=mirrors.aliyun.com \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

# 阿里云镜像源
RUN set -eux; \
    sed -i 's|http://archive.ubuntu.com/ubuntu/|http://mirrors.aliyun.com/ubuntu/|g' /etc/apt/sources.list; \
    sed -i 's|http://security.ubuntu.com/ubuntu/|http://mirrors.aliyun.com/ubuntu/|g' /etc/apt/sources.list

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
# 阶段 1: base-builder �?构建工具�?+ Python 科学计算�?# ==============================================================================
FROM base-system AS base-builder

ARG BUILDER_USER=builder
ARG BUILDER_UID=1000
ARG BUILDER_GID=1000
ARG WORKSPACE_DIR=/workspace

LABEL stage=base-builder
LABEL maintainer="Caffe Standalone Docker (Ubuntu 26.04)"
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
        sudo \
        vim \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 设置 python3 为默�?python
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3 1 && \
    update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 1 && \
    python --version && \
    pip --version

# 安装 Python 科学计算�?RUN pip install --break-system-packages --no-cache-dir \
        "numpy" \
        "scipy>=1.7" \
        "matplotlib>=3.5" \
        "scikit-image>=0.19" \
        "h5py>=3.6" \
        "networkx>=2.6" \
        "pandas>=1.4" \
        "pyyaml>=6.0" \
        "pillow>=9.0" \
        "six>=1.16" \
        "Cython>=0.29" \
        "protobuf>=7.0" \
        "python-dateutil>=2.8" \
        "python-gflags>=3.1"

# 验证核心包导�?RUN python -c "import numpy; print('numpy:', numpy.__version__)" && \
    python -c "import scipy; print('scipy:', scipy.__version__)" && \
    python -c "import matplotlib; print('matplotlib:', matplotlib.__version__)" && \
    python -c "import google.protobuf; print('protobuf:', google.protobuf.__version__)" && \
    echo "All core packages imported successfully"

# 环境变量
ENV WORKSPACE_DIR=/workspace \
    LD_LIBRARY_PATH=/workspace/caffe-slim/pycaffe/caffe-slim/pycaffe:/usr/lib:/usr/lib/x86_64-linux-gnu:/usr/local/lib \
    PYTHONPATH=/workspace/caffe-slim

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
# 阶段 2: pycaffe-builder �?PyCaffe wheel 构建（自包含 CMake + Ninja�?#
# caffe-slim/pycaffe/CMakeLists.txt 会：
#   1. 编译 caffe_core 静态库（从 caffe-slim/src/caffe/*.cpp�?#   2. 编译 _caffe.so 共享库（�?caffe-slim/pycaffe/caffe-slim/pycaffe/_caffe.cpp�?#   3. 打包 tvm_ffi 共享库到 wheel �?# 无需预先编译 Caffe 库，整个过程�?scikit-build-core 驱动�?CMake 完成�?# ==============================================================================
FROM base-builder AS pycaffe-builder

ARG CAFFE_VERSION=1.0.0-slim
ARG WORKSPACE_DIR=/workspace

LABEL stage=pycaffe-builder
LABEL caffe.version=${CAFFE_VERSION}

USER root

# 复制 浠?caffe-slim/ 源码（含 C++ 源码、头文件、pycaffe、caffeproto�?COPY --chown=${BUILDER_USER}:${BUILDER_USER} caffe/caffe-slim ${WORKSPACE_DIR}/caffe-slim

# 复制 tvm-ffi 子模块（caffe-slim/pycaffe/CMakeLists.txt 引用 ../../../tvm-ffi�?COPY --chown=${BUILDER_USER}:${BUILDER_USER} tvm-ffi ${WORKSPACE_DIR}/tvm-ffi

# 安装 Python build 工具
# --no-isolation 跳过隔离环境，避�?EXTERNALLY-MANAGED 导致�?pip 安装失败
RUN pip install --break-system-packages --no-cache-dir \
    build scikit-build-core ninja cmake numpy

USER ${BUILDER_USER}
WORKDIR ${WORKSPACE_DIR}/caffe-slim/pycaffe

# 构建 pycaffe wheel（scikit-build-core 驱动 CMake + Ninja 编译并打包）
RUN set -eux; \
    echo "========================================"; \
    echo "  Building PyCaffe Wheel (CMake+Ninja)"; \
    echo "========================================"; \
    echo "Caffe Version: ${CAFFE_VERSION}"; \
    echo ""; \
    echo "=== Step 1: Building pycaffe wheel ==="; \
    python -m build --wheel --no-isolation --outdir dist/; \
    echo ""; \
    echo "=== Step 2: Verifying wheel contents ==="; \
    ls -lh dist/*.whl; \
    echo ""; \
    echo "=== Step 3: Listing wheel contents ==="; \
    python -c "import zipfile; z=zipfile.ZipFile('dist/' + [f for f in __import__('os').listdir('dist') if f.endswith('.whl')][0]); print('\n'.join(z.namelist()))" 2>/dev/null || true; \
    echo ""; \
    echo "========================================"; \
    echo "  PyCaffe wheel build complete!"; \
    echo "========================================"

# ==============================================================================
# 阶段 3: runtime �?完整运行时镜�?# ==============================================================================
FROM base-builder AS runtime

ARG CAFFE_VERSION=1.0.0-slim
ARG WORKSPACE_DIR=/workspace

LABEL maintainer="Caffe Standalone Docker (Ubuntu 26.04)"
LABEL description="PyCaffe CPU-only standalone runtime (caffe-slim/ only)"
LABEL caffe.version=${CAFFE_VERSION}

USER root

# �?pycaffe-builder 复制 wheel
COPY --from=pycaffe-builder ${WORKSPACE_DIR}/caffe-slim/pycaffe/dist ${WORKSPACE_DIR}/caffe-slim/pycaffe/dist

# 复制验证脚本
COPY caffe/docker/standalone/pycaffe/scripts/verify-pycaffe.sh /usr/local/bin/verify-pycaffe.sh
RUN chmod +x /usr/local/bin/verify-pycaffe.sh

# 设置环境变量：使用纯 Python protobuf 实现（避�?C++ protobuf 兼容性问题）
ENV PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python

# 安装 pycaffe wheel
RUN set -eux; \
    echo "=== Installing pycaffe wheel ==="; \
    pip install --break-system-packages --no-cache-dir ${WORKSPACE_DIR}/caffe-slim/pycaffe/dist/*.whl; \
    echo ""; \
    echo "=== Verifying wheel installation ==="; \
    pip show pycaffe 2>&1 || true; \
    pip show -f pycaffe 2>&1 || true

# 验证 pycaffe 导入
RUN set -eux; \
    echo "=== Verifying pycaffe import ==="; \
    python -c "import pycaffe; print('pycaffe version:', pycaffe.__version__)"; \
    echo ""; \
    echo "=== Running pycaffe verification ==="; \
    verify-pycaffe.sh; \
    echo ""; \
    echo "=== pycaffe verification completed ==="

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD python -c "import pycaffe; print(pycaffe.__version__)" || exit 1

USER ${BUILDER_USER}
WORKDIR ${WORKSPACE_DIR}

CMD ["/bin/bash"]