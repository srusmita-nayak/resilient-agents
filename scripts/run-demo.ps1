# Demo launcher: starts backend, verifies health, starts frontend, opens browser
$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $RootDir ".venv\Scripts\python.exe"
$FrontendDir = Join-Path $RootDir "frontend"

Write-Host "=== Launching Resilient Agents Live Demo ===" -ForegroundColor Cyan

# 1. Start backend process
Write-Host "--> Launching backend on http://127.0.0.1:8000..." -ForegroundColor Yellow
$BackendProc = Start-Process -FilePath $PythonExe -ArgumentList "-m uvicorn app.main:app --host 127.0.0.1 --port 8000" -WorkingDirectory (Join-Path $RootDir "backend") -PassThru

# 2. Poll /api/health until responsive
Write-Host "--> Waiting for backend health check..." -ForegroundColor Yellow
$Healthy = $false
for ($i = 0; $i -lt 20; $i++) {
    try {
        $resp = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/health" -Method Get -TimeoutSec 2
        if ($resp.status -eq "healthy") {
            $Healthy = $true
            break
        }
    } catch {
        Start-Sleep -Seconds 1
    }
}

if (-not $Healthy) {
    Stop-Process -Id $BackendProc.Id -Force
    Write-Error "Backend failed to become healthy within 20 seconds."
}

Write-Host "--> Backend is healthy! Starting frontend on http://localhost:5173..." -ForegroundColor Green
$FrontendProc = Start-Process -FilePath "cmd.exe" -ArgumentList "/c npm run dev" -WorkingDirectory $FrontendDir -PassThru

Start-Sleep -Seconds 3
Write-Host "--> Opening browser at http://localhost:5173..." -ForegroundColor Green
Start-Process "http://localhost:5173"

Write-Host "`nDemo is running! Press enter in this window to stop both servers." -ForegroundColor Cyan
Read-Host
Stop-Process -Id $BackendProc.Id -Force -ErrorAction SilentlyContinue
Stop-Process -Id $FrontendProc.Id -Force -ErrorAction SilentlyContinue
Write-Host "Servers stopped." -ForegroundColor Yellow
