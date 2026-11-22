#!/bin/bash
# Installation script for amazon-statement-gen on Linux

set -e

PYTHON_BIN="${PYTHON_BIN:-python3}"

echo "Checking Python version..."
"$PYTHON_BIN" -c 'import sys; sys.exit(0) if sys.version_info >= (3, 12) else sys.exit("Python 3.12 or newer is required")'

echo "Creating virtual environment..."
"$PYTHON_BIN" -m venv venv

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Installation complete!"
echo "To use: source venv/bin/activate then python3 asgen.py [options]"
