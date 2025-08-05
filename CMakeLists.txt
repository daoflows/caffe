cmake_minimum_required(VERSION 3.25...4.0)
project(caffeproto LANGUAGES CXX)

find_package(protobuf CONFIG REQUIRED)

protobuf_generate_cpp(PROTO_SRCS PROTO_HDRS caffe.proto)


add_library(caffeproto src/caffeproto.cpp ${PROTO_SRCS})
target_include_directories(caffeproto PUBLIC include)

target_include_directories(caffeproto PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<BUILD_INTERFACE:${CMAKE_CURRENT_BINARY_DIR}>
  $<INSTALL_INTERFACE:include> 
)

target_link_libraries(caffeproto PUBLIC protobuf::libprotobuf)


set_target_properties(caffeproto PROPERTIES PUBLIC_HEADER "include/caffeproto.h;${PROTO_HDRS}")
install(TARGETS caffeproto)
