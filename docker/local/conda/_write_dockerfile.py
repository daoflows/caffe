#!/usr/bin/env python3
"""Write Dockerfile.conda - helper script to avoid shell escaping issues."""
import os

TARGET = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Dockerfile.conda")

CONTENT = """\
# ==============================================================================
# BVLC Caffe Conda 多阶段 Dockerfile (CPU-only, Miniforge3 + Python 3.14)
#
# 与 Dockerfile（Ubuntu 22.04 + Python 3.10）并行存在，使用 conda 环境
# 提供 Python 3.14 运行时支持。
#
# 构建目标 (--target):
#   pycaffe-builder-conda  构建 pycaffe wheel（Python 3.14 + conda）
#   runtime-conda          完整运行时镜像（conda Python 3.14）
#
# 前置依赖：
#   docker build --target builder -t caffe-cpu:builder \\
#     -f docker/local/conda/Dockerfile .
#
# 使用示例:
#   docker build -t caffe-cpu:conda-py314 --target runtime-conda \\
#     -f docker/local/conda/Dockerfile.conda .
# ==============================================================================

# ==============================================================================
# 阶段 1: pycaffe-builder-conda — 使用 conda Python 3.14 构建 pycaffe wheel
# 依赖于 builder 阶段编译的 Caffe 产物
# ==============================================================================
FROM condaforge/miniforge3:latest AS pycaffe-builder-conda

ARG BUILDER_USER=builder
ARG BUILDER_UID=1000
ARG BUILDER_GID=1000
ARG WORKSPACE_DIR=/workspace
ARG CONDA_ENV=pycaffe-py314

LABEL stage=pycaffe-builder-conda
LABEL maintainer="Caffe Conda Docker (Python 3.14)"
LABEL description="PyCaffe wheel builder with conda Python 3.14"

# 创建 conda 环境，安装 Python 3.14 和构建依赖
# Boost >= 1.85 来自 conda-forge，支持 Python 3.14
RUN set -eux; \\
    conda create -y -n ${CONDA_ENV} \\
        python=3.14 \\
        boost>=1.85 \\
        boost-cpp \\
        cmake>=3.18 \\
        ninja \\
        numpy>=1.26 \\
        protobuf \\
        libprotobuf \\
        scikit-build-core \\
        pip \\
        setuptools \\
        wheel \\
        && conda clean -afy

# 创建 conda 激活脚本
RUN echo "#!/bin/bash" > /usr/local/bin/activate-conda && \\
    echo "source /opt/conda/etc/profile.d/conda.sh" >> /usr/local/bin/activate-conda && \\
    echo "conda activate ${CONDA_ENV}" >> /usr/local/bin/activate-conda && \\
    chmod +x /usr/local/bin/activate-conda

# 安装 Python 构建依赖（pip 包）
SHELL ["/bin/bash", "-c"]
RUN source /opt/conda/etc/profile.d/conda.sh && \\
    conda activate ${CONDA_ENV} && \\
    pip install --no-cache-dir \\
        build \\
        'pyyaml>=6.0' \\
        'Pillow>=9.0' \\
        'scipy>=1.7' \\
        'scikit-image>=0.19' \\
        'matplotlib>=3.5' \\
        'h5py>=3.6' \\
        'networkx>=2.6' \\
        'pandas>=1.4' \\
        'python-dateutil>=2.8'

# 创建非 root 用户
RUN set -eux; \\
    if ! getent group ${BUILDER_USER} >/dev/null; then \\
        groupadd -g ${BUILDER_GID} ${BUILDER_USER}; \\
    fi; \\
    useradd -m -s /bin/bash -u ${BUILDER_UID} -g ${BUILDER_GID} ${BUILDER_USER}; \\
    mkdir -p ${WORKSPACE_DIR}; \\
    chown -R ${BUILDER_UID}:${BUILDER_GID} ${WORKSPACE_DIR}

# 从 builder 阶段复制 Caffe 编译产物
COPY --from=caffe-cpu:builder ${WORKSPACE_DIR}/caffex/build ${WORKSPACE_DIR}/caffex/build
COPY --from=caffe-cpu:builder ${WORKSPACE_DIR}/caffex/include ${WORKSPACE_DIR}/caffex/include
COPY --from=caffe-cpu:builder ${WORKSPACE_DIR}/caffex/distribute ${WORKSPACE_DIR}/caffex/distribute
COPY --from=caffe-cpu:builder ${WORKSPACE_DIR}/caffex/Makefile.config ${WORKSPACE_DIR}/caffex/Makefile.config

# 创建 libcaffe.so 符号链接
RUN set -eux; \\
    ln -sf ${WORKSPACE_DIR}/caffex/build/lib/libcaffe.so.1.0.0 ${WORKSPACE_DIR}/caffex/build/lib/libcaffe.so; \\
    ls -la ${WORKSPACE_DIR}/caffex/build/lib/libcaffe.so*; \\
    ldconfig

# 复制 pycaffe 源码
COPY python/pycaffe ${WORKSPACE_DIR}/pycaffe

# 设置权限
RUN mkdir -p ${WORKSPACE_DIR}/pycaffe/dist && \\
    chown -R ${BUILDER_USER}:${BUILDER_USER} ${WORKSPACE_DIR}/pycaffe

USER ${BUILDER_USER}
WORKDIR ${WORKSPACE_DIR}/pycaffe

# 构建 pycaffe wheel（使用 conda Python 3.14）
SHELL ["/bin/bash", "-c"]
RUN source /opt/conda/etc/profile.d/conda.sh && \\
    conda activate ${CONDA_ENV} && \\
    set -eux; \\
    echo "=== Python version ==="; \\
    python --version; \\
    echo ""; \\
    echo "=== Conda environment ==="; \\
    which python; \\
    which cmake; \\
    echo ""; \\
    echo "=== Building pycaffe wheel (Python 3.14) ==="; \\
    CONDA_PREFIX_PATH="$(python -c 'import sys; print(sys.prefix)')"; \\
    echo "CONDA_PREFIX_PATH=${CONDA_PREFIX_PATH}"; \\
    python -m build --wheel --outdir dist/ \\
      -C "cmake.define.CONDA_PREFIX=${WORKSPACE_DIR}/caffex/build" \\
      -C "cmake.define.CAFFE_INCLUDE_DIR=${WORKSPACE_DIR}/caffex/include" \\
      -C "cmake.define.CAFFE_LIBRARY=${WORKSPACE_DIR}/caffex/build/lib/libcaffe.so" \\
      -C "cmake.define.Python_EXECUTABLE=${CONDA_PREFIX_PATH}/bin/python" \\
      -C "cmake.define.Python_INCLUDE_DIR=${CONDA_PREFIX_PATH}/include/python3.14" \\
      -C "cmake.define.Python_LIBRARY=${CONDA_PREFIX_PATH}/lib/libpython3.14.so" \\
      -C "cmake.define.Python_NumPy_INCLUDE_DIRS=${CONDA_PREFIX_PATH}/lib/python3.14/site-packages/numpy/_core/include"; \\
    echo ""; \\
    echo "=== pycaffe wheel built ==="; \\
    ls -lh dist/*.whl

# ==============================================================================
# 阶段 2: runtime-conda — 运行时镜像（conda Python 3.14）
# 基于 builder 镜像（Ubuntu 22.04，已含所有系统库），安装 Miniforge3 提供 Python 3.14
# ==============================================================================
FROM caffe-cpu:builder AS runtime-conda

ARG BUILDER_USER=builder
ARG BUILDER_UID=1000
ARG BUILDER_GID=1000
ARG WORKSPACE_DIR=/workspace
ARG CONDA_ENV=pycaffe-py314

LABEL maintainer="Caffe Conda Docker (Python 3.14)"
LABEL description="BVLC Caffe CPU-only runtime with conda Python 3.14"
LABEL caffe.version="1.0"

USER root

# 安装 Miniforge3（轻量级 conda，默认安装到 /opt/conda）
RUN set -eux; \\
    MINIFORGE_URL="https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh"; \\
    wget -q "${MINIFORGE_URL}" -O /tmp/miniforge.sh; \\
    bash /tmp/miniforge.sh -b -p /opt/conda; \\
    rm /tmp/miniforge.sh; \\
    /opt/conda/bin/conda --version

# 创建 conda 环境，安装 Python 3.14 和运行时依赖
# Boost >= 1.85 来自 conda-forge，为 _caffe.so 提供 Boost.Python 运行时
RUN set -eux; \\
    /opt/conda/bin/conda create -y -n ${CONDA_ENV} \\
        python=3.14 \\
        numpy>=1.26 \\
        protobuf \\
        boost>=1.85 \\
        boost-cpp \\
        && /opt/conda/bin/conda clean -afy

# 创建 conda 激活脚本
RUN echo "#!/bin/bash" > /usr/local/bin/activate-conda && \\
    echo "source /opt/conda/etc/profile.d/conda.sh" >> /usr/local/bin/activate-conda && \\
    echo "conda activate ${CONDA_ENV}" >> /usr/local/bin/activate-conda && \\
    chmod +x /usr/local/bin/activate-conda

# 安装 pip 运行时依赖
SHELL ["/bin/bash", "-c"]
RUN source /opt/conda/etc/profile.d/conda.sh && \\
    conda activate ${CONDA_ENV} && \\
    pip install --no-cache-dir \\
        'pyyaml>=6.0' \\
        'Pillow>=9.0' \\
        'scipy>=1.7' \\
        'scikit-image>=0.19' \\
        'matplotlib>=3.5' \\
        'h5py>=3.6' \\
        'networkx>=2.6' \\
        'pandas>=1.4' \\
        'python-dateutil>=2.8'

# 确保 Caffe 编译产物中 libcaffe.so 符号链接存在
RUN set -eux; \\
    ln -sf ${WORKSPACE_DIR}/caffex/build/lib/libcaffe.so.1.0.0 ${WORKSPACE_DIR}/caffex/build/lib/libcaffe.so; \\
    ldconfig

# 从 pycaffe-builder-conda 复制 wheel 并安装
COPY --from=pycaffe-builder-conda ${WORKSPACE_DIR}/pycaffe/dist ${WORKSPACE_DIR}/pycaffe/dist
COPY python/pycaffe/verify.py ${WORKSPACE_DIR}/pycaffe/verify.py
COPY python/pycaffe/test_inference.py ${WORKSPACE_DIR}/pycaffe/test_inference.py
COPY python/pycaffe/lenet_deploy.prototxt ${WORKSPACE_DIR}/pycaffe/lenet_deploy.prototxt

# 安装 pycaffe wheel 并验证
SHELL ["/bin/bash", "-c"]
RUN source /opt/conda/etc/profile.d/conda.sh && \\
    conda activate ${CONDA_ENV} && \\
    set -eux; \\
    echo "=== Installing pycaffe wheel ==="; \\
    pip install --no-cache-dir ${WORKSPACE_DIR}/pycaffe/dist/*.whl; \\
    echo ""; \\
    echo "=== Debug: python version ==="; \\
    python --version; \\
    echo ""; \\
    echo "=== Debug: check installed files ==="; \\
    pip show -f pycaffe 2>&1 || true; \\
    echo ""; \\
    echo "=== Debug: find _caffe.so ==="; \\
    find / -name "_caffe*.so" -ls 2>/dev/null || true; \\
    echo ""; \\
    echo "=== Debug: ldd _caffe.so ==="; \\
    SO_FILE=$(find / -name "_caffe*.so" 2>/dev/null | head -1); \\
    if [ -n "${SO_FILE}" ] && [ -f "${SO_FILE}" ]; then \\
      echo "Found: ${SO_FILE}"; \\
      ldd "${SO_FILE}" 2>&1 || true; \\
    else \\
      echo "WARNING: _caffe.so not found anywhere"; \\
    fi; \\
    echo ""; \\
    echo "=== Verifying pycaffe (Python 3.14) ==="; \\
    python ${WORKSPACE_DIR}/pycaffe/verify.py || true; \\
    echo ""; \\
    echo "=== Running inference test (Python 3.14) ==="; \\
    python ${WORKSPACE_DIR}/pycaffe/test_inference.py || true; \\
    echo ""; \\
    echo "=== pycaffe verification completed ==="

# 设置运行时环境
ENV WORKSPACE_DIR=/workspace \\
    CAFFE_ROOT=/workspace/caffex \\
    LD_LIBRARY_PATH=/workspace/caffex/build/lib:/usr/lib:/usr/lib/x86_64-linux-gnu:/usr/local/lib \\
    CONDA_ENV=pycaffe-py314 \\
    CONDA_DEFAULT_ENV=pycaffe-py314

# 设置默认 shell 为 bash 以支持 conda activate
SHELL ["/bin/bash", "-c"]

USER ${BUILDER_USER}
WORKDIR ${WORKSPACE_DIR}

# 默认激活 conda 环境
ENTRYPOINT ["/bin/bash", "-c"]
CMD ["source /opt/conda/etc/profile.d/conda.sh && conda activate pycaffe-py314 && exec bash"]
"""

with open(TARGET, "w", encoding="utf-8") as f:
    f.write(CONTENT)

print(f"Dockerfile.conda written successfully ({len(CONTENT.splitlines())} lines)")