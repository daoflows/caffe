# ==============================================================================
# PyCaffe 独立 Docker 镜像 CMake 构建入口（仅 caffe-slim/ + tvm-ffi/）
# ==============================================================================
# 构建上下文: vendor/（caffe 的父目录，以便同时访问 caffe/caffe-slim/ 和 tvm-ffi/）
#
# 目标:
#   all              - 一键构建完整 runtime 镜像并验证
#   clean            - 清理构建产物
#
# 用法:
#   cd vendor && cmake -B build -S caffe/docker/standalone/pycaffe && cmake --build build --target all
#   cd vendor && cmake --build build --target clean
# ==============================================================================

cmake_minimum_required(VERSION 3.16)
project(standalone-pycaffe NONE)

# Docker 镜像标签
set(STANDALONE_PYCAFFE_IMAGE "caffe-cpu:standalone-pycaffe")

# Dockerfile 路径（相对于构建上下文 vendor/）
set(DOCKERFILE "caffe/docker/standalone/pycaffe/Dockerfile")

# 构建上下文（vendor/ 目录，可同时访问 caffe/caffe-slim/ 和 tvm-ffi/）
set(BUILD_CONTEXT ".")

# ==============================================================================
# 默认目标：完整构建 runtime 镜像并验证
# ==============================================================================
add_custom_target(all
    COMMAND ${CMAKE_COMMAND} -E echo "=============================================="
    COMMAND ${CMAKE_COMMAND} -E echo "  构建 ${STANDALONE_PYCAFFE_IMAGE} 镜像..."
    COMMAND ${CMAKE_COMMAND} -E echo "  Dockerfile: ${DOCKERFILE}"
    COMMAND ${CMAKE_COMMAND} -E echo "  Build context: vendor/"
    COMMAND ${CMAKE_COMMAND} -E echo "=============================================="
    COMMAND docker build
        -t ${STANDALONE_PYCAFFE_IMAGE}
        --target runtime
        -f ${DOCKERFILE}
        ${BUILD_CONTEXT}
    COMMAND ${CMAKE_COMMAND} -E echo ""
    COMMAND ${CMAKE_COMMAND} -E echo "  ${STANDALONE_PYCAFFE_IMAGE} 构建完成"
    COMMAND ${CMAKE_COMMAND} -E echo ""
    COMMAND ${CMAKE_COMMAND} -E echo "  验证镜像..."
    COMMAND docker run --rm ${STANDALONE_PYCAFFE_IMAGE} verify-pycaffe.sh
    COMMAND ${CMAKE_COMMAND} -E echo ""
    COMMAND ${CMAKE_COMMAND} -E echo "=============================================="
    COMMAND ${CMAKE_COMMAND} -E echo "  PyCaffe 独立镜像构建完成！"
    COMMAND ${CMAKE_COMMAND} -E echo "  ${STANDALONE_PYCAFFE_IMAGE}"
    COMMAND ${CMAKE_COMMAND} -E echo "=============================================="
    COMMENT "Building PyCaffe standalone Docker image"
)

# ==============================================================================
# 清理
# ==============================================================================
add_custom_target(clean
    COMMAND ${CMAKE_COMMAND} -E echo "清理构建产物..."
    COMMAND docker rmi ${STANDALONE_PYCAFFE_IMAGE} 2>/dev/null || true
    COMMAND ${CMAKE_COMMAND} -E echo "清理完成"
    COMMENT "Cleaning standalone PyCaffe Docker image"
)