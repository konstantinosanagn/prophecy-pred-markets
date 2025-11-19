# Cleanup script for Windows PowerShell
# Cleans Python cache, Next.js cache, and kills running processes

Write-Host "Starting cleanup..." -ForegroundColor Cyan

# Kill Python processes (backend)
Write-Host "`nKilling Python/uvicorn processes..." -ForegroundColor Yellow
Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*uvicorn*" -or $_.CommandLine -like "*dev_server*" } | Stop-Process -Force -ErrorAction SilentlyContinue
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1

# Kill Node.js processes (frontend)
Write-Host "Killing Node.js/Next.js processes..." -ForegroundColor Yellow
Get-Process node -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1

# Clean Python cache
Write-Host "`nCleaning Python cache (__pycache__, *.pyc)..." -ForegroundColor Yellow
Get-ChildItem -Path ..\..\ -Include __pycache__,*.pyc -Recurse -Force -ErrorAction SilentlyContinue | Remove-Item -Force -Recurse -ErrorAction SilentlyContinue
Write-Host "Python cache cleaned" -ForegroundColor Green

# Clean Next.js cache
Write-Host "`nCleaning Next.js cache (.next)..." -ForegroundColor Yellow
if (Test-Path "..\..\frontend\.next") {
    Remove-Item -Path "..\..\frontend\.next" -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "Next.js cache cleaned" -ForegroundColor Green
} else {
    Write-Host "No .next directory found" -ForegroundColor Gray
}

# Clean node_modules/.cache if exists
if (Test-Path "..\..\frontend\node_modules\.cache") {
    Remove-Item -Path "..\..\frontend\node_modules\.cache" -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "Node modules cache cleaned" -ForegroundColor Green
}

Write-Host "`nCleanup complete!" -ForegroundColor Green
