cmake_minimum_required(VERSION 3.26)
project(caffe_ffi VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

option(CAFFE_CPU_ONLY "Build Caffe-FFI with CPU only support" ON)
option(CAFFE_FFI_ENABLE_DEBUG_LOG "Enable detailed debug logging for memory/container operations" ON)
option(CAFFE_FFI_ENABLE_BACKTRACE "Enable stack backtrace support for memory leak diagnosis" ON)

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

# ── BLAS detection (OpenBLAS via conda or system) ──
set(BLAS_FOUND OFF)
set(BLAS_LIBRARIES "")
set(BLAS_INCLUDE_DIRS "")

# First try CMake's FindBLAS
find_package(BLAS QUIET)
if(BLAS_FOUND)
  message(STATUS "Found BLAS via FindBLAS: ${BLAS_LIBRARIES}")
  # FindBLAS doesn't set include dirs - locate cblas.h manually
  find_path(BLAS_INCLUDE_DIRS
    NAMES cblas.h
    PATHS
      "${CMAKE_PREFIX_PATH}/include"
      "$ENV{CONDA_PREFIX}/Library/include"
      "$ENV{CONDA_PREFIX}/include"
    PATH_SUFFIXES openblas
    NO_DEFAULT_PATH
  )
  if(NOT BLAS_INCLUDE_DIRS)
    # Fallback: derive from library path
    foreach(_blas_lib ${BLAS_LIBRARIES})
      get_filename_component(_blas_lib_dir "${_blas_lib}" DIRECTORY)
      get_filename_component(_blas_root "${_blas_lib_dir}" DIRECTORY)
      if(EXISTS "${_blas_root}/include/cblas.h")
        set(BLAS_INCLUDE_DIRS "${_blas_root}/include")
        break()
      elseif(EXISTS "${_blas_root}/include/openblas/cblas.h")
        set(BLAS_INCLUDE_DIRS "${_blas_root}/include/openblas")
        break()
      endif()
    endforeach()
  endif()
  if(BLAS_INCLUDE_DIRS)
    message(STATUS "BLAS include dir: ${BLAS_INCLUDE_DIRS}")
  else()
    message(WARNING "BLAS library found but cblas.h not found - disabling BLAS")
    set(BLAS_FOUND OFF)
    set(BLAS_LIBRARIES "")
  endif()
endif()

if(NOT BLAS_FOUND)
  # Manual search for OpenBLAS (common in conda environments)
  find_path(OPENBLAS_INCLUDE_DIR
    NAMES cblas.h openblas_config.h
    PATHS
      "${CMAKE_PREFIX_PATH}/include"
      "$ENV{CONDA_PREFIX}/Library/include"
      "$ENV{CONDA_PREFIX}/include"
    PATH_SUFFIXES openblas
    NO_DEFAULT_PATH
  )
  find_library(OPENBLAS_LIBRARY
    NAMES openblas openblas.lib
    PATHS
      "${CMAKE_PREFIX_PATH}/lib"
      "$ENV{CONDA_PREFIX}/Library/lib"
      "$ENV{CONDA_PREFIX}/lib"
    NO_DEFAULT_PATH
  )
  if(OPENBLAS_INCLUDE_DIR AND OPENBLAS_LIBRARY)
    set(BLAS_FOUND ON)
    set(BLAS_LIBRARIES "${OPENBLAS_LIBRARY}")
    set(BLAS_INCLUDE_DIRS "${OPENBLAS_INCLUDE_DIR}")
    message(STATUS "Found OpenBLAS: ${OPENBLAS_LIBRARY} (include: ${OPENBLAS_INCLUDE_DIR})")
  else()
    message(STATUS "BLAS not found - building without BLAS acceleration (will use fallback C++ implementations)")
  endif()
endif()

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

tvm_ffi_configure_target(_caffe_ffi LINK_SHARED ON LINK_HEADER ON MSVC_FLAGS ON DEBUG_SYMBOL ON)

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
if(CAFFE_FFI_ENABLE_BACKTRACE)
  target_compile_definitions(_caffe_ffi PUBLIC CAFFE_FFI_ENABLE_BACKTRACE)
endif()
if(BLAS_FOUND OR BLAS_LIBRARIES)
  target_compile_definitions(_caffe_ffi PUBLIC CAFFE_USE_BLAS HAVE_CBLAS_H)
endif()

if(MSVC)
  target_compile_options(_caffe_ffi PRIVATE /W3)
else()
  target_compile_options(_caffe_ffi PRIVATE -Wall -Wextra -Wno-unused-parameter)
endif()

target_link_libraries(_caffe_ffi PUBLIC
  tvm_ffi::header
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

  add_custom_command(TARGET _caffe_ffi POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
      "$<TARGET_FILE:tvm_ffi::shared>"
      "$<TARGET_FILE_DIR:_caffe_ffi>"
    COMMENT "Copying tvm_ffi shared library to output directory"
  )

  # Copy OpenBLAS DLL if available
  if(BLAS_FOUND AND BLAS_LIBRARIES)
    foreach(_blas_lib ${BLAS_LIBRARIES})
      get_filename_component(_blas_lib_dir "${_blas_lib}" DIRECTORY)
      file(GLOB _openblas_dlls "${_blas_lib_dir}/../bin/libopenblas*.dll" "${_blas_lib_dir}/../bin/openblas*.dll")
      foreach(_dll ${_openblas_dlls})
        if(EXISTS "${_dll}")
          add_custom_command(TARGET _caffe_ffi POST_BUILD
            COMMAND ${CMAKE_COMMAND} -E copy_if_different
              "${_dll}"
              "$<TARGET_FILE_DIR:_caffe_ffi>"
            COMMENT "Copying OpenBLAS DLL to output directory"
          )
        endif()
      endforeach()
    endforeach()
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

# ---- C++ unit tests ----
file(GLOB CAFFE_FFI_CPP_TEST_SRCS
  "${CMAKE_CURRENT_SOURCE_DIR}/tests/cpp/*.cpp"
)

add_executable(caffe_ffi_tests
  ${CAFFE_FFI_CPP_TEST_SRCS}
)

target_include_directories(caffe_ffi_tests PRIVATE
  "${CAFFE_FFI_INCLUDE_DIR}"
  "${CAFFE_FFI_GEN_PROTO_DIR}"
  "${CMAKE_CURRENT_SOURCE_DIR}/tests/cpp"
  "${Protobuf_INCLUDE_DIRS}"
)
if(BLAS_INCLUDE_DIRS)
  target_include_directories(caffe_ffi_tests PRIVATE "${BLAS_INCLUDE_DIRS}")
endif()

target_compile_definitions(caffe_ffi_tests PRIVATE
  CPU_ONLY
  CAFFE_FFI_VERSION="${PROJECT_VERSION}"
)
if(CAFFE_FFI_ENABLE_DEBUG_LOG)
  target_compile_definitions(caffe_ffi_tests PRIVATE CAFFE_FFI_ENABLE_DEBUG_LOG)
endif()
if(CAFFE_FFI_ENABLE_BACKTRACE)
  target_compile_definitions(caffe_ffi_tests PRIVATE CAFFE_FFI_ENABLE_BACKTRACE)
endif()
if(BLAS_FOUND OR BLAS_LIBRARIES)
  target_compile_definitions(caffe_ffi_tests PRIVATE CAFFE_USE_BLAS HAVE_CBLAS_H)
endif()

if(MSVC)
  target_compile_options(caffe_ffi_tests PRIVATE /W3)
else()
  target_compile_options(caffe_ffi_tests PRIVATE -Wall -Wextra -Wno-unused-parameter)
endif()

target_link_libraries(caffe_ffi_tests PRIVATE
  _caffe_ffi
  tvm_ffi::shared
  protobuf::libprotobuf
  Threads::Threads
)
if(BLAS_LIBRARIES)
  target_link_libraries(caffe_ffi_tests PRIVATE ${BLAS_LIBRARIES})
endif()
if(MSVC)
  target_link_libraries(caffe_ffi_tests PRIVATE DbgHelp.lib)
endif()

if(MSVC)
  # Copy required DLLs to test output directory
  add_custom_command(TARGET caffe_ffi_tests POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
      "$<TARGET_FILE:tvm_ffi::shared>"
      "$<TARGET_FILE_DIR:caffe_ffi_tests>"
    COMMENT "Copying tvm_ffi DLL for tests"
  )
  add_custom_command(TARGET caffe_ffi_tests POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
      "$<TARGET_FILE:_caffe_ffi>"
      "$<TARGET_FILE_DIR:caffe_ffi_tests>"
    COMMENT "Copying _caffe_ffi DLL for tests"
  )
  # Copy protobuf DLLs
  set(_protobuf_dll_dirs "${Protobuf_DIR}/../../../bin" "${Protobuf_DIR}/../../bin")
  foreach(_dll_dir ${_protobuf_dll_dirs})
    file(GLOB _protobuf_dlls "${_dll_dir}/libprotobuf*.dll" "${_dll_dir}/libprotoc*.dll")
    foreach(_dll ${_protobuf_dlls})
      if(EXISTS "${_dll}")
        add_custom_command(TARGET caffe_ffi_tests POST_BUILD
          COMMAND ${CMAKE_COMMAND} -E copy_if_different
            "${_dll}"
            "$<TARGET_FILE_DIR:caffe_ffi_tests>"
          COMMENT "Copying ${_dll} for tests"
        )
      endif()
    endforeach()
  endforeach()
  # Copy abseil DLLs
  get_filename_component(_absl_dir "${Protobuf_DIR}" DIRECTORY)
  set(_absl_dll_dirs "${_absl_dir}/bin" "${_absl_dir}/../bin")
  if(DEFINED ENV{CONDA_PREFIX})
    list(APPEND _absl_dll_dirs "$ENV{CONDA_PREFIX}/Library/bin")
  endif()
  foreach(_dll_dir ${_absl_dll_dirs})
    file(GLOB _absl_dlls "${_dll_dir}/absl_*.dll" "${_dll_dir}/abseil*.dll")
    foreach(_dll ${_absl_dlls})
      if(EXISTS "${_dll}")
        add_custom_command(TARGET caffe_ffi_tests POST_BUILD
          COMMAND ${CMAKE_COMMAND} -E copy_if_different
            "${_dll}"
            "$<TARGET_FILE_DIR:caffe_ffi_tests>"
          COMMENT "Copying ${_dll} for tests"
        )
      endif()
    endforeach()
  endforeach()
  # Copy OpenBLAS DLL
  if(BLAS_FOUND AND BLAS_LIBRARIES)
    foreach(_blas_lib ${BLAS_LIBRARIES})
      get_filename_component(_blas_lib_dir "${_blas_lib}" DIRECTORY)
      file(GLOB _openblas_dlls "${_blas_lib_dir}/../bin/libopenblas*.dll" "${_blas_lib_dir}/../bin/openblas*.dll")
      foreach(_dll ${_openblas_dlls})
        if(EXISTS "${_dll}")
          add_custom_command(TARGET caffe_ffi_tests POST_BUILD
            COMMAND ${CMAKE_COMMAND} -E copy_if_different
              "${_dll}"
              "$<TARGET_FILE_DIR:caffe_ffi_tests>"
            COMMENT "Copying OpenBLAS DLL for tests"
          )
        endif()
      endforeach()
    endforeach()
  endif()
endif()

add_test(NAME caffe_ffi_cpp_tests COMMAND caffe_ffi_tests)

install(TARGETS _caffe_ffi
  LIBRARY DESTINATION caffe_ffi
  RUNTIME DESTINATION caffe_ffi
)

if(EXISTS "${CAFFE_FFI_PROTO_PY}")
  install(FILES "${CAFFE_FFI_PROTO_PY}" DESTINATION caffe_ffi/proto)
endif()
