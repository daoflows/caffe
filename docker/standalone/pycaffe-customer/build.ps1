# ==============================================================================
# PyCaffe Customer Distribution Image - Build & Export Script (PowerShell)
# Usage: .\build.ps1 [options]
# Builds the Docker image and automatically exports it as a .tar (or .tar.gz) file.
# ==============================================================================
#Requires -Version 5.1

[CmdletBinding()]
param(
    [Parameter(HelpMessage = "Image tag (default: customer)")]
    [string]$Tag = "customer",

    [Parameter(HelpMessage = "Image name (default: caffe-cpu)")]
    [string]$ImageName = "caffe-cpu",

    [Parameter(HelpMessage = "Version string for filename (default: 1.0.0)")]
    [string]$Version = "1.0.0",

    [Parameter(HelpMessage = "Output directory for exported tar (default: ./dist)")]
    [string]$OutputDir = "",

    [Parameter(HelpMessage = "Build target stage (default: customer-runtime)")]
    [string]$Target = "customer-runtime",

    [Parameter(HelpMessage = "Build without cache")]
    [switch]$NoCache,

    [Parameter(HelpMessage = "Use China mirrors (Aliyun for apt + PyPI)")]
    [switch]$China,

    [Parameter(HelpMessage = "Compress output with gzip (.tar.gz)")]
    [switch]$Gzip,

    [Parameter(HelpMessage = "Skip export step (build only)")]
    [switch]$BuildOnly,

    [Parameter(HelpMessage = "Skip SHA256 checksum generation")]
    [switch]$NoChecksum,

    [Parameter(HelpMessage = "Additional build arguments (key=value, can be repeated)")]
    [string[]]$BuildArg = @()
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

# ---------------------------------------------------------------------------
# Helper functions (colored logging)
# ---------------------------------------------------------------------------
function Write-Info    { param([string]$Msg) Write-Host "[INFO] $Msg" -ForegroundColor Cyan }
function Write-Ok      { param([string]$Msg) Write-Host "[OK]   $Msg" -ForegroundColor Green }
function Write-WarnMsg { param([string]$Msg) Write-Host "[WARN] $Msg" -ForegroundColor Yellow }
function Write-Err     { param([string]$Msg) Write-Host "[ERROR] $Msg" -ForegroundColor Red }
function Write-Header  { param([string]$Msg) Write-Host ""; Write-Host ("=" * 48) -ForegroundColor Cyan; Write-Host " $Msg" -ForegroundColor Cyan; Write-Host ("=" * 48) -ForegroundColor Cyan }
function Write-Section { param([string]$Msg) Write-Host ""; Write-Host "--- $Msg ---" -ForegroundColor White }
function Write-Kv      { param([string]$Key, [string]$Val) Write-Host "  $Key`: " -NoNewline -ForegroundColor Gray; Write-Host $Val }

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
$ScriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Definition
$VendorDir   = Resolve-Path (Join-Path $ScriptDir "../../../..")
$Dockerfile  = Join-Path $ScriptDir "Dockerfile"
if ([string]::IsNullOrEmpty($OutputDir)) {
    $OutputDir = Join-Path $ScriptDir "dist"
}
$DateStr     = Get-Date -Format "yyyyMMdd"
$BuildDate   = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
$ImageSpec   = "${ImageName}:${Tag}"

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------
Write-Header "PyCaffe Customer Build & Export"

Write-Section "Environment Checks"

# Check Docker CLI
$dockerCmd = Get-Command docker -ErrorAction SilentlyContinue
if (-not $dockerCmd) {
    Write-Err "docker command not found. Please install Docker Desktop first."
    exit 1
}
Write-Ok "Docker found: $(docker --version 2>&1)"

# Check Docker daemon
$daemonCheck = docker info 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Err "Docker daemon is not running. Start Docker Desktop first."
    exit 1
}
Write-Ok "Docker daemon is running"

# Check Dockerfile
if (-not (Test-Path $Dockerfile)) {
    Write-Err "Dockerfile not found: $Dockerfile"
    exit 1
}
Write-Ok "Dockerfile: $Dockerfile"

# Check caffe-slim submodule
$CaffeSlimDir = Join-Path $VendorDir "caffe/caffe-slim"
if (-not (Test-Path $CaffeSlimDir)) {
    Write-Err "caffe-slim source not found: $CaffeSlimDir"
    Write-Info "Initialize submodules: git submodule update --init --recursive"
    exit 1
}
Write-Ok "caffe-slim source: present"

# Check tvm-ffi submodule
$TvmFfiDir = Join-Path $VendorDir "tvm-ffi"
if (-not (Test-Path $TvmFfiDir)) {
    Write-Err "tvm-ffi submodule not found: $TvmFfiDir"
    Write-Info "Initialize submodules: git submodule update --init --recursive"
    exit 1
}
Write-Ok "tvm-ffi source: present"

# Check BuildKit
$env:DOCKER_BUILDKIT = "1"
Write-Ok "BuildKit: enabled"

