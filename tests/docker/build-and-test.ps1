# ==============================================================================
# build-and-test.ps1 — Windows PowerShell: 一键编译 pycaffe 并运行算子测试
#
# 用法（PowerShell）:
#   cd projects\xuanspace\vendor\caffe
#   .\tests\docker\build-and-test.ps1 [-NoCache] [-Quick] [-Interactive]
#
# 参数：
#   -NoCache     Docker build 不使用缓存
#   -Quick       仅验证 import，不跑全部测试
#   -Interactive 构建完成后进入交互式 bash shell
# ==============================================================================

param(
    [switch]$NoCache,
    [switch]$Quick,
    [switch]$Interactive
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$CaffeDir = Resolve-Path (Join-Path $ScriptDir "..\..")
$ImageName = "caffe-pycaffe:full"

Set-Location $CaffeDir

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Caffe PyCaffe Full Build & Test" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Caffe dir: $CaffeDir"
Write-Host "  Image:     $ImageName"
Write-Host "  No cache:  $NoCache"
Write-Host "  Quick:     $Quick"
Write-Host ""

# Step 1: Build
Write-Host "[1/3] Building Docker image..." -ForegroundColor Yellow
$buildArgs = @("build", "-t", $ImageName, "-f", "tests/docker/Dockerfile")
if ($NoCache) { $buildArgs += "--no-cache" }
$buildArgs += "."
& docker @buildArgs
if ($LASTEXITCODE -ne 0) {
    Write-Host "Docker build failed!" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Step 2: Verify
Write-Host "[2/3] Verifying pycaffe import..." -ForegroundColor Yellow
& docker run --rm $ImageName python -c @"
import caffe
from caffe import layers as L, params as P
print('Caffe version:', getattr(caffe, '__version__', 'BVLC'))
print('SGDSolver:', caffe.SGDSolver)
print('NetSpec:', caffe.NetSpec)
print('Net:', caffe.Net)
print('Pooling.MAX:', P.Pooling.MAX)
print('All core APIs available!')
"@
if ($LASTEXITCODE -ne 0) {
    Write-Host "PyCaffe verification failed!" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Step 3: Tests or Interactive
if ($Interactive) {
    Write-Host "[3/3] Entering interactive shell..." -ForegroundColor Yellow
    Write-Host "Tests directory mounted at /workspace/tests" -ForegroundColor Gray
    & docker run --rm -it -v "${CaffeDir}/tests/ops:/workspace/tests" $ImageName bash
}
elseif ($Quick) {
    Write-Host "[3/3] Quick mode: collecting tests..." -ForegroundColor Yellow
    & docker run --rm -v "${CaffeDir}/tests/ops:/workspace/tests" $ImageName `
        bash -c "cd /workspace/tests && python -m pytest --collect-only 2>&1 | tail -30"
}
else {
    Write-Host "[3/3] Running full test suite with coverage..." -ForegroundColor Yellow

    $coverageDir = Join-Path $CaffeDir "tests\coverage"
    if (-not (Test-Path $coverageDir)) {
        New-Item -ItemType Directory -Path $coverageDir -Force | Out-Null
    }

    & docker run --rm -v "${CaffeDir}/tests/ops:/workspace/tests" $ImageName bash -c @"
set -e
cd /workspace/tests
echo '=== Environment Check ==='
python -c 'import caffe; print(\"Caffe OK\")'
echo ''
echo '=== Running Tests (CAFFE_LOG_LEVEL=INFO) ==='
CAFFE_LOG_LEVEL=INFO python -m pytest -v \
    --cov=. \
    --cov-report=term-missing \
    --cov-report=html:/workspace/coverage/htmlcov \
    --cov-report=xml:/workspace/coverage/coverage.xml \
    2>&1
echo ''
echo '=== Tests complete ==='
"@
    Write-Host ""
    Write-Host "Coverage HTML report: $coverageDir\htmlcov\index.html" -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Done!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Useful commands:" -ForegroundColor Yellow
Write-Host "  Interactive: docker run --rm -it -v ${CaffeDir}/tests/ops:/workspace/tests ${ImageName} bash"
Write-Host "  Run tests:   docker run --rm -v ${CaffeDir}/tests/ops:/workspace/tests ${ImageName} bash -c 'cd /workspace/tests && CAFFE_LOG_LEVEL=DEBUG pytest -v'"
