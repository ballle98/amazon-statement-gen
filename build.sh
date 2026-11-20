#!/bin/bash
# Build script to create standalone executable on Linux
# This creates a single executable file that includes all dependencies

set -e

echo "Building standalone executable..."
echo "This may take a few minutes..."

# Ensure we're in a virtual environment with all dependencies
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Running install.sh first..."
    ./install.sh
fi

source venv/bin/activate

# Install PyInstaller if not already installed
pip install pyinstaller

# Build the executable
pyinstaller --onefile --name asgen asgen.py

echo "Build complete!"
echo "Executable created: dist/asgen ($(du -h dist/asgen | cut -f1))"
echo "You can now run ./dist/asgen directly without any installation!"
