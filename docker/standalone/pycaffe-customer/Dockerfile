# ==============================================================================
# PyCaffe Customer Distribution Dockerfile (CPU-only, Ubuntu 26.04)
# ==============================================================================
# Self-contained, customer-ready Docker image for PyCaffe inference.
# Builds everything from ubuntu:26.04 with no dependency on local pre-built images.
# The final stage contains ONLY runtime dependencies (no gcc/cmake/git/ninja).
#
# Build context: vendor/ (parent of caffe/, needs caffe/caffe-slim/ and tvm-ffi/)
# BuildKit required (for Dockerfile.dockerignore support).
#
# Stages:
#   base-system     - Minimal base (CA certs, basic tools, official apt sources)
#   base-builder    - Build toolchain + Python build/runtime packages
#   caffe-builder   - Compile tvm-ffi + caffe-slim, collect artifacts to /opt/caffe-dist
#   customer-runtime - Final minimal image (runtime only, no build tools)
#
# Build:
#   cd vendor && DOCKER_BUILDKIT=1 docker build -t caffe-cpu:customer \
#       -f caffe/docker/standalone/pycaffe-customer/Dockerfile .
#
# China mirror (optional):
#   cd vendor && DOCKER_BUILDKIT=1 docker build -t caffe-cpu:customer \
#       --build-arg APTPROXY=mirrors.aliyun.com \
#       --build-arg PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple \
#       --build-arg PIP_TRUSTED_HOST=mirrors.aliyun.com \
#       -f caffe/docker/standalone/pycaffe-customer/Dockerfile .
#
# Run:
#   docker run -d -p 8888:8888 -p 2222:22 --name caffe caffe-cpu:customer
#
# Default credentials (CHANGE IN PRODUCTION):
#   SSH:      builder / caffepass
#   Jupyter:  token = caffe-token
# ==============================================================================

# ==============================================================================
# Stage 0: base-system - Minimal Ubuntu 26.04 base
# ==============================================================================
FROM ubuntu:26.04 AS base-system

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    TZ=UTC \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

ARG APTPROXY=""

RUN set -eux; \
    if [ -n "${APTPROXY}" ]; then \
        echo "Using apt proxy: ${APTPROXY}"; \
        rm -f /etc/apt/sources.list.d/ubuntu.sources; \
        echo "deb http://${APTPROXY}/ubuntu/ resolute main restricted universe multiverse" > /etc/apt/sources.list; \
        echo "deb http://${APTPROXY}/ubuntu/ resolute-updates main restricted universe multiverse" >> /etc/apt/sources.list; \
        echo "deb http://${APTPROXY}/ubuntu/ resolute-backports main restricted universe multiverse" >> /etc/apt/sources.list; \
        echo "deb http://${APTPROXY}/ubuntu/ resolute-security main restricted universe multiverse" >> /etc/apt/sources.list; \
    fi; \
    apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get upgrade -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        libgomp1 \
        procps \
        tzdata \
        wget \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# ==============================================================================
# Stage 1: base-builder - Build toolchain + Python packages
# ==============================================================================
FROM base-system AS base-builder

ARG BUILDER_USER=builder
ARG BUILDER_UID=1000
ARG BUILDER_GID=1000
ARG WORKSPACE_DIR=/workspace
ARG PIP_INDEX_URL="https://pypi.org/simple"
ARG PIP_TRUSTED_HOST=""

LABEL stage=base-builder

RUN set -eux; \
    apt-get update && \
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
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN update-alternatives --install /usr/bin/python python /usr/bin/python3 1 && \
    update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 1

RUN set -eux; \
    PIP_ARGS="--break-system-packages --no-cache-dir"; \
    if [ -n "${PIP_TRUSTED_HOST}" ]; then \
        PIP_ARGS="${PIP_ARGS} --trusted-host ${PIP_TRUSTED_HOST} -i ${PIP_INDEX_URL}"; \
    else \
        PIP_ARGS="${PIP_ARGS} -i ${PIP_INDEX_URL}"; \
    fi; \
    pip install ${PIP_ARGS} \
        "numpy>=2" \
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
        "scikit-build-core>=0.10"; \
    python -c "import numpy; print('numpy:', numpy.__version__)"; \
    python -c "import google.protobuf; print('protobuf ok')"

