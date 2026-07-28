@echo off
call "C:\Program Files\Microsoft Visual Studio\18\Insiders\VC\Auxiliary\Build\vcvarsall.bat" x64 >nul 2>&1
cd /d d:\spaces\SpecWeave\projects\xuanspace\vendor\caffe\caffe-ffi

set CONDA_PREFIX=D:\Users\xinzo\anaconda3
set PATH=%CONDA_PREFIX%\Library\bin;%CONDA_PREFIX%\Library\lib;%CONDA_PREFIX%\Scripts;%CONDA_PREFIX%;%PATH%

if exist build-cmake rmdir /s /q build-cmake
mkdir build-cmake

echo === CMAKE CONFIGURE === > build_log.txt 2>&1
cmake -B build-cmake -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH="%CONDA_PREFIX%\Library;%CONDA_PREFIX%" >> build_log.txt 2>&1
echo CMAKE_CONFIGURE_EXIT=%ERRORLEVEL% >> build_log.txt 2>&1

echo. >> build_log.txt 2>&1
echo === CMAKE BUILD === >> build_log.txt 2>&1
cmake --build build-cmake --config Release -v >> build_log.txt 2>&1
echo CMAKE_BUILD_EXIT=%ERRORLEVEL% >> build_log.txt 2>&1

echo Build done. Check build_log.txt
