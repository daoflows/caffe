# ==============================================================================
# PyCaffe Full Build Dockerfile (BVLC Caffe, CPU-only, Ubuntu 22.04)
#
# 用途：编译完整 pycaffe（含 SGDSolver、所有 Layer、NetSpec），用于运行
#       tests/ops/ 下的 Caffe 算子测试。
#
# 与 standalone/pycaffe 的区别：
#   - standalone/pycaffe: caffe-slim 推理-only，Solver 为 stub（NotImplementedError）
#   - 本镜像：BVLC 原版 Caffe（caffex/），完整训练/推理能力
#
# 构建上下文：vendor/caffe/（需能访问 caffex/ 目录）
# 构建命令：
#   cd projects/xuanspace/vendor/caffe
#   docker build -t caffe-pycaffe:full -f tests/docker/Dockerfile .
#
# 运行测试：
#   docker run --rm -v ${PWD}/tests/ops:/workspace/tests caffe-pycaffe:full \
#     bash -c "cd /workspace/tests && CAFFE_LOG_LEVEL=DEBUG pytest -v --cov=. --cov-report=term-missing"
# ==============================================================================

FROM ubuntu:22.04 AS base-system

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    CAFFE_ROOT=/opt/caffe

# 阿里云镜像源
RUN sed -i 's@//.*archive.ubuntu.com@//mirrors.aliyun.com@g' /etc/apt/sources.list && \
    sed -i 's@//.*security.ubuntu.com@//mirrors.aliyun.com@g' /etc/apt/sources.list

# 系统依赖（BVLC Caffe CPU-only 编译所需）
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
        git \
        wget \
        ca-certificates \
        libatlas-base-dev \
        libboost-all-dev \
        libgflags-dev \
        libgoogle-glog-dev \
        libhdf5-serial-dev \
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
        python3-numpy \
        python3-scipy \
        python3-h5py \
        python3-matplotlib \
        python3-skimage-lib \
        python3-pandas \
        python3-sympy \
        python3-pytest \
        python3-pip \
        pkg-config \
        sudo \
        vim \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 设置 python3 为默认 python
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3 1 && \
    update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 1 && \
    python --version

# 升级 pip 并安装 Python 依赖
RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple \
        --trusted-host mirrors.aliyun.com \
        "numpy>=1.21,<2.0" \
        scikit-image \
        protobuf \
        pytest \
        pytest-cov \
        coverage \
        pyyaml \
        pillow \
        six \
        networkx \
        python-dateutil \
        pydot \
        graphviz

WORKDIR ${CAFFE_ROOT}

# ==============================================================================
# 阶段 2: 编译 Caffe + PyCaffe
# ==============================================================================
FROM base-system AS caffe-builder

# 复制 caffex 源码（BVLC Caffe）
COPY caffex/ ${CAFFE_ROOT}/

# 修复 HDF5 路径（Ubuntu 22.04 的 HDF5 路径与 CMake 查找路径不同）
RUN set -eux; \
    echo "Fixing HDF5 paths for Ubuntu 22.04..."; \
    HDF5_DIR=$(dpkg -L libhdf5-serial-dev | grep -E 'libhdf5.*\.so$' | head -1 | xargs dirname 2>/dev/null || echo "/usr/lib/x86_64-linux-gnu"); \
    echo "HDF5 lib dir: ${HDF5_DIR}"; \
    ln -sf ${HDF5_DIR}/libhdf5_serial.so ${HDF5_DIR}/libhdf5.so 2>/dev/null || true; \
    ln -sf ${HDF5_DIR}/libhdf5_serial_hl.so ${HDF5_DIR}/libhdf5_hl.so 2>/dev/null || true; \
    find /usr -name "hdf5.h" 2>/dev/null; \
    HDF5_INCLUDE=$(find /usr/include -name "hdf5.h" -exec dirname {} \; 2>/dev/null | head -1); \
    echo "HDF5 include: ${HDF5_INCLUDE}"

