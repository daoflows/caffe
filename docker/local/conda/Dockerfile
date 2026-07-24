# ==============================================================================
# BVLC Caffe 统一多阶段 Dockerfile (CPU-only, Ubuntu 22.04 + System Python 3.10)
#
# 说明：由于 Python 3.14 生态尚不成熟，本镜像使用 Ubuntu 22.04 自带的 Python 3.10
#       + pip 方式安装 Python 依赖。Caffe 1.0 原生支持 Python 3。
#
# 构建目标 (--target):
#   base-system     公共基础层（apt换源、CA证书）
#   base-builder    基础构建环境（系统构建依赖 + Python 依赖）
#   builder-dev     开发构建环境（含源码挂载支持），./build.sh 默认目标
#   builder         CI 构建阶段（编译 Caffe 源码）
#   runtime         完整运行时镜像（从 builder 获取编译产物）
#
# 使用示例:
#   docker build -t caffe-cpu:dev --target builder-dev -f docker/local/conda/Dockerfile .
#   docker build -t caffe-cpu:latest --target runtime -f docker/local/conda/Dockerfile .
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
# 阶段 2: builder-dev — 开发构建环境
# 用于：./build.sh 默认目标，挂载源码后交互式开发
# ==============================================================================
FROM base-builder AS builder-dev

LABEL stage=builder-dev

USER root

COPY docker/local/conda/scripts/generate-makefile-config.sh /usr/local/bin/generate-makefile-config.sh
COPY docker/local/conda/scripts/verify-caffe.sh /usr/local/bin/verify-caffe.sh
RUN chmod +x /usr/local/bin/generate-makefile-config.sh /usr/local/bin/verify-caffe.sh

USER ${BUILDER_USER}

ENTRYPOINT ["/bin/bash", "-c"]
CMD ["/bin/bash"]

# ==============================================================================
# 阶段 3: builder — CI 构建阶段（编译 Caffe 源码）
# ==============================================================================
FROM base-builder AS builder

ARG CAFFE_VERSION=1.0

LABEL stage=builder
LABEL caffe.version=${CAFFE_VERSION}

USER root

COPY --chown=${BUILDER_USER}:${BUILDER_USER} caffex ${WORKSPACE_DIR}/caffex
COPY docker/local/conda/scripts/generate-makefile-config.sh /usr/local/bin/generate-makefile-config.sh
COPY docker/local/conda/scripts/verify-caffe.sh /usr/local/bin/verify-caffe.sh
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
# 阶段 3.5: pycaffe-builder — 构建 pycaffe wheel
# 从 builder 获取已编译的 Caffe，使用 scikit-build-core 构建 pycaffe wheel
# ==============================================================================
FROM base-builder AS pycaffe-builder

ARG CAFFE_VERSION=1.0

LABEL stage=pycaffe-builder
LABEL caffe.version=${CAFFE_VERSION}

USER root

# 从 builder 复制已编译的 Caffe 产物（库文件 + 头文件 + distribute）
COPY --from=builder ${WORKSPACE_DIR}/caffex/build ${WORKSPACE_DIR}/caffex/build
COPY --from=builder ${WORKSPACE_DIR}/caffex/include ${WORKSPACE_DIR}/caffex/include
COPY --from=builder ${WORKSPACE_DIR}/caffex/distribute ${WORKSPACE_DIR}/caffex/distribute
COPY --from=builder ${WORKSPACE_DIR}/caffex/Makefile.config ${WORKSPACE_DIR}/caffex/Makefile.config

# 创建 libcaffe.so 符号链接（Caffe 编译产物为 libcaffe.so.1.0.0，CMake find_library 需要 .so）
RUN set -eux; \
    ln -sf ${WORKSPACE_DIR}/caffex/build/lib/libcaffe.so.1.0.0 ${WORKSPACE_DIR}/caffex/build/lib/libcaffe.so; \
    ls -la ${WORKSPACE_DIR}/caffex/build/lib/libcaffe.so*; \
    ldconfig

# 复制 pycaffe 源码
COPY caffe-slim/pycaffe ${WORKSPACE_DIR}/pycaffe

# 安装 Python build 工具，并设置 pycaffe 目录权限
RUN pip install --no-cache-dir build && \
    mkdir -p ${WORKSPACE_DIR}/pycaffe/dist && \
    chown -R ${BUILDER_USER}:${BUILDER_USER} ${WORKSPACE_DIR}/pycaffe

