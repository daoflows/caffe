#!/usr/bin/env bash
# ==============================================================================
# Caffe 客户分发包一键构建脚本
# 功能：从 caffe-cpu:jupyter 基础镜像构建自包含客户镜像，包含Notebook、
#       自动复制entrypoint、SHA256校验、分发包打包
# 用法：./build-customer.sh [选项]
# 前置条件：caffe-cpu:jupyter 镜像已存在（通过 ./build.sh --jupyter 构建）
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd -P)"
DIST_DIR="${SCRIPT_DIR}/dist"
WORKSPACE_DIR="${PROJECT_DIR}/workspace"

# ------------------------------------------------------------------------------
# 日志函数（与 build.sh 风格一致）
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
# 默认配置
# ------------------------------------------------------------------------------
DEFAULT_BASE_IMAGE="caffe-cpu:jupyter"
DEFAULT_CUSTOMER_TAG="customer-notebook"
DEFAULT_IMAGE_NAME="caffe-cpu"
DEFAULT_JUPYTER_TOKEN="caffe-notebook-2026"
DEFAULT_USER_PASSWORD="caffepass"
DEFAULT_NOTEBOOK_SRC="${WORKSPACE_DIR}/01_caffe_forward_pass.ipynb"
DEFAULT_EXAMPLES_DIR="/opt/caffe-examples"
DEFAULT_ENTRYPOINT_NAME="entrypoint-customer.sh"
DEFAULT_OUTPUT_PREFIX="caffe-cpu-customer-notebook"

BASE_IMAGE="${DEFAULT_BASE_IMAGE}"
CUSTOMER_TAG="${DEFAULT_CUSTOMER_TAG}"
IMAGE_NAME="${DEFAULT_IMAGE_NAME}"
JUPYTER_TOKEN="${DEFAULT_JUPYTER_TOKEN}"
USER_PASSWORD="${DEFAULT_USER_PASSWORD}"
NOTEBOOK_SRC="${DEFAULT_NOTEBOOK_SRC}"
OUTPUT_PREFIX="${DEFAULT_OUTPUT_PREFIX}"
SKIP_BUILD=false
SKIP_EXPORT=false
SKIP_VERIFY=false
SKIP_PACKAGE=false
NO_CACHE=""
CUSTOM_DATE="$(date +%Y%m%d)"

show_help() {
    cat <<EOF
用法: $(basename "$0") [选项]

一键构建 Caffe 客户分发包（自包含Notebook镜像 + 操作指南 + ZIP包）

选项:
  --base IMAGE        指定基础镜像 (默认: ${DEFAULT_BASE_IMAGE})
  -t TAG              指定客户镜像标签 (默认: ${DEFAULT_CUSTOMER_TAG})
  --token TOKEN       设置 Jupyter Token (默认: ${DEFAULT_JUPYTER_TOKEN})
  --password PASS     设置用户密码 (默认: ${DEFAULT_USER_PASSWORD})
  --notebook PATH     指定Notebook源文件路径 (默认: ${DEFAULT_NOTEBOOK_SRC})
  --output-prefix PFX 输出文件名前缀 (默认: ${DEFAULT_OUTPUT_PREFIX})
  --date DATE         日期标签 (默认: 当天 YYYYMMDD)
  --skip-build        跳过镜像构建（复用已有镜像）
  --skip-export       跳过tar导出
  --skip-verify       跳过验证步骤
  --skip-package      跳过ZIP打包
  --no-cache          无缓存构建
  -h, --help          显示此帮助信息

完整流程:
  1. 前置检查（Docker运行、基础镜像存在、Notebook文件存在）
  2. VOLUME检查（警告基础镜像中的VOLUME声明）
  3. 构建客户镜像（Dockerfile.customer）
  4. 导出镜像为tar + SHA256校验
  5. 端到端验证（可选，加载镜像→启动→访问测试）
  6. 打包为ZIP分发包

示例:
  $(basename "$0")                           # 完整构建流程
  $(basename "$0") --skip-verify             # 跳过验证（快速构建）
  $(basename "$0") -t v1.0 --token mytoken   # 自定义标签和Token
  $(basename "$0") --skip-build --skip-export --skip-verify  # 仅打包
EOF
}