# 修复 Python 包路径（Ubuntu 22.04 的 python3 包路径可能不同）
RUN set -eux; \
    PYTHON_INCLUDE=$(python3 -c "import sysconfig; print(sysconfig.get_path('include'))"); \
    PYTHON_LIB=$(python3 -c "import sysconfig; print(sysconfig.get_config_var('LIBDIR'))"); \
    NUMPY_INCLUDE=$(python3 -c "import numpy; print(numpy.get_include())"); \
    echo "Python include: ${PYTHON_INCLUDE}"; \
    echo "Python lib: ${PYTHON_LIB}"; \
    echo "NumPy include: ${NUMPY_INCLUDE}"

# 配置 CMake（CPU-only，Python 3）
RUN set -eux; \
    mkdir -p build && cd build && \
    cmake .. \
        -DCPU_ONLY=ON \
        -DUSE_CUDNN=OFF \
        -DUSE_NCCL=OFF \
        -DUSE_OPENCV=ON \
        -DUSE_LEVELDB=ON \
        -DUSE_LMDB=ON \
        -DUSE_HDF5=ON \
        -DBUILD_python=ON \
        -DBUILD_python_layer=ON \
        -Dpython_version=3 \
        -DPYTHON_EXECUTABLE=$(which python3) \
        -DBUILD_docs=OFF \
        -DBUILD_matlab=OFF \
        -DBUILD_examples=OFF \
        -DBUILD_tools=OFF \
        -DUSE_OPENMP=ON \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_INSTALL_PREFIX=/usr/local 2>&1 | tail -30

# 编译
RUN set -eux; \
    cd build && \
    make -j"$(nproc)" 2>&1 | tail -50 && \
    echo "=== Caffe build complete ===" && \
    ls -lh lib/ 2>/dev/null || true

# 编译 pycaffe
RUN set -eux; \
    cd build && \
    make pycaffe -j"$(nproc)" 2>&1 | tail -30 && \
    echo "=== PyCaffe build complete ===" && \
    ls -lh python/caffe/ 2>/dev/null || true

# ==============================================================================
# 阶段 3: 运行时镜像
# ==============================================================================
FROM base-system AS runtime

COPY --from=caffe-builder ${CAFFE_ROOT} ${CAFFE_ROOT}

# 安装 pycaffe
RUN set -eux; \
    cd ${CAFFE_ROOT} && \
    cp -r python/caffe /usr/lib/python3/dist-packages/ 2>/dev/null || \
    cp -r python/caffe $(python3 -c "import site; print(site.getsitepackages()[0])")/; \
    cp build/lib/*.so* /usr/local/lib/ 2>/dev/null || true; \
    ldconfig; \
    echo "=== Setting PYTHONPATH ==="; \
    echo "export PYTHONPATH=${CAFFE_ROOT}/python:${PYTHONPATH}" >> /etc/profile.d/caffe.sh; \
    echo "export LD_LIBRARY_PATH=${CAFFE_ROOT}/build/lib:/usr/local/lib:${LD_LIBRARY_PATH}" >> /etc/profile.d/caffe.sh; \
    chmod +x /etc/profile.d/caffe.sh

ENV PYTHONPATH=${CAFFE_ROOT}/python:${PYTHONPATH} \
    LD_LIBRARY_PATH=${CAFFE_ROOT}/build/lib:/usr/local/lib:${LD_LIBRARY_PATH} \
    GLOG_minloglevel=2

WORKDIR /workspace

# 验证 pycaffe 导入
RUN set -eux; \
    echo "=== Verifying pycaffe import ==="; \
    python -c "import caffe; print('Caffe imported successfully'); print('Caffe CPU mode:', caffe.TEST)"; \
    python -c "from caffe import layers as L, params as P; print('Layers and Params imported'); print('Pooling.MAX =', P.Pooling.MAX)"; \
    python -c "import caffe; print('SGDSolver:', caffe.SGDSolver); print('NetSpec:', caffe.NetSpec); print('Net:', caffe.Net)"; \
    echo "=== PyCaffe verification passed ==="

# 默认命令
CMD ["/bin/bash"]
