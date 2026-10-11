# Run all tests (backend pytest + frontend vitest)
$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $RootDir ".venv\Scripts\python.exe"
$FrontendDir = Join-Path $RootDir "frontend"

Write-Host "=== Running Resilient Agents Test Suites ===" -ForegroundColor Cyan

# 1. Backend tests
Write-Host "`n--> [1/2] Running Backend Tests (pytest)..." -ForegroundColor Yellow
$env:PYTHONPATH = (Join-Path $RootDir "backend")
& $PythonExe -m pytest -v (Join-Path $RootDir "backend\tests")
if ($LASTEXITCODE -ne 0) {
    Write-Error "Backend tests failed with exit code $LASTEXITCODE"
}

# 2. Frontend tests
Write-Host "`n--> [2/2] Running Frontend Tests (vitest)..." -ForegroundColor Yellow
Push-Location $FrontendDir
try {
    npm test
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Frontend tests failed with exit code $LASTEXITCODE"
    }
} finally {
    Pop-Location
}

Write-Host "`n=== All Test Suites Passed Successfully! ===" -ForegroundColor Green
