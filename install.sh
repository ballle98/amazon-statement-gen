#!/bin/bash
# Installation script for amazon-statement-gen on Linux
# This script handles the Pillow dependency issue with amazoncaptcha

set -e

echo "Creating virtual environment..."
python3 -m venv venv

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing dependencies first..."
pip install click requests beautifulsoup4 PyYAML python-dateutil pyotp pillow

echo "Installing amazoncaptcha without dependencies..."
pip install amazoncaptcha --no-deps

echo "Installing amazon-orders without dependencies..."
pip install amazon-orders --no-deps

echo "Installation complete!"
echo "To use: source venv/bin/activate then python3 asgen.py [options]"