ENV WORKSPACE_DIR=/workspace \
    LD_LIBRARY_PATH=/usr/local/lib:/usr/lib:/usr/lib/x86_64-linux-gnu

RUN set -eux; \
    if ! getent group ${BUILDER_USER} >/dev/null; then \
        if getent group ${BUILDER_GID} >/dev/null; then groupadd ${BUILDER_USER}; \
        else groupadd -g ${BUILDER_GID} ${BUILDER_USER}; fi; \
    fi; \
    if id -u ${BUILDER_USER} >/dev/null 2>&1; then \
        usermod -g ${BUILDER_USER} -s /bin/bash ${BUILDER_USER}; \
    else \
        if getent passwd ${BUILDER_UID} >/dev/null; then useradd -m -s /bin/bash -g ${BUILDER_USER} ${BUILDER_USER}; \
        else useradd -m -s /bin/bash -u ${BUILDER_UID} -g ${BUILDER_GID} ${BUILDER_USER}; fi; \
    fi; \
    usermod -aG sudo ${BUILDER_USER}; \
    mkdir -p ${WORKSPACE_DIR}; \
    chown -R ${BUILDER_UID}:${BUILDER_GID} ${WORKSPACE_DIR}

# ==============================================================================
# Stage 2: caffe-builder - Compile tvm-ffi + caffe-slim, collect artifacts
# ==============================================================================
FROM base-builder AS caffe-builder

ARG CAFFE_VERSION=1.0.0
ARG WORKSPACE_DIR=/workspace

LABEL stage=caffe-builder
LABEL caffe.version=${CAFFE_VERSION}-slim

USER root

RUN mkdir -p ${WORKSPACE_DIR}/caffe

COPY tvm-ffi ${WORKSPACE_DIR}/tvm-ffi
COPY caffe/caffe-slim ${WORKSPACE_DIR}/caffe/caffe-slim

WORKDIR ${WORKSPACE_DIR}/tvm-ffi

ENV SETUPTOOLS_SCM_PRETEND_VERSION=0.1.0 \
    SKBUILD_CMAKE_ARGS="-DTVM_FFI_ATTACH_DEBUG_SYMBOLS=ON;-DTVM_FFI_BUILD_TESTS=OFF;-DTVM_FFI_BUILD_PYTHON_MODULE=ON;-DTVM_FFI_USE_LIBBACKTRACE=OFF"

RUN set -eux; \
    pip install --break-system-packages --no-cache-dir -v . --no-build-isolation; \
    python -c "import tvm_ffi; print('tvm_ffi version:', tvm_ffi.__version__)"

WORKDIR ${WORKSPACE_DIR}/caffe/caffe-slim

RUN set -eux; \
    cmake -B build -G Ninja \
        -DCMAKE_BUILD_TYPE=Release \
        -DCAFFE_CPU_ONLY=ON \
        -DCAFFE_VERSION="${CAFFE_VERSION}-slim" \
        -DTVM_FFI_USE_LIBBACKTRACE=OFF \
        -DTVM_FFI_BACKTRACE_ON_SEGFAULT=OFF \
        -DCMAKE_INSTALL_PREFIX=${WORKSPACE_DIR}/caffe-install; \
    cmake --build build --parallel

