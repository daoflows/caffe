#!/bin/bash
set -e
conan profile detect --force
conan install . -c tools.cmake.cmaketoolchain:generator=Ninja --build missing
cmake --preset conan-release
cmake --build --preset conan-release
