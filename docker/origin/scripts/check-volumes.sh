#!/usr/bin/env bash
# ==============================================================================
# Docker VOLUME 前置检查脚本
# 功能：检查基础镜像中的VOLUME声明，判断是否影响分发包构建方案
# 用法：./check-volumes.sh <基础镜像名> [目标写入路径...]
# 原理：Docker commit 不会保存VOLUME挂载点内的文件变更，
#       若需向VOLUME路径预置文件，必须使用 Dockerfile + entrypoint wrapper 方案
# ==============================================================================

set -euo pipefail

log_info()    { echo -e "\033[34m[INFO]\033[0m $*"; }
log_success() { echo -e "\033[32m[OK]\033[0m $*"; }
log_warn()    { echo -e "\033[33m[WARN]\033[0m $*"; }
log_error()   { echo -e "\033[31m[ERROR]\033[0m $*" >&2; }
log_header()  { echo -e "\n\033[1;36m=== $* ===\033[0m"; }

if [[ $# -lt 1 ]]; then
    cat <<EOF
用法: $(basename "$0") <IMAGE> [TARGET_PATH...]

检查Docker镜像的VOLUME声明，并判断指定目标路径是否在VOLUME内。

参数:
  IMAGE         要检查的Docker镜像名（如 caffe-cpu:jupyter）
  TARGET_PATH   可选，一个或多个计划写入文件的容器内路径

输出:
  - 列出镜像中所有VOLUME声明
  - 判断每个TARGET_PATH是否受VOLUME影响
  - 给出构建方案建议（docker commit 还是 Dockerfile + entrypoint wrapper）

示例:
  $(basename "$0") caffe-cpu:jupyter
  $(basename "$0") caffe-cpu:jupyter /workspace/notebooks /app/data
EOF
    exit 1
fi

IMAGE="$1"
shift
TARGET_PATHS=("$@")

log_header "Docker VOLUME 前置检查"
log_info "检查镜像: ${IMAGE}"

if ! docker image inspect "${IMAGE}" &>/dev/null; then
    log_error "镜像不存在: ${IMAGE}"
    exit 1
fi

VOLUMES_JSON=$(docker inspect "$IMAGE" --format='{{json .Config.Volumes}}' 2>/dev/null || echo "{}")

if [[ "$VOLUMES_JSON" == "{}" ]] || [[ -z "$VOLUMES_JSON" ]] || [[ "$VOLUMES_JSON" == "null" ]]; then
    log_success "✓ 该镜像无 VOLUME 声明"
    echo ""
    echo "方案建议："
    echo "  ✓ 可以直接使用 docker commit 保存文件变更"
    echo "  ✓ 可以直接用 Dockerfile COPY 写入任意路径"
    exit 0
fi

# 解析VOLUME列表
VOLUME_LIST=()
while IFS= read -r vol; do
    [[ -n "$vol" ]] && VOLUME_LIST+=("$vol")
done < <(echo "$VOLUMES_JSON" | python3 -c "
import sys, json
try:
    vols = json.load(sys.stdin)
    for v in sorted(vols.keys()):
        print(v)
except Exception as e:
    print(f'_PARSE_ERROR: {e}', file=sys.stderr)
" 2>/dev/null || echo "$VOLUMES_JSON" | tr -d '{}"' | tr ',' '\n' | sed 's/^ *//;s/ *$//')

log_warn "⚠ 镜像声明了以下 VOLUME:"
for v in "${VOLUME_LIST[@]}"; do
    echo "    • $v"
done
echo ""

CONFLICT_FOUND=false

if [[ ${#TARGET_PATHS[@]} -gt 0 ]]; then
    log_header "目标路径冲突检测"
    for target in "${TARGET_PATHS[@]}"; do
        conflict=false
        conflict_vol=""
        for v in "${VOLUME_LIST[@]}"; do
            if [[ "$target" == "$v" ]] || [[ "$target" == "$v"/* ]] || [[ "$v" == "$target"/* ]]; then
                conflict=true
                conflict_vol="$v"
                break
            fi
        done
        if $conflict; then
            log_error "✗ ${target} → 在VOLUME ${conflict_vol} 内，docker commit 无法保存！"
            CONFLICT_FOUND=true
        else
            log_success "✓ ${target} → 不在VOLUME内，可正常写入"
        fi
    done
    echo ""
fi

log_header "方案建议"
if $CONFLICT_FOUND; then
    echo "  ❌ docker commit 方案不可用！"
    echo ""
    echo "  ✅ 推荐方案：Dockerfile + entrypoint wrapper 模式"
    echo ""
    echo "  步骤："
    echo "  1. 将预置文件 COPY 到非VOLUME路径（如 /opt/<product>-assets/）"
    echo "  2. 创建 entrypoint wrapper 脚本，容器启动时："
    echo "     - 将文件从非VOLUME路径复制到VOLUME工作目录"
    echo "     - 使用幂等检查（[ ! -f ... ]）避免覆盖用户文件"
    echo "     - 最后 exec 原始 entrypoint"
    echo "  3. Dockerfile 中 ENTRYPOINT 指向 wrapper 脚本"
    echo ""
    echo "  参考模板：scripts/templates/entrypoint-wrapper.template.sh"
else
    echo "  ✓ 目标路径均不在VOLUME内"
    echo "  ✓ 可使用 docker commit 或 Dockerfile COPY 方案"
    if [[ ${#TARGET_PATHS[@]} -eq 0 ]]; then
        echo ""
        echo "  提示：如需检查特定路径，请将路径作为参数传入"
    fi
fi
echo ""
