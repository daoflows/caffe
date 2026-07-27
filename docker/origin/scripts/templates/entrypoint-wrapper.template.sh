#!/bin/bash
# ==============================================================================
# Entrypoint Wrapper 模板 —— VOLUME目录文件注入模式
# ==============================================================================
# 用途：当基础镜像声明了VOLUME，无法通过Dockerfile COPY直接向VOLUME路径写入
#       预置文件时，使用此wrapper在容器启动时将预置文件复制到VOLUME工作目录。
#
# 使用方法：
#   1. 复制此模板为 entrypoint-<product>.sh
#   2. 修改下方配置区的变量（SRC_DIR / DEST_DIR / FILE_PATTERN / ORIGINAL_ENTRYPOINT）
#   3. 在 Dockerfile 中：
#        COPY your-preset-files/ /opt/<product>-assets/
#        COPY entrypoint-<product>.sh /usr/local/bin/
#        RUN chmod +x /usr/local/bin/entrypoint-<product>.sh
#        ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/entrypoint-<product>.sh"]
#        CMD []
#
# 设计原则：
#   - 幂等性：文件不存在时才复制，不覆盖用户已有文件
#   - 透明委托：最后 exec 原始entrypoint，完整保留原有启动流程
#   - 容错性：chown等非关键操作失败不阻止启动
#   - 通用性：通配符遍历支持任意数量预置文件
# ==============================================================================

set -e

# ==============================================================================
# 配置区（根据实际产品修改）
# ==============================================================================

# 预置文件存放路径（非VOLUME路径，Dockerfile COPY的目标位置）
SRC_DIR="/opt/__PRODUCT__-assets"

# 应用工作目录（VOLUME路径，运行时可见的目录）
DEST_DIR="/workspace/__WORKDIR__"

# 要复制的文件通配符（如 *.ipynb, *.py, *.txt 等）
FILE_PATTERN="*"

# 文件权限：目标文件的所有者（运行应用的用户，通常是基础镜像中定义的用户）
OWNER_USER="__APP_USER__"
OWNER_GROUP="__APP_USER__"

# 原始entrypoint路径（基础镜像的启动脚本，wrapper最后委托给它）
ORIGINAL_ENTRYPOINT="/usr/local/bin/__ORIGINAL_ENTRYPOINT__.sh"

# 日志前缀（方便在docker logs中识别wrapper输出）
LOG_PREFIX="[__PRODUCT__-wrapper]"

# ==============================================================================
# 核心逻辑（一般不需要修改）
# ==============================================================================

echo "${LOG_PREFIX} Preparing preset files..."

# 确保目标目录存在
mkdir -p "${DEST_DIR}"

# 遍历预置文件，幂等复制
COPIED_COUNT=0
SKIPPED_COUNT=0

for f in "${SRC_DIR}"/${FILE_PATTERN}; do
    if [ -f "$f" ]; then
        fname="$(basename "$f")"
        dest_path="${DEST_DIR}/${fname}"
        if [ ! -f "${dest_path}" ]; then
            cp "$f" "${dest_path}"
            echo "${LOG_PREFIX} Copied: ${fname}"
            COPIED_COUNT=$((COPIED_COUNT + 1))
        else
            echo "${LOG_PREFIX} Skipped (already exists): ${fname}"
            SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
        fi
    fi
done

echo "${LOG_PREFIX} File sync complete: ${COPIED_COUNT} copied, ${SKIPPED_COUNT} skipped"

# 设置文件权限（忽略错误，非关键步骤）
chown -R "${OWNER_USER}:${OWNER_GROUP}" "${DEST_DIR}" 2>/dev/null || true

echo "${LOG_PREFIX} Starting application services..."

# 委托给原始entrypoint（必须使用exec，确保信号正确传递）
exec "${ORIGINAL_ENTRYPOINT}" "$@"