# ---------------------------------------------------------------------------
# Build configuration
# ---------------------------------------------------------------------------
Write-Section "Build Configuration"
Write-Kv "Build context" $VendorDir
Write-Kv "Dockerfile"    $Dockerfile
Write-Kv "Target stage"  $Target
Write-Kv "Image tag"     $ImageSpec
Write-Kv "Version"       $Version
Write-Kv "Build date"    $BuildDate

$buildArgs = @(
    "--build-arg", "BUILD_DATE=$BuildDate",
    "--build-arg", "IMAGE_VERSION=$Version"
)

if ($China) {
    Write-Kv "Mirror" "China (Aliyun)"
    $buildArgs += @(
        "--build-arg", "APTPROXY=mirrors.aliyun.com",
        "--build-arg", "PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple",
        "--build-arg", "PIP_TRUSTED_HOST=mirrors.aliyun.com"
    )
} else {
    Write-Kv "Mirror" "Official sources (default)"
}

foreach ($ba in $BuildArg) {
    $buildArgs += @("--build-arg", $ba)
    Write-Kv "Extra build-arg" $ba
}

if ($Gzip) {
    $OutputFile = Join-Path $OutputDir "caffe-cpu-customer-${Version}-${DateStr}.tar.gz"
} else {
    $OutputFile = Join-Path $OutputDir "caffe-cpu-customer-${Version}-${DateStr}.tar"
}

if (-not $BuildOnly) {
    Write-Kv "Output file"   $OutputFile
    Write-Kv "Compress"      $(if ($Gzip) { "Yes (gzip)" } else { "No (.tar)" })
    Write-Kv "Checksum"      $(if ($NoChecksum) { "Skip" } else { "SHA256" })
} else {
    Write-Kv "Export"        "Skip (build only)"
}

# ---------------------------------------------------------------------------
# Docker Build
# ---------------------------------------------------------------------------
Write-Section "Building Image"
Write-WarnMsg "This is a FULL self-contained build (compiles Caffe from source)."
Write-WarnMsg "First build may take 15-30 minutes. Subsequent builds use cache."
Write-Host ""

$buildStart = Get-Date

$dockerBuildArgs = @(
    "build",
    "--target", $Target,
    "-t", $ImageSpec,
    "-f", $Dockerfile
)

if ($NoCache) {
    $dockerBuildArgs += "--no-cache"
}

$dockerBuildArgs += $buildArgs
$dockerBuildArgs += $VendorDir

& docker @dockerBuildArgs
$buildExitCode = $LASTEXITCODE

$buildEnd = Get-Date
$buildDuration = $buildEnd - $buildStart
$buildMin = [math]::Floor($buildDuration.TotalMinutes)
$buildSec = $buildDuration.Seconds

if ($buildExitCode -ne 0) {
    Write-Host ""
    Write-Header "BUILD FAILED"
    Write-Err "Build failed with exit code: $buildExitCode"
    Write-Kv "Duration" "${buildMin}m ${buildSec}s"
    exit $buildExitCode
}

Write-Host ""
Write-Header "BUILD SUCCESSFUL"
Write-Kv "Image"    $ImageSpec
Write-Kv "Duration" "${buildMin}m ${buildSec}s"

# Get image size
$imageSizeInfo = docker image inspect $ImageSpec --format='{{.Size}}' 2>&1
if ($LASTEXITCODE -eq 0 -and $imageSizeInfo -match '^\d+$') {
    $imageSizeMB = [math]::Round([long]$imageSizeInfo / 1MB)
    $imageSizeGB = [math]::Round($imageSizeMB / 1024, 2)
    Write-Kv "Image size" "${imageSizeMB} MB (${imageSizeGB} GB)"
    if ($imageSizeMB -gt 3072) {
        Write-WarnMsg "Image size exceeds 3GB target."
    } else {
        Write-Ok "Image size within 3GB target"
    }
}

if ($BuildOnly) {
    Write-Host ""
    Write-Section "Quick Start"
    Write-Info "Run container:"
    Write-Host "  docker run -d -p 8888:8888 -p 2222:22 --name caffe $ImageSpec"
    Write-Host ""
    Write-Info "View logs (get credentials):"
    Write-Host "  docker logs caffe"
    Write-Host ""
    Write-Info "Jupyter URL:  http://localhost:8888/ (token: caffe-token)"
    Write-Info "SSH:          ssh builder@localhost -p 2222 (password: caffepass)"
    Write-Host ""
    Write-Info "Verify:"
    Write-Host "  docker exec caffe caffe-verify"
    Write-Host ""
    Write-Info "To export later, run this script again without -BuildOnly."
    Write-Ok "Build complete!"
    exit 0
}

# ---------------------------------------------------------------------------
# Docker Save (Export)
# ---------------------------------------------------------------------------
Write-Section "Exporting Image"

if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}
Write-Ok "Output directory: $OutputDir"

Write-Info "Exporting $ImageSpec -> $OutputFile"
Write-WarnMsg "This may take several minutes depending on image size..."
Write-Host ""

