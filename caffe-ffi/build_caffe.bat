@echo off
setlocal

echo ========================================
echo Caffe-FFI Windows Build Script
echo ========================================

set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"

echo [1/4] Cleaning build directory...
if exist build rmdir /s /q build

echo [2/4] Running CMake configuration (Visual Studio 2026)...
cmake -B build -G "Visual Studio 18 2026" -A x64 -DCMAKE_BUILD_TYPE=Release
if errorlevel 1 (
    echo ERROR: CMake configuration failed, trying Visual Studio 17 2022...
    cmake -B build -G "Visual Studio 17 2022" -A x64 -DCMAKE_BUILD_TYPE=Release
    if errorlevel 1 (
        echo ERROR: CMake configuration failed
        exit /b 1
    )
)

echo [3/4] Building...
cmake --build build --config Release
if errorlevel 1 (
    echo ERROR: Build failed
    exit /b 1
)

echo [4/4] Build succeeded!
echo ========================================
endlocal
exit /b 0
