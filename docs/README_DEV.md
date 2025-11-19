# Development Server Setup

## Why You Need to Clear Cache

Python caches imported modules and bytecode, which can cause issues when:
- Code changes aren't detected by the reloader
- Multiple Python processes are running
- Windows file system watching is unreliable

## Quick Restart Options

### Option 1: Use the PowerShell Script (Easiest)
```powershell
.\restart_server.ps1
```

### Option 2: Use the Python Dev Server
```powershell
python dev_server.py
```
This automatically clears cache before starting.

### Option 3: Manual (Current Method)
```powershell
taskkill /F /IM python.exe
Get-ChildItem -Path . -Include __pycache__,*.pyc -Recurse -Force | Remove-Item -Force -Recurse
python -m uvicorn app.main:app --reload --port 8000
```

## Better Reload with watchfiles

The `uvicorn[standard]` package includes `watchfiles`, which is more reliable on Windows:

```powershell
python -m uvicorn app.main:app --reload --reload-engine watchfiles --port 8000
```

## Tips to Reduce Cache Issues

1. **Use the restart script** - It's faster than manual steps
2. **Close unused Python processes** - Multiple processes can interfere
3. **Use watchfiles reloader** - More reliable than default on Windows
4. **Restart after major refactors** - Some changes require a full restart

## When You MUST Restart

- After changing imports or module structure
- After adding new files
- When the reloader seems "stuck"
- After dependency changes