$exportStart = Get-Date

if ($Gzip) {
    # Use pipeline: docker save | gzip via .NET GZipStream for reliable compression
    # This avoids external gzip dependency on Windows
    $tarStream = $null
    $gzStream  = $null
    $fileStream = $null
    try {
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName = "docker"
        $psi.Arguments = "save $ImageSpec"
        $psi.UseShellExecute = $false
        $psi.RedirectStandardOutput = $true
        $psi.RedirectStandardError = $false
        $psi.CreateNoWindow = $true

        $process = [System.Diagnostics.Process]::Start($psi)

        $fileStream = [System.IO.File]::Create($OutputFile)
        $gzStream   = New-Object System.IO.Compression.GZipStream($fileStream, [System.IO.Compression.CompressionLevel]::Optimal)
        $process.StandardOutput.BaseStream.CopyTo($gzStream)
        $process.WaitForExit()
        $exportExitCode = $process.ExitCode

        $gzStream.Close()
        $fileStream.Close()

        if ($exportExitCode -ne 0) {
            Write-Err "docker save failed with exit code: $exportExitCode"
            if (Test-Path $OutputFile) { Remove-Item $OutputFile -Force }
            exit $exportExitCode
        }
    }
    finally {
        if ($gzStream)  { $gzStream.Dispose() }
        if ($fileStream) { $fileStream.Dispose() }
        if ($process)    { $process.Dispose() }
    }
} else {
    & docker save $ImageSpec -o $OutputFile
    $exportExitCode = $LASTEXITCODE

    if ($exportExitCode -ne 0) {
        Write-Err "docker save failed with exit code: $exportExitCode"
        exit $exportExitCode
    }
}

$exportEnd = Get-Date
$exportDuration = $exportEnd - $exportStart
$exportMin = [math]::Floor($exportDuration.TotalMinutes)
$exportSec = $exportDuration.Seconds

if (-not (Test-Path $OutputFile)) {
    Write-Err "Export failed: output file not created"
    exit 1
}

$fileInfo = Get-Item $OutputFile
$fileSizeMB = [math]::Round($fileInfo.Length / 1MB)
$fileSizeGB = [math]::Round($fileSizeMB / 1024, 2)

Write-Host ""
Write-Ok "Export complete!"
Write-Kv "Output file" $OutputFile
Write-Kv "File size"   "${fileSizeMB} MB (${fileSizeGB} GB)"
Write-Kv "Duration"    "${exportMin}m ${exportSec}s"

# ---------------------------------------------------------------------------
# SHA256 Checksum
# ---------------------------------------------------------------------------
$ChecksumFile = "${OutputFile}.sha256"

if (-not $NoChecksum) {
    Write-Section "Checksum"
    Write-Info "Computing SHA256..."
    $hash = (Get-FileHash -Path $OutputFile -Algorithm SHA256).Hash.ToLower()
    $fileName = Split-Path $OutputFile -Leaf
    "$hash  $fileName" | Out-File -FilePath $ChecksumFile -Encoding ASCII -NoNewline
    Write-Ok "SHA256: $hash"
    Write-Ok "Checksum saved to: $ChecksumFile"
}

# ---------------------------------------------------------------------------
# Customer instructions
# ---------------------------------------------------------------------------
$totalDuration = (Get-Date) - $buildStart
$totalMin = [math]::Floor($totalDuration.TotalMinutes)
$totalSec = $totalDuration.Seconds

Write-Section "Summary"
Write-Kv "Total time" "${totalMin}m ${totalSec}s"
Write-Kv "Image"      $ImageSpec
Write-Kv "Tarball"    $OutputFile
if (-not $NoChecksum) {
    Write-Kv "Checksum" $ChecksumFile
}

Write-Host ""
Write-Section "Customer Instructions"
Write-Host ""
Write-Host "  Send these files to the customer:" -ForegroundColor White
Write-Host "    1. $OutputFile"
if (-not $NoChecksum) {
    Write-Host "    2. $ChecksumFile"
}
Write-Host ""
Write-Host "  Customer quick start:" -ForegroundColor White
Write-Host "    1. Load image:   docker load -i $(Split-Path $OutputFile -Leaf)"
if (-not $NoChecksum) {
    Write-Host "       (verify:      Get-FileHash -Algorithm SHA256 $((Split-Path $OutputFile -Leaf))  # PowerShell)"
    Write-Host "       (or:          sha256sum -c $((Split-Path $ChecksumFile -Leaf))              # Linux/WSL)"
}
Write-Host "    2. Run:"
Write-Host "       docker run -d -p 8888:8888 -p 2222:22 --name caffe $ImageSpec"
Write-Host "    3. Jupyter:     http://localhost:8888/  (token: caffe-token)"
Write-Host "    4. SSH:         ssh builder@localhost -p 2222  (password: caffepass)"
Write-Host "    5. Verify:      docker exec caffe caffe-verify"
Write-Host ""
Write-Ok "Build & export finished!"
