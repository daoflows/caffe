cmake_minimum_required(VERSION 3.18)
project(pycaffe VERSION 1.0.0 LANGUAGES CXX)

if(POLICY CMP0167)
  cmake_policy(SET CMP0167 NEW)
endif()
if(POLICY CMP0144)
  cmake_policy(SET CMP0144 NEW)
endif()

if(DEFINED ENV{CONDA_PREFIX} AND NOT DEFINED Boost_ROOT)
  set(Boost_ROOT $ENV{CONDA_PREFIX})
endif()
if(CONDA_ENV_PREFIX AND NOT DEFINED Boost_ROOT)
  set(Boost_ROOT ${CONDA_ENV_PREFIX})
endif()
if(DEFINED BOOST_ROOT AND NOT DEFINED Boost_ROOT)
  set(Boost_ROOT ${BOOST_ROOT})
endif()

find_package(
  Python
  COMPONENTS Interpreter Development NumPy
  REQUIRED
)

set(_py_version_nodot "${Python_VERSION_MAJOR}${Python_VERSION_MINOR}")

find_package(Boost QUIET COMPONENTS python${_py_version_nodot})

if(NOT Boost_FOUND OR NOT TARGET Boost::python${_py_version_nodot})
  find_package(Boost QUIET COMPONENTS python${_py_version_nodot}t)
endif()

if(NOT Boost_FOUND OR NOT TARGET Boost::python${_py_version_nodot}t)
  find_package(Boost QUIET COMPONENTS python${Python_VERSION_MAJOR})
endif()

if(NOT Boost_FOUND)
  find_package(Boost REQUIRED COMPONENTS python)
endif()

find_library(PROTOBUF_LIBRARY protobuf
  PATHS /usr/lib /usr/lib/x86_64-linux-gnu /usr/local/lib
  REQUIRED
)
find_path(PROTOBUF_INCLUDE_DIR google/protobuf/message.h
  PATHS /usr/include /usr/local/include
  REQUIRED
)
set(Protobuf_INCLUDE_DIRS ${PROTOBUF_INCLUDE_DIR})
set(Protobuf_LIBRARIES ${PROTOBUF_LIBRARY})

find_library(CAFFE_LIBRARY caffe
  PATHS
    ${CAFFE_BUILD_DIR}/lib
    /workspace/caffex/build/lib
    /workspace/caffex/.build_release/lib
    /workspace/caffex/distribute/lib
    ${CONDA_ENV_PREFIX}/lib
    ${CONDA_PREFIX}/lib
    ${BOOST_ROOT}/lib
    /usr/lib
    /usr/lib/x86_64-linux-gnu
    /usr/local/lib
  REQUIRED
)

find_path(CAFFE_INCLUDE_DIR caffe/caffe.hpp
  PATHS
    ${CAFFE_BUILD_DIR}/include
    /workspace/caffex/distribute/include
    /workspace/caffex/include
    ${CONDA_ENV_PREFIX}/include
    ${CONDA_PREFIX}/include
    ${BOOST_ROOT}/include
    /usr/include
    /usr/local/include
  REQUIRED
)

find_path(CAFFE_PROTO_INCLUDE_DIR caffe/proto/caffe.pb.h
  PATHS
    ${CAFFE_BUILD_DIR}/src
    /workspace/caffex/build/src
    /workspace/caffex/.build_release/src
  REQUIRED
)

find_library(GLOG_LIBRARY glog
  PATHS /usr/lib/x86_64-linux-gnu /usr/lib /usr/local/lib ${CONDA_ENV_PREFIX}/lib ${CONDA_PREFIX}/lib ${BOOST_ROOT}/lib
  REQUIRED
)
find_library(GFLAGS_LIBRARY gflags
  PATHS /usr/lib/x86_64-linux-gnu /usr/lib /usr/local/lib ${CONDA_ENV_PREFIX}/lib ${CONDA_PREFIX}/lib ${BOOST_ROOT}/lib
  REQUIRED
)
find_path(GLOG_INCLUDE_DIR glog/logging.h
  PATHS /usr/include /usr/local/include ${CONDA_ENV_PREFIX}/include ${CONDA_PREFIX}/include ${BOOST_ROOT}/include
  REQUIRED
)
find_path(GFLAGS_INCLUDE_DIR gflags/gflags.h
  PATHS /usr/include /usr/local/include ${CONDA_ENV_PREFIX}/include ${CONDA_PREFIX}/include ${BOOST_ROOT}/include
  REQUIRED
)