# ------------------------------------------------------------------------------
# 参数解析
# ------------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help) show_help; exit 0 ;;
        --base) BASE_IMAGE="$2"; shift 2 ;;
        -t) CUSTOMER_TAG="$2"; shift 2 ;;
        --token) JUPYTER_TOKEN="$2"; shift 2 ;;
        --password) USER_PASSWORD="$2"; shift 2 ;;
        --notebook) NOTEBOOK_SRC="$2"; shift 2 ;;
        --output-prefix) OUTPUT_PREFIX="$2"; shift 2 ;;
        --date) CUSTOM_DATE="$2"; shift 2 ;;
        --skip-build) SKIP_BUILD=true; shift ;;
        --skip-export) SKIP_EXPORT=true; shift ;;
        --skip-verify) SKIP_VERIFY=true; shift ;;
        --skip-package) SKIP_PACKAGE=true; shift ;;
        --no-cache) NO_CACHE="--no-cache"; shift ;;
        *) log_error "未知选项: $1"; exit 1 ;;
    esac
done

CUSTOMER_IMAGE="${IMAGE_NAME}:${CUSTOMER_TAG}"
TAR_FILENAME="${OUTPUT_PREFIX}_${CUSTOM_DATE}.tar"
SHA_FILENAME="${TAR_FILENAME}.sha256"
ZIP_FILENAME="${OUTPUT_PREFIX}_${CUSTOM_DATE}.zip"
TAR_PATH="${DIST_DIR}/${TAR_FILENAME}"
SHA_PATH="${DIST_DIR}/${SHA_FILENAME}"
GUIDE_PATH="${DIST_DIR}/使用指南.txt"
ZIP_PATH="${DIST_DIR}/${ZIP_FILENAME}"

# ------------------------------------------------------------------------------
# VOLUME 检查函数（ACT-02 的核心逻辑内联在此）
# ------------------------------------------------------------------------------
check_volumes() {
    local image="$1"
    log_section "VOLUME 前置检查"

    local volumes_json
    volumes_json=$(docker inspect "$image" --format='{{json .Config.Volumes}}' 2>/dev/null || echo "{}")

    if [[ "$volumes_json" == "{}" ]] || [[ -z "$volumes_json" ]] || [[ "$volumes_json" == "null" ]]; then
        log_success "基础镜像无 VOLUME 声明"
        return 0
    fi

    log_warn "基础镜像声明了以下 VOLUME（这些目录中的文件不会被 docker commit 保存）:"
    echo "$volumes_json" | python3 -c "
import sys, json
try:
    vols = json.load(sys.stdin)
    for v in vols:
        print(f'  ⚠️  {v}')
except:
    print('  (无法解析VOLUME信息)')
" 2>/dev/null || echo "  $volumes_json"

    log_info "当前方案使用 Dockerfile + entrypoint wrapper 模式，可正确处理VOLUME目录文件注入"
    log_info "预置文件将存放在非VOLUME路径: ${DEFAULT_EXAMPLES_DIR}/"
    return 0
}

# ------------------------------------------------------------------------------
# 前置检查
# ------------------------------------------------------------------------------
preflight_check() {
    log_section "前置检查"

    if ! command -v docker &>/dev/null; then
        log_error "未找到 docker 命令"
        exit 1
    fi
    log_success "Docker 命令可用"

    if ! docker info &>/dev/null; then
        log_error "Docker 未运行，请启动 Docker Desktop"
        exit 1
    fi
    log_success "Docker 服务运行中"

    if [[ "$SKIP_BUILD" != "true" ]]; then
        if ! docker image inspect "${BASE_IMAGE}" &>/dev/null; then
            log_error "基础镜像不存在: ${BASE_IMAGE}"
            log_info "请先运行: ./build.sh --jupyter"
            exit 1
        fi
        log_success "基础镜像存在: ${BASE_IMAGE}"
    fi

    if [[ ! -f "${NOTEBOOK_SRC}" ]]; then
        log_error "Notebook文件不存在: ${NOTEBOOK_SRC}"
        exit 1
    fi
    log_success "Notebook文件: ${NOTEBOOK_SRC}"

    local notebook_size
    notebook_size=$(wc -c < "${NOTEBOOK_SRC}" 2>/dev/null || echo "0")
    log_kv "Notebook大小" "$((notebook_size / 1024)) KB"

    mkdir -p "${DIST_DIR}"
    log_success "输出目录: ${DIST_DIR}"

    local entrypoint_path="${SCRIPT_DIR}/${DEFAULT_ENTRYPOINT_NAME}"
    if [[ ! -f "${entrypoint_path}" ]]; then
        log_error "Entrypoint脚本不存在: ${entrypoint_path}"
        exit 1
    fi
    log_success "Entrypoint脚本: ${entrypoint_path}"
}

