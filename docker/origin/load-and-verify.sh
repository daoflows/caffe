#!/usr/bin/env bash
# ==============================================================================
# Caffe Docker 镜像加载与验证脚本 (origin)
# 功能：加载 tar 镜像文件并运行 verify-caffe.sh 验证环境
# 用法：./load-and-verify.sh [镜像文件1] [镜像文件2]
# 自包含版本：不依赖外部库，内联日志函数
# ==============================================================================

set -euo pipefail

# ------------------------------------------------------------------------------
# 内联日志函数（自包含，参考 build.sh 风格）
# ------------------------------------------------------------------------------
log_info()    { echo -e "\033[34m[INFO]\033[0m $*"; }
log_success() { echo -e "\033[32m[OK]\033[0m $*"; }
log_warn()    { echo -e "\033[33m[WARN]\033[0m $*"; }
log_error()   { echo -e "\033[31m[ERROR]\033[0m $*" >&2; }
log_header()  { echo -e "\n\033[1;36m========================================\033[0m"; echo -e "\033[1;36m $* \033[0m"; echo -e "\033[1;36m========================================\033[0m"; }
log_section() { echo -e "\n\033[1;37m--- $* ---\033[0m"; }
log_kv()      { echo -e "  \033[37m$1:\033[0m $2"; }
log_blank()   { echo ""; }

# ------------------------------------------------------------------------------
# 路径变量（Windows/WSL2 兼容）
# ------------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
DIST_DIR="${SCRIPT_DIR}/dist"

DEFAULT_IMAGE_NAME="caffe-cpu"
DEFAULT_RUNTIME_TAG="origin-runtime"
DEFAULT_JUPYTER_TAG="origin-jupyter"

LOADED_IMAGES=()
VERIFY_RESULTS=()
RUNTIME_IMAGE=""
JUPYTER_IMAGE=""

# ------------------------------------------------------------------------------
# 帮助信息
# ------------------------------------------------------------------------------
show_help() {
    cat <<EOF
用法: $(basename "$0") [选项] [镜像文件1] [镜像文件2]

加载 Caffe Docker tar 镜像并验证运行环境

参数:
  (无参数)            自动在 dist/ 目录查找最新的 runtime 和 jupyter 镜像并加载
  镜像文件1           只加载指定的单个镜像文件
  镜像文件1 镜像文件2 按顺序加载两个镜像文件
  -h, --help          显示此帮助信息

镜像文件检测:
  - 查找位置: 脚本所在目录的 dist/ 子目录
  - 文件名模式: caffe-cpu-origin-runtime*.tar / caffe-cpu-origin-jupyter*.tar
  - 支持 .tar 和 .tar.gz 格式
  - 多个匹配时选择最新修改的文件

示例:
  $(basename "$0")                                    # 自动检测并加载所有镜像
  $(basename "$0") dist/caffe-cpu-origin-runtime.tar  # 加载指定 runtime 镜像
  $(basename "$0") runtime.tar jupyter.tar.gz         # 加载两个指定镜像
EOF
}

# ------------------------------------------------------------------------------
# Docker 环境检查
# ------------------------------------------------------------------------------
check_docker() {
    log_section "环境检查"

    if ! command -v docker &>/dev/null; then
        log_error "未找到 docker 命令"
        log_info "请先安装 Docker Desktop 并启用 WSL2 后端（Windows 推荐）"
        exit 1
    fi
    log_success "Docker 已安装: $(docker --version 2>&1 | head -1)"

    if ! docker info &>/dev/null; then
        log_error "Docker 服务未运行"
        log_info "请启动 Docker Desktop 并等待服务就绪（系统托盘图标变绿）"
        exit 1
    fi
    log_success "Docker 服务运行中"
}

# ------------------------------------------------------------------------------
# 在 dist/ 目录查找最新匹配的镜像文件
# ------------------------------------------------------------------------------
find_latest_image() {
    local pattern="$1"
    local latest_file=""
    local latest_mtime=0

    if [[ ! -d "${DIST_DIR}" ]]; then
        echo ""
        return
    fi

    for ext in tar tar.gz; do
        while IFS= read -r -d '' file; do
            if [[ -f "${file}" ]]; then
                local mtime
                mtime=$(stat -c %Y "${file}" 2>/dev/null || stat -f %m "${file}" 2>/dev/null || echo "0")
                if [[ "${mtime}" -gt "${latest_mtime}" ]]; then
                    latest_mtime="${mtime}"
                    latest_file="${file}"
                fi
            fi
        done < <(find "${DIST_DIR}" -maxdepth 1 -name "${pattern}.${ext}" -print0 2>/dev/null)
    done

    echo "${latest_file}"
}

# ------------------------------------------------------------------------------
# 根据文件名推断镜像类型（runtime 或 jupyter）
# ------------------------------------------------------------------------------
guess_image_type() {
    local filename
    filename=$(basename "$1" | tr '[:upper:]' '[:lower:]')
    if [[ "${filename}" == *jupyter* ]]; then
        echo "jupyter"
    else
        echo "runtime"
    fi
}