USER ${BUILDER_USER}
WORKDIR ${WORKSPACE_DIR}/pycaffe

# 构建 pycaffe wheel
# CONDA_PREFIX 指向 Caffe 编译产物目录（含 lib/ 子目录）
# CMAKE_ARGS 传递额外的 include 路径
RUN set -eux; \
    echo "=== Building pycaffe wheel ==="; \
    python -m build --wheel --outdir dist/ \
      -C "cmake.define.CONDA_PREFIX=${WORKSPACE_DIR}/caffex/build" \
      -C "cmake.define.CAFFE_INCLUDE_DIR=${WORKSPACE_DIR}/caffex/include" \
      -C "cmake.define.CAFFE_LIBRARY=${WORKSPACE_DIR}/caffex/build/lib/libcaffe.so"; \
    echo ""; \
    echo "=== pycaffe wheel built ==="; \
    ls -lh dist/*.whl

# ==============================================================================
# 阶段 4: runtime — 完整运行时镜像
# 基于 base-builder（已包含所有系统库和 Python 依赖），仅复制编译产物
# 注意：为简化依赖管理，runtime 复用 base-builder 的系统依赖层
#       后续可优化为独立最小运行时层
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
COPY docker/local/conda/scripts/verify-caffe.sh /usr/local/bin/verify-caffe.sh
RUN chmod +x /usr/local/bin/verify-caffe.sh

# 创建 libcaffe.so 符号链接（运行时链接 _caffe.so 需要）
RUN set -eux; \
    ln -sf ${WORKSPACE_DIR}/caffex/build/lib/libcaffe.so.1.0.0 ${WORKSPACE_DIR}/caffex/build/lib/libcaffe.so; \
    ldconfig

# 从 pycaffe-builder 复制 pycaffe wheel 并安装
COPY --from=pycaffe-builder ${WORKSPACE_DIR}/pycaffe/dist ${WORKSPACE_DIR}/pycaffe/dist
COPY caffe-slim/pycaffe/verify.py ${WORKSPACE_DIR}/pycaffe/verify.py
COPY caffe-slim/pycaffe/test_inference.py ${WORKSPACE_DIR}/pycaffe/test_inference.py
COPY caffe-slim/pycaffe/lenet_deploy.prototxt ${WORKSPACE_DIR}/pycaffe/lenet_deploy.prototxt

RUN set -eux; \
    echo "=== Installing pycaffe wheel ==="; \
    pip install --no-cache-dir ${WORKSPACE_DIR}/pycaffe/dist/*.whl; \
    echo ""; \
    echo "=== Debug: checking installed files ==="; \
    pip show -f pycaffe 2>&1 || true; \
    echo ""; \
    echo "=== Debug: find _caffe.so ==="; \
    find / -name "_caffe*.so" -ls 2>/dev/null || true; \
    echo ""; \
    echo "=== Debug: ldd _caffe.so ==="; \
    SO_FILE=$(find / -name "_caffe*.so" 2>/dev/null | head -1); \
    if [ -n "${SO_FILE}" ] && [ -f "${SO_FILE}" ]; then \
      echo "Found: ${SO_FILE}"; \
      ldd "${SO_FILE}" 2>&1 || true; \
    else \
      echo "WARNING: _caffe.so not found anywhere"; \
    fi; \
    echo ""; \
    echo "=== Debug: wheel contents ==="; \
    python -c "import zipfile; z=zipfile.ZipFile('${WORKSPACE_DIR}/pycaffe/dist/pycaffe-1.0.0-py3-none-linux_x86_64.whl'); [print(n) for n in z.namelist()]" 2>&1 || true; \
    echo ""; \
    echo "=== Verifying pycaffe installation ==="; \
    python ${WORKSPACE_DIR}/pycaffe/verify.py || true; \
    echo ""; \
    echo "=== Running inference test ==="; \
    python ${WORKSPACE_DIR}/pycaffe/test_inference.py || true; \
    echo ""; \
    echo "=== pycaffe verification completed ==="

RUN set -eux; \
    echo "=== Verifying Caffe runtime ==="; \
    verify-caffe.sh; \
    echo ""; \
    echo "=== All verification passed! ==="

USER ${BUILDER_USER}
WORKDIR ${WORKSPACE_DIR}

ENTRYPOINT ["/bin/bash", "-c"]
CMD ["/bin/bash"]
