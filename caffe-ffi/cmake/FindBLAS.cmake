# FindBLAS.cmake - BLAS/OpenBLAS 检测与配置
# 提供变量：BLAS_FOUND, BLAS_LIBRARIES, BLAS_INCLUDE_DIRS

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
