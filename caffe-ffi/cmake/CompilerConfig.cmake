# CompilerConfig.cmake - 公共编译配置函数
# 提供 caffe_ffi_configure_target(target VISIBILITY <PUBLIC|PRIVATE>) 函数，
# 统一设置 include 目录、编译定义、编译选项、链接库，消除主库和测试目标之间的重复配置。

function(caffe_ffi_configure_target target_name)
  cmake_parse_arguments(ARG "" "VISIBILITY" "" ${ARGN})
  if(NOT ARG_VISIBILITY)
    set(ARG_VISIBILITY PUBLIC)
  endif()

  # Include directories
  target_include_directories(${target_name} ${ARG_VISIBILITY}
    "${CAFFE_FFI_INCLUDE_DIR}"
    "${CAFFE_FFI_GEN_PROTO_DIR}"
    "${Protobuf_INCLUDE_DIRS}"
  )
  if(BLAS_INCLUDE_DIRS)
    target_include_directories(${target_name} ${ARG_VISIBILITY} "${BLAS_INCLUDE_DIRS}")
  endif()

  # Compile definitions
  target_compile_definitions(${target_name} ${ARG_VISIBILITY}
    CAFFE_FFI_VERSION="${PROJECT_VERSION}"
  )
  if(CAFFE_CPU_ONLY)
    target_compile_definitions(${target_name} ${ARG_VISIBILITY} CPU_ONLY)
  endif()
  if(CAFFE_FFI_ENABLE_DEBUG_LOG)
    target_compile_definitions(${target_name} ${ARG_VISIBILITY} CAFFE_FFI_ENABLE_DEBUG_LOG)
  endif()
  if(CAFFE_FFI_ENABLE_BACKTRACE)
    target_compile_definitions(${target_name} ${ARG_VISIBILITY} CAFFE_FFI_ENABLE_BACKTRACE)
  endif()
  if(BLAS_FOUND OR BLAS_LIBRARIES)
    target_compile_definitions(${target_name} ${ARG_VISIBILITY} CAFFE_USE_BLAS HAVE_CBLAS_H)
  endif()

  # Compile options
  if(MSVC)
    target_compile_options(${target_name} ${ARG_VISIBILITY} /W3)
  else()
    target_compile_options(${target_name} ${ARG_VISIBILITY} -Wall -Wextra -Wno-unused-parameter)
  endif()

  # Link libraries
  target_link_libraries(${target_name} ${ARG_VISIBILITY}
    protobuf::libprotobuf
    Threads::Threads
  )
  if(BLAS_LIBRARIES)
    target_link_libraries(${target_name} ${ARG_VISIBILITY} ${BLAS_LIBRARIES})
  endif()
  if(MSVC)
    target_link_libraries(${target_name} ${ARG_VISIBILITY} DbgHelp.lib)
  endif()
endfunction()
