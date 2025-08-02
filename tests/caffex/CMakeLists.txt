cmake_minimum_required(VERSION 3.25)
project(caffex CXX)

add_library(caffex src/caffex.cpp)
target_include_directories(caffex PUBLIC include)

set_target_properties(caffex PROPERTIES PUBLIC_HEADER "include/caffex.h")
install(TARGETS caffex)