# ------------------------------------------------------------------------------
# 准备构建上下文
# ------------------------------------------------------------------------------
prepare_context() {
    log_section "准备构建上下文"

    BUILD_CTX="$(mktemp -d)"
    trap "rm -rf '${BUILD_CTX}'" EXIT

    log_info "临时构建上下文: ${BUILD_CTX}"

    local notebook_name
    notebook_name="$(basename "${NOTEBOOK_SRC}")"

    cp "${NOTEBOOK_SRC}" "${BUILD_CTX}/${notebook_name}"
    cp "${SCRIPT_DIR}/${DEFAULT_ENTRYPOINT_NAME}" "${BUILD_CTX}/entrypoint-customer.sh"

    cat > "${BUILD_CTX}/Dockerfile" <<DOCKERFILE
FROM ${BASE_IMAGE}

LABEL version="1.0.0"
LABEL description="Caffe-Jupyter-customer-self-contained"
LABEL built="${CUSTOM_DATE}"

ENV USER_PASSWORD=${USER_PASSWORD}
ENV JUPYTER_TOKEN=${JUPYTER_TOKEN}
ENV GRANT_SUDO=yes

COPY ${notebook_name} ${DEFAULT_EXAMPLES_DIR}/${notebook_name}
RUN chmod 644 ${DEFAULT_EXAMPLES_DIR}/${notebook_name}

COPY entrypoint-customer.sh /usr/local/bin/entrypoint-customer.sh
RUN chmod +x /usr/local/bin/entrypoint-customer.sh

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/entrypoint-customer.sh"]
CMD []
DOCKERFILE

    log_success "Dockerfile已生成"
    echo "${BUILD_CTX}"
}

# ------------------------------------------------------------------------------
# 构建客户镜像
# ------------------------------------------------------------------------------
build_customer_image() {
    local ctx="$1"
    log_header "构建客户镜像: ${CUSTOMER_IMAGE}"

    check_volumes "${BASE_IMAGE}"

    log_section "构建配置"
    log_kv "基础镜像" "${BASE_IMAGE}"
    log_kv "客户镜像" "${CUSTOMER_IMAGE}"
    log_kv "Jupyter Token" "${JUPYTER_TOKEN}"
    log_kv "构建上下文" "${ctx}"
    log_blank

    local start_ts end_ts duration mins secs
    start_ts=$(date +%s)

    docker build \
        ${NO_CACHE} \
        -t "${CUSTOMER_IMAGE}" \
        -f "${ctx}/Dockerfile" \
        "${ctx}"

    end_ts=$(date +%s)
    duration=$((end_ts - start_ts))
    mins=$((duration / 60))
    secs=$((duration % 60))

    local img_size
    img_size=$(docker image inspect "${CUSTOMER_IMAGE}" --format='{{.Size}}' 2>/dev/null || echo "0")
    local img_size_mb=$((img_size / 1024 / 1024))

    log_success "客户镜像构建成功！"
    log_kv "镜像标签" "${CUSTOMER_IMAGE}"
    log_kv "镜像大小" "${img_size_mb} MB"
    log_kv "构建耗时" "${mins}分${secs}秒"
}

# ------------------------------------------------------------------------------
# 导出镜像
# ------------------------------------------------------------------------------
export_image() {
    log_header "导出镜像为tar文件"

    if [[ -f "${TAR_PATH}" ]]; then
        log_warn "覆盖已存在的tar文件: ${TAR_PATH}"
        rm -f "${TAR_PATH}" "${SHA_PATH}"
    fi

    log_section "导出中..."
    log_info "输出: ${TAR_PATH}"
    log_warn "镜像较大（约750MB），导出需30秒-2分钟..."

    local start_ts end_ts
    start_ts=$(date +%s)

    docker save -o "${TAR_PATH}" "${CUSTOMER_IMAGE}"

    end_ts=$(date +%s)
    local duration=$((end_ts - start_ts))

    local tar_size
    tar_size=$(wc -c < "${TAR_PATH}")
    local tar_size_mb=$((tar_size / 1024 / 1024))

    log_success "镜像导出完成"
    log_kv "tar大小" "${tar_size_mb} MB"
    log_kv "导出耗时" "${duration}秒"

    log_section "生成SHA256校验和"
    (cd "${DIST_DIR}" && sha256sum "${TAR_FILENAME}" > "${SHA_FILENAME}")
    log_success "校验和已保存: ${SHA_FILENAME}"
    cat "${SHA_PATH}"
}

