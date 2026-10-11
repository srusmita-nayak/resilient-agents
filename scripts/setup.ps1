# Setup script for Resilient Agents Platform on Windows PowerShell
$ErrorActionPreference = "Stop"

Write-Host "=== Setting up Resilient Agents Research Platform ===" -ForegroundColor Cyan

# 1. Root & paths
$RootDir = Split-Path -Parent $PSScriptRoot
$BackendDir = Join-Path $RootDir "backend"
$FrontendDir = Join-Path $RootDir "frontend"
$VenvDir = Join-Path $RootDir ".venv"

# 2. Check Python & Node
Write-Host "--> Checking Python and Node versions..." -ForegroundColor Yellow
python --version
node --version
npm --version

# 3. Copy .env if missing
$EnvFile = Join-Path $RootDir ".env"
$EnvExample = Join-Path $RootDir ".env.example"
if (-not (Test-Path $EnvFile)) {
    Write-Host "--> Creating .env from .env.example..." -ForegroundColor Yellow
    Copy-Item $EnvExample $EnvFile
}

# 4. Create virtual environment
if (-not (Test-Path $VenvDir)) {
    Write-Host "--> Creating Python virtual environment at .venv..." -ForegroundColor Yellow
    python -m venv $VenvDir
}

# 5. Install backend dependencies
$PythonExe = Join-Path $VenvDir "Scripts\python.exe"
Write-Host "--> Installing backend Python dependencies..." -ForegroundColor Yellow
& $PythonExe -m pip install --upgrade pip
& $PythonExe -m pip install -r (Join-Path $BackendDir "requirements-dev.txt")

# 6. Install frontend dependencies
Write-Host "--> Installing frontend dependencies via npm..." -ForegroundColor Yellow
Push-Location $FrontendDir
try {
    npm install
} finally {
    Pop-Location
}

Write-Host "=== Setup Completed Successfully! ===" -ForegroundColor Green
Write-Host "To launch backend:  .\scripts\run-backend.ps1"
Write-Host "To launch frontend: .\scripts\run-frontend.ps1"
Write-Host "To run all tests:   .\scripts\run-tests.ps1"
