# generate protobuf sources
file(GLOB proto_files proto/*.proto)
caffe_protobuf_generate_cpp_py(${proto_gen_folder} proto_srcs proto_hdrs proto_python ${proto_files})

# include python files either to force generation
add_library(caffeproto STATIC ${proto_hdrs} ${proto_srcs} ${proto_python})
caffe_default_properties(caffeproto)
target_link_libraries(caffeproto PUBLIC ${PROTOBUF_LIBRARIES})
target_include_directories(caffeproto PUBLIC ${PROTOBUF_INCLUDE_DIR})

list(INSERT Caffe_LINKER_LIBS 0 PUBLIC caffeproto) # note, crucial to prepend!

# --[ Caffe library

# creates 'test_srcs', 'srcs', 'test_cuda', 'cuda' lists
caffe_pickup_caffe_sources(${PROJECT_SOURCE_DIR})

if(HAVE_CUDA)
  caffe_cuda_compile(cuda_objs ${cuda})
  list(APPEND srcs ${cuda_objs} ${cuda})
endif()

add_library(caffe ${srcs})
caffe_default_properties(caffe)
target_link_libraries(caffe PUBLIC
    ${Caffe_LINKER_LIBS}
    ${Boost_LIBRARIES}
    Boost::boost
    ${PROTOBUF_LIBRARIES}
    ${BLAS_LIBRARIES}
    ${LEVELDB_LIBRARIES}
    ${LMDB_LIBRARIES}
    ${GLOG_LIBRARIES}
    ${GFLAGS_LIBRARIES}
    ${HDF5_LIBRARIES}
    ${OPENCV_LIBRARIES}
    ${CUDNN_LIBRARIES}
    ${CURAND_LIBRARY}
)
target_include_directories(caffe PRIVATE ${Python3_INCLUDE_DIRS} ${Caffe_INCLUDE_DIRS}
                                   PUBLIC
                                   $<BUILD_INTERFACE:${Caffe_INCLUDE_DIR}>
                                 $<INSTALL_INTERFACE:include>)
target_compile_definitions(caffe ${Caffe_DEFINITIONS})
if(Caffe_COMPILE_OPTIONS)
  target_compile_options(caffe ${Caffe_COMPILE_OPTIONS})
endif()

if("${CMAKE_CXX_COMPILER_ID}" STREQUAL "Clang"
  OR "${CMAKE_CXX_COMPILER_ID}" STREQUAL "AppleClang")
  target_link_options(caffe PUBLIC -Wl,-force_load $<TARGET_FILE:caffe>)
elseif("${CMAKE_CXX_COMPILER_ID}" STREQUAL "GNU")
  target_link_options(caffe PUBLIC -Wl,--whole-archive $<TARGET_FILE:caffe> -Wl,--no-whole-archive)
elseif(MSVC)
  target_link_options(caffe PUBLIC /WHOLEARCHIVE:$<TARGET_FILE:caffe>)
endif()

set_target_properties(caffe PROPERTIES
    VERSION   ${CAFFE_TARGET_VERSION}
    SOVERSION ${CAFFE_TARGET_SOVERSION}
    )

# ---[ Tests
 add_subdirectory(test)

# ---[ Install
install(DIRECTORY ${Caffe_INCLUDE_DIR}/caffe DESTINATION ${CMAKE_INSTALL_INCLUDEDIR})
install(FILES ${proto_hdrs} DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/caffe/proto)
install(TARGETS caffe caffeproto EXPORT CaffeTargets DESTINATION ${CMAKE_INSTALL_LIBDIR})

file(WRITE ${PROJECT_BINARY_DIR}/__init__.py)
list(APPEND proto_python ${PROJECT_BINARY_DIR}/__init__.py)
install(PROGRAMS ${proto_python} DESTINATION python/caffe/proto)

