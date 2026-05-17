# PowerShell script to start the unified backend system

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Starting Beauty Shop Backend System" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Get the current directory
$projectRoot = Get-Location

# Start Backend API with integrated LangGraph (Port 8000)
Write-Host "Starting Backend API (with integrated LangGraph) on port 8000..." -ForegroundColor Green
Write-Host ""

Push-Location "$projectRoot\backend"
uvicorn app.main:app --reload --port 8000
Pop-Location

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Backend stopped" -ForegroundColor Yellow
Write-Host "=======================================" -ForegroundColor Cyan
