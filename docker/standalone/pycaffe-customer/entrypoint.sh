#!/bin/bash
set -euo pipefail

if [ "${DEBUG:-0}" = "1" ]; then
    set -x
fi

if [ -n "${ENABLE_SUDO_NOPASSWD:-}" ] && [ "${GRANT_SUDO:-no}" = "no" ]; then
    if [ "${ENABLE_SUDO_NOPASSWD}" = "1" ] || [ "${ENABLE_SUDO_NOPASSWD}" = "yes" ] || [ "${ENABLE_SUDO_NOPASSWD}" = "true" ]; then
        export GRANT_SUDO=yes
    fi
fi

if [ -n "${JUPYTER_CORS_ORIGIN:-}" ] && [ -z "${JUPYTER_ALLOW_ORIGIN:-}" ]; then
    export JUPYTER_ALLOW_ORIGIN="${JUPYTER_CORS_ORIGIN}"
fi

log_info()  { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [INFO]  $*"; }
log_warn()  { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [WARN]  $*" >&2; }
log_error() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR] $*" >&2; }

print_banner() {
    local ver="unknown"
    if [ -f /etc/caffe-customer-release ]; then
        ver=$(grep IMAGE_VERSION /etc/caffe-customer-release 2>/dev/null | cut -d= -f2 || echo "unknown")
    fi
    echo ""
    echo "============================================================"
    echo "  PyCaffe Customer Docker Image v${ver}"
    echo "  $(grep '^CAFFE_VERSION=' /etc/caffe-customer-release 2>/dev/null || echo 'Caffe slim')"
    echo ""
    echo "  Time:      $(date)"
    echo "  Host:      $(hostname)"
    echo "  Timezone:  ${TZ:-UTC} (set TZ env var to change)"
    echo "  Locale:    ${LANG:-C.UTF-8}"
    echo "============================================================"
    echo ""
}

diagnose_system() {
    log_info "========== System Info =========="
    log_info "OS:       $(grep PRETTY_NAME /etc/os-release | cut -d= -f2 | tr -d '"')"
    log_info "Kernel:   $(uname -r)"
    log_info "Arch:     $(uname -m)"
    log_info "User:     $(id)"
    if [ -f /etc/caffe-customer-release ]; then
        log_info "Build info:"
        while IFS= read -r line; do log_info "  $line"; done < /etc/caffe-customer-release
    fi
    log_info "================================"
    echo ""
}

setup_passwords() {
    log_info "[Setup 1/6] Configuring user credentials..."
    local user="${NON_ROOT_USER:-builder}"

    if [ "${ALLOW_ROOT_SSH:-no}" = "yes" ]; then
        if [ -n "${ROOT_PASSWORD:-}" ]; then
            echo "root:${ROOT_PASSWORD}" | chpasswd
            log_info "Root password set from ROOT_PASSWORD env var"
        else
            ROOT_PASSWORD=$(pwgen -s 16 1)
            echo "root:${ROOT_PASSWORD}" | chpasswd
            log_warn "ROOT_PASSWORD not set, generated random root password (see log below)"
            echo "    *** Root password: ${ROOT_PASSWORD} ***"
        fi
    fi

    if [ -n "${USER_PASSWORD:-}" ]; then
        echo "${user}:${USER_PASSWORD}" | chpasswd
        log_info "${user} password set from USER_PASSWORD env var"
    else
        USER_PASSWORD="${DEFAULT_USER_PASSWORD:-caffepass}"
        echo "${user}:${USER_PASSWORD}" | chpasswd
        log_info "Using default password for ${user} (set USER_PASSWORD env var to change)"
    fi

    if [ "${GRANT_SUDO:-no}" = "yes" ]; then
        echo "${user} ALL=(ALL) NOPASSWD:ALL" > "/etc/sudoers.d/${user}"
        chmod 0440 "/etc/sudoers.d/${user}"
        log_info "Sudo NOPASSWD enabled for ${user}"
    else
        rm -f "/etc/sudoers.d/${user}"
    fi
}

generate_host_keys() {
    log_info "[Setup 2/6] Generating SSH host keys (fresh per container)..."
    rm -f /etc/ssh/ssh_host_*_key /etc/ssh/ssh_host_*_key.pub 2>/dev/null || true
    ssh-keygen -A
    if [ ! -f /etc/ssh/ssh_host_ed25519_key ]; then
        ssh-keygen -t ed25519 -f /etc/ssh/ssh_host_ed25519_key -N "" -q
    fi
    log_info "SSH host keys generated successfully"
}

configure_sshd() {
    log_info "[Setup 3/6] Configuring SSH daemon..."
    mkdir -p /run/sshd && chmod 755 /run/sshd

    if [ "${ALLOW_ROOT_SSH:-no}" = "yes" ]; then
        sed -i "s/^#*PermitRootLogin.*/PermitRootLogin yes/" /etc/ssh/sshd_config
        log_info "Root SSH login ENABLED (ALLOW_ROOT_SSH=yes)"
    else
        sed -i "s/^#*PermitRootLogin.*/PermitRootLogin no/" /etc/ssh/sshd_config
        log_info "Root SSH login disabled (ALLOW_ROOT_SSH=no)"
    fi

    if /usr/sbin/sshd -t; then
        log_info "sshd_config validation: OK"
    else
        log_error "sshd_config syntax error!"
        /usr/sbin/sshd -T 2>&1 | head -20 | while IFS= read -r line; do log_error "  $line"; done
        exit 1
    fi
}

setup_ssh_keys() {
    log_info "[Setup 4/6] Configuring SSH public key auth..."
    local user="${NON_ROOT_USER:-builder}"
    if [ -n "${SSH_PUBLIC_KEY:-}" ]; then
        echo "$SSH_PUBLIC_KEY" >> "/home/${user}/.ssh/authorized_keys"
        chmod 600 "/home/${user}/.ssh/authorized_keys"
        chown "${user}:${user}" "/home/${user}/.ssh/authorized_keys"
        if [ "${ALLOW_ROOT_SSH:-no}" = "yes" ]; then
            mkdir -p /root/.ssh
            echo "$SSH_PUBLIC_KEY" >> /root/.ssh/authorized_keys
            chmod 600 /root/.ssh/authorized_keys
        fi
        local key_count
        key_count=$(grep -c "ssh-" "/home/${user}/.ssh/authorized_keys" 2>/dev/null || echo 0)
        log_info "SSH public keys injected (count: ${key_count})"
    else
        log_info "No SSH_PUBLIC_KEY set; password authentication only"
    fi
}

setup_jupyter() {
    log_info "[Setup 5/6] Configuring Jupyter Notebook..."
    local user="${NON_ROOT_USER:-builder}"
    local jupyter_config_dir="/home/${user}/.jupyter"
    local jupyter_server_config_d="${jupyter_config_dir}/jupyter_server_config.d"
    local jupyter_notebook_config_d="${jupyter_config_dir}/jupyter_notebook_config.d"

    mkdir -p "/workspace" "${jupyter_server_config_d}" "${jupyter_notebook_config_d}"
    chown -R "${user}:${user}" "/workspace" "${jupyter_config_dir}" 2>/dev/null || true
    chmod 755 "/workspace"
    chmod 700 "/home/${user}/.ssh"

    local token_file_server="${jupyter_server_config_d}/runtime.py"
    local token_file_notebook="${jupyter_notebook_config_d}/runtime.py"

    _write_jupyter_config() {
        local target_file="$1"
        cat > "$target_file" << 'JUPYTER_RUNTIME_EOF'
c = get_config()
JUPYTER_RUNTIME_EOF

    if [ -n "${JUPYTER_PASSWORD:-}" ]; then
        log_info "Setting Jupyter password from JUPYTER_PASSWORD env var..."
        local jupyter_password_hash
        jupyter_password_hash=$(JUPYTER_PASSWORD="${JUPYTER_PASSWORD}" python -c "
import os
from jupyter_server.auth import passwd
print(passwd(os.environ['JUPYTER_PASSWORD']))
")
        cat >> "$target_file" << JUPYTER_RUNTIME_EOF
c.ServerApp.password = '${jupyter_password_hash}'
c.ServerApp.token = ''
c.IdentityProvider.token = ''
c.NotebookApp.password = '${jupyter_password_hash}'
c.NotebookApp.token = ''
JUPYTER_RUNTIME_EOF
        log_info "Jupyter password authentication configured"
    else
        if [ -z "${JUPYTER_TOKEN:-}" ]; then
            JUPYTER_TOKEN="${DEFAULT_JUPYTER_TOKEN:-caffe-token}"
            log_info "Using default Jupyter token (set JUPYTER_TOKEN env var to change)"
        else
            log_info "Using Jupyter token from JUPYTER_TOKEN env var"
        fi
        cat >> "$target_file" << JUPYTER_RUNTIME_EOF
c.ServerApp.token = '${JUPYTER_TOKEN}'
c.ServerApp.password = ''
c.IdentityProvider.token = '${JUPYTER_TOKEN}'
c.NotebookApp.token = '${JUPYTER_TOKEN}'
c.NotebookApp.password = ''
JUPYTER_RUNTIME_EOF
        export JUPYTER_TOKEN
    fi

    cat >> "$target_file" << JUPYTER_RUNTIME_EOF
c.ServerApp.ip = '0.0.0.0'
c.ServerApp.port = ${JUPYTER_PORT:-8888}
c.ServerApp.open_browser = False
c.ServerApp.root_dir = '/workspace'
c.ServerApp.allow_root = False
c.ServerApp.allow_origin = '${JUPYTER_ALLOW_ORIGIN:-*}'
c.ServerApp.allow_credentials = True
c.NotebookApp.ip = '0.0.0.0'
c.NotebookApp.port = ${JUPYTER_PORT:-8888}
c.NotebookApp.open_browser = False
c.NotebookApp.notebook_dir = '/workspace'
c.NotebookApp.allow_root = False
c.NotebookApp.allow_origin = '${JUPYTER_ALLOW_ORIGIN:-*}'
JUPYTER_RUNTIME_EOF
    }

    _write_jupyter_config "$token_file_server"
    _write_jupyter_config "$token_file_notebook"
    touch "${jupyter_config_dir}/jupyter_server_config.py" "${jupyter_config_dir}/jupyter_notebook_config.py" 2>/dev/null || true

    chown -R "${user}:${user}" "${jupyter_config_dir}" 2>/dev/null || true
}

print_access_info() {
    local user="${NON_ROOT_USER:-builder}"
    local ssh_status="enabled"
    if [ "${DISABLE_SSH:-no}" = "yes" ] || [ "${DISABLE_SSH:-no}" = "1" ] || [ "${DISABLE_SSH:-no}" = "true" ]; then
        ssh_status="DISABLED"
    fi

    echo ""
    echo "============================================================"
    echo "  Container is READY!"
    echo ""
    echo "  ---- Jupyter Notebook ----"
    echo "  URL:      http://localhost:${JUPYTER_PORT:-8888}/"
    if [ -n "${JUPYTER_PASSWORD:-}" ]; then
    echo "  Auth:     Password (set via JUPYTER_PASSWORD)"
    else
    echo "  Token:    ${JUPYTER_TOKEN}"
    fi
    echo ""
    echo "  ---- SSH Access ----"
    if [ "$ssh_status" = "DISABLED" ]; then
    echo "  SSH is DISABLED (set DISABLE_SSH=no to enable)"
    else
    echo "  Command:  ssh ${user}@<host> -p <mapped-port>"
    echo "  User:     ${user}"
    echo "  Password: ${USER_PASSWORD}"
    fi
    echo ""
    echo "  ---- Quick Verification ----"
    echo "  Run 'caffe-verify' inside the container to verify all"
    echo "  components are working correctly."
    echo ""
    echo "  ---- Examples ----"
    echo "  ResNet50 demo:    /opt/caffe-examples/infer.py"
    echo "  Inference script: python /opt/caffe-examples/infer.py"
    echo "  LeNet deploy:     /workspace/pycaffe-examples/"
    echo ""
    echo "  !!! SECURITY NOTICE !!!"
    echo "  Default credentials are in use. For production deployments,"
    echo "  set USER_PASSWORD and JUPYTER_TOKEN environment variables."
    echo "============================================================"
    echo ""
}

print_banner

# Source profile scripts for environment variables
set +u
if [ -f /etc/profile.d/pycaffe.sh ]; then
    . /etc/profile.d/pycaffe.sh
fi
if [ -d /etc/profile.d ]; then
    for f in /etc/profile.d/*.sh; do
        if [ -f "$f" ] && [ "$f" != "/etc/profile.d/pycaffe.sh" ]; then
            . "$f" 2>/dev/null || true
        fi
    done
fi
set -u

# Command mode: exec user command directly
if [ $# -gt 0 ]; then
    log_info "Command mode: '$*' - executing directly (no services)"
    diagnose_system
    setup_passwords
    if [ "$(id -u)" = "0" ]; then
        target_user="${NON_ROOT_USER:-builder}"
        export HOME="/home/${target_user}"
        export USER="${target_user}"
        export LOGNAME="${target_user}"
        cd /workspace
        exec gosu "${target_user}" "$@"
    else
        exec "$@"
    fi
fi

# Service mode: full startup
diagnose_system
setup_passwords

ssh_status="enabled"
if [ "${DISABLE_SSH:-no}" = "yes" ] || [ "${DISABLE_SSH:-no}" = "1" ] || [ "${DISABLE_SSH:-no}" = "true" ]; then
    ssh_status="disabled"
    log_info "SSH service disabled (DISABLE_SSH=${DISABLE_SSH})"
    rm -f /etc/supervisor/conf.d/sshd.conf
else
    generate_host_keys
    configure_sshd
fi

setup_ssh_keys
setup_jupyter
print_access_info

log_info "Starting supervisord..."
exec /usr/bin/supervisord -c /etc/supervisor/supervisord.conf
