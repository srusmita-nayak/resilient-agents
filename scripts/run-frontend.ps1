# Launch script for Vite React frontend dev server
$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $PSScriptRoot
$FrontendDir = Join-Path $RootDir "frontend"

Write-Host "=== Starting Resilient Agents Frontend Dev Server ===" -ForegroundColor Cyan
Write-Host "URL: http://127.0.0.1:5173" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop." -ForegroundColor Yellow

Push-Location $FrontendDir
try {
    npm run dev
} finally {
    Pop-Location
}