# Collect ALL distribution artifacts into /opt/caffe-dist (clean directory for COPY)
RUN set -eux; \
    DIST=/opt/caffe-dist; \
    SITE_PACKAGES=$(python -c "import site; print(site.getsitepackages()[0])"); \
    mkdir -p ${DIST}/lib ${DIST}/python ${DIST}/protos ${DIST}/pycaffe-modules ${DIST}/config ${DIST}/scripts ${DIST}/examples; \
    mkdir -p ${DIST}/python/caffe; \
    # Find _caffe.so from multiple possible locations
    CAFFE_SO=""; \
    for p in \
        build/python/caffe/_caffe.so \
        build/lib/_caffe.so \
        build/_caffe.so \
        pycaffe/build/pycaffe/_caffe.so \
        pycaffe/build/_caffe.so \
        pycaffe/python/pycaffe/_caffe.so; do \
        if [ -f "$p" ]; then CAFFE_SO="$p"; break; fi; \
    done; \
    if [ -z "${CAFFE_SO}" ]; then echo "ERROR: _caffe.so not found!"; find . -name "_caffe.so" -type f; exit 1; fi; \
    echo "Found _caffe.so at: ${CAFFE_SO}"; \
    cp "${CAFFE_SO}" ${DIST}/python/caffe/_caffe.so; \
    cp "${CAFFE_SO}" ${DIST}/lib/_caffe.so; \
    # Auto-collect ALL transitive shared library dependencies of _caffe.so via ldd
    echo "Collecting shared library dependencies via ldd..."; \
    ldd "${CAFFE_SO}" | grep -oP '=>\s*\K/\S+\.so\S*' | while read -r libpath; do \
        if [ -f "$libpath" ]; then \
            cp -L "$libpath" ${DIST}/lib/ 2>/dev/null || true; \
            libname=$(basename "$libpath"); \
            echo "  Collected: $libpath -> $libname"; \
        fi; \
    done; \
    # Also collect any not-found deps and symlink targets
    ldd "${CAFFE_SO}" | grep -oP '^\s*\S+\.so\S*' | while read -r libname; do \
        if [ -n "$libname" ] && [ ! -f "${DIST}/lib/$libname" ]; then \
            for dir in /usr/lib /usr/local/lib /usr/lib/x86_64-linux-gnu /lib/x86_64-linux-gnu; do \
                if [ -f "$dir/$libname" ]; then \
                    cp -L "$dir/$libname" ${DIST}/lib/ 2>/dev/null || true; \
                    echo "  Collected (fallback): $dir/$libname"; \
                    break; \
                fi; \
            done; \
        fi; \
    done; \
    # Find libtvm_ffi.so from build tree (subproject build), site-packages, or system
    TVM_FFI_LIB=""; \
    for p in \
        $(find build -name "libtvm_ffi.so" -type f 2>/dev/null | head -1) \
        $(find ${SITE_PACKAGES}/tvm_ffi -name "libtvm_ffi.so*" -type f 2>/dev/null | head -1) \
        $(find /usr -name "libtvm_ffi.so" -type f 2>/dev/null | head -1); do \
        if [ -n "$p" ] && [ -f "$p" ]; then TVM_FFI_LIB="$p"; break; fi; \
    done; \
    if [ -n "${TVM_FFI_LIB}" ]; then \
        echo "Found libtvm_ffi.so at: ${TVM_FFI_LIB}"; \
        cp "${TVM_FFI_LIB}" ${DIST}/python/caffe/; \
        cp "${TVM_FFI_LIB}".* ${DIST}/python/caffe/ 2>/dev/null || true; \
        if [ ! -f "${DIST}/lib/$(basename ${TVM_FFI_LIB})" ]; then \
            cp "${TVM_FFI_LIB}" ${DIST}/lib/; \
            cp "${TVM_FFI_LIB}".* ${DIST}/lib/ 2>/dev/null || true; \
        fi; \
    else \
        echo "WARNING: libtvm_ffi.so not found, will rely on pip-installed tvm_ffi"; \
    fi; \
    # Collect tvm_ffi Python package
    cp -r ${SITE_PACKAGES}/tvm_ffi* ${DIST}/python/ 2>/dev/null || true; \
    cp ${WORKSPACE_DIR}/caffe/caffe-slim/python/caffe/__init__.py ${DIST}/python/caffe/; \
    mkdir -p ${DIST}/python/protos ${DIST}/python/caffeproto ${DIST}/python/pycaffe; \
    cp ${WORKSPACE_DIR}/caffe/caffe-slim/protos/caffe_pb2.py ${DIST}/python/protos/; \
    cp ${WORKSPACE_DIR}/caffe/caffe-slim/protos/caffe.proto ${DIST}/python/protos/; \
    cp ${WORKSPACE_DIR}/caffe/caffe-slim/caffeproto/__init__.py ${DIST}/python/caffeproto/; \
    cp ${WORKSPACE_DIR}/caffe/caffe-slim/caffeproto/caffe_utils.py ${DIST}/python/caffeproto/ 2>/dev/null || true; \
    cp ${WORKSPACE_DIR}/caffe/caffe-slim/caffeproto/caffe_fuse.py ${DIST}/python/caffeproto/ 2>/dev/null || true; \
    PYCAFFE_PY=${WORKSPACE_DIR}/caffe/caffe-slim/pycaffe/python/pycaffe; \
    for f in transforms.py classifier.py detector.py draw.py net_spec.py coord_map.py data_types.py; do \
        if [ -f "${PYCAFFE_PY}/$f" ]; then cp "${PYCAFFE_PY}/$f" ${DIST}/pycaffe-modules/; fi; \
    done; \
    mkdir -p ${DIST}/examples/lenet; \
    cp ${WORKSPACE_DIR}/caffe/caffe-slim/pycaffe/lenet_deploy.prototxt ${DIST}/examples/lenet/; \
    echo "Artifacts collected to ${DIST}"; \
    echo "=== Collected libraries ==="; \
    ls -lh ${DIST}/lib/; \
    echo "=== caffe package ==="; \
    ls -lh ${DIST}/python/caffe/; \
    echo "=== Python packages ==="; \
    ls ${DIST}/python/

