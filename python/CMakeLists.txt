cmake_minimum_required(VERSION 3.26)
project(caffe_python LANGUAGES CXX C)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

option(CAFFE_CPU_ONLY "Build Caffe with CPU only support" ON)
if(NOT CAFFE_VERSION)
  set(CAFFE_VERSION "1.0.0-slim")
endif()

set(TVM_FFI_USE_LIBBACKTRACE OFF CACHE BOOL "Disable libbacktrace for Caffe slim build" FORCE)
set(TVM_FFI_BACKTRACE_ON_SEGFAULT OFF CACHE BOOL "Disable segfault backtrace" FORCE)

if(POLICY CMP0144)
  cmake_policy(SET CMP0144 NEW)
endif()
if(POLICY CMP0167)
  cmake_policy(SET CMP0167 NEW)
endif()

set(TVM_FFI_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../../tvm-ffi")
if(NOT EXISTS "${TVM_FFI_DIR}/CMakeLists.txt")
  message(FATAL_ERROR "tvm-ffi not found at ${TVM_FFI_DIR}")
endif()
add_subdirectory("${TVM_FFI_DIR}" tvm-ffi EXCLUDE_FROM_ALL)

find_package(Protobuf REQUIRED)
find_package(Threads REQUIRED)
find_package(BLAS QUIET)
if(NOT BLAS_FOUND)
  find_library(BLAS_LIBRARIES NAMES openblas cblas blas PATHS /usr/lib /usr/local/lib ${CONDA_PREFIX}/lib ${CONDA_ENV_PREFIX}/lib)
  find_path(BLAS_INCLUDE_DIRS cblas.h openblas.h PATHS /usr/include /usr/include/x86_64-linux-gnu /usr/local/include ${CONDA_PREFIX}/include ${CONDA_ENV_PREFIX}/include)
endif()

set(CAFFE_INCLUDE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/include")
set(CAFFE_SRC_PARENT_DIR "${CMAKE_CURRENT_SOURCE_DIR}/src")
set(CAFFE_PROTO_DIR "${CAFFE_SRC_PARENT_DIR}/caffe/proto")
set(CAFFE_GEN_PROTO_DIR "${CMAKE_BINARY_DIR}/caffe_proto_gen")
file(MAKE_DIRECTORY "${CAFFE_GEN_PROTO_DIR}")

set(CAFFE_PROTO_FILE "${CAFFE_PROTO_DIR}/caffe.proto")
set(CAFFE_PROTO_HDR "${CAFFE_GEN_PROTO_DIR}/caffe/proto/caffe.pb.h")
set(CAFFE_PROTO_SRC "${CAFFE_GEN_PROTO_DIR}/caffe/proto/caffe.pb.cc")
if(EXISTS "${CAFFE_PROTO_FILE}")
  find_program(PROTOBUF_PROTOC protoc REQUIRED)
  add_custom_command(
    OUTPUT "${CAFFE_PROTO_SRC}" "${CAFFE_PROTO_HDR}"
    COMMAND ${PROTOBUF_PROTOC}
      --proto_path=${CAFFE_SRC_PARENT_DIR}
      --cpp_out=${CAFFE_GEN_PROTO_DIR}
      caffe/proto/caffe.proto
    DEPENDS "${CAFFE_PROTO_FILE}"
    COMMENT "Generating caffe.pb.cc/caffe.pb.h from caffe.proto"
  )
  set(CAFFE_PROTO_SRCS "${CAFFE_PROTO_SRC}")
  set(CAFFE_PROTO_HDRS "${CAFFE_PROTO_HDR}")
else()
  message(FATAL_ERROR "caffe.proto not found at ${CAFFE_PROTO_FILE}")
endif()

file(GLOB CAFFE_CORE_SRCS
  "${CMAKE_CURRENT_SOURCE_DIR}/src/caffe/*.cpp"
)
file(GLOB CAFFE_UTIL_SRCS
  "${CMAKE_CURRENT_SOURCE_DIR}/src/caffe/util/*.cpp"
)
file(GLOB CAFFE_LAYER_SRCS
  "${CMAKE_CURRENT_SOURCE_DIR}/src/caffe/layers/*.cpp"
)
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

set(_caffe_ffi_src "${CMAKE_CURRENT_SOURCE_DIR}/src/caffe/_caffe.cpp")
add_library(_caffe SHARED "${_caffe_ffi_src}")
set_target_properties(_caffe PROPERTIES
  PREFIX ""
  OUTPUT_NAME "_caffe"
  LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/python/caffe"
  RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/python/caffe"
)
if(MSVC)
  foreach(config_type Release RELEASE Debug DEBUG RelWithDebInfo)
    set_target_properties(_caffe PROPERTIES
      RUNTIME_OUTPUT_DIRECTORY_${config_type} "${CMAKE_BINARY_DIR}/python/caffe"
      LIBRARY_OUTPUT_DIRECTORY_${config_type} "${CMAKE_BINARY_DIR}/python/caffe"
      ARCHIVE_OUTPUT_DIRECTORY_${config_type} "${CMAKE_BINARY_DIR}/python/caffe"
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

enable_testing()

set(CAFFE_TEST_SRC "${CMAKE_CURRENT_SOURCE_DIR}/tests/test_caffe_slim.cpp")
if(EXISTS "${CAFFE_TEST_SRC}")
  add_executable(test_caffe_slim "${CAFFE_TEST_SRC}")
  target_include_directories(test_caffe_slim PRIVATE
    "${CAFFE_INCLUDE_DIR}"
    "${CAFFE_GEN_PROTO_DIR}"
  )
  if(MSVC)
    target_link_libraries(test_caffe_slim PRIVATE
      -WHOLEARCHIVE:$<TARGET_FILE:caffe_core>
      tvm_ffi::shared
    )
  else()
    target_link_libraries(test_caffe_slim PRIVATE
      -Wl,--whole-archive caffe_core -Wl,--no-whole-archive
      tvm_ffi::shared
    )
  endif()
  set_target_properties(test_caffe_slim PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/tests"
  )
  add_test(NAME caffe_slim_unit_tests
    COMMAND test_caffe_slim "${CMAKE_CURRENT_SOURCE_DIR}/tests"
    WORKING_DIRECTORY "${CMAKE_BINARY_DIR}/tests"
  )
endif()

install(TARGETS _caffe
  LIBRARY DESTINATION python/caffe
  RUNTIME DESTINATION python/caffe
)
