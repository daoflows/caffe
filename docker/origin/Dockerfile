# ==============================================================================
# BVLC Caffe 多阶段 Dockerfile (CPU-only, Ubuntu 22.04 + System Python 3.10)
#
# 说明：使用 Ubuntu 22.04 自带的 Python 3.10 + pip 方式安装 Python 依赖。
#       Caffe 1.0 原生支持 Python 3。
#
# 构建目标 (--target):
#   base-system     公共基础层（apt换源、CA证书）
#   base-builder    基础构建环境（系统构建依赖 + Python 依赖）
#   builder         CI 构建阶段（编译 Caffe 源码）
#   runtime         完整运行时镜像（从 builder 获取编译产物）
#
# 使用示例:
#   docker build -t caffe-cpu:ci --target builder -f docker/origin/Dockerfile .
#   docker build -t caffe-cpu:latest --target runtime -f docker/origin/Dockerfile .
# ==============================================================================

# ==============================================================================
# 阶段 0: base-system — 公共基础层（Ubuntu 22.04）
# ==============================================================================
FROM ubuntu:22.04 AS base-system

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple \
    PIP_TRUSTED_HOST=mirrors.aliyun.com \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN set -eux; \
    sed -i 's@archive.ubuntu.com@mirrors.aliyun.com@g' /etc/apt/sources.list; \
    sed -i 's@security.ubuntu.com@mirrors.aliyun.com@g' /etc/apt/sources.list