# ------------------------------------------------------------------------------
# 根据文件名推断默认标签
# ------------------------------------------------------------------------------
guess_default_tag() {
    local img_type
    img_type=$(guess_image_type "$1")
    if [[ "${img_type}" == "jupyter" ]]; then
        echo "${DEFAULT_JUPYTER_TAG}"
    else
        echo "${DEFAULT_RUNTIME_TAG}"
    fi
}

# ------------------------------------------------------------------------------
# 从 docker load 输出解析镜像名:标签
# ------------------------------------------------------------------------------
parse_loaded_image() {
    local load_output="$1"
    local image=""

    image=$(echo "${load_output}" | grep -E '^Loaded image:' | sed -E 's/^Loaded image:[[:space:]]*//' | tr -d '\r' | head -1)

    if [[ -z "${image}" ]]; then
        image=$(echo "${load_output}" | grep -E '^Loaded image ID:' | sed -E 's/^Loaded image ID:[[:space:]]*//' | tr -d '\r' | head -1)
    fi

    echo "${image}"
}

# ------------------------------------------------------------------------------
# 检查文件是否存在且非空
# ------------------------------------------------------------------------------
validate_image_file() {
    local file="$1"

    if [[ ! -f "${file}" ]]; then
        log_error "镜像文件不存在: ${file}"
        return 1
    fi

    local file_size
    file_size=$(stat -c %s "${file}" 2>/dev/null || stat -f %z "${file}" 2>/dev/null || echo "0")
    if [[ "${file_size}" -eq 0 ]]; then
        log_error "镜像文件为空: ${file}"
        return 1
    fi

    local size_mb=$((file_size / 1024 / 1024))
    log_kv "文件大小" "${size_mb} MB"
    return 0
}

# ------------------------------------------------------------------------------
# 加载单个镜像
# ------------------------------------------------------------------------------
load_image() {
    local file="$1"
    local img_type
    img_type=$(guess_image_type "${file}")
    local default_tag
    default_tag=$(guess_default_tag "${file}")
    local default_image="${DEFAULT_IMAGE_NAME}:${default_tag}"

    log_header "加载镜像 ($(basename "${file}"))"

    if ! validate_image_file "${file}"; then
        return 1
    fi

    log_kv "镜像类型" "${img_type}"
    log_kv "文件路径" "${file}"
    log_blank

    log_info "正在加载镜像（大文件可能需要几分钟）..."

    set +e
    local load_output
    load_output=$(docker load -i "${file}" 2>&1)
    local load_exit=$?
    set -e

    echo "${load_output}"

    if [[ ${load_exit} -ne 0 ]]; then
        log_error "镜像加载失败（退出码: ${load_exit}）"
        return 1
    fi

    local loaded_image
    loaded_image=$(parse_loaded_image "${load_output}")

    if [[ -z "${loaded_image}" ]]; then
        log_warn "无法从 docker load 输出解析镜像名，尝试使用默认标签: ${default_image}"
        loaded_image="${default_image}"
    elif [[ "${loaded_image}" == sha256:* ]]; then
        log_warn "镜像加载为 ID (${loaded_image:0:19}...)，自动打标签为: ${default_image}"
        docker tag "${loaded_image}" "${default_image}"
        loaded_image="${default_image}"
    fi

    if ! docker image inspect "${loaded_image}" &>/dev/null; then
        log_error "镜像 ${loaded_image} 加载后仍不可用"
        return 1
    fi

    log_success "镜像加载成功: ${loaded_image}"
    LOADED_IMAGES+=("${loaded_image}")

    if [[ "${img_type}" == "runtime" ]]; then
        RUNTIME_IMAGE="${loaded_image}"
    else
        JUPYTER_IMAGE="${loaded_image}"
    fi

    verify_image "${loaded_image}" "${img_type}"
    return $?
}

# ------------------------------------------------------------------------------
# 验证镜像
# ------------------------------------------------------------------------------
verify_image() {
    local image="$1"
    local img_type="$2"

    log_section "验证镜像: ${image}"
    log_info "启动临时容器运行 verify-caffe.sh（不挂载宿主机目录）..."
    log_blank

    set +e
    docker run --rm --entrypoint verify-caffe.sh "${image}"
    local verify_exit=$?
    set -e

    log_blank

    if [[ ${verify_exit} -eq 0 ]]; then
        log_success "[OK] 镜像验证通过: ${image}"
        VERIFY_RESULTS+=("OK:${image}:${img_type}")
        return 0
    else
        log_error "[ERROR] 镜像验证失败: ${image}（退出码: ${verify_exit}）"
        VERIFY_RESULTS+=("FAIL:${image}:${img_type}")
        return 1
    fi
}