find_library(HDF5_LIBRARY hdf5
  PATHS /usr/lib/x86_64-linux-gnu /usr/lib /usr/local/lib
)
find_library(HDF5_HL_LIBRARY hdf5_hl
  PATHS /usr/lib/x86_64-linux-gnu /usr/lib /usr/local/lib
)
find_library(LEVELDB_LIBRARY leveldb
  PATHS /usr/lib/x86_64-linux-gnu /usr/lib /usr/local/lib
)
find_library(LMDB_LIBRARY lmdb
  PATHS /usr/lib/x86_64-linux-gnu /usr/lib /usr/local/lib
)
find_library(SNAPPY_LIBRARY snappy
  PATHS /usr/lib/x86_64-linux-gnu /usr/lib /usr/local/lib
)
find_library(OPENCV_CORE opencv_core
  PATHS /usr/lib/x86_64-linux-gnu /usr/lib /usr/local/lib
)
find_library(OPENCV_HIGHGUI opencv_highgui
  PATHS /usr/lib/x86_64-linux-gnu /usr/lib /usr/local/lib
)
find_library(OPENCV_IMGPROC opencv_imgproc
  PATHS /usr/lib/x86_64-linux-gnu /usr/lib /usr/local/lib
)
find_library(OPENCV_IMGCODECS opencv_imgcodecs
  PATHS /usr/lib/x86_64-linux-gnu /usr/lib /usr/local/lib
)
find_library(BOOST_THREAD_LIBRARY boost_thread
  PATHS /usr/lib/x86_64-linux-gnu /usr/lib /usr/local/lib ${CONDA_ENV_PREFIX}/lib ${CONDA_PREFIX}/lib ${BOOST_ROOT}/lib
)
find_library(BOOST_FILESYSTEM_LIBRARY boost_filesystem
  PATHS /usr/lib/x86_64-linux-gnu /usr/lib /usr/local/lib ${CONDA_ENV_PREFIX}/lib ${CONDA_PREFIX}/lib ${BOOST_ROOT}/lib
)

set(CAFFE_EXT_SRC "${CMAKE_CURRENT_SOURCE_DIR}/python/pycaffe/_caffe.cpp")

Python_add_library(_caffe MODULE "${CAFFE_EXT_SRC}")

if(CONDA_ENV_NAME)
  set(_rpath_conda "/opt/conda/envs/${CONDA_ENV_NAME}/lib")
else()
  set(_rpath_conda "")
endif()

set_target_properties(_caffe PROPERTIES
  CXX_STANDARD 17
  CXX_STANDARD_REQUIRED ON
  PREFIX ""
  OUTPUT_NAME "_caffe"
  BUILD_RPATH "/workspace/caffex/build/lib;/workspace/caffex/.build_release/lib;${_rpath_conda};${CONDA_ENV_PREFIX}/lib;${CONDA_PREFIX}/lib;${BOOST_ROOT}/lib"
  INSTALL_RPATH "/workspace/caffex/build/lib;/workspace/caffex/.build_release/lib;${_rpath_conda};${CONDA_ENV_PREFIX}/lib;${CONDA_PREFIX}/lib;${BOOST_ROOT}/lib"
  BUILD_WITH_INSTALL_RPATH TRUE
)
if(NOT CAFFE_VERSION)
  set(CAFFE_VERSION "1.0.0")
endif()
target_compile_definitions(_caffe PRIVATE
  CPU_ONLY
  CAFFE_VERSION=${CAFFE_VERSION}
)

target_include_directories(_caffe PRIVATE
  ${CAFFE_INCLUDE_DIR}
  ${CAFFE_PROTO_INCLUDE_DIR}
  ${CONDA_PREFIX}/src
  ${Boost_INCLUDE_DIRS}
  ${Python_NumPy_INCLUDE_DIRS}
  ${Protobuf_INCLUDE_DIRS}
  ${GLOG_INCLUDE_DIR}
  ${GFLAGS_INCLUDE_DIR}
)

if(TARGET Boost::python${_py_version_nodot})
  set(_boost_python_target Boost::python${_py_version_nodot})
elseif(TARGET Boost::python${Python_VERSION_MAJOR})
  set(_boost_python_target Boost::python${Python_VERSION_MAJOR})
elseif(TARGET Boost::python)
  set(_boost_python_target Boost::python)
else()
  message(FATAL_ERROR "Could not find Boost.Python target")
endif()

target_link_libraries(_caffe PRIVATE
  ${CAFFE_LIBRARY}
  ${_boost_python_target}
  Python::Module
  Python::NumPy
  ${Protobuf_LIBRARIES}
  ${GLOG_LIBRARY}
  ${GFLAGS_LIBRARY}
)

set(_optional_libs
  HDF5_LIBRARY HDF5_HL_LIBRARY LEVELDB_LIBRARY LMDB_LIBRARY SNAPPY_LIBRARY
  OPENCV_CORE OPENCV_HIGHGUI OPENCV_IMGPROC OPENCV_IMGCODECS
  BOOST_THREAD_LIBRARY BOOST_FILESYSTEM_LIBRARY
)
foreach(_lib ${_optional_libs})
  if(${_lib})
    target_link_libraries(_caffe PRIVATE ${${_lib}})
  endif()
endforeach()

install(TARGETS _caffe DESTINATION pycaffe)
install(DIRECTORY python/pycaffe/
  DESTINATION pycaffe
  FILES_MATCHING
  PATTERN "*.py"
  PATTERN "*.cpp" EXCLUDE
  PATTERN "test" EXCLUDE
  PATTERN "proto" EXCLUDE
)
install(DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/../../caffeproto/
  DESTINATION caffeproto
  FILES_MATCHING
  PATTERN "*.py"
)