# ==============================================================================
# Stage 3: customer-runtime - Final minimal runtime image
# ==============================================================================
FROM base-system AS customer-runtime

ARG CAFFE_VERSION=1.0.0
ARG BUILDER_USER=builder
ARG BUILDER_UID=1000
ARG BUILDER_GID=1000
ARG WORKSPACE_DIR=/workspace
ARG IMAGE_VERSION="1.0.0"
ARG BUILD_DATE=""
ARG PIP_INDEX_URL="https://pypi.org/simple"
ARG PIP_TRUSTED_HOST=""

LABEL maintainer="Caffe Standalone Docker Maintainers" \
      maintainer.email="c***@noreply.example.com" \
      version="${IMAGE_VERSION}" \
      description="PyCaffe CPU-only customer distribution (caffe-slim + tvm-ffi + Jupyter + SSH)" \
      caffe.version="${CAFFE_VERSION}-slim" \
      source="https://github.com/xinetzone/SpecWeave" \
      vendor="Caffe Standalone Docker" \
      org.opencontainers.image.title="PyCaffe Customer Distribution" \
      org.opencontainers.image.description="Self-contained PyCaffe CPU-only image with Jupyter and SSH" \
      org.opencontainers.image.version="${IMAGE_VERSION}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.licenses="BSD-2-Clause"

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    TZ=UTC \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python \
    WORKSPACE_DIR=/workspace \
    LD_LIBRARY_PATH=/usr/local/lib:/usr/lib:/usr/lib/x86_64-linux-gnu \
    NON_ROOT_USER=builder \
    JUPYTER_PORT=8888 \
    SSH_PORT=22 \
    GRANT_SUDO=no \
    ALLOW_ROOT_SSH=no \
    DISABLE_SSH=no \
    DEFAULT_USER_PASSWORD=caffepass \
    DEFAULT_JUPYTER_TOKEN=caffe-token \
    JUPYTER_ALLOW_ORIGIN=* \
    PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