RUN set -eux; \
    apt-get update -qq; \
    apt-get install -y --no-install-recommends -qq \
        ca-certificates \
        curl \
        libgomp1 \
        procps \
        tzdata \
        wget \
    ; \
    rm -rf /var/lib/apt/lists/*

# ==============================================================================
# 阶段 1: base-builder — 构建工具链基础
# 包含：编译工具链、Caffe 系统依赖、Python 3.10 + 科学计算包
# ==============================================================================
FROM base-system AS base-builder

ARG BUILDER_USER=builder
ARG BUILDER_UID=1000
ARG BUILDER_GID=1000
ARG WORKSPACE_DIR=/workspace

LABEL stage=base-builder
LABEL maintainer="Caffe Docker (Ubuntu 22.04)"
LABEL description="BVLC Caffe CPU-only build environment"

RUN set -eux; \
    apt-get update -qq; \
    apt-get install -y --no-install-recommends -qq \
        bash-completion \
        build-essential \
        cmake \
        gdb \
        git \
        less \
        libatlas-base-dev \
        libboost-all-dev \
        libgflags-dev \
        libgoogle-glog-dev \
        libhdf5-dev \
        libleveldb-dev \
        liblmdb-dev \
        libopencv-dev \
        libprotobuf-dev \
        libsnappy-dev \
        pkg-config \
        protobuf-compiler \
        python3-dev \
        python3-pip \
        python3-setuptools \
        python3-wheel \
        sudo \
        vim \
    ; \
    rm -rf /var/lib/apt/lists/*

RUN set -eux; \
    update-alternatives --install /usr/bin/python python /usr/bin/python3 1; \
    update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 1; \
    python --version; \
    pip --version

RUN set -eux; \
    pip install --no-cache-dir --upgrade pip==24.0 setuptools==68.0.0 wheel

RUN set -eux; \
    pip install --no-cache-dir \
        'numpy>=1.21,<2.0' \
        'scipy>=1.7' \
        'matplotlib>=3.5' \
        'scikit-image>=0.19' \
        'h5py>=3.6' \
        'networkx>=2.6' \
        'pandas>=1.4' \
        'pyyaml>=6.0' \
        'pillow>=9.0' \
        'six>=1.16' \
        'Cython>=0.29' \
        'ipython>=8.0' \
        'nose>=1.3' \
        'python-dateutil>=2.8' \
        'protobuf==3.20.3' \
        'python-gflags>=3.1' \
        'leveldb>=0.201'

RUN set -eux; \
    echo "=== Verifying Python packages ==="; \
    python --version; \
    python -c "import numpy; print('numpy:', numpy.__version__)"; \
    python -c "import scipy; print('scipy:', scipy.__version__)"; \
    python -c "import matplotlib; print('matplotlib:', matplotlib.__version__)"; \
    python -c "import google.protobuf; print('protobuf:', google.protobuf.__version__)"; \
    echo "All core packages imported successfully"

ENV WORKSPACE_DIR=/workspace \
    CC=gcc \
    CXX=g++ \
    CAFFE_ROOT=/workspace/caffex \
    PATH=/workspace/caffex/build/tools:${PATH} \
    LD_LIBRARY_PATH=/workspace/caffex/build/lib:/usr/lib:/usr/lib/x86_64-linux-gnu:/usr/local/lib \
    PYTHONPATH=/workspace/caffex/python

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

USER ${BUILDER_USER}
WORKDIR ${WORKSPACE_DIR}

# ==============================================================================
# 阶段 2: builder — CI 构建阶段（编译 Caffe 源码）
# ==============================================================================
FROM base-builder AS builder

ARG CAFFE_VERSION=1.0

LABEL stage=builder
LABEL caffe.version=${CAFFE_VERSION}

USER root

COPY --chown=${BUILDER_USER}:${BUILDER_USER} caffex ${WORKSPACE_DIR}/caffex
COPY docker/origin/scripts/generate-makefile-config.sh /usr/local/bin/generate-makefile-config.sh
COPY docker/origin/scripts/verify-caffe.sh /usr/local/bin/verify-caffe.sh
RUN chmod +x /usr/local/bin/generate-makefile-config.sh /usr/local/bin/verify-caffe.sh

USER ${BUILDER_USER}
WORKDIR ${WORKSPACE_DIR}/caffex

RUN set -eux; \
    echo "========================================"; \
    echo "  Building BVLC Caffe (CPU-only)"; \
    echo "========================================"; \
    echo "Caffe Version: ${CAFFE_VERSION}"; \
    echo ""; \
    echo "=== Step 1: Generating Makefile.config ==="; \
    generate-makefile-config.sh; \
    echo ""; \
    echo "=== Step 2: Compiling Caffe (CPU-only) ==="; \
    make all -j$(nproc) 2>&1 | tail -30; \
    echo ""; \
    echo "=== Step 3: Compiling PyCaffe ==="; \
    make pycaffe -j$(nproc) 2>&1 | tail -20; \
    echo ""; \
    echo "=== Step 4: Building tools ==="; \
    make tools -j$(nproc) 2>&1 | tail -20; \
    echo ""; \
    echo "=== Step 5: Verifying build artifacts ==="; \
    ls -lh build/lib/; \
    ls -lh python/caffe/_caffe*.so; \
    ls -lh build/tools/ 2>/dev/null || true; \
    echo ""; \
    echo "=== Step 6: Distribution ==="; \
    make distribute 2>&1 | tail -10; \
    echo ""; \
    echo "========================================"; \
    echo "  Build complete!"; \
    echo "========================================"

# ==============================================================================
# 阶段 3: runtime — 完整运行时镜像
# 基于 base-builder（已包含所有系统库和 Python 依赖），仅复制编译产物
# ==============================================================================
FROM base-builder AS runtime

ARG CAFFE_VERSION=1.0

LABEL maintainer="Caffe Docker (Ubuntu 22.04)"
LABEL description="BVLC Caffe CPU-only runtime environment"
LABEL caffe.version=${CAFFE_VERSION}

USER root

COPY --from=builder ${WORKSPACE_DIR}/caffex/build ${WORKSPACE_DIR}/caffex/build
COPY --from=builder ${WORKSPACE_DIR}/caffex/python ${WORKSPACE_DIR}/caffex/python
COPY --from=builder ${WORKSPACE_DIR}/caffex/distribute ${WORKSPACE_DIR}/caffex/distribute
COPY --from=builder ${WORKSPACE_DIR}/caffex/Makefile.config ${WORKSPACE_DIR}/caffex/Makefile.config
COPY docker/origin/scripts/verify-caffe.sh /usr/local/bin/verify-caffe.sh
RUN chmod +x /usr/local/bin/verify-caffe.sh

# 创建 libcaffe.so 符号链接（运行时链接 _caffe.so 需要）
RUN set -eux; \
    ln -sf /workspace/caffex/build/lib/libcaffe.so.1.0.0 /workspace/caffex/build/lib/libcaffe.so; \
    ldconfig

RUN set -eux; \
    echo "=== Verifying Caffe runtime ==="; \
    verify-caffe.sh; \
    echo ""; \
    echo "=== All verification passed! ==="

USER ${BUILDER_USER}
WORKDIR ${WORKSPACE_DIR}

CMD ["/bin/bash"]