# ------------------------------------------------------------------------------
# 快速验证
# ------------------------------------------------------------------------------
verify_image() {
    log_header "端到端验证"

    log_section "清理已有测试容器"
    docker rm -f caffe-customer-verify 2>/dev/null || true

    log_section "从tar加载验证"
    local load_output
    load_output=$(docker load -i "${TAR_PATH}" 2>&1)
    echo "$load_output"
    if echo "$load_output" | grep -q "Loaded image"; then
        log_success "镜像加载成功"
    else
        log_error "镜像加载可能有问题"
        return 1
    fi

    log_section "启动验证容器"
    docker run -d --name caffe-customer-verify -p 18888:8888 "${CUSTOMER_IMAGE}"
    sleep 8

    log_section "检查服务可用性"
    local http_code
    http_code=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:18888/ 2>/dev/null || echo "000")

    if [[ "$http_code" == "200" ]] || [[ "$http_code" == "302" ]]; then
        log_success "Jupyter服务响应正常 (HTTP ${http_code})"
    else
        log_warn "Jupyter服务响应异常 (HTTP ${http_code})，可能仍在启动中"
    fi

    log_section "验证Caffe导入"
    local caffe_check
    caffe_check=$(docker exec caffe-customer-verify python3 -c "import caffe; print('Caffe version:', caffe.__version__)" 2>&1 || echo "FAILED")
    if echo "$caffe_check" | grep -q "Caffe version"; then
        log_success "Caffe库可正常导入: $caffe_check"
    else
        log_warn "Caffe导入检查: $caffe_check"
    fi

    log_section "验证Notebook文件"
    local nb_check
    nb_check=$(docker exec caffe-customer-verify ls /workspace/notebooks/*.ipynb 2>&1 || echo "NOT FOUND")
    if echo "$nb_check" | grep -q "ipynb"; then
        log_success "Notebook已自动复制到工作目录:"
        echo "$nb_check" | while read -r line; do echo "    $line"; done
    else
        log_warn "Notebook文件检查: $nb_check"
    fi

    log_section "清理验证容器"
    docker rm -f caffe-customer-verify 2>/dev/null || true
    log_success "验证容器已清理"

    log_success "端到端验证完成"
}

# ------------------------------------------------------------------------------
# 生成简易使用指南
# ------------------------------------------------------------------------------
generate_guide() {
    if [[ -f "${GUIDE_PATH}" ]]; then
        log_info "使用指南已存在，跳过生成: ${GUIDE_PATH}"
        return 0
    fi

    log_section "生成简易使用指南"

    cat > "${GUIDE_PATH}" <<'GUIDE'
# Caffe Notebook 使用指南（简易版）

---

## 📦 您收到的文件

| 文件 | 说明 |
|------|------|
| caffe-cpu-customer-notebook_YYYYMMDD.tar | Caffe 环境镜像文件（请勿解压） |
| 使用指南.txt | 本文件 |

---

## 🚀 快速开始（3步）

### 第一步：安装 Docker（仅首次需要）

如果您的电脑还没有安装 Docker，请先安装：

- Windows/Mac：下载并安装 Docker Desktop (https://www.docker.com/products/docker-desktop/)
- Linux：按官方文档安装 Docker Engine

安装完成后，请确保 Docker 正在运行。

### 第二步：加载镜像文件

1. 打开命令行（Windows 按 Win+R，输入 cmd 回车）
2. 使用 cd 命令进入存放镜像文件的文件夹
3. 执行加载命令：
   docker load -i caffe-cpu-customer-notebook_YYYYMMDD.tar
4. 等待加载完成，看到 Loaded image 字样即成功

### 第三步：启动并使用 Notebook

1. 执行启动命令：
   docker run -d --name caffe-notebook -p 8888:8888 caffe-cpu:customer-notebook
2. 等待约15秒
3. 浏览器打开：http://localhost:8888
4. Token（令牌）输入：__TOKEN__
5. 进入后点击 notebooks/ 文件夹，点击 .ipynb 文件开始使用

🎉 恭喜！您已成功启动 Caffe Notebook 环境！

---

## ⚡ 常用操作

停止使用：  docker stop caffe-notebook
再次使用：  docker start caffe-notebook
完全重置：  docker rm -f caffe-notebook  （会丢失修改，请先下载备份）

---

## ❓ 常见问题

Q: 浏览器打不开 http://localhost:8888 ？
A: 确认Docker正在运行；确认已执行启动命令；等待15秒；关闭代理/防火墙

Q: Token 是什么？
A: 默认Token是：__TOKEN__

Q: 提示"docker 不是内部或外部命令"？
A: Docker没有安装或没有启动，请重新安装并启动Docker Desktop

Q: 提示端口被占用？
A: 改用其他端口启动：docker run -d --name caffe-notebook -p 8889:8888 caffe-cpu:customer-notebook
   然后访问 http://localhost:8889

Q: 修改的Notebook如何保存？
A: 在Notebook中按 Ctrl+S 保存。重要：完全重置会丢失修改，请用 File → Download 下载备份。

Q: 电脑重启后还能用吗？
A: 需要：1) 启动Docker Desktop；2) 执行 docker start caffe-notebook；3) 打开浏览器

Q: tar文件可以删除吗？
A: 加载成功后可以删除（约750MB），如需在其他电脑安装请保留。

---

*本产品内置Caffe深度学习环境，所有计算均在本地运行，无需联网。*
GUIDE

    sed -i "s/__TOKEN__/${JUPYTER_TOKEN}/g" "${GUIDE_PATH}"
    sed -i "s/YYYYMMDD/${CUSTOM_DATE}/g" "${GUIDE_PATH}"

    log_success "使用指南已生成: ${GUIDE_PATH}"
}

# ------------------------------------------------------------------------------
# 打包ZIP
# ------------------------------------------------------------------------------
package_zip() {
    log_header "打包ZIP分发包"

    if [[ ! -f "${GUIDE_PATH}" ]]; then
        generate_guide
    fi

    if [[ -f "${ZIP_PATH}" ]]; then
        log_warn "覆盖已存在的ZIP文件: ${ZIP_PATH}"
        rm -f "${ZIP_PATH}"
    fi

    log_section "打包中..."

    (cd "${DIST_DIR}" && zip -j "${ZIP_PATH}" "${TAR_FILENAME}" "使用指南.txt" "${SHA_FILENAME}")

    local zip_size
    zip_size=$(wc -c < "${ZIP_PATH}")
    local zip_size_mb=$((zip_size / 1024 / 1024))

    log_success "ZIP打包完成"
    log_kv "ZIP文件" "${ZIP_FILENAME}"
    log_kv "ZIP大小" "${zip_size_mb} MB"

    log_section "ZIP内容"
    unzip -l "${ZIP_PATH}"
}

# ------------------------------------------------------------------------------
# 主流程
# ------------------------------------------------------------------------------
log_header "Caffe 客户分发包一键构建"
log_kv "脚本目录" "${SCRIPT_DIR}"
log_kv "项目目录" "${PROJECT_DIR}"
log_kv "输出目录" "${DIST_DIR}"

preflight_check

BUILD_CTX=""
if [[ "$SKIP_BUILD" != "true" ]]; then
    BUILD_CTX=$(prepare_context)
    build_customer_image "${BUILD_CTX}"
else
    log_warn "跳过镜像构建（--skip-build）"
    if ! docker image inspect "${CUSTOMER_IMAGE}" &>/dev/null; then
        log_error "镜像不存在且跳过构建: ${CUSTOMER_IMAGE}"
        exit 1
    fi
fi

if [[ "$SKIP_EXPORT" != "true" ]]; then
    export_image
else
    log_warn "跳过镜像导出（--skip-export）"
fi

if [[ "$SKIP_VERIFY" != "true" ]] && [[ "$SKIP_EXPORT" != "true" ]]; then
    verify_image || log_warn "验证过程有警告，但不影响分发包生成"
else
    log_warn "跳过端到端验证（--skip-verify）"
fi

if [[ "$SKIP_PACKAGE" != "true" ]]; then
    generate_guide
    package_zip
else
    log_warn "跳过ZIP打包（--skip-package）"
fi

log_blank
log_header "构建汇总"
log_success "客户镜像: ${CUSTOMER_IMAGE}"
if [[ -f "${TAR_PATH}" ]]; then
    log_success "镜像tar: ${TAR_PATH} ($(du -h "${TAR_PATH}" | cut -f1))"
fi
if [[ -f "${SHA_PATH}" ]]; then
    log_success "校验文件: ${SHA_PATH}"
fi
if [[ -f "${GUIDE_PATH}" ]]; then
    log_success "使用指南: ${GUIDE_PATH}"
fi
if [[ -f "${ZIP_PATH}" ]]; then
    log_success "ZIP分发包: ${ZIP_PATH} ($(du -h "${ZIP_PATH}" | cut -f1))"
fi
log_blank
log_section "分发给客户"
log_info "将ZIP文件发送给客户，客户解压后按使用指南.txt操作即可"
log_blank
