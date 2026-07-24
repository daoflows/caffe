# ==============================================================================
# PyCaffe 模块镜像 — 基于 caffe-cpu:python-module 构建
#
# 说明：caffex/python 已废弃，caffe-slim/pycaffe 是新的 PyCaffe 模块。
#       本镜像构建并安装 pycaffe wheel，确保与 caffex/python 行为一致。
#
# 构建目标:
#   default         构建并安装 pycaffe wheel，验证导入
#
# 使用示例:
#   docker build -t caffe-cpu:pycaffe -f docker/modules/pycaffe/Dockerfile .
# ==============================================================================

FROM caffe-cpu:python-module

ARG BUILDER_USER=builder
ARG WORKSPACE_DIR=/workspace

LABEL maintainer="Caffe Docker (PyCaffe Module)"
LABEL description="BVLC Caffe PyCaffe module — Python wrapper for Caffe"
LABEL based.on="caffe-cpu:python-module"

# ==============================================================================
# 阶段 1: 构建 pycaffe wheel
# ==============================================================================
USER root

# 创建 libcaffe.so 符号链接（Caffe 编译产物为 libcaffe.so.1.0.0，CMake find_library 需要 .so）
RUN set -eux; \
    ln -sf ${WORKSPACE_DIR}/caffex/build/lib/libcaffe.so.1.0.0 ${WORKSPACE_DIR}/caffex/build/lib/libcaffe.so; \
    ldconfig

# 复制 pycaffe 源码
COPY caffe-slim/pycaffe ${WORKSPACE_DIR}/pycaffe

# 安装 Python build 工具和构建依赖（venv 已内置在 Python 3.14 中）
# --no-isolation 跳过隔离环境，避免 EXTERNALLY-MANAGED 导致的 pip 安装失败
RUN pip install --break-system-packages --no-cache-dir \
    build scikit-build-core ninja cmake numpy

# 设置 pycaffe 目录权限
RUN chown -R ${BUILDER_USER}:${BUILDER_USER} ${WORKSPACE_DIR}/pycaffe

USER ${BUILDER_USER}
WORKDIR ${WORKSPACE_DIR}/pycaffe

# 构建 pycaffe wheel
RUN set -eux; \
    echo "=== Building pycaffe wheel ==="; \
    python -m build --wheel --no-isolation --outdir dist/ \
      -C "cmake.define.CONDA_PREFIX=${WORKSPACE_DIR}/caffex/build" \
      -C "cmake.define.CAFFE_INCLUDE_DIR=${WORKSPACE_DIR}/caffex/include" \
      -C "cmake.define.CAFFE_LIBRARY=${WORKSPACE_DIR}/caffex/build/lib/libcaffe.so"; \
    echo ""; \
    echo "=== pycaffe wheel built ==="; \
    ls -lh dist/

# ==============================================================================
# 阶段 2: 安装 wheel 并验证
# ==============================================================================
USER root

# 安装 pycaffe wheel
RUN set -eux; \
    echo "=== Installing pycaffe wheel ==="; \
    pip install --break-system-packages --no-cache-dir ${WORKSPACE_DIR}/pycaffe/dist/*.whl; \
    echo ""; \
    echo "=== Verifying wheel installation ==="; \
    pip show pycaffe 2>&1 || true; \
    pip show -f pycaffe 2>&1 || true

# 复制验证脚本和测试文件
COPY docker/modules/pycaffe/scripts/verify-pycaffe.sh /usr/local/bin/verify-pycaffe.sh
COPY docker/modules/pycaffe/scripts/verify-parity.sh /usr/local/bin/verify-parity.sh
RUN chmod +x /usr/local/bin/verify-pycaffe.sh /usr/local/bin/verify-parity.sh

# 复制 caffex/python 测试文件（用于对标验证）
COPY --chown=${BUILDER_USER}:${BUILDER_USER} \
    caffex/python/caffe/test/ \
    ${WORKSPACE_DIR}/caffex/python/caffe/test/

# 设置环境变量：使用纯 Python protobuf 实现（避免 C++ protobuf 兼容性问题）
ENV PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python

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