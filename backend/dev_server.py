#!/usr/bin/env python
"""Development server with better reload handling."""

import os
import sys


def clear_cache():
    """Clear Python cache before starting."""
    if sys.platform == "win32":
        import subprocess

        try:
            subprocess.run(
                [
                    "powershell",
                    "-Command",
                    (
                        "Get-ChildItem -Path . -Include __pycache__,*.pyc -Recurse -Force "
                        "| Remove-Item -Force -Recurse"
                    ),
                ],
                cwd=os.path.dirname(__file__),
                shell=True,
                check=False,  # Don't fail if cache clearing fails
                timeout=10,  # Prevent hanging
            )
        except Exception:
            # Ignore errors in cache clearing - not critical
            pass
    else:
        import shutil

        for root, dirs, files in os.walk(os.path.dirname(__file__)):
            if "__pycache__" in dirs:
                try:
                    shutil.rmtree(os.path.join(root, "__pycache__"))
                except Exception:
                    pass
            for file in files:
                if file.endswith(".pyc"):
                    try:
                        os.remove(os.path.join(root, file))
                    except Exception:
                        pass


# Now start uvicorn with better reload settings
if __name__ == "__main__":
    # Only clear cache when running as main script, not when imported by uvicorn reload
    clear_cache()
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_dirs=["app"],  # Only watch app directory
        reload_includes=["*.py"],  # Only watch Python files
        reload_excludes=["__pycache__", "*.pyc"],  # Exclude cache files
    )
