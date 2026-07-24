# pycaffe CMakeLists.txt (tvm-ffi slim version)
#
# Legacy boost::python version preserved as CMakeLists.txt.legacy for caffex builds.
# This version builds the tvm-ffi slimmed _caffe.so without boost/glog/gflags dependencies.
#
# Build with scikit-build-core:
#   pip install scikit-build-core ninja build
#   python -m build --wheel
#
# Or standalone CMake build:
#   mkdir build && cd build
#   cmake .. -DCMAKE_BUILD_TYPE=Release
#   cmake --build . -j

cmake_minimum_required(VERSION 3.18)
project(pycaffe VERSION 1.0.0-slim LANGUAGES CXX C)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

if(NOT CAFFE_VERSION)
  set(CAFFE_VERSION "1.0.0-slim")
endif()

set(TVM_FFI_USE_LIBBACKTRACE OFF CACHE BOOL "Disable libbacktrace" FORCE)
set(TVM_FFI_BACKTRACE_ON_SEGFAULT OFF CACHE BOOL "Disable segfault backtrace" FORCE)

if(POLICY CMP0144)
  cmake_policy(SET CMP0144 NEW)
endif()
if(POLICY CMP0167)
  cmake_policy(SET CMP0167 NEW)
endif()

# tvm-ffi path (relative to pycaffe/ directory)
set(TVM_FFI_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../../../tvm-ffi")
if(NOT EXISTS "${TVM_FFI_DIR}/CMakeLists.txt")
  message(FATAL_ERROR "tvm-ffi not found at ${TVM_FFI_DIR}")
endif()
add_subdirectory("${TVM_FFI_DIR}" tvm-ffi EXCLUDE_FROM_ALL)

find_package(Protobuf REQUIRED)
find_package(Threads REQUIRED)
find_package(BLAS QUIET)
if(NOT BLAS_FOUND)
  find_library(BLAS_LIBRARIES NAMES openblas cblas blas
    PATHS /usr/lib /usr/local/lib ${CONDA_PREFIX}/lib ${CONDA_ENV_PREFIX}/lib)
  find_path(BLAS_INCLUDE_DIRS cblas.h openblas.h
    PATHS /usr/include /usr/include/x86_64-linux-gnu /usr/local/include
          ${CONDA_PREFIX}/include ${CONDA_ENV_PREFIX}/include)
endif()

# Caffe source paths (relative to pycaffe/ -> python/ is parent)
set(CAFFE_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/..")
set(CAFFE_INCLUDE_DIR "${CAFFE_ROOT}/include")
set(CAFFE_SRC_DIR "${CAFFE_ROOT}/src")
set(CAFFE_PROTO_DIR "${CAFFE_SRC_DIR}/caffe/proto")
set(CAFFE_GEN_PROTO_DIR "${CMAKE_BINARY_DIR}/caffe_proto_gen")
file(MAKE_DIRECTORY "${CAFFE_GEN_PROTO_DIR}")

# Protobuf generation
set(CAFFE_PROTO_FILE "${CAFFE_PROTO_DIR}/caffe.proto")
set(CAFFE_PROTO_HDR "${CAFFE_GEN_PROTO_DIR}/caffe/proto/caffe.pb.h")
set(CAFFE_PROTO_SRC "${CAFFE_GEN_PROTO_DIR}/caffe/proto/caffe.pb.cc")
if(EXISTS "${CAFFE_PROTO_FILE}")
  find_program(PROTOBUF_PROTOC protoc REQUIRED)
  add_custom_command(
    OUTPUT "${CAFFE_PROTO_SRC}" "${CAFFE_PROTO_HDR}"
    COMMAND ${PROTOBUF_PROTOC}
      --proto_path=${CAFFE_SRC_DIR}
      --cpp_out=${CAFFE_GEN_PROTO_DIR}
      caffe/proto/caffe.proto
    DEPENDS "${CAFFE_PROTO_FILE}"
    COMMENT "Generating caffe.pb.cc/caffe.pb.h from caffe.proto"
  )
  set(CAFFE_PROTO_SRCS "${CAFFE_PROTO_SRC}")
else()
  message(FATAL_ERROR "caffe.proto not found at ${CAFFE_PROTO_FILE}")
endif()

# Collect caffe_core sources (excluding _caffe.cpp)
file(GLOB CAFFE_CORE_SRCS "${CAFFE_SRC_DIR}/caffe/*.cpp")
file(GLOB CAFFE_UTIL_SRCS "${CAFFE_SRC_DIR}/caffe/util/*.cpp")
file(GLOB CAFFE_LAYER_SRCS "${CAFFE_SRC_DIR}/caffe/layers/*.cpp")
list(APPEND CAFFE_CORE_SRCS ${CAFFE_UTIL_SRCS} ${CAFFE_LAYER_SRCS})
list(FILTER CAFFE_CORE_SRCS EXCLUDE REGEX "_caffe\\.cpp$")

add_library(caffe_core STATIC
  ${CAFFE_CORE_SRCS}
  ${CAFFE_PROTO_SRCS}
)

target_include_directories(caffe_core PUBLIC
  "${CAFFE_INCLUDE_DIR}"
  "${CAFFE_GEN_PROTO_DIR}"
  "${Protobuf_INCLUDE_DIRS}"
)
if(BLAS_INCLUDE_DIRS)
  target_include_directories(caffe_core PUBLIC "${BLAS_INCLUDE_DIRS}")
endif()

target_compile_definitions(caffe_core PUBLIC
  CPU_ONLY
  CAFFE_VERSION="${CAFFE_VERSION}"
)

if(MSVC)
  target_compile_definitions(caffe_core PUBLIC
    WIN32_LEAN_AND_MEAN
    _CRT_SECURE_NO_WARNINGS
    _SCL_SECURE_NO_WARNINGS
    NOMINMAX
  )
  target_compile_options(caffe_core PRIVATE /W3 /bigobj /Zi)
else()
  target_compile_options(caffe_core PRIVATE -Wall -Wextra -Wno-unused-parameter)
endif()

target_link_libraries(caffe_core PUBLIC
  tvm_ffi::header
  ${Protobuf_LIBRARIES}
  Threads::Threads
)
if(BLAS_LIBRARIES)
  target_link_libraries(caffe_core PUBLIC ${BLAS_LIBRARIES})
endif()
if(MSVC)
  target_link_libraries(caffe_core PUBLIC DbgHelp.lib)
endif()

# Build _caffe shared library from local _caffe.cpp (pycaffe copy)
set(_caffe_ffi_src "${CMAKE_CURRENT_SOURCE_DIR}/python/pycaffe/_caffe.cpp")
if(NOT EXISTS "${_caffe_ffi_src}")
  # Fallback to src/caffe/_caffe.cpp if local copy not found
  set(_caffe_ffi_src "${CAFFE_SRC_DIR}/caffe/_caffe.cpp")
endif()

add_library(_caffe SHARED "${_caffe_ffi_src}")
set_target_properties(_caffe PROPERTIES
  PREFIX ""
  OUTPUT_NAME "_caffe"
  LIBRARY_OUTPUT_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/python/pycaffe"
  RUNTIME_OUTPUT_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/python/pycaffe"
)
if(MSVC)
  foreach(config_type Release RELEASE Debug DEBUG RelWithDebInfo)
    set_target_properties(_caffe PROPERTIES
      RUNTIME_OUTPUT_DIRECTORY_${config_type} "${CMAKE_CURRENT_SOURCE_DIR}/python/pycaffe"
      LIBRARY_OUTPUT_DIRECTORY_${config_type} "${CMAKE_CURRENT_SOURCE_DIR}/python/pycaffe"
      ARCHIVE_OUTPUT_DIRECTORY_${config_type} "${CMAKE_CURRENT_SOURCE_DIR}/python/pycaffe"
    )
  endforeach()
endif()

target_include_directories(_caffe PRIVATE
  "${CAFFE_INCLUDE_DIR}"
  "${CAFFE_GEN_PROTO_DIR}"
)

if(MSVC)
  target_link_libraries(_caffe PRIVATE
    -WHOLEARCHIVE:$<TARGET_FILE:caffe_core>
    tvm_ffi::shared
  )
else()
  target_link_libraries(_caffe PRIVATE
    -Wl,--whole-archive caffe_core -Wl,--no-whole-archive
    tvm_ffi::shared
  )
endif()

if(MSVC)
  set_target_properties(_caffe PROPERTIES
    WINDOWS_EXPORT_ALL_SYMBOLS TRUE
  )
endif()

# Also copy tvm_ffi shared library next to _caffe so it can be found at runtime
if(TARGET tvm_ffi::shared)
  add_custom_command(TARGET _caffe POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
      $<TARGET_FILE:tvm_ffi::shared>
      "${CMAKE_CURRENT_SOURCE_DIR}/python/pycaffe/"
    COMMENT "Copying tvm_ffi shared library to pycaffe package directory"
  )
endif()

enable_testing()

install(TARGETS _caffe
  LIBRARY DESTINATION pycaffe
  RUNTIME DESTINATION pycaffe
)
install(DIRECTORY python/pycaffe/
  DESTINATION pycaffe
  FILES_MATCHING
  PATTERN "*.py"
  PATTERN "*.cpp" EXCLUDE
  PATTERN "test" EXCLUDE
  PATTERN "proto" EXCLUDE
)
install(DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/../caffeproto/
  DESTINATION caffeproto
  FILES_MATCHING
  PATTERN "*.py"
)
