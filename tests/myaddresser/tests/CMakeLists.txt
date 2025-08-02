cmake_minimum_required(VERSION 3.25...4.0)
project(PackageTest CXX)

find_package(myaddresser CONFIG REQUIRED)

add_executable(example src/example.cpp)
target_link_libraries(example PRIVATE myaddresser::myaddresser)
