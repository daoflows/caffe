# Dependencies.cmake - 第三方依赖查找与配置
# TVM FFI、Protobuf、Threads 依赖在此查找；BLAS 检测委托给 DetectBLAS.cmake

set(TVM_FFI_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../../tvm-ffi")
if(EXISTS "${TVM_FFI_DIR}/CMakeLists.txt")
  set(TVM_FFI_USE_LIBBACKTRACE OFF CACHE BOOL "Disable libbacktrace" FORCE)
  set(TVM_FFI_BACKTRACE_ON_SEGFAULT OFF CACHE BOOL "Disable segfault backtrace" FORCE)
  add_subdirectory("${TVM_FFI_DIR}" tvm-ffi EXCLUDE_FROM_ALL)
  if(NOT TARGET tvm_ffi::shared)
    add_library(tvm_ffi::shared ALIAS tvm_ffi_shared)
  endif()
else()
  find_package(Python COMPONENTS Interpreter REQUIRED)
  execute_process(
    COMMAND "${Python_EXECUTABLE}" -m tvm_ffi.config --cmakedir
    OUTPUT_STRIP_TRAILING_WHITESPACE
    OUTPUT_VARIABLE tvm_ffi_ROOT
  )
  find_package(tvm_ffi CONFIG REQUIRED)
endif()

set(protobuf_MODULE_COMPATIBLE ON CACHE BOOL "Use module-compatible protobuf variables" FORCE)
find_package(Protobuf CONFIG REQUIRED)
if(Protobuf_VERSION VERSION_LESS "7.0.0")
  message(FATAL_ERROR "Protobuf >= 7.0.0 is required, found ${Protobuf_VERSION}")
endif()
message(STATUS "Using Protobuf version: ${Protobuf_VERSION}")
find_package(Threads REQUIRED)

include(DetectBLAS)

find_package(Python COMPONENTS Interpreter QUIET)
