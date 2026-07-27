# ==============================================================================
# PyCaffe + SSH + Jupyter Dockerfile (CPU-only, Ubuntu 26.04)
#
# 说明：基于 caffe-cpu:standalone-pycaffe 镜像扩展，添加 OpenSSH Server 和
#       Jupyter Notebook/Lab，通过 supervisord 管理双服务。
#       不在本 Dockerfile 中重复编译 pycaffe，而是复用 standalone-pycaffe 的
#       构建产物（已正确配置 caffe/_caffe.so + pycaffe 兼容包）。
#
# 前置条件：需要先构建 caffe-cpu:standalone-pycaffe 基础镜像：
#   cd vendor && docker build -t caffe-cpu:standalone-pycaffe --target runtime \
#     -f caffe/docker/standalone/pycaffe/Dockerfile .
#
# 构建上下文：vendor/（需要访问 config/ 和 scripts/ 目录）
#
# 使用示例:
#   cd vendor && docker build -t caffe-cpu:pycaffe-jupyter-ssh \
#     -f caffe/docker/standalone/pycaffe-jupyter-ssh/Dockerfile .
#
# 运行示例:
#   docker run -d -p 2222:22 -p 8888:8888 \
#     -e USER_PASSWORD=changeme -e JUPYTER_TOKEN=mysecret \
#     -v $(pwd)/workspace:/workspace \
#     caffe-cpu:pycaffe-jupyter-ssh
# ==============================================================================

FROM caffe-cpu:standalone-pycaffe AS runtime

LABEL maintainer="Caffe Standalone Docker (Ubuntu 26.04)"
LABEL description="PyCaffe CPU-only runtime with SSH + Jupyter Notebook, managed by supervisord"

ARG CAFFE_VERSION=1.0.0-slim

ENV TZ=Asia/Shanghai \
    LANG=zh_CN.UTF-8 \
    LANGUAGE=zh_CN:zh \
    LC_ALL=zh_CN.UTF-8 \
    NON_ROOT_USER=builder \
    JUPYTER_PORT=8888 \
    SSH_PORT=22 \
    GRANT_SUDO=no \
    ALLOW_ROOT_SSH=no \
    JUPYTER_ALLOW_ORIGIN=

USER root

