cmake_minimum_required(VERSION 3.26)
project(caffe_ffi VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

option(CAFFE_CPU_ONLY "Build Caffe-FFI with CPU only support" ON)
option(CAFFE_FFI_ENABLE_DEBUG_LOG "Enable detailed debug logging for memory/container operations" ON)

if(POLICY CMP0144)
  cmake_policy(SET CMP0144 NEW)
endif()
if(POLICY CMP0167)
  cmake_policy(SET CMP0167 NEW)
endif()

set(TVM_FFI_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../../tvm-ffi")
if(EXISTS "${TVM_FFI_DIR}/CMakeLists.txt")
  set(TVM_FFI_USE_LIBBACKTRACE OFF CACHE BOOL "Disable libbacktrace" FORCE)
  set(TVM_FFI_BACKTRACE_ON_SEGFAULT OFF CACHE BOOL "Disable segfault backtrace" FORCE)
  add_subdirectory("${TVM_FFI_DIR}" tvm-ffi EXCLUDE_FROM_ALL)
else()
  find_package(tvm_ffi CONFIG REQUIRED)
endif()

set(protobuf_MODULE_COMPATIBLE ON CACHE BOOL "Use module-compatible protobuf variables" FORCE)
find_package(Protobuf CONFIG REQUIRED)
if(Protobuf_VERSION VERSION_LESS "7.0.0")
  message(FATAL_ERROR "Protobuf >= 7.0.0 is required, found ${Protobuf_VERSION}")
endif()
message(STATUS "Using Protobuf version: ${Protobuf_VERSION}")
find_package(Threads REQUIRED)

set(BLAS_FOUND OFF)
set(BLAS_LIBRARIES "")
set(BLAS_INCLUDE_DIRS "")

find_package(Python COMPONENTS Interpreter QUIET)

set(CAFFE_FFI_INCLUDE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/include")
set(CAFFE_FFI_SRC_DIR "${CMAKE_CURRENT_SOURCE_DIR}/src")
set(CAFFE_FFI_PROTO_DIR "${CMAKE_CURRENT_SOURCE_DIR}/proto")
set(CAFFE_FFI_GEN_PROTO_DIR "${CMAKE_BINARY_DIR}/caffe_proto_gen")
file(MAKE_DIRECTORY "${CAFFE_FFI_GEN_PROTO_DIR}")

set(CAFFE_FFI_PROTO_FILE "${CAFFE_FFI_PROTO_DIR}/caffe/proto/caffe.proto")
set(CAFFE_FFI_PROTO_HDR "${CAFFE_FFI_GEN_PROTO_DIR}/caffe/proto/caffe.pb.h")
set(CAFFE_FFI_PROTO_SRC "${CAFFE_FFI_GEN_PROTO_DIR}/caffe/proto/caffe.pb.cc")
set(CAFFE_FFI_PROTO_PY "${CAFFE_FFI_GEN_PROTO_DIR}/caffe/proto/caffe_pb2.py")

if(EXISTS "${CAFFE_FFI_PROTO_FILE}")
  find_program(PROTOBUF_PROTOC protoc REQUIRED)
  file(MAKE_DIRECTORY "${CAFFE_FFI_GEN_PROTO_DIR}/caffe/proto")
  add_custom_command(
    OUTPUT "${CAFFE_FFI_PROTO_SRC}" "${CAFFE_FFI_PROTO_HDR}" "${CAFFE_FFI_PROTO_PY}"
    COMMAND ${PROTOBUF_PROTOC}
      --proto_path=${CAFFE_FFI_PROTO_DIR}
      --cpp_out=${CAFFE_FFI_GEN_PROTO_DIR}
      --python_out=${CAFFE_FFI_GEN_PROTO_DIR}
      caffe/proto/caffe.proto
    DEPENDS "${CAFFE_FFI_PROTO_FILE}"
    COMMENT "Generating caffe.pb.cc/caffe.pb.h/caffe_pb2.py from caffe.proto"
  )
  set(CAFFE_FFI_PROTO_SRCS "${CAFFE_FFI_PROTO_SRC}")
  set(CAFFE_FFI_PROTO_HDRS "${CAFFE_FFI_PROTO_HDR}")
else()
  message(STATUS "caffe.proto not found at ${CAFFE_FFI_PROTO_FILE} - proto generation will be added in Task 2")
  set(CAFFE_FFI_PROTO_SRCS "")
  set(CAFFE_FFI_PROTO_HDRS "")
endif()

file(GLOB CAFFE_FFI_CORE_SRCS
  "${CMAKE_CURRENT_SOURCE_DIR}/src/caffe_ffi/*.cc"
  "${CMAKE_CURRENT_SOURCE_DIR}/src/caffe_ffi/*.cpp"
)
file(GLOB CAFFE_FFI_LAYER_SRCS
  "${CMAKE_CURRENT_SOURCE_DIR}/src/caffe_ffi/layers/*.cc"
  "${CMAKE_CURRENT_SOURCE_DIR}/src/caffe_ffi/layers/*.cpp"
)
list(APPEND CAFFE_FFI_CORE_SRCS ${CAFFE_FFI_LAYER_SRCS})

add_library(_caffe_ffi SHARED
  ${CAFFE_FFI_CORE_SRCS}
  ${CAFFE_FFI_PROTO_SRCS}
)

set_target_properties(_caffe_ffi PROPERTIES
  PREFIX ""
  OUTPUT_NAME "_caffe_ffi"
)

if(DEFINED SKBUILD_PROJECT_NAME)
  set_target_properties(_caffe_ffi PROPERTIES
    LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/python/caffe_ffi"
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/python/caffe_ffi"
  )
  if(MSVC)
    foreach(config_type Release RELEASE Debug DEBUG RelWithDebInfo)
      set_target_properties(_caffe_ffi PROPERTIES
        RUNTIME_OUTPUT_DIRECTORY_${config_type} "${CMAKE_BINARY_DIR}/python/caffe_ffi"
        LIBRARY_OUTPUT_DIRECTORY_${config_type} "${CMAKE_BINARY_DIR}/python/caffe_ffi"
        ARCHIVE_OUTPUT_DIRECTORY_${config_type} "${CMAKE_BINARY_DIR}/python/caffe_ffi"
      )
    endforeach()
  endif()
endif()

target_include_directories(_caffe_ffi PUBLIC
  "${CAFFE_FFI_INCLUDE_DIR}"
  "${CAFFE_FFI_GEN_PROTO_DIR}"
  "${Protobuf_INCLUDE_DIRS}"
)
if(BLAS_INCLUDE_DIRS)
  target_include_directories(_caffe_ffi PUBLIC "${BLAS_INCLUDE_DIRS}")
endif()

target_compile_definitions(_caffe_ffi PUBLIC
  CPU_ONLY
  CAFFE_FFI_VERSION="${PROJECT_VERSION}"
)
if(CAFFE_FFI_ENABLE_DEBUG_LOG)
  target_compile_definitions(_caffe_ffi PUBLIC CAFFE_FFI_ENABLE_DEBUG_LOG)
endif()
if(BLAS_FOUND OR BLAS_LIBRARIES)
  target_compile_definitions(_caffe_ffi PUBLIC CAFFE_USE_BLAS)
endif()

if(MSVC)
  target_compile_definitions(_caffe_ffi PUBLIC
    WIN32_LEAN_AND_MEAN
    _CRT_SECURE_NO_WARNINGS
    _SCL_SECURE_NO_WARNINGS
    NOMINMAX
  )
  target_compile_options(_caffe_ffi PRIVATE /W3 /bigobj /Zi)
else()
  target_compile_options(_caffe_ffi PRIVATE -Wall -Wextra -Wno-unused-parameter)
endif()

target_link_libraries(_caffe_ffi PUBLIC
  tvm_ffi::header
  tvm_ffi::shared
  protobuf::libprotobuf
  Threads::Threads
)
if(BLAS_LIBRARIES)
  target_link_libraries(_caffe_ffi PUBLIC ${BLAS_LIBRARIES})
endif()
if(MSVC)
  target_link_libraries(_caffe_ffi PUBLIC DbgHelp.lib)
endif()

if(MSVC)
  set_target_properties(_caffe_ffi PROPERTIES
    WINDOWS_EXPORT_ALL_SYMBOLS TRUE
  )
endif()

if(MSVC)
  function(caffe_ffi_copy_dll_if_exists target_name dll_path)
    if(dll_path AND EXISTS "${dll_path}")
      add_custom_command(TARGET ${target_name} POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_if_different
          "${dll_path}"
          "$<TARGET_FILE_DIR:${target_name}>"
        COMMENT "Copying ${dll_path} to output directory"
      )
    endif()
  endfunction()

  get_target_property(_tvm_ffi_shared_LOC tvm_ffi_shared IMPORTED_LOCATION_RELEASE)
  if(NOT _tvm_ffi_shared_LOC)
    get_target_property(_tvm_ffi_shared_LOC tvm_ffi_shared IMPORTED_LOCATION)
  endif()
  if(NOT _tvm_ffi_shared_LOC AND TARGET tvm_ffi_shared)
    set(_tvm_ffi_shared_LOC "$<TARGET_FILE:tvm_ffi_shared>")
  endif()
  if(_tvm_ffi_shared_LOC)
    add_custom_command(TARGET _caffe_ffi POST_BUILD
      COMMAND ${CMAKE_COMMAND} -E copy_if_different
        "${_tvm_ffi_shared_LOC}"
        "$<TARGET_FILE_DIR:_caffe_ffi>"
      COMMENT "Copying tvm_ffi shared library to output directory"
    )
  endif()

  set(_protobuf_dll_dirs "${Protobuf_DIR}/../../../bin" "${Protobuf_DIR}/../../bin")
  foreach(_dll_dir ${_protobuf_dll_dirs})
    file(GLOB _protobuf_dlls "${_dll_dir}/libprotobuf*.dll" "${_dll_dir}/libprotoc*.dll")
    foreach(_dll ${_protobuf_dlls})
      if(EXISTS "${_dll}")
        add_custom_command(TARGET _caffe_ffi POST_BUILD
          COMMAND ${CMAKE_COMMAND} -E copy_if_different
            "${_dll}"
            "$<TARGET_FILE_DIR:_caffe_ffi>"
          COMMENT "Copying ${_dll} to output directory"
        )
      endif()
    endforeach()
  endforeach()

  get_filename_component(_absl_dir "${Protobuf_DIR}" DIRECTORY)
  set(_absl_dll_dirs "${_absl_dir}/bin" "${_absl_dir}/../bin")
  foreach(_dll_dir ${_absl_dll_dirs})
    file(GLOB _absl_dlls "${_dll_dir}/absl_*.dll")
    foreach(_dll ${_absl_dlls})
      if(EXISTS "${_dll}")
        add_custom_command(TARGET _caffe_ffi POST_BUILD
          COMMAND ${CMAKE_COMMAND} -E copy_if_different
            "${_dll}"
            "$<TARGET_FILE_DIR:_caffe_ffi>"
          COMMENT "Copying ${_dll} to output directory"
        )
      endif()
    endforeach()
  endforeach()

  set(_utf8_dirs "${_absl_dir}/bin" "${_absl_dir}/../bin")
  foreach(_dll_dir ${_utf8_dirs})
    file(GLOB _utf8_dlls "${_dll_dir}/utf8_range*.dll")
    foreach(_dll ${_utf8_dlls})
      if(EXISTS "${_dll}")
        add_custom_command(TARGET _caffe_ffi POST_BUILD
          COMMAND ${CMAKE_COMMAND} -E copy_if_different
            "${_dll}"
            "$<TARGET_FILE_DIR:_caffe_ffi>"
          COMMENT "Copying ${_dll} to output directory"
        )
      endif()
    endforeach()
  endforeach()
endif()

enable_testing()

install(TARGETS _caffe_ffi
  LIBRARY DESTINATION caffe_ffi
  RUNTIME DESTINATION caffe_ffi
)

if(EXISTS "${CAFFE_FFI_PROTO_PY}")
  install(FILES "${CAFFE_FFI_PROTO_PY}" DESTINATION caffe_ffi/proto)
endif()