# ------------------------------------------------------------------------------
# 显示加载结果和快速启动命令
# ------------------------------------------------------------------------------
show_summary() {
    log_header "加载验证结果汇总"

    local success_count=0
    local fail_count=0

    for result in "${VERIFY_RESULTS[@]}"; do
        local status="${result%%:*}"
        local rest="${result#*:}"
        local image="${rest%%:*}"
        local img_type="${rest##*:}"

        if [[ "${status}" == "OK" ]]; then
            log_success "✓ [${img_type}] ${image}"
            success_count=$((success_count + 1))
        else
            log_error "✗ [${img_type}] ${image}"
            fail_count=$((fail_count + 1))
        fi
    done

    log_blank
    log_kv "成功" "${success_count} 个"
    log_kv "失败" "${fail_count} 个"

    if [[ ${success_count} -gt 0 ]]; then
        log_section "快速启动命令"

        if [[ -n "${RUNTIME_IMAGE}" ]]; then
            log_info "【Runtime 镜像 - 命令行模式】"
            echo -e "  \033[32mdocker run -it --rm ${RUNTIME_IMAGE} bash\033[0m"
            log_blank
        fi

        if [[ -n "${JUPYTER_IMAGE}" ]]; then
            log_info "【Jupyter+SSH 镜像 - 交互式开发】"
            log_info "方式1: 使用 Jupyter Notebook（推荐）"
            echo -e "  \033[32mdocker run -d -p 8888:8888 -p 2222:22 \\"
            echo -e "    -e USER_PASSWORD=pass -e JUPYTER_TOKEN=mysecret \\"
            echo -e "    -v \$(pwd)/workspace:/workspace \\"
            echo -e "    --name caffe-jupyter ${JUPYTER_IMAGE}\033[0m"
            log_blank
            log_kv "Jupyter 地址" "http://localhost:8888"
            log_kv "Jupyter Token" "mysecret"
            log_kv "SSH 地址" "ssh -p 2222 caffe-origin@localhost"
            log_kv "SSH 密码" "pass"
            log_blank
            log_info "方式2: 使用 run-jupyter.sh 脚本管理"
            echo -e "  \033[32m$(dirname "$0")/run-jupyter.sh start\033[0m"
            log_blank
        fi

        log_info "提示: 也可以使用 run-standalone.sh 脚本（如果提供）进行独立启动"
    fi

    log_blank

    if [[ ${fail_count} -eq 0 ]]; then
        log_success "🎉 所有镜像加载并验证通过！"
        return 0
    else
        log_error "❌ 有 ${fail_count} 个镜像验证失败"
        return 1
    fi
}

# ------------------------------------------------------------------------------
# 主流程
# ------------------------------------------------------------------------------
main() {
    local image_files=()

    while [[ $# -gt 0 ]]; do
        case "$1" in
            -h|--help)
                show_help
                exit 0
                ;;
            -*)
                log_error "未知选项: $1"
                log_info "使用 -h 查看帮助信息"
                exit 1
                ;;
            *)
                image_files+=("$1")
                shift
                ;;
        esac
    done

    log_header "Caffe Docker 镜像加载与验证 (origin)"

    check_docker

    if [[ ${#image_files[@]} -eq 0 ]]; then
        log_section "自动检测镜像文件"
        log_info "在 ${DIST_DIR} 目录查找镜像..."

        if [[ ! -d "${DIST_DIR}" ]]; then
            log_error "dist/ 目录不存在: ${DIST_DIR}"
            log_info "请将镜像 tar 文件放入 dist/ 目录，或手动指定镜像文件路径"
            exit 1
        fi

        local runtime_file jupyter_file
        runtime_file=$(find_latest_image "caffe-cpu-origin-runtime*")
        jupyter_file=$(find_latest_image "caffe-cpu-origin-jupyter*")

        if [[ -z "${runtime_file}" ]] && [[ -z "${jupyter_file}" ]]; then
            log_error "在 ${DIST_DIR} 目录未找到任何匹配的镜像文件"
            log_info "期望的文件名模式: caffe-cpu-origin-runtime*.tar / caffe-cpu-origin-jupyter*.tar"
            log_info "支持格式: .tar / .tar.gz"
            exit 1
        fi

        if [[ -n "${runtime_file}" ]]; then
            image_files+=("${runtime_file}")
            log_success "找到 runtime 镜像: $(basename "${runtime_file}")"
        else
            log_warn "未找到 runtime 镜像"
        fi

        if [[ -n "${jupyter_file}" ]]; then
            image_files+=("${jupyter_file}")
            log_success "找到 jupyter 镜像: $(basename "${jupyter_file}")"
        else
            log_warn "未找到 jupyter 镜像"
        fi
    elif [[ ${#image_files[@]} -gt 2 ]]; then
        log_error "最多支持 2 个镜像文件参数"
        log_info "使用 -h 查看帮助信息"
        exit 1
    fi

    log_blank

    local overall_exit=0
    for file in "${image_files[@]}"; do
        if ! load_image "${file}"; then
            overall_exit=1
        fi
        log_blank
    done

    show_summary
    exit ${overall_exit}
}

main "$@"
