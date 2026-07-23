cmake_minimum_required(VERSION 3.15)
project(proto_python_generator)

# 查找 Protobuf 包
find_package(Protobuf REQUIRED)

# 定义 .proto 文件
set(PROTO_FILES
  ${CMAKE_CURRENT_SOURCE_DIR}/python/protos/caffe.proto
)

# 配置 Python 代码输出目录
set(PYTHON_OUTPUT_DIR ${CMAKE_CURRENT_SOURCE_DIR}/python)
file(MAKE_DIRECTORY ${PYTHON_OUTPUT_DIR})

# 使用 CMake 内置函数生成 Python 代码
protobuf_generate_python(PROTO_PY_SRCS PROTO_FILES
  OUT_DIR ${PYTHON_OUTPUT_DIR}
)

# 创建构建目标
add_custom_target(proto_python ALL
  DEPENDS ${PROTO_PY_SRCS}
)

# 调试信息
message(STATUS "Protobuf Python 代码输出目录: ${PYTHON_OUTPUT_DIR}")
message(STATUS "protoc 路径: ${Protobuf_PROTOC_EXECUTABLE}")