# Scripts Directory

This directory contains utility scripts for development and deployment.

## Structure

```
scripts/
├── backend/
│   ├── start.ps1      # Start backend server (Windows)
│   ├── start.sh       # Start backend server (Linux/Mac)
│   └── restart.ps1    # Restart backend server with cache cleanup (Windows)
├── frontend/
│   ├── start.ps1      # Start frontend server (Windows)
│   └── start.sh       # Start frontend server (Linux/Mac)
├── cleanup.ps1        # Cleanup script (Windows)
└── cleanup.sh         # Cleanup script (Linux/Mac)
```

## Usage

### Starting Services

**Backend (Windows):**
```powershell
.\scripts\backend\start.ps1
```

**Backend (Linux/Mac):**
```bash
./scripts/backend/start.sh
```

**Frontend (Windows):**
```powershell
.\scripts\frontend\start.ps1
```

**Frontend (Linux/Mac):**
```bash
./scripts/frontend/start.sh
```

### Restarting Backend

**Windows:**
```powershell
.\scripts\backend\restart.ps1
```

This will:
1. Stop all Python processes
2. Clear Python cache (`__pycache__`, `*.pyc`)
3. Start a fresh server on port 8000

### Cleanup

**Windows:**
```powershell
.\scripts\cleanup.ps1
```

**Linux/Mac:**
```bash
./scripts/cleanup.sh
```

This will:
1. Kill Python/uvicorn processes
2. Kill Node.js/Next.js processes
3. Clean Python cache (`__pycache__`, `*.pyc`)
4. Clean Next.js cache (`.next` directory)
5. Clean node_modules cache

## Notes

- All scripts should be run from the project root directory
- Scripts automatically navigate to the correct directories
- Make sure you have the required dependencies installed before running

