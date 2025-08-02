cmake_minimum_required(VERSION 3.25)

project(Hello)

find_package(caffex REQUIRED)

add_executable(hello src/hello.cpp)
target_link_libraries(hello caffex::caffex)
