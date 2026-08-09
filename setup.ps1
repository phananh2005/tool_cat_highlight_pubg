#!/usr/bin/env pwsh
# Script setup hoàn chỉnh cho PUBG Highlight Cutter

param(
    [switch]$SkipFFmpeg = $false,
    [switch]$SkipPython = $false
)

$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "PUBG Highlight Cutter - Setup Toàn Bộ" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# === Kiểm tra Python ===
Write-Host "1. Kiểm tra Python..." -ForegroundColor Yellow
try {
    $pythonVersion = & python --version 2>&1
    Write-Host "✓ $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Python không tìm thấy" -ForegroundColor Red
    Write-Host "  Cài từ: https://www.python.org/" -ForegroundColor Yellow
    exit 1
}

# === Cài Python packages ===
if (-not $SkipPython) {
    Write-Host ""
    Write-Host "2. Cài đặt Python packages..." -ForegroundColor Yellow
    
    Write-Host "  - Nâng cấp pip..." -ForegroundColor Gray
    & python -m pip install --upgrade pip -q
    
    Write-Host "  - Cài packages từ requirements.txt..." -ForegroundColor Gray
    $requirementsFile = Join-Path $PSScriptRoot "requirements.txt"
    if (Test-Path $requirementsFile) {
        & python -m pip install -r $requirementsFile -q
        Write-Host "✓ Packages đã cài" -ForegroundColor Green
    } else {
        Write-Host "✗ requirements.txt không tìm thấy" -ForegroundColor Red
        exit 1
    }
}

# === Kiểm tra FFmpeg ===
Write-Host ""
Write-Host "3. Kiểm tra FFmpeg..." -ForegroundColor Yellow
$ffmpegFound = $false
try {
    $ffmpegVersion = & ffmpeg -version 2>&1 | Select-Object -First 1
    Write-Host "✓ $ffmpegVersion" -ForegroundColor Green
    $ffmpegFound = $true
} catch {
    Write-Host "✗ FFmpeg không tìm thấy" -ForegroundColor Red
}

if (-not $ffmpegFound -and -not $SkipFFmpeg) {
    Write-Host ""
    Write-Host "  Hướng dẫn cài FFmpeg:" -ForegroundColor Yellow
    Write-Host "  1. Tải: https://www.gyan.dev/ffmpeg/builds/" -ForegroundColor Gray
    Write-Host "  2. Chọn: ffmpeg-9.0-essentials.zip" -ForegroundColor Gray
    Write-Host "  3. Giải nén vào: C:\ffmpeg\" -ForegroundColor Gray
    Write-Host "  4. Thêm C:\ffmpeg\bin vào PATH" -ForegroundColor Gray
    Write-Host "  5. Restart terminal/IDE" -ForegroundColor Gray
}

# === Kiểm tra dependencies ===
Write-Host ""
Write-Host "4. Chạy kiểm tra hoàn chỉnh..." -ForegroundColor Yellow
$setupCheckFile = Join-Path $PSScriptRoot "setup_check.py"
if (Test-Path $setupCheckFile) {
    & python $setupCheckFile
} else {
    Write-Host "✗ setup_check.py không tìm thấy" -ForegroundColor Red
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Setup hoàn tất!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Để chạy ứng dụng:" -ForegroundColor Yellow
Write-Host "  python main.py" -ForegroundColor White
Write-Host "  hoặc" -ForegroundColor Gray
Write-Host "  .\start.bat" -ForegroundColor White
Write-Host ""
