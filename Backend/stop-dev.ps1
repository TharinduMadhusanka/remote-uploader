# Stop all development services
# Usage: .\stop-dev.ps1

Write-Host "Stopping Remote Uploader Development Environment..." -ForegroundColor Red

# Stop Redis in WSL
Write-Host "`nStopping Redis..." -ForegroundColor Cyan
wsl pkill redis-server

# Stop Uvicorn (Web Server)
Write-Host "Stopping Web Server..." -ForegroundColor Cyan
Get-Process | Where-Object {$_.CommandLine -like "*uvicorn*"} | Stop-Process -Force

# Stop Celery Worker
Write-Host "Stopping Celery Worker..." -ForegroundColor Cyan
Get-Process | Where-Object {$_.CommandLine -like "*celery*"} | Stop-Process -Force

Write-Host "`nAll services stopped!" -ForegroundColor Green
