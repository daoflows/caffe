# ============================================================================
# python-module Docker 镜像
# 为 caffe-slim/ 模块构建独立 Docker 镜像（caffex/python 已废弃，caffe-slim/ 是主力模块）
# ============================================================================

# ----------------------------------------------------------------------------
# 阶段 0: base-system — 基础系统环境
# ----------------------------------------------------------------------------
FROM ubuntu:26.04 AS base-system

# 阿里云镜像源
RUN sed -i 's|http://archive.ubuntu.com/ubuntu/|http://mirrors.aliyun.com/ubuntu/|g' /etc/apt/sources.list && \
    sed -i 's|http://security.ubuntu.com/ubuntu/|http://mirrors.aliyun.com/ubuntu/|g' /etc/apt/sources.list

# 基础工具
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        wget \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

ENV PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple

# ----------------------------------------------------------------------------
# 阶段 1: base-builder — 构建依赖与 Python 环境
# ----------------------------------------------------------------------------
FROM base-system AS base-builder

# 构建依赖
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
        git \
        libopenblas-dev \
        libboost-all-dev \
        libgflags-dev \
        libgoogle-glog-dev \
        libhdf5-dev \
        libleveldb-dev \
        liblmdb-dev \
        libopencv-dev \
        libprotobuf-dev \
        libsnappy-dev \
        protobuf-compiler \
        python3-dev \
        python3-pip \
        python3-setuptools \
        python3-wheel \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 设置 python3 为默认 python
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3 1

# pip 安装 Python 依赖
RUN pip3 install --break-system-packages --no-cache-dir \
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

# 创建 builder 用户
RUN groupadd -f -g 1000 builder && \
    useradd -m -u 1000 -g 1000 -s /bin/bash builder 2>/dev/null || \
    useradd -m -u 1001 -g 1001 -s /bin/bash builder

# 环境变量
ENV CAFFE_ROOT=/workspace/caffex
ENV LD_LIBRARY_PATH=/workspace/caffex/build/lib
ENV PYTHONPATH=/workspace/caffex/python

WORKDIR /workspace

# ----------------------------------------------------------------------------
# 阶段 2: builder — Caffe 编译
# ----------------------------------------------------------------------------
FROM base-builder AS builder

# 复制 caffex 源码
COPY caffex/ /workspace/caffex/

# 复制 Makefile 配置生成脚本
COPY docker/local/conda/scripts/generate-makefile-config.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/generate-makefile-config.sh

# 执行 makefile 构建
RUN cd /workspace/caffex && \
    generate-makefile-config.sh && \
    make all -j$(nproc) && \
    make pycaffe -j$(nproc) && \
    make distribute 2>/dev/null || true && \
    mkdir -p distribute/bin distribute/lib && \
    cp -r src/caffe/proto distribute/ 2>/dev/null || true && \
    cp -r include distribute/ 2>/dev/null || true && \
    mkdir -p distribute/include/caffe/proto && \
    cp .build_release/src/caffe/proto/caffe.pb.h distribute/include/caffe/proto 2>/dev/null || true && \
    cp build/lib/libcaffe* distribute/lib/ 2>/dev/null || true && \
    cp -r python distribute/ 2>/dev/null || true

# ----------------------------------------------------------------------------
# 阶段 3: runtime — 运行时镜像
# ----------------------------------------------------------------------------
FROM base-builder AS runtime

# 从 builder 复制构建产物
COPY --from=builder /workspace/caffex/build /workspace/caffex/build
COPY --from=builder /workspace/caffex/python /workspace/caffex/python
COPY --from=builder /workspace/caffex/distribute /workspace/caffex/distribute
COPY --from=builder /workspace/caffex/include /workspace/caffex/include

# 复制 caffe-slim/ 目录（主模块）
COPY caffe-slim/ /workspace/caffe-slim/

# 替换 caffex 中的旧 caffe_pb2.py 为 caffeproto 重导出，避免 proto descriptor 重复注册
RUN printf '%s\n' \
    '# Re-export from caffeproto (canonical protobuf module)' \
    'from caffeproto.caffe_pb2 import *  # noqa: F401, F403' \
    > /workspace/caffex/python/caffe/proto/caffe_pb2.py

# 复制验证脚本
COPY docker/modules/python-module/scripts/verify-python-module.sh /usr/local/bin/verify-python-module.sh
RUN chmod +x /usr/local/bin/verify-python-module.sh

# 创建 libcaffe.so 符号链接（Makefile 编译产物为 libcaffe.so.1.0.0）
RUN set -eux; \
    if [ -f /workspace/caffex/build/lib/libcaffe.so.1.0.0 ]; then \
        ln -sf /workspace/caffex/build/lib/libcaffe.so.1.0.0 /workspace/caffex/build/lib/libcaffe.so; \
    elif [ -f /workspace/caffex/build/lib/libcaffe.so ]; then \
        echo "libcaffe.so already exists"; \
    else \
        echo "WARNING: libcaffe.so not found!"; \
        ls /workspace/caffex/build/lib/ 2>/dev/null || true; \
    fi; \
    ldconfig

# 设置 PYTHONPATH
ENV PYTHONPATH=/workspace/caffex/python:/workspace/caffe-slim:${PYTHONPATH}
ENV LD_LIBRARY_PATH=/workspace/caffex/build/lib:${LD_LIBRARY_PATH}

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD python -c "import caffe; from caffeproto import caffe_pb2" || exit 1

WORKDIR /workspace
USER builder

CMD ["/bin/bash"]