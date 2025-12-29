# Start all services for local development
# Usage: .\start-dev.ps1

$ErrorActionPreference = "Stop"
$BACKEND_PATH = "D:\WebDevelopment\Remote Uploader\Backend"

Write-Host "Starting Remote Uploader Development Environment..." -ForegroundColor Green

# 1. Start Redis in WSL (background)
Write-Host "`nStarting Redis in WSL..." -ForegroundColor Cyan
# Start-Process wsl -ArgumentList "redis-server" -WindowStyle Minimized
# jus open the WSL terminal and it automatically starts redis-server
start ubuntu

# Wait for Redis to start
Start-Sleep -Seconds 2

# 2. Start Web Server (new window)
Write-Host "Starting Web Server..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$BACKEND_PATH'; conda activate tensenv; uvicorn web.main:app --host 0.0.0.0 --port 8000 --reload"
) -WindowStyle Normal

# Wait a bit
Start-Sleep -Seconds 2

# 3. Start Celery Worker (new window)
Write-Host "Starting Celery Worker..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit", 
    "-Command",
    "cd '$BACKEND_PATH'; conda activate tensenv; celery -A worker.celery_app worker --loglevel=info --pool=solo"
) -WindowStyle Normal

Write-Host "`nAll services started!" -ForegroundColor Green
Write-Host "   - Redis: WSL" -ForegroundColor White
Write-Host "   - Web API: http://localhost:8000" -ForegroundColor White
Write-Host "   - Celery Worker: Running" -ForegroundColor White
Write-Host "`nTo stop: Run .\stop-dev.ps1" -ForegroundColor Yellow
