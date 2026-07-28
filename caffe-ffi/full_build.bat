@echo off
cd /d d:\spaces\SpecWeave\projects\xuanspace\vendor\caffe\caffe-ffi

set "CONDA_PREFIX=D:\Users\xinzo\anaconda3\envs\py314"

set "PATH=C:\Windows\System32;C:\Windows;C:\Windows\System32\Wbem;C:\Windows\System32\WindowsPowerShell\v1.0\"

call "C:\Program Files\Microsoft Visual Studio\18\Insiders\VC\Auxiliary\Build\vcvarsall.bat" x64
if errorlevel 1 (
    echo Failed to initialize VS environment
    exit /b 1
)

set "PATH=%CONDA_PREFIX%\Library\bin;%CONDA_PREFIX%\Scripts;%CONDA_PREFIX%;%PATH%"

if exist build-cmake rmdir /s /q build-cmake

echo === CMAKE CONFIGURE ===
cmake -B build-cmake -G Ninja -DCMAKE_BUILD_TYPE=Release ^
    -DCMAKE_PREFIX_PATH="%CONDA_PREFIX%\Library;%CONDA_PREFIX%" ^
    -DProtobuf_DIR="%CONDA_PREFIX%\Library\lib\cmake\protobuf"
if errorlevel 1 (
    echo CMAKE CONFIGURE FAILED
    exit /b 1
)

echo.
echo === CMAKE BUILD ===
cmake --build build-cmake --config Release
set BUILD_RESULT=%errorlevel%
echo BUILD_EXIT=%BUILD_RESULT%
exit /b %BUILD_RESULT%