# Install RUNTIME packages only (no build-essential, no gcc, no cmake, no ninja, no git)
RUN set -eux; \
    apt-get update && \
    apt-get upgrade -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        gosu \
        libfreetype6 \
        libgcc-s1 \
        libgfortran5 \
        libgomp1 \
        libjpeg-turbo8 \
        libopenblas0 \
        libpng16-16t64 \
        libprotobuf32t64 \
        libstdc++6 \
        libwebp7 \
        locales \
        netcat-openbsd \
        openssh-server \
        openssh-client \
        passwd \
        procps \
        pwgen \
        python3 \
        python3-pip \
        python3-setuptools \
        sudo \
        supervisor \
        tini \
        tzdata \
        wget \
        zlib1g \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /var/cache/apt/*

RUN update-alternatives --install /usr/bin/python python /usr/bin/python3 1 && \
    update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 1

# Install RUNTIME Python packages (no Cython, scikit-build-core, cmake, etc.)
RUN set -eux; \
    PIP_ARGS="--break-system-packages --no-cache-dir"; \
    if [ -n "${PIP_TRUSTED_HOST}" ]; then \
        PIP_ARGS="${PIP_ARGS} --trusted-host ${PIP_TRUSTED_HOST} -i ${PIP_INDEX_URL}"; \
    else \
        PIP_ARGS="${PIP_ARGS} -i ${PIP_INDEX_URL}"; \
    fi; \
    pip install ${PIP_ARGS} \
        "numpy>=2" \
        "scipy>=1.7" \
        "matplotlib>=3.5" \
        "scikit-image>=0.19" \
        "h5py>=3.6" \
        "networkx>=2.6" \
        "pandas>=1.4" \
        "pyyaml>=6.0" \
        "pillow>=9.0" \
        "six>=1.16" \
        "protobuf" \
        "python-dateutil>=2.8" \
        "typing-extensions>=4.5" \
        "tabulate>=0.8.9" \
        "imageio>=2.31" \
        notebook==7.2.2 \
        jupyterlab==4.2.5 \
        ipykernel==6.29.5 \
        nbconvert==7.16.4 \
        jupyter_server==2.14.1; \
    python -c "import numpy; print('numpy:', numpy.__version__)"; \
    python -c "import google.protobuf; print('protobuf ok')"; \
    jupyter --version

# Copy compiled Caffe artifacts from caffe-builder
COPY --from=caffe-builder /opt/caffe-dist/ /opt/caffe-dist/

# Copy BVLC API compatibility layer patches
COPY caffe/docker/standalone/pycaffe-customer/python/caffe_patches/caffe/__init__.py /opt/caffe-patches/__init__.py
COPY caffe/docker/standalone/pycaffe-customer/python/caffe_patches/caffe/io.py /opt/caffe-patches/io.py
COPY caffe/docker/standalone/pycaffe-customer/python/caffe_patches/caffe/proto/__init__.py /opt/caffe-patches/proto/__init__.py
COPY caffe/docker/standalone/pycaffe-customer/python/caffe_patches/protos/__init__.py /opt/caffe-patches/protos/__init__.py

# Install compiled libraries and Python packages into system paths + apply compat patches
RUN set -eux; \
    echo "/usr/local/lib" > /etc/ld.so.conf.d/caffe.conf; \
    cp /opt/caffe-dist/lib/*.so* /usr/local/lib/; \
    cp /opt/caffe-dist/lib/*.so* /usr/lib/ 2>/dev/null || true; \
    ldconfig; \
    SITE_PACKAGES=$(python -c "import site; print(site.getsitepackages()[0])"); \
    cp -r /opt/caffe-dist/python/* ${SITE_PACKAGES}/; \
    mkdir -p ${SITE_PACKAGES}/caffe/proto; \
    cp /opt/caffe-patches/__init__.py ${SITE_PACKAGES}/caffe/__init__.py; \
    cp /opt/caffe-patches/io.py ${SITE_PACKAGES}/caffe/io.py; \
    cp /opt/caffe-patches/proto/__init__.py ${SITE_PACKAGES}/caffe/proto/__init__.py; \
    cp /opt/caffe-patches/protos/__init__.py ${SITE_PACKAGES}/protos/__init__.py; \
    cp ${SITE_PACKAGES}/protos/caffe_pb2.py ${SITE_PACKAGES}/caffe/proto/caffe_pb2.py; \
    echo "Installed caffe native libraries, Python packages, and BVLC compat layer"; \
    ls -lh /usr/local/lib/libtvm_ffi* /usr/local/lib/_caffe* 2>/dev/null || true; \
    ldconfig -p | grep -E "tvm_ffi|_caffe" || echo "WARNING: libraries not in ldconfig cache"

# Create pycaffe compatibility __init__.py
RUN set -eux; \
    SITE_PACKAGES=$(python -c "import site; print(site.getsitepackages()[0])"); \
    mkdir -p ${SITE_PACKAGES}/pycaffe; \
    cat > ${SITE_PACKAGES}/pycaffe/__init__.py << 'PYEOF'
"""pycaffe compatibility package - wraps caffe (tvm-ffi inference) with old API."""
from __future__ import annotations
import caffe as _caffe_mod

TRAIN = 0
TEST = 1
Net = _caffe_mod.Net
set_mode_cpu = _caffe_mod.set_mode_cpu
set_mode_gpu = _caffe_mod.set_mode_gpu if hasattr(_caffe_mod, 'set_mode_gpu') else lambda: None
set_device = _caffe_mod.set_device if hasattr(_caffe_mod, 'set_device') else lambda x: None
set_random_seed = _caffe_mod.set_random_seed
layer_type_list = _caffe_mod.layer_type_list
__version__ = _caffe_mod.version()

class _SolverStub:
    def __init__(self, *a, **kw):
        raise NotImplementedError("Solver classes not available in slim inference-only build.")

SGDSolver = type("SGDSolver", (_SolverStub,), {})
NesterovSolver = type("NesterovSolver", (_SolverStub,), {})
AdaGradSolver = type("AdaGradSolver", (_SolverStub,), {})
RMSPropSolver = type("RMSPropSolver", (_SolverStub,), {})
AdaDeltaSolver = type("AdaDeltaSolver", (_SolverStub,), {})
AdamSolver = type("AdamSolver", (_SolverStub,), {})
NCCL = None
Timer = None

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

import logging
log = logging.getLogger("pycaffe")
def init_log(name="pycaffe"):
    logging.basicConfig(level=logging.INFO)
    return logging.getLogger(name)
def get_solver(*a, **kw):
    raise NotImplementedError("get_solver not available in slim build")
def solver_count(): return 1
def set_solver_count(v): pass
def solver_rank(): return 0
def set_solver_rank(v): pass
def set_multiprocess(v): pass
def has_nccl(): return False
PYEOF

# Copy pycaffe auxiliary modules
RUN set -eux; \
    SITE_PACKAGES=$(python -c "import site; print(site.getsitepackages()[0])"); \
    cp /opt/caffe-dist/pycaffe-modules/* ${SITE_PACKAGES}/pycaffe/ 2>/dev/null || true; \
    touch ${SITE_PACKAGES}/pycaffe/py.typed 2>/dev/null || true

# Create builder user and directory structure
RUN set -eux; \
    if ! getent group ${BUILDER_USER} >/dev/null; then \
        if getent group ${BUILDER_GID} >/dev/null; then groupadd ${BUILDER_USER}; \
        else groupadd -g ${BUILDER_GID} ${BUILDER_USER}; fi; \
    fi; \
    if ! id -u ${BUILDER_USER} >/dev/null 2>&1; then \
        if getent passwd ${BUILDER_UID} >/dev/null; then useradd -m -s /bin/bash -g ${BUILDER_USER} ${BUILDER_USER}; \
        else useradd -m -s /bin/bash -u ${BUILDER_UID} -g ${BUILDER_GID} ${BUILDER_USER}; fi; \
    fi; \
    usermod -aG sudo ${BUILDER_USER}; \
    mkdir -p ${WORKSPACE_DIR} /opt/caffe-examples /run/sshd /var/log/supervisor /etc/supervisor/conf.d \
             /home/builder/.jupyter/jupyter_server_config.d \
             /home/builder/.jupyter/jupyter_notebook_config.d \
             /home/builder/.local/share/jupyter/runtime \
             /home/builder/.ssh; \
    chmod 755 /run/sshd; \
    chmod 700 /home/builder/.ssh; \
    chown -R ${BUILDER_UID}:${BUILDER_GID} ${WORKSPACE_DIR} /home/builder /opt/caffe-examples; \
    ln -sf /opt/caffe-examples ${WORKSPACE_DIR}/examples; \
    ln -sf /usr/share/zoneinfo/UTC /etc/localtime; \
    echo "UTC" > /etc/timezone; \
    echo "export PATH=/usr/local/bin:/usr/bin:/bin" >> /home/builder/.bashrc; \
    chown builder:builder /home/builder/.bashrc; \
    mkdir -p ${WORKSPACE_DIR}/pycaffe-examples && \
    cp /opt/caffe-dist/examples/lenet/* ${WORKSPACE_DIR}/pycaffe-examples/ 2>/dev/null || true; \
    chown -R builder:builder ${WORKSPACE_DIR}/pycaffe-examples

# Copy configuration files
COPY caffe/docker/standalone/pycaffe-customer/config/sshd_config /etc/ssh/sshd_config
COPY caffe/docker/standalone/pycaffe-customer/config/supervisord.conf /etc/supervisor/supervisord.conf
COPY caffe/docker/standalone/pycaffe-customer/config/supervisor/conf.d/ /etc/supervisor/conf.d/
COPY caffe/docker/standalone/pycaffe-customer/config/jupyter_notebook_config.py /home/builder/.jupyter/jupyter_notebook_config.py

# Copy scripts
COPY caffe/docker/standalone/pycaffe-customer/entrypoint.sh /usr/local/bin/entrypoint.sh
COPY caffe/docker/standalone/pycaffe-customer/scripts/healthcheck.sh /usr/local/bin/healthcheck.sh
COPY caffe/docker/standalone/pycaffe-customer/scripts/caffe-verify /usr/local/bin/caffe-verify

# Copy example files (ResNet50 model + inference script)
# ResNet50 model files come from pycaffe-jupyter-ssh/examples (already in build context)
COPY caffe/docker/standalone/pycaffe-jupyter-ssh/examples/resnet50/ /opt/caffe-examples/resnet50/
COPY caffe/docker/standalone/pycaffe-customer/scripts/infer.py /opt/caffe-examples/infer.py

# Copy user workspace (test models, notebooks, scripts) into the image
COPY caffe/workspace/ ${WORKSPACE_DIR}/user-data/

# Set permissions and validate
RUN set -eux; \
    chmod +x /usr/local/bin/entrypoint.sh /usr/local/bin/healthcheck.sh /usr/local/bin/caffe-verify; \
    chown -R builder:builder /home/builder/.jupyter /home/builder/.ssh /opt/caffe-examples ${WORKSPACE_DIR}; \
    echo "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" >> /etc/environment; \
    sshd -t; \
    echo "Configs validated"; \
    rm -f /etc/ssh/ssh_host_*_key /etc/ssh/ssh_host_*_key.pub

# Write build info
RUN set -eux; \
    echo "BUILD_DATE=${BUILD_DATE:-$(date -u +%Y-%m-%dT%H:%M:%SZ)}" > /etc/caffe-customer-release; \
    echo "IMAGE_VERSION=${IMAGE_VERSION}" >> /etc/caffe-customer-release; \
    echo "CAFFE_VERSION=${CAFFE_VERSION}-slim" >> /etc/caffe-customer-release; \
    echo "BASE_IMAGE=ubuntu:26.04" >> /etc/caffe-customer-release; \
    echo "BUILD_TYPE=self-contained-multi-stage" >> /etc/caffe-customer-release; \
    echo "LOCALE=C.UTF-8" >> /etc/caffe-customer-release; \
    echo "TIMEZONE=UTC" >> /etc/caffe-customer-release; \
    echo "NON_ROOT_USER=${BUILDER_USER}" >> /etc/caffe-customer-release; \
    echo "NON_ROOT_UID=${BUILDER_UID}" >> /etc/caffe-customer-release; \
    echo "SERVICES=sshd,jupyter" >> /etc/caffe-customer-release; \
    echo "DEFAULT_SSH_PASSWORD=caffepass" >> /etc/caffe-customer-release; \
    echo "DEFAULT_JUPYTER_TOKEN=caffe-token" >> /etc/caffe-customer-release

# Final verification: pycaffe imports correctly, no build tools present
RUN set -eux; \
    python -c "import pycaffe; print('pycaffe version:', pycaffe.__version__)"; \
    python -c "import caffe; print('caffe loaded')"; \
    python -c "import tvm_ffi; print('tvm_ffi ok')"; \
    echo "--- Checking build tools are NOT present ---"; \
    for tool in gcc g++ cmake ninja git make; do \
        if command -v $tool >/dev/null 2>&1; then echo "WARNING: $tool found in runtime!"; else echo "OK: $tool not present"; fi; \
    done; \
    supervisord --version; \
    tini --version; \
    gosu --version; \
    jupyter --version; \
    echo "Final verification passed"

# Clean up
RUN set -eux; \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /var/cache/apt/* /root/.cache/pip /opt/caffe-dist; \
    find /usr -name "*.pyc" -delete 2>/dev/null || true; \
    find /usr -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

WORKDIR ${WORKSPACE_DIR}
VOLUME ["/workspace"]
EXPOSE 22 8888

HEALTHCHECK --interval=30s --timeout=10s --start-period=45s --retries=3 \
    CMD /usr/local/bin/healthcheck.sh

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/entrypoint.sh"]
CMD []
