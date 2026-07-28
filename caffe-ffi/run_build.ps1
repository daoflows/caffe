$vsPath = "C:\Program Files\Microsoft Visual Studio\18\Insiders"
$vcvarsall = "$vsPath\VC\Auxiliary\Build\vcvarsall.bat"

$tempFile = [System.IO.Path]::GetTempFileName()
cmd /c "`"$vcvarsall`" x64 >nul 2>&1 && set > `"$tempFile`"" 2>&1 | Out-Null

Get-Content $tempFile | ForEach-Object {
    if ($_ -match '^([A-Za-z_][A-Za-z0-9_]*)=(.*)$') {
        $name = $matches[1]
        $value = $matches[2]
        [Environment]::SetEnvironmentVariable($name, $value, 'Process')
    }
}
Remove-Item $tempFile -ErrorAction SilentlyContinue

Write-Host "LIB exists: $([bool]$env:LIB)"
if ($env:LIB) { Write-Host "LIB=$($env:LIB.Substring(0, [Math]::Min(300, $env:LIB.Length)))..." }
Write-Host "INCLUDE exists: $([bool]$env:INCLUDE)"
if ($env:INCLUDE) { Write-Host "INCLUDE=$($env:INCLUDE.Substring(0, [Math]::Min(300, $env:INCLUDE.Length)))..." }

Set-Location d:\spaces\SpecWeave\projects\xuanspace\vendor\caffe\caffe-ffi
if (Test-Path build-cmake) { Remove-Item build-cmake -Recurse -Force }

$env:PATH = "D:\Users\xinzo\anaconda3\Library\bin;D:\Users\xinzo\anaconda3\Scripts;D:\Users\xinzo\anaconda3;" + $env:PATH

Write-Host "=== CMAKE CONFIGURE ==="
cmake -B build-cmake -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH="D:\Users\xinzo\anaconda3\Library;D:\Users\xinzo\anaconda3" 2>&1
Write-Host "CONFIGURE_EXIT=$LASTEXITCODE"
