#!/bin/bash
# Start Backend Server
echo "🚀 Starting Backend Server..."
cd "$(dirname "$0")/../../backend"
python dev_server.py

