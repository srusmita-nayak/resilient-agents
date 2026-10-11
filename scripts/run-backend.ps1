# Launch script for FastAPI backend on Windows PowerShell
$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $PSScriptRoot
$BackendDir = Join-Path $RootDir "backend"
$PythonExe = Join-Path $RootDir ".venv\Scripts\python.exe"

if (-not (Test-Path $PythonExe)) {
    Write-Error "Virtual environment python not found at $PythonExe. Please run .\scripts\setup.ps1 first."
}

Write-Host "=== Starting Resilient Agents Backend Server ===" -ForegroundColor Cyan
Write-Host "URL: http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "API Documentation: http://127.0.0.1:8000/docs" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop." -ForegroundColor Yellow

$env:PYTHONPATH = $BackendDir
& $PythonExe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
