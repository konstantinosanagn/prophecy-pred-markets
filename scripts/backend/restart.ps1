# PowerShell script to clean restart the server
Write-Host "Stopping all Python processes..." -ForegroundColor Yellow
taskkill /F /IM python.exe 2>$null
Start-Sleep -Seconds 2

Write-Host "Clearing Python cache..." -ForegroundColor Yellow
Get-ChildItem -Path ..\..\backend -Include __pycache__,*.pyc -Recurse -Force | Remove-Item -Force -Recurse

Write-Host "Starting fresh server..." -ForegroundColor Green
Set-Location ..\..\backend
python -m uvicorn app.main:app --reload --port 8000

