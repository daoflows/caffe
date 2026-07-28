@echo off
call "C:\Program Files\Microsoft Visual Studio\18\Insiders\VC\Auxiliary\Build\vcvarsall.bat" x64
cd /d d:\spaces\SpecWeave\projects\xuanspace\vendor\caffe\caffe-ffi
if exist build-cmake rmdir /s /q build-cmake
cmake -B build-cmake -G Ninja 2>&1
echo CMAKE_EXIT_CODE=%ERRORLEVEL%
