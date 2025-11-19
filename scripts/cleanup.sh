#!/bin/bash
# Cleanup script for Git Bash
# Cleans Python cache, Next.js cache, and kills running processes

echo "🧹 Starting cleanup..."

# Kill Python processes (backend)
echo ""
echo "🛑 Killing Python/uvicorn processes..."
pkill -f "uvicorn" 2>/dev/null
pkill -f "dev_server.py" 2>/dev/null
pkill -f "python.*dev_server" 2>/dev/null
sleep 1

# Kill Node.js processes (frontend)
echo "🛑 Killing Node.js/Next.js processes..."
pkill -f "next dev" 2>/dev/null
pkill -f "node.*next" 2>/dev/null
sleep 1

# Clean Python cache
echo ""
echo "🗑️  Cleaning Python cache (__pycache__, *.pyc)..."
cd "$(dirname "$0")/.."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete 2>/dev/null
find . -type f -name "*.pyo" -delete 2>/dev/null
echo "✅ Python cache cleaned"

# Clean Next.js cache
echo ""
echo "🗑️  Cleaning Next.js cache (.next)..."
if [ -d "frontend/.next" ]; then
    rm -rf frontend/.next
    echo "✅ Next.js cache cleaned"
else
    echo "ℹ️  No .next directory found"
fi

# Clean node_modules/.cache if exists
if [ -d "frontend/node_modules/.cache" ]; then
    rm -rf frontend/node_modules/.cache
    echo "✅ Node modules cache cleaned"
fi

echo ""
echo "✨ Cleanup complete!"