# -----------------------------------------------------------------------------
# Stage 1: 安装 SSH + Jupyter 运行时系统包 + 中文 locale
# -----------------------------------------------------------------------------
RUN echo "=== Stage 1: Installing SSH+Jupyter runtime packages + Chinese locale ===" && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        gosu \
        locales \
        openssh-server \
        openssh-client \
        pwgen \
        supervisor \
        tini \
    && echo "[BUILD] Runtime packages installed (gosu included for privilege dropping)" && \
    echo "[BUILD] Generating zh_CN.UTF-8 locale..." && \
    sed -i 's/^# *zh_CN.UTF-8 UTF-8/zh_CN.UTF-8 UTF-8/' /etc/locale.gen && \
    locale-gen zh_CN.UTF-8 && \
    update-locale LANG=zh_CN.UTF-8 && \
    ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && \
    echo "Asia/Shanghai" > /etc/timezone && \
    echo "[BUILD] zh_CN locale + Asia/Shanghai timezone ready" && \
    rm -rf /var/lib/apt/lists/*

# -----------------------------------------------------------------------------
# Stage 2: 安装 Jupyter Python 包
# -----------------------------------------------------------------------------
RUN echo "=== Stage 2: Installing Jupyter Python packages ===" && \
    pip install --break-system-packages --no-cache-dir \
        notebook==7.2.2 \
        jupyterlab==4.2.5 \
        ipykernel==6.29.5 \
        nbconvert==7.16.4 \
        jupyter_server==2.14.1 && \
    echo "[BUILD] Jupyter packages installed:" && \
    jupyter --version

# -----------------------------------------------------------------------------
# Stage 3: 确保 builder 用户 HOME 目录和权限正确
# -----------------------------------------------------------------------------
RUN echo "=== Stage 3: Ensuring builder user directories ===" && \
    mkdir -p /home/builder/.jupyter/jupyter_server_config.d /home/builder/.ssh /run/sshd /var/log/supervisor /etc/supervisor/conf.d && \
    chmod 755 /run/sshd && \
    chmod 700 /home/builder/.ssh && \
    chown -R builder:builder /workspace /home/builder/.jupyter /home/builder/.ssh && \
    echo "export PATH=/usr/local/bin:/usr/bin:/bin" >> /home/builder/.bashrc && \
    chown builder:builder /home/builder/.bashrc && \
    echo "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" >> /etc/environment && \
    echo "[BUILD] Working directory /workspace and .jupyter/.ssh directories ready"

# -----------------------------------------------------------------------------
# Stage 4: 安装配置文件和脚本
# -----------------------------------------------------------------------------
RUN echo "=== Stage 4: Installing configuration files ===" && \
    ssh-keygen -A >/dev/null 2>&1 && \
    echo "[BUILD] Initial SSH host keys generated (will be regenerated at entrypoint)"

COPY caffe/docker/standalone/pycaffe-jupyter-ssh/config/sshd_config /etc/ssh/sshd_config
COPY caffe/docker/standalone/pycaffe-jupyter-ssh/config/supervisord.conf /etc/supervisor/supervisord.conf
COPY caffe/docker/standalone/pycaffe-jupyter-ssh/config/supervisor/conf.d/ /etc/supervisor/conf.d/
COPY caffe/docker/standalone/pycaffe-jupyter-ssh/config/jupyter_notebook_config.py /home/builder/.jupyter/jupyter_notebook_config.py
COPY caffe/docker/standalone/pycaffe-jupyter-ssh/entrypoint.sh /usr/local/bin/entrypoint.sh
COPY caffe/docker/standalone/pycaffe-jupyter-ssh/scripts/healthcheck.sh /usr/local/bin/healthcheck.sh
RUN chmod +x /usr/local/bin/entrypoint.sh /usr/local/bin/healthcheck.sh && \
    chown -R builder:builder /home/builder/.jupyter && \
    chown -R builder:builder /workspace && \
    echo "[BUILD] Permissions set: entrypoint.sh and healthcheck.sh executable" && \
    echo "[BUILD] Validating sshd_config..." && \
    sshd -t && echo "[BUILD] sshd_config syntax: OK"

# -----------------------------------------------------------------------------
# Stage 5: 移除预配置的 sudoers，让 entrypoint 运行时管理
# -----------------------------------------------------------------------------
RUN echo "=== Stage 5: Finalizing sudo configuration ===" && \
    rm -f /etc/sudoers.d/90-builder && \
    echo "[BUILD] Default sudo NOPASSWD removed (controlled by GRANT_SUDO env var at runtime)"

# -----------------------------------------------------------------------------
# Stage 6: 构建信息、清理、最终验证
# -----------------------------------------------------------------------------
RUN echo "=== Stage 6: Final configuration and verification ===" && \
    BUILDER_UID_VAL=$(id -u builder) && \
    echo "BUILD_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ)" > /etc/jupyter-ssh-build-info && \
    echo "BASE_IMAGE=caffe-cpu:standalone-pycaffe" >> /etc/jupyter-ssh-build-info && \
    echo "BUILD_TYPE=layered-extension" >> /etc/jupyter-ssh-build-info && \
    echo "LOCALE=zh_CN.UTF-8" >> /etc/jupyter-ssh-build-info && \
    echo "TIMEZONE=Asia/Shanghai" >> /etc/jupyter-ssh-build-info && \
    echo "NON_ROOT_USER=builder" >> /etc/jupyter-ssh-build-info && \
    echo "NON_ROOT_UID=${BUILDER_UID_VAL}" >> /etc/jupyter-ssh-build-info && \
    echo "SERVICES=sshd,jupyter" >> /etc/jupyter-ssh-build-info && \
    echo "SUPERVISOR=enabled" >> /etc/jupyter-ssh-build-info && \
    echo "PYTHON=system-python3" >> /etc/jupyter-ssh-build-info && \
    echo "CAFFE_VERSION=${CAFFE_VERSION}" >> /etc/jupyter-ssh-build-info && \
    cat /etc/jupyter-ssh-build-info && \
    echo "[BUILD] Build info written to /etc/jupyter-ssh-build-info" && \
    echo "[BUILD] Running cleanup..." && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* && \
    echo "[BUILD] Cleanup complete" && \
    echo "[BUILD] Running final verification..." && \
    sshd -t && echo "[OK] sshd config valid" && \
    supervisord --version && echo "[OK] supervisord available" && \
    gosu --version && echo "[OK] gosu available (privilege dropping)" && \
    tini --version && echo "[OK] tini available" && \
    python --version && echo "[OK] python available" && \
    pip --version && echo "[OK] pip available" && \
    jupyter --version && echo "[OK] jupyter available" && \
    python -c "import pycaffe; print('[OK] pycaffe version:', pycaffe.__version__)" && \
    bash -n /usr/local/bin/entrypoint.sh && echo "[OK] entrypoint.sh syntax valid" && \
    bash -n /usr/local/bin/healthcheck.sh && echo "[OK] healthcheck.sh syntax valid" && \
    id builder && echo "[OK] builder user exists (UID=$(id -u builder))" && \
    echo "" && \
    echo "[BUILD] ========== BUILD COMPLETE ==========" && \
    echo ""

WORKDIR /workspace
VOLUME ["/workspace"]
EXPOSE 22 8888

HEALTHCHECK --interval=30s --timeout=10s --start-period=45s --retries=3 \
    CMD /usr/local/bin/healthcheck.sh

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/entrypoint.sh"]
CMD []
